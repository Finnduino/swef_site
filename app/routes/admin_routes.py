from flask import Blueprint, render_template, redirect, request, url_for, session, flash
import requests
from functools import wraps
from config import OSU_CLIENT_ID, OSU_CLIENT_SECRET, ADMIN_REDIRECT_URI, AUTHORIZATION_URL, TOKEN_URL, OSU_API_BASE_URL, ADMIN_OSU_ID
from ..data_manager import get_tournament_data, save_tournament_data
from ..bracket_logic import generate_bracket
from ..services.match_service import MatchService
from ..services.seeding_service import SeedingService
from ..services.streaming_service import StreamingService
from .. import api

# Import broadcast functions that use overlay state instead of SocketIO
from ..http_events import broadcast_match_update, broadcast_match_victory, broadcast_map_victory, broadcast_exit_afk, broadcast_flip_players

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login')
def admin_login():
    params = {'client_id': OSU_CLIENT_ID, 'redirect_uri': ADMIN_REDIRECT_URI, 'response_type': 'code', 'scope': 'identify'}
    auth_url = f"{AUTHORIZATION_URL}?{requests.compat.urlencode(params)}"
    return redirect(auth_url)


@admin_bp.route('/callback')
def admin_callback():
    code = request.args.get('code')
    token_data = {'client_id': OSU_CLIENT_ID, 'client_secret': OSU_CLIENT_SECRET, 'code': code, 'grant_type': 'authorization_code', 'redirect_uri': ADMIN_REDIRECT_URI}
    token_response = requests.post(TOKEN_URL, data=token_data)
    access_token = token_response.json().get('access_token')
    
    headers = {'Authorization': f'Bearer {access_token}'}
    me_response = requests.get(f'{OSU_API_BASE_URL}/me', headers=headers)
    user_id = str(me_response.json().get('id'))

    if user_id in ADMIN_OSU_ID:
        session['is_admin'] = True
        return redirect(url_for('admin.admin_panel'))
    return "Access Denied.", 403


@admin_bp.route('/')
@admin_required
def admin_panel():
    data = get_tournament_data()
    return render_template('admin.html', data=data)


