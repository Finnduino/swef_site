from flask import Flask, render_template, redirect, request, url_for, session
import json
import os
from dotenv import load_dotenv
from ossapi import Ossapi
import requests
from functools import wraps
import uuid

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# --- Config ---
OSU_CLIENT_ID = int(os.getenv('OSU_CLIENT_ID'))
OSU_CLIENT_SECRET = os.getenv('OSU_CLIENT_SECRET')
REDIRECT_URI = os.getenv('OSU_CALLBACK_URL')
ADMIN_REDIRECT_URI = REDIRECT_URI.replace('/callback/osu', '/callback/admin')
ADMIN_OSU_ID = '11365195' # Your osu! user ID

OSU_API_BASE_URL = 'https://osu.ppy.sh/api/v2'
TOKEN_URL = 'https://osu.ppy.sh/oauth/token'
AUTHORIZATION_URL = 'https://osu.ppy.sh/oauth/authorize'

api = Ossapi(OSU_CLIENT_ID, OSU_CLIENT_SECRET)
TOURNAMENT_FILE = 'tournament.json'

# --- Data Handling ---
def get_tournament_data():
    try:
        with open(TOURNAMENT_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Create a default structure if file doesn't exist
        return {'competitors': [], 'brackets': {'upper': [], 'lower': []}}

def save_tournament_data(data):
    # Sort competitors by pp before saving
    data['competitors'].sort(key=lambda x: x.get('pp', 0), reverse=True)
    with open(TOURNAMENT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# --- Bracket Generation ---
def generate_bracket():
    data = get_tournament_data()
    competitors = data['competitors']
    num_competitors = len(competitors)
    
    if num_competitors < 2:
        data['brackets'] = {'upper': [], 'lower': []}
        save_tournament_data(data)
        return

    next_power_of_2 = 1 << (num_competitors - 1).bit_length()
    seeded_players = list(competitors)
    num_byes = next_power_of_2 - num_competitors
    for _ in range(num_byes):
        seeded_players.append({'name': 'BYE', 'id': None})

    half_len = len(seeded_players) // 2
    top_half = seeded_players[:half_len]
    bottom_half = seeded_players[half_len:]
    bottom_half.reverse()

    matches = []
    for i in range(half_len):
        p1 = top_half[i]
        p2 = bottom_half[i]
        match = {
            'id': str(uuid.uuid4()), # Unique ID for each match
            'player1': p1,
            'player2': p2,
            'winner': p1 if p2['name'] == 'BYE' else None
        }
        matches.append(match)
    
    data['brackets']['upper'] = [matches] # Store as round 1
    data['brackets']['lower'] = [] # Reset lower bracket
    save_tournament_data(data)

# --- Admin Auth ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login/admin')
def admin_login():
    params = {'client_id': OSU_CLIENT_ID, 'redirect_uri': ADMIN_REDIRECT_URI, 'response_type': 'code', 'scope': 'identify'}
    auth_url = f"{AUTHORIZATION_URL}?{requests.compat.urlencode(params)}"
    return redirect(auth_url)

@app.route('/callback/admin')
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
        return redirect(url_for('admin_panel'))
    return "Access Denied.", 403

# --- Admin Routes ---
@app.route('/admin')
@admin_required
def admin_panel():
    data = get_tournament_data()
    return render_template('admin.html', data=data)

@app.route('/admin/remove/<int:user_id>', methods=['POST'])
@admin_required
def remove_competitor(user_id):
    data = get_tournament_data()
    data['competitors'] = [c for c in data['competitors'] if c.get('id') != user_id]
    save_tournament_data(data)
    generate_bracket() # Regenerate bracket after removing a player
    return redirect(url_for('admin_panel'))

@app.route('/admin/reset_bracket', methods=['POST'])
@admin_required
def reset_bracket():
    generate_bracket()
    return redirect(url_for('admin_panel'))

@app.route('/admin/set_winner', methods=['POST'])
@admin_required
def set_winner():
    match_id = request.form.get('match_id')
    winner_id = request.form.get('winner_id')
    
    data = get_tournament_data()
    
    # Find the match in any round of any bracket
    match_found = False
    for bracket_type in ['upper', 'lower']:
        if bracket_type in data['brackets']:
            for round_matches in data['brackets'][bracket_type]:
                for match in round_matches:
                    if match['id'] == match_id:
                        if match['player1'].get('id') and str(match['player1']['id']) == winner_id:
                            match['winner'] = match['player1']
                            match_found = True
                            break
                        if match['player2'].get('id') and str(match['player2']['id']) == winner_id:
                            match['winner'] = match['player2']
                            match_found = True
                            break
                if match_found:
                    break
        if match_found:
            break
            
    # Pass the modified data directly to the advance function
    advance_round_if_ready(data)
    
    # The advance function now handles saving
    return redirect(url_for('admin_panel'))

def advance_round_if_ready(data):
    """
    Checks if rounds are complete and generates the next rounds for both brackets.
    This function is now idempotent and handles bracket states independently.
    """
    
    # --- Process Upper Bracket ---
    if data['brackets']['upper']:
        last_upper_round_index = len(data['brackets']['upper']) - 1
        last_upper_round = data['brackets']['upper'][last_upper_round_index]
        
        # Check if the last upper round is complete
        if all(m.get('winner') for m in last_upper_round):
            # Get winners for the next upper round
            winners = [m['winner'] for m in last_upper_round]
            
            # Get losers to be moved to the lower bracket
            losers_from_upper = []
            for match in last_upper_round:
                if match['player1'].get('id') and match['player2'].get('id'): # Exclude BYEs
                    loser = match['player2'] if match['winner']['id'] == match['player1']['id'] else match['player1']
                    # Tag losers with the round they dropped from
                    loser['dropped_from_round'] = last_upper_round_index
                    losers_from_upper.append(loser)

            # Create next upper round if it's not the final
            if len(winners) > 1:
                next_upper_matches = []
                for i in range(0, len(winners), 2):
                    p1, p2 = winners[i], winners[i+1] if i + 1 < len(winners) else {'name': 'BYE', 'id': None}
                    match = {'id': str(uuid.uuid4()), 'player1': p1, 'player2': p2, 'winner': p1 if p2['name'] == 'BYE' else None}
                    next_upper_matches.append(match)
                
                # Add the new round only if it doesn't already exist
                if len(data['brackets']['upper']) == last_upper_round_index + 1:
                    data['brackets']['upper'].append(next_upper_matches)

            # Add the collected losers to a holding pool in the data structure
            if 'loser_pool' not in data:
                data['loser_pool'] = []
            data['loser_pool'].extend(losers_from_upper)

    # --- Process Lower Bracket ---
    # The lower bracket has a more complex lifecycle
    # A new lower round is formed from winners of the previous lower round AND players dropping from upper.
    
    # Condition 1: Initial population of the lower bracket
    if not data['brackets']['lower'] and 'loser_pool' in data and len(data['loser_pool']) >= 2:
        pool = data.pop('loser_pool')
        next_lower_matches = []
        for i in range(0, len(pool), 2):
            p1, p2 = pool[i], pool[i+1] if i + 1 < len(pool) else {'name': 'BYE', 'id': None}
            match = {'id': str(uuid.uuid4()), 'player1': p1, 'player2': p2, 'winner': p1 if p2['name'] == 'BYE' else None}
            next_lower_matches.append(match)
        if next_lower_matches:
            data['brackets']['lower'].append(next_lower_matches)

    # Condition 2: Advancing an existing lower bracket
    elif data['brackets']['lower']:
        last_lower_round = data['brackets']['lower'][-1]
        
        # If the last lower round is complete, create the next one
        if all(m.get('winner') for m in last_lower_round):
            winners_from_lower = [m['winner'] for m in last_lower_round]
            
            # Combine with any players waiting in the loser pool
            next_pool = winners_from_lower
            if 'loser_pool' in data:
                next_pool.extend(data.pop('loser_pool'))

            if len(next_pool) >= 2:
                next_lower_matches = []
                for i in range(0, len(next_pool), 2):
                    p1, p2 = next_pool[i], next_pool[i+1] if i + 1 < len(next_pool) else {'name': 'BYE', 'id': None}
                    match = {'id': str(uuid.uuid4()), 'player1': p1, 'player2': p2, 'winner': p1 if p2['name'] == 'BYE' else None}
                    next_lower_matches.append(match)
                
                # Add the new round only if it doesn't already exist
                if len(data['brackets']['lower']) == len(data['brackets']['lower'][:-1]) + 1:
                     data['brackets']['lower'].append(next_lower_matches)

    save_tournament_data(data)


# --- Public Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tournament')
def tournament():
    data = get_tournament_data()
    return render_template('tournament.html', data=data)

@app.route('/login/osu')
def osu_login():
    params = {'client_id': OSU_CLIENT_ID, 'redirect_uri': REDIRECT_URI, 'response_type': 'code', 'scope': 'identify'}
    auth_url = f"{AUTHORIZATION_URL}?{requests.compat.urlencode(params)}"
    return redirect(auth_url)

@app.route('/callback/osu')
def osu_callback():
    code = request.args.get('code')
    token_data = {'client_id': OSU_CLIENT_ID, 'client_secret': OSU_CLIENT_SECRET, 'code': code, 'grant_type': 'authorization_code', 'redirect_uri': REDIRECT_URI}
    token_response = requests.post(TOKEN_URL, data=token_data)
    access_token = token_response.json().get('access_token')

    headers = {'Authorization': f'Bearer {access_token}'}
    me_response = requests.get(f'{OSU_API_BASE_URL}/me', headers=headers)
    user_id = me_response.json().get('id')
    
    data = get_tournament_data()
    if any(c.get('id') == user_id for c in data['competitors']):
        return redirect(url_for('tournament'))

    user_data = api.user(user_id)
    new_competitor = {
        'id': user_data.id,
        'name': user_data.username,
        'pp': user_data.statistics.pp if user_data.statistics else 0,
        'avatar_url': user_data.avatar_url
    }
    data['competitors'].append(new_competitor)
    save_tournament_data(data)
    generate_bracket() # Regenerate bracket when a new player joins
    return redirect(url_for('tournament'))

if __name__ == '__main__':
    port = int(REDIRECT_URI.split(':')[-1].split('/')[0])
    app.run(debug=True, port=port)