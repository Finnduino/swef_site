from flask import Blueprint, render_template, redirect, request, url_for, session, flash
import requests
from functools import wraps
from datetime import datetime, timedelta
from config import *
from .data_manager import get_tournament_data, save_tournament_data
from .bracket_logic import generate_bracket, advance_round_if_ready
from . import api # Import the api instance from __init__.py
import re
from urllib.parse import urlparse


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

    if user_id in ADMIN_OSU_ID:
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

@admin_bp.route('/start_match', methods=['POST'])
@admin_required
def start_match():
    match_id = request.form.get('match_id')
    data = get_tournament_data()
    
    match_found = False
    for bracket_type in ['upper', 'lower', 'grand_finals']:
        if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
            rounds = data['brackets'][bracket_type] if bracket_type != 'grand_finals' else [data['brackets'][bracket_type]]
            for round_matches in rounds:
                matches_to_check = round_matches if isinstance(round_matches, list) else [round_matches]
                for match in matches_to_check:
                    if match.get('id') == match_id:
                        match['status'] = 'in_progress'
                        match_found = True
                        break
                if match_found: break
            if match_found: break
    
    if match_found:
        save_tournament_data(data)
        flash('Match started!', 'success')
    else:
        flash('Match not found.', 'error')
    
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/reset_match', methods=['POST'])
@admin_required
def reset_match():
    match_id = request.form.get('match_id')
    data = get_tournament_data()
    
    match_found = False
    for bracket_type in ['upper', 'lower', 'grand_finals']:
        if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
            rounds = data['brackets'][bracket_type] if bracket_type != 'grand_finals' else [data['brackets'][bracket_type]]
            for round_matches in rounds:
                matches_to_check = round_matches if isinstance(round_matches, list) else [round_matches]
                for match in matches_to_check:
                    if match.get('id') == match_id:
                        match['status'] = 'next_up'
                        match['winner'] = None
                        match['score_p1'] = 0
                        match['score_p2'] = 0
                        match['mp_room_url'] = None
                        match_found = True
                        break
                if match_found: break
            if match_found: break
    
    if match_found:
        save_tournament_data(data)
        flash('Match reset to "Next Up" status.', 'success')
    else:
        flash('Match not found.', 'error')
    
    return redirect(url_for('admin.admin_panel'))

