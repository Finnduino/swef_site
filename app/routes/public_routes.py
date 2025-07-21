from flask import Blueprint, render_template, redirect, request, url_for, flash
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


@public_bp.route('/login/osu')
def osu_login():
    params = {'client_id': OSU_CLIENT_ID, 'redirect_uri': OSU_CALLBACK_URL, 'response_type': 'code', 'scope': 'identify'}
    auth_url = f"{AUTHORIZATION_URL}?{requests.compat.urlencode(params)}"
    return redirect(auth_url)


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
    
    data = get_tournament_data()
    if not any(c.get('id') == user_id for c in data.get('competitors', [])):
        new_competitor = {
            'id': user_id,
            'name': user_json.get('username'),
            'pp': user_json.get('statistics', {}).get('pp', 0),
            'rank': user_json.get('statistics', {}).get('global_rank', 0),
            'avatar_url': user_json.get('avatar_url')
        }
        if 'competitors' not in data:
            data['competitors'] = []
        data['competitors'].append(new_competitor)
        save_tournament_data(data)
        generate_bracket()
    
    return redirect(url_for('public.tournament'))


@public_bp.route('/user/<int:user_id>')
def user_profile(user_id):
    try:
        user = api.user(user_id)
        return render_template('user_profile.html', user=user)
    except Exception as e:
        flash(f'Could not find or load user with ID {user_id}. Error: {e}', 'error')
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
