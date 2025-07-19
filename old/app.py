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
    
    # Find the match in any round of any bracket, including grand finals
    match_found = False
    for bracket_type in ['upper', 'lower', 'grand_finals']:
        if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
            # Grand finals is a single match, not a list of rounds
            rounds = data['brackets'][bracket_type] if bracket_type != 'grand_finals' else [data['brackets'][bracket_type]]
            for round_matches in rounds:
                # Handle case where grand_finals might be a single dict not in a list
                matches_to_check = round_matches if isinstance(round_matches, list) else [round_matches]
                for match in matches_to_check:
                    if match.get('id') == match_id:
                        if match.get('player1', {}).get('id') and str(match['player1']['id']) == winner_id:
                            match['winner'] = match['player1']
                            match_found = True
                            break
                        if match.get('player2', {}).get('id') and str(match['player2']['id']) == winner_id:
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
    Rewritten, robust function to advance a double-elimination bracket.
    This function correctly paces the upper and lower brackets and is idempotent.
    """
    # --- Process Upper Bracket ---
    # This part remains largely the same, as it was mostly correct.
    # It advances the upper bracket and collects losers into a temporary list.
    losers_from_this_advancement = []
    if data['brackets'].get('upper'):
        last_upper_round_index = len(data['brackets']['upper']) - 1
        last_upper_round = data['brackets']['upper'][last_upper_round_index]
        
        # Check if the last upper round is finished and hasn't been processed yet
        if all(m.get('winner') for m in last_upper_round) and len(data['brackets']['upper']) == last_upper_round_index + 1:
            winners = [m['winner'] for m in last_upper_round]
            
            # Collect losers from this round
            for match in last_upper_round:
                if match.get('player1') and match['player1'].get('id') and match.get('player2') and match['player2'].get('id'):
                    loser = match['player2'] if match['winner']['id'] == match['player1']['id'] else match['player1']
                    # Tag loser with the round they dropped from for correct seeding
                    loser['dropped_from_round'] = last_upper_round_index 
                    losers_from_this_advancement.append(loser)
            
            # If there's more than one winner, create the next upper round
            if len(winners) > 1:
                next_upper_matches = []
                for i in range(0, len(winners), 2):
                    p1 = winners[i]
                    p2 = winners[i+1] if i + 1 < len(winners) else {'name': 'BYE', 'id': None}
                    match = {'id': str(uuid.uuid4()), 'player1': p1, 'player2': p2, 'winner': p1 if p2['name'] == 'BYE' else None}
                    next_upper_matches.append(match)
                data['brackets']['upper'].append(next_upper_matches)

    # --- Process Lower Bracket ---
    # This is the completely rewritten logic.
    # It decides whether to create a new round from lower bracket winners OR
    # to merge those winners with players who just dropped from the upper bracket.
    
    # If there are no lower bracket rounds yet, create the first one from the losers.
    if not data['brackets'].get('lower') and losers_from_this_advancement:
        next_lower_matches = []
        # Sort losers for fair initial pairing
        losers_from_this_advancement.sort(key=lambda p: -p.get('pp', 0))
        for i in range(0, len(losers_from_this_advancement), 2):
            p1 = losers_from_this_advancement[i]
            p2 = losers_from_this_advancement[i+1] if i + 1 < len(losers_from_this_advancement) else {'name': 'BYE', 'id': None}
            match = {'id': str(uuid.uuid4()), 'player1': p1, 'player2': p2, 'winner': p1 if p2['name'] == 'BYE' else None}
            next_lower_matches.append(match)
        if next_lower_matches:
            data['brackets']['lower'].append(next_lower_matches)
    
    # If there are existing lower bracket rounds, check if the last one is finished.
    elif data['brackets'].get('lower'):
        last_lower_round = data['brackets']['lower'][-1]
        if all(m.get('winner') for m in last_lower_round):
            winners_from_lower = [m['winner'] for m in last_lower_round]
            
            # Pool for the next round starts with the winners from the last lower round
            next_pool = list(winners_from_lower)
            
            # Add any players who just dropped from the upper bracket
            next_pool.extend(losers_from_this_advancement)

            # Only create a new round if there are players to play
            if len(next_pool) >= 2:
                # Sort the combined pool for fair matchups
                next_pool.sort(key=lambda p: (p.get('dropped_from_round', 999), -p.get('pp', 0)))
                
                next_lower_matches = []
                for i in range(0, len(next_pool), 2):
                    p1 = next_pool[i]
                    p2 = next_pool[i+1] if i + 1 < len(next_pool) else {'name': 'BYE', 'id': None}
                    match = {'id': str(uuid.uuid4()), 'player1': p1, 'player2': p2, 'winner': p1 if p2['name'] == 'BYE' else None}
                    next_lower_matches.append(match)
                
                # Idempotency check: only add if it's a new round
                if data['brackets']['lower'][-1] != next_lower_matches:
                    data['brackets']['lower'].append(next_lower_matches)

    # --- Process Grand Finals ---
    # This logic is now more robust.
    upper_winner = None
    lower_winner = None

    # Check for definitive upper bracket winner
    if data['brackets'].get('upper'):
        final_upper_round = data['brackets']['upper'][-1]
        if len(final_upper_round) == 1 and final_upper_round[0].get('winner'):
            upper_winner = final_upper_round[0]['winner']

    # Check for definitive lower bracket winner
    if data['brackets'].get('lower'):
        final_lower_round = data['brackets']['lower'][-1]
        if len(final_lower_round) == 1 and final_lower_round[0].get('winner'):
            # Ensure no more players are waiting to drop from upper bracket
            if not losers_from_this_advancement:
                lower_winner = final_lower_round[0]['winner']

    if upper_winner and lower_winner and not data['brackets'].get('grand_finals'):
        grand_finals_match = {
            'id': str(uuid.uuid4()),
            'player1': upper_winner,
            'player2': lower_winner,
            'winner': None,
            'is_grand_finals': True
        }
        data['brackets']['grand_finals'] = grand_finals_match

    # Clear the now-unused loser_pool if it exists from old data
    if 'loser_pool' in data:
        del data['loser_pool']

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