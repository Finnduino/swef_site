from flask import Blueprint, render_template, redirect, request, url_for, session, flash
import requests
from functools import wraps
from datetime import datetime, timedelta
from config import *
from .data_manager import get_tournament_data, save_tournament_data
from .bracket_logic import generate_bracket, advance_round_if_ready
from . import api # Import the api instance from __init__.py


# --- Blueprints ---
public_bp = Blueprint('public', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# --- Admin Auth Decorator ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('public.index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Public Routes ---
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
            # If timestamp is invalid, force a refresh
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
        
        # Update the timestamp and save the new data
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


# --- Admin Routes ---
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

    if user_id == ADMIN_OSU_ID:
        session['is_admin'] = True
        return redirect(url_for('admin.admin_panel'))
    return "Access Denied.", 403

@admin_bp.route('/')
@admin_required
def admin_panel():
    data = get_tournament_data()
    return render_template('admin.html', data=data)

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
        # Check the exception type's name to see if it's a UserNotFound error
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
    """Clears all competitors and resets the bracket."""
    data = get_tournament_data()
    data['competitors'] = []
    data['brackets'] = {'upper': [], 'lower': []}
    save_tournament_data(data)
    flash('All competitors have been removed and the tournament has been reset.', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/reset_bracket', methods=['POST'])
@admin_required
def reset_bracket():
    generate_bracket()
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/set_winner', methods=['POST'])
@admin_required
def set_winner():
    match_id = request.form.get('match_id')
    winner_id = request.form.get('winner_id')
    data = get_tournament_data()
    
    match_found = False
    for bracket_type in ['upper', 'lower', 'grand_finals']:
        if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
            rounds = data['brackets'][bracket_type] if bracket_type != 'grand_finals' else [data['brackets'][bracket_type]]
            for round_matches in rounds:
                matches_to_check = round_matches if isinstance(round_matches, list) else [round_matches]
                for match in matches_to_check:
                    if match.get('id') == match_id:
                        if match.get('player1', {}).get('id') and str(match['player1']['id']) == winner_id:
                            match['winner'] = match['player1']
                        elif match.get('player2', {}).get('id') and str(match['player2']['id']) == winner_id:
                            match['winner'] = match['player2']
                        match_found = True
                        break
                if match_found: break
            if match_found: break
            
    if match_found:
        advance_round_if_ready(data)
    
    return redirect(url_for('admin.admin_panel'))
