from flask import Blueprint, render_template, redirect, request, url_for, flash, jsonify, session
import requests
from datetime import datetime, timedelta
from config import OSU_CLIENT_ID, OSU_CLIENT_SECRET, OSU_CALLBACK_URL, AUTHORIZATION_URL, TOKEN_URL, OSU_API_BASE_URL
from ..data_manager import get_tournament_data, save_tournament_data
from ..bracket_logic import generate_bracket
from .. import api


public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def index():
    return render_template('index.html')


@public_bp.route('/legal')
def legal():
    return render_template('legal.html')


@public_bp.route('/tournament')
def tournament():
    data = get_tournament_data()
    
    now = datetime.utcnow()
    should_refresh = True
    
    # Check if we should refresh based on the last update time
    last_updated_str = data.get('last_updated')
    if last_updated_str:
        try:
            last_updated = datetime.fromisoformat(last_updated_str)
            if last_updated > (now - timedelta(minutes=5)):
                should_refresh = False
        except ValueError:
            print("Invalid timestamp format in tournament data. Forcing refresh.")

    if should_refresh and 'competitors' in data and data['competitors']:
        print("Cache expired or invalid. Refreshing competitor data from osu! API.")
        for competitor in data['competitors']:
            try:
                user_details = api.user(competitor['id'])
                competitor['name'] = user_details.username
                competitor['pp'] = user_details.statistics.pp if user_details.statistics else 0
                competitor['rank'] = user_details.statistics.global_rank if user_details.statistics else 0
                competitor['avatar_url'] = user_details.avatar_url
            except Exception as e:
                print(f"Could not update user {competitor.get('id')}: {e}")
        
        data['last_updated'] = now.isoformat()
        save_tournament_data(data)
    
    return render_template('tournament.html', data=data)


@public_bp.route('/tournament/details')
def tournament_details():
    """Display detailed tournament rules and format information"""
    data = get_tournament_data()
    return render_template('tournament_details.html', data=data)


@public_bp.route('/login/osu')
def osu_login():
    params = {'client_id': OSU_CLIENT_ID, 'redirect_uri': OSU_CALLBACK_URL, 'response_type': 'code', 'scope': 'identify'}
    auth_url = f"{AUTHORIZATION_URL}?{requests.compat.urlencode(params)}"
    return redirect(auth_url)


@public_bp.route('/logout')
def logout():
    from flask import session
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('public.index'))


@public_bp.route('/callback/osu')
def osu_callback():
    code = request.args.get('code')
    token_data = {'client_id': OSU_CLIENT_ID, 'client_secret': OSU_CLIENT_SECRET, 'code': code, 'grant_type': 'authorization_code', 'redirect_uri': OSU_CALLBACK_URL}
    token_response = requests.post(TOKEN_URL, data=token_data)
    access_token = token_response.json().get('access_token')

    headers = {'Authorization': f'Bearer {access_token}'}
    me_response = requests.get(f'{OSU_API_BASE_URL}/me', headers=headers)
    user_json = me_response.json()
    user_id = user_json.get('id')
    
    # Store user session
    from flask import session
    session['user_id'] = user_id
    session['username'] = user_json.get('username')
    session['avatar_url'] = user_json.get('avatar_url')
    
    data = get_tournament_data()
    
    # Check if signups are locked
    if data.get('signups_locked', False):
        flash('Tournament signups are currently closed.', 'error')
        return redirect(url_for('public.tournament'))
    
    # Check if user is already a competitor or has a pending signup
    if any(c.get('id') == user_id for c in data.get('competitors', [])):
        # User is already approved
        pass
    elif any(s.get('id') == user_id for s in data.get('pending_signups', [])):
        # User already has pending signup
        flash('Your signup is pending approval by tournament administrators.', 'info')
        return redirect(url_for('public.tournament'))
    else:
        # Create new pending signup
        new_signup = {
            'id': user_id,
            'name': user_json.get('username'),
            'pp': user_json.get('statistics', {}).get('pp', 0),
            'rank': user_json.get('statistics', {}).get('global_rank', 0),
            'avatar_url': user_json.get('avatar_url'),
            'signup_time': datetime.utcnow().isoformat()
        }
        if 'pending_signups' not in data:
            data['pending_signups'] = []
        data['pending_signups'].append(new_signup)
        save_tournament_data(data)
        flash('Your signup has been submitted and is pending approval by tournament administrators.', 'success')
        return redirect(url_for('public.tournament'))
    
    # Check if user is a tournament participant and redirect accordingly
    if any(c.get('id') == user_id for c in data.get('competitors', [])):
        flash(f'Welcome back, {user_json.get("username")}!', 'success')
        return redirect(url_for('player.profile'))
    else:
        return redirect(url_for('public.tournament'))