# Competitor management routes
@admin_bp.route('/add_competitor', methods=['POST'])
@admin_required
def add_competitor():
    username = request.form.get('username')
    if not username:
        flash('Username cannot be empty.', 'error')
        return redirect(url_for('admin.admin_panel'))

    try:
        user = api.user(username)
        
        data = get_tournament_data()
        if any(c.get('id') == user.id for c in data.get('competitors', [])):
            flash(f'User "{user.username}" is already registered.', 'info')
            return redirect(url_for('admin.admin_panel'))

        new_competitor = {
            'id': user.id,
            'name': user.username,
            'pp': user.statistics.pp if user.statistics else 0,
            'avatar_url': user.avatar_url
        }
        data['competitors'].append(new_competitor)
        save_tournament_data(data)
        generate_bracket()
        flash(f'Successfully added "{user.username}" to the tournament.', 'success')

    except Exception as e:
        if e.__class__.__name__ == 'UserNotFound':
            flash(f'User "{username}" not found.', 'error')
        else:
            flash(f'An unexpected error occurred: {e}', 'error')
    
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/remove/<int:user_id>', methods=['POST'])
@admin_required
def remove_competitor(user_id):
    data = get_tournament_data()
    data['competitors'] = [c for c in data.get('competitors', []) if c.get('id') != user_id]
    save_tournament_data(data)
    generate_bracket()
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/reset_competitors', methods=['POST'])
@admin_required
def reset_competitors():
    data = get_tournament_data()
    data['competitors'] = []
    data['brackets'] = {'upper': [], 'lower': []}
    save_tournament_data(data)
    flash('All competitors have been removed and the tournament has been reset.', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/reset_bracket', methods=['POST'])
@admin_required
def reset_bracket():
    data = get_tournament_data()
    
    # Preserve only competitors with their placements, streaming settings, and seeding data
    preserved_data = {
        'competitors': data.get('competitors', []),
        'twitch_channel': data.get('twitch_channel', ''),
        'stream_live': data.get('stream_live', False),
        'seeding_playlist_url': data.get('seeding_playlist_url', None)
    }
    
    # Clear all match/bracket related data
    preserved_data.update({
        'brackets': {'upper': [], 'lower': []},
        'eliminated': [],
        'pending_upper_losers': [],
        'last_updated': None
    })
    
    # Save the reset data and regenerate bracket
    save_tournament_data(preserved_data)
    generate_bracket()
    flash('Bracket reset successfully. All match progress cleared while preserving competitors and seeds.', 'success')
    return redirect(url_for('admin.admin_panel'))


# Match management routes
@admin_bp.route('/start_match', methods=['POST'])
@admin_required
def start_match():
    match_id = request.form.get('match_id')
    match_service = MatchService()
    
    if match_service.start_match(match_id):
        # Broadcast match update to overlay
        broadcast_match_update()
        
        # Exit AFK screen to show the active match
        broadcast_exit_afk()
        
        flash('Match started! Overlay automatically updated.', 'success')
    else:
        flash('Match not found.', 'error')
    
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/reset_match', methods=['POST'])
@admin_required
def reset_match():
    match_id = request.form.get('match_id')
    match_service = MatchService()
    
    if match_service.reset_match(match_id):
        # Broadcast match update to overlay
        broadcast_match_update()
        
        # Exit AFK screen to show the reset match
        broadcast_exit_afk()
        
        flash('Match reset to "Next Up" status. Overlay updated.', 'success')
    else:
        flash('Match not found.', 'error')
    
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/set_match_room', methods=['POST'])
@admin_required
def set_match_room():
    match_id = request.form.get('match_id')
    mp_room_url = request.form.get('mp_room_url', '').strip()
    action = request.form.get('action', 'set')
    
    match_service = MatchService()
    # Always set the room URL
    set_result = match_service.set_match_room(match_id, mp_room_url)
    # If combined action, start the match after setting room
    if action == 'set_and_start' and set_result.get('type') == 'success':
        start_result = match_service.start_match(match_id)
        if start_result:
            # Broadcast updates to overlay
            broadcast_match_update()
            broadcast_exit_afk()
            flash('Room set and match started! Overlay updated.', 'success')
        else:
            flash('Room set, but failed to start match.', 'error')
    else:
        flash(set_result.get('message', 'Room updated.'), set_result.get('type', 'info'))
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/set_score', methods=['POST'])
@admin_required
def set_score():
    match_id = request.form.get('match_id')
    score_p1 = request.form.get('score_p1', 0)
    score_p2 = request.form.get('score_p2', 0)
    mp_room_url = request.form.get('mp_room_url', '').strip()
    
    match_service = MatchService()
    result = match_service.set_match_score(match_id, score_p1, score_p2, mp_room_url)
    
    # Broadcast match update to overlay
    broadcast_match_update()
    
    # Check if this was a map win (score increased by 1)
    if result.get('type') == 'success':
        try:
            data = get_tournament_data()
            # Find the match to check if it's completed
            current_match = None
            for bracket_type in ['upper', 'lower', 'grand_finals']:
                if bracket_type in data.get('brackets', {}):
                    if bracket_type == 'grand_finals':
                        match = data['brackets'][bracket_type]
                        if match and match.get('id') == match_id:
                            current_match = match
                            break
                    else:
                        for round_matches in data['brackets'][bracket_type]:
                            for match in round_matches:
                                if match and match.get('id') == match_id:
                                    current_match = match
                                    break
                            if current_match:
                                break
                if current_match:
                    break
            
            # Check if match is complete (Best of 7 = first to 4)
            if current_match:
                p1_score = int(current_match.get('score_p1', 0))
                p2_score = int(current_match.get('score_p2', 0))
                
                if p1_score >= 4 or p2_score >= 4:
                    # Match is complete - broadcast match victory
                    winner = current_match.get('player1', {}) if p1_score > p2_score else current_match.get('player2', {})
                    final_score = f"{p1_score}-{p2_score}"
                    broadcast_match_victory(winner.get('name', 'Winner'), final_score, "Advances to next round")
        except (KeyError, AttributeError, TypeError):
            pass  # Continue without broadcasting if there's an error
    
    flash(result['message'], result['type'])
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/set_winner', methods=['POST'])
@admin_required
def set_winner():
    match_id = request.form.get('match_id')
    winner_id = request.form.get('winner_id')
    
    match_service = MatchService()
    result = match_service.set_winner(match_id, winner_id)
    
    # Broadcast match update and victory
    broadcast_match_update()
    
    if result.get('type') == 'success':
        try:
            data = get_tournament_data()
            # Find the match to get winner info
            current_match = None
            for bracket_type in ['upper', 'lower', 'grand_finals']:
                if bracket_type in data.get('brackets', {}):
                    if bracket_type == 'grand_finals':
                        match = data['brackets'][bracket_type]
                        if match and match.get('id') == match_id:
                            current_match = match
                            break
                    else:
                        for round_matches in data['brackets'][bracket_type]:
                            for match in round_matches:
                                if match and match.get('id') == match_id:
                                    current_match = match
                                    break
                            if current_match:
                                break
                if current_match:
                    break
            
            if current_match:
                winner = current_match.get('winner', {})
                final_score = f"{current_match.get('score_p1', 0)}-{current_match.get('score_p2', 0)}"
                broadcast_match_victory(winner.get('name', 'Winner'), final_score, "Advances to next round")
        except (KeyError, AttributeError, TypeError):
            pass  # Continue without broadcasting if there's an error
    
    flash(result['message'], result['type'])
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/refresh_match_scores', methods=['POST'])
@admin_required
def refresh_match_scores():
    match_id = request.form.get('match_id')
    
    match_service = MatchService()
    result = match_service.refresh_match_scores(match_id)
    
    flash(result['message'], result['type'])
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/cache_all_match_details', methods=['POST'])
@admin_required
def cache_all_match_details():
    match_service = MatchService()
    result = match_service.cache_all_match_details()
    
    for message, msg_type in result['messages']:
        flash(message, msg_type)
    
    return redirect(url_for('admin.admin_panel'))


# Seeding routes
@admin_bp.route('/set_seed/<int:user_id>', methods=['POST'])
@admin_required
def set_seed(user_id):
    placement = request.form.get('placement')
    data = get_tournament_data()
    for c in data.get('competitors', []):
        if c.get('id') == user_id:
            try:
                c['placement'] = int(placement)
            except (TypeError, ValueError):
                c.pop('placement', None)
            break
    save_tournament_data(data)
    generate_bracket()
    flash('Seed updated.', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/reset_seeding', methods=['POST'])
@admin_required
def reset_seeding():
    data = get_tournament_data()
    for c in data.get('competitors', []):
        c.pop('placement', None)
    save_tournament_data(data)
    generate_bracket()
    flash('All seed placements have been reset.', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/start_seeding', methods=['POST'])
@admin_required
def start_seeding():
    seeding_room_url = request.form.get('seeding_room_url', '').strip()
    
    seeding_service = SeedingService()
    result = seeding_service.start_seeding(seeding_room_url)
    
    flash(result['message'], result['type'])
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/update_seeding_scores', methods=['POST'])
@admin_required
def update_seeding_scores():
    seeding_service = SeedingService()
    result = seeding_service.update_seeding_scores()
    
    flash(result['message'], result['type'])
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/finalize_seeding', methods=['POST'])
@admin_required
def finalize_seeding():
    seeding_service = SeedingService()
    result = seeding_service.finalize_seeding()
    
    flash(result['message'], result['type'])
    return redirect(url_for('admin.admin_panel'))


# Streaming routes
@admin_bp.route('/set_stream', methods=['POST'])
@admin_required
def set_stream():
    twitch_channel = request.form.get('twitch_channel', '').strip()
    
    streaming_service = StreamingService()
    result = streaming_service.set_stream_channel(twitch_channel)
    
    flash(result['message'], result['type'])
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/set_seeding_playlist', methods=['POST'])
@admin_required
def set_seeding_playlist():
    """Set the seeding mappool playlist URL"""
    playlist_url = request.form.get('playlist_url', '').strip()
    
    data = get_tournament_data()
    if playlist_url:
        data['seeding_playlist_url'] = playlist_url
        flash('Seeding playlist URL updated successfully!', 'success')
    else:
        data.pop('seeding_playlist_url', None)
        flash('Seeding playlist URL cleared.', 'info')
    
    save_tournament_data(data)
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/toggle_stream', methods=['POST'])
@admin_required
def toggle_stream():
    streaming_service = StreamingService()
    result = streaming_service.toggle_stream()
    
    flash(result['message'], result['type'])
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/clear_stream', methods=['POST'])
@admin_required
def clear_stream():
    streaming_service = StreamingService()
    result = streaming_service.clear_stream()
    
    flash(result['message'], result['type'])
    return redirect(url_for('admin.admin_panel'))


# Overlay control routes
@admin_bp.route('/overlay/toggle_afk', methods=['POST'])
@admin_required
def overlay_toggle_afk():
    """Toggle AFK screen on overlay"""
    from ..overlay_state import add_overlay_event
    add_overlay_event('toggle_afk')
    flash('AFK screen toggled on overlay', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/overlay/show_match_victory', methods=['POST'])
@admin_required
def overlay_show_match_victory():
    """Show match victory screen on overlay"""
    try:
        data = get_tournament_data()
        # Find the current active match to get winner info
        current_match = None
        bracket_name = None
        
        # Check grand finals first
        if 'grand_finals' in data.get('brackets', {}):
            match = data['brackets']['grand_finals']
            if match and (match.get('status') in ['in_progress', 'completed'] or 
                         match.get('score_p1', 0) > 0 or match.get('score_p2', 0) > 0):
                current_match = match
                bracket_name = 'Grand Finals'
        
        # Check upper bracket
        if not current_match and 'upper' in data.get('brackets', {}):
            for round_matches in data['brackets']['upper']:
                for match in round_matches:
                    if match and (match.get('status') in ['in_progress', 'completed'] or 
                                 match.get('score_p1', 0) > 0 or match.get('score_p2', 0) > 0):
                        current_match = match
                        bracket_name = 'Upper Bracket'
                        break
                if current_match:
                    break
        
        # Check lower bracket
        if not current_match and 'lower' in data.get('brackets', {}):
            for round_matches in data['brackets']['lower']:
                for match in round_matches:
                    if match and (match.get('status') in ['in_progress', 'completed'] or 
                                 match.get('score_p1', 0) > 0 or match.get('score_p2', 0) > 0):
                        current_match = match
                        bracket_name = 'Lower Bracket'
                        break
                if current_match:
                    break
        
        if current_match:
            # Determine winner based on score
            p1_score = int(current_match.get('score_p1', 0))
            p2_score = int(current_match.get('score_p2', 0))
            
            # Get player names with fallbacks
            p1_name = current_match.get('player1', {}).get('name', 'Player 1')
            p2_name = current_match.get('player2', {}).get('name', 'Player 2')
            
            # Determine winner - prefer player with 4+ points, otherwise current leader
            if p1_score >= 4 or (p1_score > p2_score and p1_score > 0):
                winner_name = p1_name
            elif p2_score >= 4 or (p2_score > p1_score and p2_score > 0):
                winner_name = p2_name
            else:
                # No clear winner, default to player 1
                winner_name = p1_name
            
            final_score = f"{p1_score}-{p2_score}"
            advancement_text = f"Advances in {bracket_name}"
            
            print(f"Broadcasting match victory: {winner_name}, {final_score}, {advancement_text}")
            broadcast_match_victory(winner_name, final_score, advancement_text)
            flash(f'Match victory shown for {winner_name} ({final_score})', 'success')
        else:
            # No match found, show a generic victory screen
            broadcast_match_victory("Winner", "4-0", "Tournament Continues")
            flash('No active match found - showing generic victory screen', 'warning')
    except Exception as e:
        print(f"Error in overlay_show_match_victory: {e}")
        # Fallback: show a generic victory screen
        broadcast_match_victory("Winner", "4-0", "Tournament Continues")
        flash(f'Error finding match data - showing generic victory screen: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/overlay/show_map_victory', methods=['POST'])
@admin_required
def overlay_show_map_victory():
    """Show map victory screen on overlay"""
    winner = request.form.get('winner', 'Winner')
    map_title = request.form.get('map_title', 'Map Complete')
    
    broadcast_map_victory(winner, {'title': map_title})
    flash(f'Map victory shown for {winner}', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/overlay/hide_victory', methods=['POST'])
@admin_required
def overlay_hide_victory():
    """Hide victory screens on overlay"""
    from ..overlay_state import add_overlay_event
    add_overlay_event('hide_victory_screens')
    flash('Victory screens hidden on overlay', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/overlay/refresh_data', methods=['POST'])
@admin_required
def overlay_refresh_data():
    """Force refresh overlay data"""
    broadcast_match_update()
    flash('Overlay data refreshed', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/overlay/flip_players', methods=['POST'])
@admin_required
def overlay_flip_players():
    """Flip player positions on overlay"""
    print('Admin triggered flip_players route')  # debug
    # Use helper to broadcast flip_players event
    broadcast_flip_players()
    flash('Players flipped on overlay', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/overlay/show_welcome', methods=['POST'])
@admin_required
def overlay_show_welcome():
    """Show welcome screen on overlay"""
    from ..overlay_state import add_overlay_event
    add_overlay_event('show_welcome')
    flash('Welcome screen shown on overlay', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/overlay/show_outro', methods=['POST'])
@admin_required
def overlay_show_outro():
    """Show outro screen on overlay"""
    champion = request.form.get('champion', '')
    message = request.form.get('message', 'Thank you for watching the Sand World OSU Cup 2025')
    
    from ..overlay_state import add_overlay_event
    add_overlay_event('show_outro', {
        'champion': champion,
        'message': message
    })
    flash('Outro screen shown on overlay', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/overlay/hide_welcome', methods=['POST'])
@admin_required
def overlay_hide_welcome():
    """Hide welcome screen on overlay"""
    from ..overlay_state import add_overlay_event
    add_overlay_event('hide_welcome')
    flash('Welcome screen hidden on overlay', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/overlay/hide_outro', methods=['POST'])
@admin_required
def overlay_hide_outro():
    """Hide outro screen on overlay"""
    from ..overlay_state import add_overlay_event
    add_overlay_event('hide_outro')
    flash('Outro screen hidden on overlay', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/overlay/show_match_interface', methods=['POST'])
@admin_required
def overlay_show_match_interface():
    """Show match interface overlay"""
    from ..overlay_state import add_overlay_event
    add_overlay_event('show_match_interface')
    flash('Match interface overlay shown', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/overlay/hide_match_interface', methods=['POST'])
@admin_required
def overlay_hide_match_interface():
    """Hide match interface overlay"""
    from ..overlay_state import add_overlay_event
    add_overlay_event('hide_match_interface')
    flash('Match interface overlay hidden', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/set_tiebreaker_map', methods=['POST'])
@admin_required
def set_tiebreaker_map():
    """Set tiebreaker map for a 3-3 match"""
    match_id = request.form.get('match_id')
    tiebreaker_map_url = request.form.get('tiebreaker_map_url', '').strip()
    
    if not match_id:
        flash('Match ID is required', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    try:
        data = get_tournament_data()
        match_found = False
        
        # Find the match in all brackets
        for bracket_type in ['upper', 'lower', 'grand_finals']:
            if bracket_type in data.get('brackets', {}):
                if bracket_type == 'grand_finals':
                    match = data['brackets'][bracket_type]
                    if isinstance(match, dict) and match.get('id') == match_id:
                        # Verify it's actually 3-3
                        if match.get('score_p1', 0) == 3 and match.get('score_p2', 0) == 3:
                            match['tiebreaker_map_url'] = tiebreaker_map_url
                            match_found = True
                            break
                else:
                    for round_matches in data['brackets'][bracket_type]:
                        for match in round_matches:
                            if match and match.get('id') == match_id:
                                # Verify it's actually 3-3
                                if match.get('score_p1', 0) == 3 and match.get('score_p2', 0) == 3:
                                    match['tiebreaker_map_url'] = tiebreaker_map_url
                                    match_found = True
                                    break
                        if match_found:
                            break
                if match_found:
                    break
        
        if match_found:
            save_tournament_data(data)
            broadcast_match_update()
            flash(f'Tiebreaker map set for match {match_id}', 'success')
        else:
            flash('Match not found or not in 3-3 state', 'error')
            
    except Exception as e:
        flash(f'Error setting tiebreaker map: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/clear_tiebreaker_map', methods=['POST'])
@admin_required
def clear_tiebreaker_map():
    """Clear tiebreaker map for a match"""
    match_id = request.form.get('match_id')
    
    if not match_id:
        flash('Match ID is required', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    try:
        data = get_tournament_data()
        match_found = False
        
        # Find the match in all brackets
        for bracket_type in ['upper', 'lower', 'grand_finals']:
            if bracket_type in data.get('brackets', {}):
                if bracket_type == 'grand_finals':
                    match = data['brackets'][bracket_type]
                    if isinstance(match, dict) and match.get('id') == match_id:
                        if 'tiebreaker_map_url' in match:
                            del match['tiebreaker_map_url']
                        match_found = True
                        break
                else:
                    for round_matches in data['brackets'][bracket_type]:
                        for match in round_matches:
                            if match and match.get('id') == match_id:
                                if 'tiebreaker_map_url' in match:
                                    del match['tiebreaker_map_url']
                                match_found = True
                                break
                        if match_found:
                            break
                if match_found:
                    break
        
        if match_found:
            save_tournament_data(data)
            broadcast_match_update()
            flash(f'Tiebreaker map cleared for match {match_id}', 'success')
        else:
            flash('Match not found', 'error')
            
    except Exception as e:
        flash(f'Error clearing tiebreaker map: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_panel'))


# Developer Authentication Endpoints
@admin_bp.route('/dev_login_as_user', methods=['POST'])
@admin_required
def dev_login_as_user():
    """Developer-only endpoint to log in as any user for testing purposes"""
    user_identifier = request.form.get('user_id', '').strip()
    
    if not user_identifier:
        flash('Please provide a user ID or username', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    try:
        data = get_tournament_data()
        user = None
        
        # First, try to find user in competitors
        if user_identifier.isdigit():
            # Search by ID
            user_id = int(user_identifier)
            user = next((c for c in data.get('competitors', []) if c['id'] == user_id), None)
        else:
            # Search by username
            user = next((c for c in data.get('competitors', []) if c['name'].lower() == user_identifier.lower()), None)
        
        # If not found in competitors, try to fetch from osu! API
        if not user:
            try:
                # Try to fetch user data from osu! API using ossapi
                if user_identifier.isdigit():
                    user_data = api.user(int(user_identifier))
                else:
                    user_data = api.user(user_identifier)
                
                if user_data:
                    user = {
                        'id': user_data.id,
                        'name': user_data.username,
                        'avatar_url': user_data.avatar_url,
                        'country_code': user_data.country_code,
                        'is_dev_login': True  # Flag to indicate this is a dev login
                    }
                else:
                    flash(f'User "{user_identifier}" not found in tournament or osu! API', 'error')
                    return redirect(url_for('admin.admin_panel'))
                    
            except Exception as e:
                flash(f'Failed to fetch user from osu! API: {str(e)}', 'error')
                return redirect(url_for('admin.admin_panel'))
        
        # Set session data
        session['user_id'] = user['id']
        session['username'] = user['name']
        session['avatar_url'] = user.get('avatar_url', '')
        session['country_code'] = user.get('country_code', '')
        session['is_dev_login'] = True  # Mark as developer login
        
        flash(f'Successfully logged in as {user["name"]} (ID: {user["id"]}) - DEV MODE', 'success')
        
    except Exception as e:
        flash(f'Error during developer login: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/dev_logout', methods=['POST'])
@admin_required
def dev_logout():
    """Developer logout endpoint"""
    username = session.get('username', 'Unknown')
    
    # Clear user session data but keep admin session
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('avatar_url', None)
    session.pop('country_code', None)
    session.pop('is_dev_login', None)
    
    flash(f'Logged out from user session ({username}) - Admin session maintained', 'success')
    return redirect(url_for('admin.admin_panel'))
