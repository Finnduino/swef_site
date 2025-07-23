from flask import Blueprint, render_template, redirect, request, url_for, session, flash, jsonify
import requests
import re
import random
from datetime import datetime, timedelta
from config import OSU_CLIENT_ID, OSU_CLIENT_SECRET, OSU_CALLBACK_URL, AUTHORIZATION_URL, TOKEN_URL, OSU_API_BASE_URL
from ..data_manager import get_tournament_data, save_tournament_data
from .. import api


player_bp = Blueprint('player', __name__, url_prefix='/player')


def player_required(f):
    """Decorator to check if user is authenticated as a tournament participant"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('public.osu_login'))
        
        # Check if user is a tournament participant
        data = get_tournament_data()
        user_id = session.get('user_id')
        if not any(c.get('id') == user_id for c in data.get('competitors', [])):
            flash('You must be a registered tournament participant to access this page.', 'error')
            return redirect(url_for('public.tournament'))
        
        return f(*args, **kwargs)
    return decorated_function


@player_bp.route('/profile')
@player_required
def profile():
    """Player profile page with mappool management"""
    user_id = session.get('user_id')
    data = get_tournament_data()
    
    # Find player data
    player = None
    for competitor in data.get('competitors', []):
        if competitor.get('id') == user_id:
            player = competitor
            break
    
    if not player:
        flash('Player data not found.', 'error')
        return redirect(url_for('public.tournament'))
    
    return render_template('player_profile.html', player=player, data=data)


@player_bp.route('/upload_mappool', methods=['POST'])
@player_required
def upload_mappool():
    """Upload or paste your mappool and save individual beatmap IDs."""
    user_id = session.get('user_id')
    playlist_url = request.form.get('playlist_url', '').strip()
    map_links    = request.form.get('map_links',    '').strip()

    # 1) If user pasted links, parse those
    if map_links:
        beatmap_ids = []
        for line in map_links.splitlines():
            url = line.strip()
            if not url:
                continue
            # try to grab the beatmap ID (last numeric segment after #osu/ or at end)
            m = re.search(r'#osu/(\d+)', url) or re.search(r'/(\d+)(?:$|\D)', url)
            if not m:
                flash('Invalid beatmap URL: {}'.format(url), 'error')
                return redirect(url_for('player.profile'))
            beatmap_ids.append(int(m.group(1)))
        if len(beatmap_ids) != 10:
            flash('Please paste exactly 10 beatmap links.', 'error')
            return redirect(url_for('player.profile'))

    # 2) Otherwise fetch from multiplayer room URL
    else:
        if not playlist_url:
            flash('Provide a multiplayer room URL or paste map links.', 'error')
            return redirect(url_for('player.profile'))

        if 'osu.ppy.sh' not in playlist_url or 'multiplayer' not in playlist_url:
            flash('Please provide a valid osu! multiplayer room URL.', 'error')
            return redirect(url_for('player.profile'))

        room_id = playlist_url.rstrip('/').split('/')[-1]
        try:
            # fetch room data via ossapi
            room_data = api.room(room_id)
            playlist = room_data.playlist if hasattr(room_data, 'playlist') else []
            
            # Extract beatmap IDs from playlist
            beatmap_ids = []
            for item in playlist:
                if hasattr(item, 'beatmap_id'):
                    beatmap_ids.append(item.beatmap_id)
                elif hasattr(item, 'beatmap') and hasattr(item.beatmap, 'id'):
                    beatmap_ids.append(item.beatmap.id)
                    
        except Exception as e:
            flash('Failed to fetch room data from osu! API: {}'.format(str(e)), 'error')
            return redirect(url_for('player.profile'))

        if len(beatmap_ids) != 10:
            flash('Room must contain exactly 10 beatmaps, found {}.'.format(len(beatmap_ids)), 'error')
            return redirect(url_for('player.profile'))

    # Fetch detailed beatmap information from osu! API
    try:
        beatmap_details = []
        for beatmap_id in beatmap_ids:
            try:
                beatmap = api.beatmap(beatmap_id)
                if beatmap:
                    detail = {
                        'id': beatmap_id,
                        'title': getattr(beatmap._beatmapset, 'title', 'Unknown Title') if hasattr(beatmap, '_beatmapset') else 'Unknown Title',
                        'artist': getattr(beatmap._beatmapset, 'artist', 'Unknown Artist') if hasattr(beatmap, '_beatmapset') else 'Unknown Artist',
                        'difficulty_name': getattr(beatmap, 'version', 'Unknown Difficulty'),
                        'mapper': getattr(beatmap._beatmapset, 'creator', 'Unknown Mapper') if hasattr(beatmap, '_beatmapset') else 'Unknown Mapper',
                        'length': getattr(beatmap, 'total_length', 0),
                        'bpm': getattr(beatmap, 'bpm', 0),
                        'cs': getattr(beatmap, 'cs', 0),
                        'od': getattr(beatmap, 'accuracy', 0),
                        'ar': getattr(beatmap, 'ar', 0),
                        'hp': getattr(beatmap, 'drain', 0),
                        'star_rating': getattr(beatmap, 'difficulty_rating', 0),
                        'url': 'https://osu.ppy.sh/beatmapsets/{}#osu/{}'.format(
                            getattr(beatmap._beatmapset, 'id', beatmap_id) if hasattr(beatmap, '_beatmapset') else beatmap_id,
                            beatmap_id
                        )
                    }
                    beatmap_details.append(detail)
                else:
                    # Fallback if beatmap data is not available
                    beatmap_details.append({
                        'id': beatmap_id,
                        'title': 'Unknown Title',
                        'artist': 'Unknown Artist', 
                        'difficulty_name': 'Unknown Difficulty',
                        'mapper': 'Unknown Mapper',
                        'length': 0,
                        'bpm': 0,
                        'cs': 0,
                        'od': 0,
                        'ar': 0,
                        'hp': 0,
                        'star_rating': 0,
                        'url': 'https://osu.ppy.sh/b/{}'.format(beatmap_id)
                    })
            except Exception as beatmap_error:
                flash('Warning: Could not fetch details for beatmap ID {}: {}'.format(beatmap_id, str(beatmap_error)), 'warning')
                # Add minimal data as fallback
                beatmap_details.append({
                    'id': beatmap_id,
                    'title': 'Unknown Title',
                    'artist': 'Unknown Artist',
                    'difficulty_name': 'Unknown Difficulty', 
                    'mapper': 'Unknown Mapper',
                    'length': 0,
                    'bpm': 0,
                    'cs': 0,
                    'od': 0,
                    'ar': 0,
                    'hp': 0,
                    'star_rating': 0,
                    'url': 'https://osu.ppy.sh/b/{}'.format(beatmap_id)
                })
                
    except Exception as e:
        flash('Error fetching beatmap details: {}'.format(str(e)), 'error')
        return redirect(url_for('player.profile'))

    # Save into tournament data
    data = get_tournament_data()
    for comp in data.get('competitors', []):
        if comp.get('id') == user_id:
            comp['mappool_ids'] = beatmap_ids
            comp['mappool_details'] = beatmap_details
            comp['mappool_url'] = playlist_url if not map_links else ''
            comp['mappool_uploaded'] = datetime.now().isoformat()
            break

    save_tournament_data(data)
    flash('Mappool saved (individual map IDs)!', 'success')
    return redirect(url_for('player.profile'))


@player_bp.route('/match/<string:match_id>')
@player_required
def match_interface(match_id):
    """Match interface for pick/ban and abilities"""
    user_id = session.get('user_id')
    data = get_tournament_data()
    
    # Find the match
    target_match = None
    for bracket_type in ['upper', 'lower', 'grand_finals']:
        if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
            if bracket_type == 'grand_finals':
                match = data['brackets'][bracket_type]
                if isinstance(match, dict) and match.get('id') == match_id:
                    target_match = match
                    break
            else:
                for round_matches in data['brackets'][bracket_type]:
                    for match in round_matches:
                        if match and match.get('id') == match_id:
                            target_match = match
                            break
                    if target_match:
                        break
        if target_match:
            break
    
    if not target_match:
        flash('Match not found.', 'error')
        return redirect(url_for('public.tournament'))
    
    # Check if user is a participant in this match
    player1_id = target_match.get('player1', {}).get('id')
    player2_id = target_match.get('player2', {}).get('id')
    
    if user_id not in [player1_id, player2_id]:
        flash('You are not a participant in this match.', 'error')
        return redirect(url_for('public.tournament'))
    
    # Check if match is ready for player interaction (status = next_up or in_progress)
    if target_match.get('status') not in ['next_up', 'in_progress']:
        flash('This match is not ready for player interaction.', 'info')
        return redirect(url_for('public.match_details', match_id=match_id))
    
    # Get opponent
    opponent_id = player2_id if user_id == player1_id else player1_id
    is_player1 = user_id == player1_id
    
    # Get mappool data for both players
    player_mappool = None
    opponent_mappool = None
    player_mappool_ids = []
    opponent_mappool_ids = []
    player_mappool_details = []
    opponent_mappool_details = []
    
    for competitor in data.get('competitors', []):
        if competitor.get('id') == user_id:
            player_mappool = competitor.get('mappool_url')
            player_mappool_ids = competitor.get('mappool_ids', [])
            player_mappool_details = competitor.get('mappool_details', [])
        elif competitor.get('id') == opponent_id:
            opponent_mappool = competitor.get('mappool_url')
            opponent_mappool_ids = competitor.get('mappool_ids', [])
            opponent_mappool_details = competitor.get('mappool_details', [])
    
    return render_template('match_interface.html', 
                         match=target_match,
                         player_mappool=player_mappool,
                         opponent_mappool=opponent_mappool,
                         player_mappool_ids=player_mappool_ids,
                         opponent_mappool_ids=opponent_mappool_ids,
                         player_mappool_details=player_mappool_details,
                         opponent_mappool_details=opponent_mappool_details,
                         is_player1=is_player1,
                         data=data)


@player_bp.route('/match/<string:match_id>/action', methods=['POST'])
@player_required
def match_action(match_id):
    """Handle pick/ban/ability actions in a match"""
    user_id = session.get('user_id')
    action_type = request.form.get('action_type')  # 'ban', 'pick', 'ability'
    target_map = request.form.get('target_map')   # map identifier
    ability_type = request.form.get('ability_type')  # for abilities
    mod_choice = request.form.get('mod_choice')   # for mod abilities
    
    print(f"DEBUG: match_action called with action_type={action_type}, target_map={target_map}, ability_type={ability_type}, mod_choice={mod_choice}")
    
    data = get_tournament_data()
    
    # Find the match
    target_match = None
    for bracket_type in ['upper', 'lower', 'grand_finals']:
        if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
            if bracket_type == 'grand_finals':
                match = data['brackets'][bracket_type]
                if isinstance(match, dict) and match.get('id') == match_id:
                    target_match = match
                    break
            else:
                for round_matches in data['brackets'][bracket_type]:
                    for match in round_matches:
                        if match and match.get('id') == match_id:
                            target_match = match
                            break
                    if target_match:
                        break
        if target_match:
            break
    
    if not target_match:
        return jsonify({'error': 'Match not found'}), 404
    
    # Verify user participation
    player1_id = target_match.get('player1', {}).get('id')
    player2_id = target_match.get('player2', {}).get('id')
    
    if user_id not in [player1_id, player2_id]:
        return jsonify({'error': 'Unauthorized'}), 403
    
    is_player1 = user_id == player1_id
    
    # Initialize match state if not exists
    if 'match_state' not in target_match:
        # Random coin flip to determine who goes first
        first_player = random.choice(['player1', 'player2'])
        
        target_match['match_state'] = {
            'phase': 'ban',  # ban -> pick -> play
            'current_turn': first_player,  # who's turn it is (randomly chosen)
            'first_player': first_player,  # store who goes first for UI display
            'banned_maps': [],
            'picked_maps': [],
            'abilities_used': {
                'player1': {
                    'force_nomod': False,
                    'force_mod': False,
                    'personal_mod': 0  # can use twice
                },
                'player2': {
                    'force_nomod': False,
                    'force_mod': False,
                    'personal_mod': 0
                }
            },
            'map_mods': {},  # map_id -> mod requirements
            'action_history': [{
                'type': 'system',
                'message': f'{target_match["player1"]["name"] if first_player == "player1" else target_match["player2"]["name"]} won the coin flip and will go first!',
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }]  # Track all actions for the feed
        }
    
    match_state = target_match['match_state']
    player_key = 'player1' if is_player1 else 'player2'
    
    # Check if interface should be locked - after EACH pick, require a point to be scored
    current_score_total = target_match.get('score_p1', 0) + target_match.get('score_p2', 0)
    picks_made = len(match_state.get('picked_maps', []))
    
    # Lock logic: After ANY pick, require a corresponding point to be scored before the next pick
    if action_type == 'pick' and picks_made > 0 and current_score_total < picks_made:
        return jsonify({'error': 'Cannot make new pick until the previous round result is recorded (need point for last pick)'}), 400
    
    # Check if it's the player's turn or if they have a Force NoMod counter opportunity
    has_counter_opportunity = (
        'pending_force_nomod_counter' in match_state and 
        match_state['pending_force_nomod_counter']['target_player'] == player_key
    )
    
    # Check if player just picked and is using an ability on their own pick
    just_picked_ability = False
    if action_type == 'ability' and match_state.get('picked_maps'):
        last_picked = match_state['picked_maps'][-1]
        if last_picked.get('picked_by') == player_key:
            just_picked_ability = True
    
    # Allow abilities to be used more flexibly - not just after picks
    is_ability_action = action_type in ['ability', 'force_nomod_counter', 'skip_force_nomod_counter']
    
    print(f"DEBUG: current_turn={match_state['current_turn']}, player_key={player_key}, has_counter={has_counter_opportunity}, just_picked_ability={just_picked_ability}, is_ability={is_ability_action}")
    
    # More flexible turn checking for abilities
    if action_type in ['ban', 'pick']:
        # Strict turn checking for ban/pick actions
        if match_state['current_turn'] != player_key:
            print(f"DEBUG: Turn check failed for {action_type} - not player's turn")
            return jsonify({'error': 'Not your turn'}), 400
    elif action_type in ['force_nomod_counter', 'skip_force_nomod_counter']:
        # Counter actions only require the counter opportunity
        if not has_counter_opportunity:
            print(f"DEBUG: Counter action failed - no counter opportunity")
            return jsonify({'error': 'No counter opportunity available'}), 400
    elif action_type == 'ability':
        # Abilities can be used after picking or during certain phases
        # Allow if: it's their turn, they just picked, or it's during pick phase and they have picked maps
        if (match_state['current_turn'] != player_key and 
            not just_picked_ability and 
            not (match_state['phase'] == 'pick' and match_state.get('picked_maps'))):
            print(f"DEBUG: Ability check failed - not the right time to use abilities")
            return jsonify({'error': 'Cannot use abilities at this time'}), 400
    
    # Process the action
    try:
        if action_type == 'ban':
            if match_state['phase'] != 'ban':
                return jsonify({'error': 'Ban phase is over'}), 400
            
            if target_map in match_state['banned_maps']:
                return jsonify({'error': 'Map already banned'}), 400
            
            match_state['banned_maps'].append(target_map)
            
            # Add to action history
            player_name = target_match.get('player1', {}).get('name') if is_player1 else target_match.get('player2', {}).get('name')
            match_state['action_history'].append({
                'type': 'ban',
                'player': player_name or f'Player {1 if is_player1 else 2}',
                'map': f'Map {target_map}',
                'timestamp': 'Just now'
            })
            
            # Switch turns and check if ban phase is complete (6 bans total, 3 each)
            match_state['current_turn'] = 'player2' if is_player1 else 'player1'
            
            if len(match_state['banned_maps']) >= 6:
                match_state['phase'] = 'pick'
                # First pick goes to random player (for now, player1)
                match_state['current_turn'] = 'player1'
        
        elif action_type == 'pick':
            if match_state['phase'] != 'pick':
                return jsonify({'error': 'Pick phase not active'}), 400
            
            if target_map in match_state['banned_maps']:
                return jsonify({'error': 'Cannot pick banned map'}), 400
            
            if target_map in [m['map_id'] for m in match_state['picked_maps']]:
                return jsonify({'error': 'Map already picked'}), 400
            
            match_state['picked_maps'].append({
                'map_id': target_map,
                'picked_by': player_key,
                'order': len(match_state['picked_maps']) + 1
            })
            
            # Add to action history
            player_name = target_match.get('player1', {}).get('name') if is_player1 else target_match.get('player2', {}).get('name')
            match_state['action_history'].append({
                'type': 'pick',
                'player': player_name or f'Player {1 if is_player1 else 2}',
                'map': f'Map {target_map}',
                'timestamp': 'Just now'
            })
            
            # Switch turns for alternating picks
            # After bans complete, picks alternate with loser-picks-first after each round
            match_state['current_turn'] = 'player2' if is_player1 else 'player1'
            
            # Phase management - we stay in pick phase, but after each pick we wait for scoring
            if len(match_state['picked_maps']) >= 1:
                match_state['phase'] = 'pick'  # Stay in pick phase for alternating picks
        
        elif action_type == 'ability':
            print(f"DEBUG: Processing ability - ability_type={ability_type}, target_map={target_map}, mod_choice={mod_choice}")
            abilities = match_state['abilities_used'][player_key]
            
            if ability_type == 'force_nomod':
                if abilities['force_nomod']:
                    return jsonify({'error': 'Force NoMod already used'}), 400
                abilities['force_nomod'] = True
                match_state['map_mods'][target_map] = 'nomod'
                
                # Add to action history
                player_name = target_match.get('player1', {}).get('name') if is_player1 else target_match.get('player2', {}).get('name')
                match_state['action_history'].append({
                    'type': 'ability',
                    'player': player_name or f'Player {1 if is_player1 else 2}',
                    'ability': 'Force NoMod',
                    'map': f'Map {target_map}',
                    'timestamp': 'Just now'
                })
            
            elif ability_type == 'force_mod':
                if abilities['force_mod']:
                    return jsonify({'error': 'Force Mod already used'}), 400
                if not mod_choice:
                    return jsonify({'error': 'Mod choice required'}), 400
                abilities['force_mod'] = True
                match_state['map_mods'][target_map] = mod_choice
                
                # Add to action history
                player_name = target_match.get('player1', {}).get('name') if is_player1 else target_match.get('player2', {}).get('name')
                match_state['action_history'].append({
                    'type': 'ability',
                    'player': player_name or f'Player {1 if is_player1 else 2}',
                    'ability': f'Force Mod ({mod_choice.upper()})',
                    'map': f'Map {target_map}',
                    'timestamp': 'Just now'
                })
            
            elif ability_type == 'personal_mod':
                print(f"DEBUG: Personal Mod - current usage: {abilities['personal_mod']}, mod_choice: {mod_choice}")
                if abilities['personal_mod'] >= 2:
                    return jsonify({'error': 'Personal Mod used maximum times'}), 400
                if not mod_choice:
                    return jsonify({'error': 'Mod choice required'}), 400
                abilities['personal_mod'] += 1
                match_state['map_mods'][target_map] = {
                    'type': 'personal',
                    'player': player_key,
                    'mod': mod_choice
                }
                
                # Add to action history
                player_name = target_match.get('player1', {}).get('name') if is_player1 else target_match.get('player2', {}).get('name')
                match_state['action_history'].append({
                    'type': 'ability',
                    'player': player_name or f'Player {1 if is_player1 else 2}',
                    'ability': f'Personal Mod ({mod_choice.upper()})',
                    'map': f'Map {target_map}',
                    'timestamp': 'Just now'
                })
                
                print(f"DEBUG: Applied Personal Mod - map_mods now: {match_state['map_mods']}")
                
                # Create Force NoMod counter opportunity for opponent
                opponent_key = 'player2' if player_key == 'player1' else 'player1'
                opponent_abilities = match_state['abilities_used'][opponent_key]
                
                print(f"DEBUG: Checking opponent Force NoMod - used: {opponent_abilities['force_nomod']}")
                
                # Only offer counter if opponent hasn't used Force NoMod yet
                if not opponent_abilities['force_nomod']:
                    # Try to get the actual map name
                    map_name = f'Map {target_map}'
                    
                    # Find map details from player mappools
                    for competitor in data.get('competitors', []):
                        if competitor.get('mappool_details'):
                            for map_detail in competitor['mappool_details']:
                                if str(map_detail.get('id')) == str(target_map):
                                    map_name = map_detail.get('title', map_name)
                                    break
                    
                    counter_data = {
                        'target_player': opponent_key,
                        'map_id': target_map,
                        'map_name': map_name,
                        'opponent_mod': mod_choice,
                        'personal_mod_player': player_key
                    }
                    match_state['pending_force_nomod_counter'] = counter_data
                    print(f"DEBUG: Created Force NoMod counter opportunity: {counter_data}")
                else:
                    print(f"DEBUG: No counter opportunity - opponent already used Force NoMod")
        
        elif action_type == 'force_nomod_counter':
            # Handle Force NoMod counter to Personal Mod
            if 'pending_force_nomod_counter' not in match_state:
                return jsonify({'error': 'No Force NoMod counter opportunity available'}), 400
            
            counter_data = match_state['pending_force_nomod_counter']
            if counter_data['target_player'] != player_key:
                return jsonify({'error': 'This counter opportunity is not for you'}), 400
            
            abilities = match_state['abilities_used'][player_key]
            if abilities['force_nomod']:
                return jsonify({'error': 'Force NoMod already used'}), 400
            
            # Use Force NoMod to counter the Personal Mod
            abilities['force_nomod'] = True
            match_state['map_mods'][target_map] = 'nomod'  # Override the personal mod
            
            # Remove the counter opportunity
            del match_state['pending_force_nomod_counter']
        
        elif action_type == 'skip_force_nomod_counter':
            # Handle skipping Force NoMod counter
            if 'pending_force_nomod_counter' not in match_state:
                return jsonify({'error': 'No Force NoMod counter opportunity available'}), 400
            
            counter_data = match_state['pending_force_nomod_counter']
            if counter_data['target_player'] != player_key:
                return jsonify({'error': 'This counter opportunity is not for you'}), 400
            
            # Remove the counter opportunity without using Force NoMod
            del match_state['pending_force_nomod_counter']
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    save_tournament_data(data)
    return jsonify({
        'success': True,
        'match_state': match_state
    })


@player_bp.route('/match/<string:match_id>/state')
@player_required
def match_state(match_id):
    """Get current match state"""
    user_id = session.get('user_id')
    data = get_tournament_data()
    
    # Find the match
    target_match = None
    for bracket_type in ['upper', 'lower', 'grand_finals']:
        if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
            if bracket_type == 'grand_finals':
                match = data['brackets'][bracket_type]
                if isinstance(match, dict) and match.get('id') == match_id:
                    target_match = match
                    break
            else:
                for round_matches in data['brackets'][bracket_type]:
                    for match in round_matches:
                        if match and match.get('id') == match_id:
                            target_match = match
                            break
                    if target_match:
                        break
        if target_match:
            break
    
    if not target_match:
        return jsonify({'error': 'Match not found'}), 404
    
    # Verify user participation
    player1_id = target_match.get('player1', {}).get('id')
    player2_id = target_match.get('player2', {}).get('id')
    
    if user_id not in [player1_id, player2_id]:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'match_state': target_match.get('match_state', {}),
        'match_info': {
            'id': target_match.get('id'),
            'status': target_match.get('status'),
            'player1': target_match.get('player1'),
            'player2': target_match.get('player2'),
            'score_p1': target_match.get('score_p1', 0),
            'score_p2': target_match.get('score_p2', 0)
        }
    })