@public_bp.route('/user/<int:user_id>')
def user_profile(user_id):
    # Check if user is viewing their own profile and redirect to player profile
    if session.get('user_id') == user_id:
        return redirect(url_for('player.profile'))
    
    try:
        user = api.user(user_id)
        # Get tournament data to show mappool and matches
        data = get_tournament_data()
        
        # Find user in competitors to get additional tournament data
        user_data = None
        for competitor in data.get('competitors', []):
            if competitor.get('id') == user_id:
                user_data = competitor
                break
        
        # Create a user dict that combines API data with tournament data
        user_dict = {
            'id': user.id,
            'username': user.username,
            'avatar_url': user.avatar_url,
            'statistics': user.statistics,
            'placement': user_data.get('placement') if user_data else None,
            'mappool_url': user_data.get('mappool_url') if user_data else None,
            'mappool_ids': user_data.get('mappool_ids') if user_data else None,
            'mappool_details': user_data.get('mappool_details') if user_data else None,
            'mappool_uploaded': user_data.get('mappool_uploaded') if user_data else None
        }
        
        return render_template('user_profile.html', user=user_dict, data=data)
    except Exception as e:
        flash(f'Could not find or load user with ID {user_id}. Error: {e}', 'error')
        print(f"Error loading user profile: {e}")
        return redirect(url_for('public.tournament'))


@public_bp.route('/match/<string:match_id>')
def match_details(match_id):
    """Display detailed match results including map-by-map breakdown"""
    data = get_tournament_data()
    
    # Find the match across all brackets
    target_match = None
    for bracket_type in ['upper', 'lower', 'grand_finals']:
        if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
            if bracket_type == 'grand_finals':
                match = data['brackets'][bracket_type]
                if isinstance(match, dict) and match.get('id') == match_id:
                    target_match = match
                    break
                if match.get('previous_gf') and match['previous_gf'].get('id') == match_id:
                    target_match = match['previous_gf']
                    break
            else:
                for round_matches in data['brackets'][bracket_type]:
                    for match in round_matches:
                        if match.get('id') == match_id:
                            target_match = match
                            break
                    if target_match:
                        break
            if target_match:
                break
    
    if not target_match:
        flash('Match not found.', 'error')
        return redirect(url_for('public.tournament'))
    
    detailed_results = target_match.get('detailed_results')
    
    return render_template('match_details.html', 
                         match=target_match, 
                         detailed_results=detailed_results,
                         data=data)


@public_bp.route('/overlay')
def tournament_overlay():
    """Serve the tournament overlay for streaming"""
    return render_template('streaming/tourney_overlay.html')

# API Routes for HTTP polling (Namecheap compatible)
@public_bp.route('/api/match-data')
def get_match_data():
    """Get current match data for overlay polling"""
    try:
        from ..http_events import get_current_match_data
        match_data = get_current_match_data()
        
        # Add timestamp for cache busting
        data = get_tournament_data()
        match_data['last_updated'] = data.get('last_updated', '')
        
        return jsonify(match_data)
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'match_found': False
        }), 500

@public_bp.route('/api/overlay-events')
def get_overlay_events():
    """Get overlay events (victory screens, AFK status, etc.)"""
    try:
        from ..overlay_state import get_overlay_state
        state = get_overlay_state()
        
        return jsonify({
            'events': state.get('events', []),
            'afk_mode': state.get('afk_mode', False),
            'victory_screen_hidden': state.get('victory_screen_hidden', False),
            'timestamp': state.get('last_updated', '')
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'events': []
        }), 500