# Update existing set_score function to set status to completed when winner is determined
@admin_bp.route('/set_score', methods=['POST'])
@admin_required
def set_score():
    match_id = request.form.get('match_id')
    score_p1 = request.form.get('score_p1', 0)
    score_p2 = request.form.get('score_p2', 0)
    mp_room_url = request.form.get('mp_room_url', '').strip()
    
    try:
        score_p1 = int(score_p1)
        score_p2 = int(score_p2)
    except ValueError:
        flash('Invalid score values.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    # Validate Best of 7 format (first to 4)
    if score_p1 < 0 or score_p2 < 0 or (score_p1 > 4) or (score_p2 > 4):
        flash('Scores must be between 0-4 (Best of 7 format).', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    if score_p1 == 4 and score_p2 == 4:
        flash('Both players cannot have 4 points.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    data = get_tournament_data()
    match_found = False
    
    # Find and update the match
    for bracket_type in ['upper', 'lower', 'grand_finals']:
        if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
            rounds = data['brackets'][bracket_type] if bracket_type != 'grand_finals' else [data['brackets'][bracket_type]]
            for round_matches in rounds:
                matches_to_check = round_matches if isinstance(round_matches, list) else [round_matches]
                for match in matches_to_check:
                    if match.get('id') == match_id:
                        match['score_p1'] = score_p1
                        match['score_p2'] = score_p2
                        
                        # Validate and set multiplayer room URL
                        if mp_room_url:
                            if 'osu.ppy.sh/multiplayer/rooms/' in mp_room_url:
                                match['mp_room_url'] = mp_room_url
                            else:
                                flash('Invalid multiplayer room URL format.', 'error')
                                return redirect(url_for('admin.admin_panel'))
                        else:
                            match['mp_room_url'] = None
                        
                        # Determine winner and status based on Best of 7 (first to 4)
                        if score_p1 == 4:
                            match['winner'] = match['player1']
                            match['status'] = 'completed'
                        elif score_p2 == 4:
                            match['winner'] = match['player2']
                            match['status'] = 'completed'
                        else:
                            match['winner'] = None
                            # Set to in_progress if score has been updated but no winner yet
                            if score_p1 > 0 or score_p2 > 0:
                                match['status'] = 'in_progress'
                            else:
                                match['status'] = match.get('status', 'next_up')
                        
                        match_found = True
                        break
                if match_found: break
            if match_found: break
    
    if match_found:
        advance_round_if_ready(data)
        flash('Match score updated successfully.', 'success')
    else:
        flash('Match not found.', 'error')
    
    return redirect(url_for('admin.admin_panel'))

# Update set_winner to also set status to completed
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
                            match['score_p1'] = 4
                            match['score_p2'] = 0
                        elif match.get('player2', {}).get('id') and str(match['player2']['id']) == winner_id:
                            match['winner'] = match['player2']
                            match['score_p1'] = 0
                            match['score_p2'] = 4
                        match['status'] = 'completed'
                        match_found = True
                        break
                if match_found: break
            if match_found: break
            
    if match_found:
        advance_round_if_ready(data)
    
    return redirect(url_for('admin.admin_panel'))

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
    """Clears all qualifier placements (seeds) for competitors."""
    data = get_tournament_data()
    for c in data.get('competitors', []):
        c.pop('placement', None)
    save_tournament_data(data)
    generate_bracket()
    flash('All seed placements have been reset.', 'success')
    return redirect(url_for('admin.admin_panel'))

# Helper function to extract room ID from multiplayer URL
def extract_room_id(url):
    """Extract room ID from osu multiplayer room URL"""
    if not url:
        return None
    
    # Handle different URL formats
    patterns = [
        r'osu\.ppy\.sh/multiplayer/rooms/(\d+)',
        r'osu\.ppy\.sh/mp/(\d+)', 
        r'multiplayer/rooms/(\d+)',
        r'/rooms/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return int(match.group(1))
    
    return None

def get_match_results(room_id, player1_id, player2_id):
    """
    Fetch match results from osu! API using ossapi and determine winner based on Best of 7
    Returns: (winner_id, score_p1, score_p2, status) or (None, 0, 0, 'error') if error
    """
    try:
        print(f"Fetching match results for room {room_id}, players {player1_id} vs {player2_id}")
        
        # Get room details
        room = api.room(room_id)
        
        if not room.playlist:
            print("No playlist found in room")
            return None, 0, 0, 'no_playlist'
        
        player1_wins = 0
        player2_wins = 0
        total_maps = len(room.playlist)
        
        print(f"Found {total_maps} maps in playlist")
        
        # Check each playlist item (map) for scores
        for i, playlist_item in enumerate(room.playlist):
            try:
                print(f"Checking playlist item {i+1}/{total_maps}: {playlist_item.id}")
                
                # Get scores for this playlist item
                scores_data = api.multiplayer_scores(room_id, playlist_item.id)
                
                # Find scores for our two players
                p1_score = None
                p2_score = None
                
                for score in scores_data.scores:
                    if score.user_id == player1_id:
                        p1_score = score
                        print(f"Found player 1 score: {score.total_score}")
                    elif score.user_id == player2_id:
                        p2_score = score
                        print(f"Found player 2 score: {score.total_score}")
                
                # Determine map winner (higher score wins the map)
                if p1_score and p2_score:
                    if p1_score.total_score > p2_score.total_score:
                        player1_wins += 1
                        print(f"Player 1 wins map {i+1}")
                    elif p2_score.total_score > p1_score.total_score:
                        player2_wins += 1
                        print(f"Player 2 wins map {i+1}")
                    else:
                        print(f"Tie on map {i+1}")
                elif p1_score and not p2_score:
                    player1_wins += 1
                    print(f"Player 1 wins map {i+1} (no opponent score)")
                elif p2_score and not p1_score:
                    player2_wins += 1
                    print(f"Player 2 wins map {i+1} (no opponent score)")
                else:
                    print(f"No scores found for either player on map {i+1}")
                
            except Exception as e:
                print(f"Error fetching scores for playlist item {playlist_item.id}: {e}")
                continue
        
        print(f"Final map score: Player 1: {player1_wins}, Player 2: {player2_wins}")
        
        # Determine overall winner (first to 4 wins in Best of 7)
        if player1_wins >= 4:
            return player1_id, player1_wins, player2_wins, 'completed'
        elif player2_wins >= 4:
            return player2_id, player1_wins, player2_wins, 'completed'
        elif player1_wins > 0 or player2_wins > 0:
            # Match in progress
            return None, player1_wins, player2_wins, 'in_progress'
        else:
            # No scores yet
            return None, 0, 0, 'no_scores'
    
    except Exception as e:
        print(f"Error fetching match results for room {room_id}: {e}")
        return None, 0, 0, 'error'

def get_seeding_scores(room_id, competitor_ids):
    """
    Fetch cumulative seeding scores for all competitors from a multiplayer room
    Returns: dict of {user_id: total_score}
    """
    try:
        print(f"Fetching seeding scores for room {room_id}")
        
        # Get room details
        room = api.room(room_id)
        
        if not room.playlist:
            print("No playlist found in seeding room")
            return {}
        
        player_scores = {}
        
        # Initialize scores for all competitors
        for comp_id in competitor_ids:
            player_scores[comp_id] = 0
        
        print(f"Checking {len(room.playlist)} maps for seeding scores")
        
        # Check each playlist item (map) for scores
        for i, playlist_item in enumerate(room.playlist):
            try:
                print(f"Processing seeding map {i+1}/{len(room.playlist)}: {playlist_item.id}")
                
                # Get scores for this playlist item
                scores_data = api.multiplayer_scores(room_id, playlist_item.id)
                
                for score in scores_data.scores:
                    if score.user_id in competitor_ids:
                        player_scores[score.user_id] += score.total_score
                        print(f"Added {score.total_score} to player {score.user_id} (total: {player_scores[score.user_id]})")
                
            except Exception as e:
                print(f"Error fetching seeding scores for playlist item {playlist_item.id}: {e}")
                continue
        
        # Filter out players with 0 scores
        return {uid: score for uid, score in player_scores.items() if score > 0}
    
    except Exception as e:
        print(f"Error fetching seeding scores for room {room_id}: {e}")
        return {}

@admin_bp.route('/refresh_match_scores', methods=['POST'])
@admin_required
def refresh_match_scores():
    """Automatically refresh match scores from multiplayer room"""
    match_id = request.form.get('match_id')
    data = get_tournament_data()
    
    match_found = False
    target_match = None
    
    # Find the match
    for bracket_type in ['upper', 'lower', 'grand_finals']:
        if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
            rounds = data['brackets'][bracket_type] if bracket_type != 'grand_finals' else [data['brackets'][bracket_type]]
            for round_matches in rounds:
                matches_to_check = round_matches if isinstance(round_matches, list) else [round_matches]
                for match in matches_to_check:
                    if match.get('id') == match_id:
                        target_match = match
                        match_found = True
                        break
                if match_found: break
            if match_found: break
    
    if not match_found or not target_match:
        flash('Match not found.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    # Extract room ID from URL
    room_id = extract_room_id(target_match.get('mp_room_url'))
    if not room_id:
        flash('Invalid or missing multiplayer room URL.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    # Get player IDs
    player1_id = target_match.get('player1', {}).get('id')
    player2_id = target_match.get('player2', {}).get('id')
    
    if not player1_id or not player2_id:
        flash('Player IDs not found in match data.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    # Fetch results
    winner_id, score_p1, score_p2, status = get_match_results(room_id, player1_id, player2_id)
    
    # Update match
    target_match['score_p1'] = score_p1
    target_match['score_p2'] = score_p2
    
    if status == 'completed' and winner_id:
        if winner_id == player1_id:
            target_match['winner'] = target_match['player1']
        else:
            target_match['winner'] = target_match['player2']
        target_match['status'] = 'completed'
        flash(f'Match completed! Final score: {score_p1}-{score_p2}', 'success')
    elif status == 'in_progress':
        target_match['winner'] = None
        target_match['status'] = 'in_progress'
        flash(f'Match in progress. Current score: {score_p1}-{score_p2}', 'info')
    elif status == 'no_scores':
        flash('No scores found yet in the multiplayer room.', 'info')
    elif status == 'error':
        flash('Error fetching scores from the multiplayer room.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    # Save and advance if match is complete
    if target_match.get('winner'):
        advance_round_if_ready(data)
    else:
        save_tournament_data(data)
    
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/start_seeding', methods=['POST'])
@admin_required
def start_seeding():
    """Start seeding with a multiplayer room"""
    seeding_room_url = request.form.get('seeding_room_url', '').strip()
    
    if not seeding_room_url:
        flash('Seeding room URL is required.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    room_id = extract_room_id(seeding_room_url)
    if not room_id:
        flash('Invalid multiplayer room URL format.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    # Test if we can access the room
    try:
        room = api.room(room_id)
        if not room:
            flash('Could not access the specified multiplayer room.', 'error')
            return redirect(url_for('admin.admin_panel'))
    except Exception as e:
        flash(f'Error accessing multiplayer room: {e}', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    data = get_tournament_data()
    data['seeding_room_url'] = seeding_room_url
    data['seeding_room_id'] = room_id
    data['seeding_in_progress'] = True
    
    save_tournament_data(data)
    flash('Seeding room set! Players can now play seeding maps.', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/update_seeding_scores', methods=['POST'])
@admin_required
def update_seeding_scores():
    """Update seeding scores from the multiplayer room"""
    data = get_tournament_data()
    room_id = data.get('seeding_room_id')
    
    if not room_id:
        flash('No seeding room configured.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    # Get competitor IDs
    competitor_ids = [c['id'] for c in data.get('competitors', []) if c.get('id')]
    
    if not competitor_ids:
        flash('No competitors found.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    # Fetch seeding scores
    player_scores = get_seeding_scores(room_id, competitor_ids)
    
    if not player_scores:
        flash('No seeding scores found in the multiplayer room.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    # Update competitor scores and provisional seeding
    competitors = data.get('competitors', [])
    seeded_players = []
    
    for competitor in competitors:
        if competitor['id'] in player_scores:
            competitor['seeding_score'] = player_scores[competitor['id']]
            seeded_players.append(competitor)
        else:
            # Remove seeding score if player didn't participate
            competitor.pop('seeding_score', None)
            competitor.pop('provisional_placement', None)
    
    # Sort by seeding score (descending) and assign provisional placements
    seeded_players.sort(key=lambda x: x.get('seeding_score', 0), reverse=True)
    
    for i, player in enumerate(seeded_players):
        player['provisional_placement'] = i + 1
    
    save_tournament_data(data)
    flash(f'Updated seeding scores for {len(seeded_players)} players.', 'success')
    
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/finalize_seeding', methods=['POST'])
@admin_required
def finalize_seeding():
    """Finalize seeding and lock in placements"""
    data = get_tournament_data()
    
    competitors = data.get('competitors', [])
    finalized_count = 0
    
    for competitor in competitors:
        if 'provisional_placement' in competitor:
            competitor['placement'] = competitor['provisional_placement']
            competitor.pop('provisional_placement', None)
            competitor.pop('seeding_score', None)
            finalized_count += 1
    
    # Clean up seeding data
    data.pop('seeding_room_url', None)
    data.pop('seeding_room_id', None)
    data.pop('seeding_in_progress', None)
    
    save_tournament_data(data)
    generate_bracket()
    
    flash(f'Seeding finalized for {finalized_count} players and bracket regenerated.', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/set_stream', methods=['POST'])
@admin_required
def set_stream():
    """Set Twitch channel for streaming"""
    twitch_channel = request.form.get('twitch_channel', '').strip()
    
    if not twitch_channel:
        flash('Twitch channel name is required.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    # Clean channel name (remove twitch.tv/ if included)
    if 'twitch.tv/' in twitch_channel:
        twitch_channel = twitch_channel.split('twitch.tv/')[-1]
    
    # Remove any extra characters
    twitch_channel = re.sub(r'[^a-zA-Z0-9_]', '', twitch_channel)
    
    if not twitch_channel:
        flash('Invalid Twitch channel name.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    data = get_tournament_data()
    data['twitch_channel'] = twitch_channel
    
    save_tournament_data(data)
    flash(f'Twitch channel set to: {twitch_channel}', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/toggle_stream', methods=['POST'])
@admin_required
def toggle_stream():
    """Toggle stream live status"""
    data = get_tournament_data()
    
    if not data.get('twitch_channel'):
        flash('No Twitch channel configured.', 'error')
        return redirect(url_for('admin.admin_panel'))
    
    current_status = data.get('stream_live', False)
    data['stream_live'] = not current_status
    
    save_tournament_data(data)
    
    if data['stream_live']:
        flash('🔴 Stream is now LIVE on the tournament page!', 'success')
    else:
        flash('⚫ Stream has been stopped and hidden from the tournament page.', 'info')
    
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/clear_stream', methods=['POST'])
@admin_required
def clear_stream():
    """Clear stream settings"""
    data = get_tournament_data()
    
    data.pop('twitch_channel', None)
    data.pop('stream_live', None)
    
    save_tournament_data(data)
    flash('Stream settings cleared.', 'success')
    return redirect(url_for('admin.admin_panel'))