@public_bp.route('/api/match-interface-state')
def get_match_interface_state():
    """Get current match interface state for streaming overlay"""
    try:
        from ..http_events import get_current_match_data
        match_data = get_current_match_data()
        
        if not match_data.get('match_found'):
            return jsonify({
                'match_found': False,
                'message': 'No active match found'
            })
        
        # Get the full tournament data to access match_state
        data = get_tournament_data()
        current_match = None
        
        # Find the current match in the bracket structure
        if 'grand_finals' in data.get('brackets', {}):
            match = data['brackets']['grand_finals']
            if match and match.get('status') in ['in_progress', 'next_up']:
                current_match = match
        
        if not current_match and 'upper' in data.get('brackets', {}):
            for round_matches in data['brackets']['upper']:
                for match in round_matches:
                    if match and match.get('status') in ['in_progress', 'next_up']:
                        current_match = match
                        break
                if current_match:
                    break
        
        if not current_match and 'lower' in data.get('brackets', {}):
            for round_matches in data['brackets']['lower']:
                for match in round_matches:
                    if match and match.get('status') in ['in_progress', 'next_up']:
                        current_match = match
                        break
                if current_match:
                    break
        
        if not current_match:
            return jsonify({
                'match_found': False,
                'message': 'Current match not found in brackets'
            })
        
        # Extract match interface data
        match_state = current_match.get('match_state', {})
        
        # Get mappool details from both players
        player1_mappool = current_match.get('player1', {}).get('mappool_details', [])
        player2_mappool = current_match.get('player2', {}).get('mappool_details', [])
        combined_mappool = player1_mappool + player2_mappool
        
        # Calculate interface lock status
        picked_maps = match_state.get('picked_maps', [])
        current_score = current_match.get('score_p1', 0) + current_match.get('score_p2', 0)
        is_interface_locked = len(picked_maps) > 0 and current_score < len(picked_maps)
        
        # Debug logging
        print(f"Match interface API debug:")
        print(f"  Current match ID: {current_match.get('id', 'no-id')}")
        print(f"  Player1 mappool count: {len(player1_mappool)}")
        print(f"  Player2 mappool count: {len(player2_mappool)}")
        print(f"  Combined mappool count: {len(combined_mappool)}")
        print(f"  Picked maps count: {len(picked_maps)}")
        print(f"  Current score total: {current_score}")
        print(f"  Interface locked: {is_interface_locked}")
        
        return jsonify({
            'match_found': True,
            'player1': current_match.get('player1', {}),
            'player2': current_match.get('player2', {}),
            'score_p1': current_match.get('score_p1', 0),
            'score_p2': current_match.get('score_p2', 0),
            'phase': match_state.get('phase', 'waiting'),
            'current_turn': match_state.get('current_turn', ''),
            'first_player': match_state.get('first_player', ''),
            'banned_maps': match_state.get('banned_maps', []),
            'picked_maps': picked_maps,
            'abilities_used': match_state.get('abilities_used', {}),
            'mappool': combined_mappool,
            'action_log': match_state.get('action_log', []),
            'interface_locked': is_interface_locked,
            'tiebreaker_map_url': current_match.get('tiebreaker_map_url'),
            'is_tiebreaker': current_match.get('score_p1', 0) == 3 and current_match.get('score_p2', 0) == 3,
            'timestamp': data.get('last_updated', '')
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'match_found': False
        }), 500


@public_bp.route('/api/user/<int:user_id>')
def api_get_user(user_id):
    """Simple API endpoint to get user information"""
    try:
        user = api.user(user_id)
        return jsonify({
            'id': user.id,
            'username': user.username,
            'avatar_url': user.avatar_url,
            'country_code': user.country_code
        })
    except Exception as e:
        return jsonify({
            'error': 'User not found',
            'id': user_id
        }), 404