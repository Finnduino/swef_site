from datetime import datetime
from .. import api


def get_detailed_match_results(room_id, player1_id, player2_id):
    """
    Fetch detailed match results including map-by-map breakdown with player stats
    Returns: dict with map results and player details
    """
    assert(player1_id != player2_id), "Players must be different"
    
    try:
        
        # Get room details
        room = api.room(room_id)
        
        if not room.playlist:
            print("No playlist found in room")
            return None
        
        # Get player details
        try:
            player1 = api.user(str(player1_id))
            player2 = api.user(str(player2_id))
        except Exception as e:
            print(f"Error fetching player details: {e}")
            player1 = {'id': player1_id, 'username': f'Player {player1_id}'}
            player2 = {'id': player2_id, 'username': f'Player {player2_id}'}
        
        map_results = []
        player1_wins = 0
        player2_wins = 0
        
        # Process each map
        for i, playlist_item in enumerate(room.playlist):
            try:
                
                # Get scores for this map
                scores_data = api.multiplayer_scores(room_id, playlist_item.id)
                
                # Find scores for both players
                p1_score = None
                p2_score = None
                
                for score in scores_data.scores:
                    if score.user_id == player1_id:
                        p1_score = score
                    elif score.user_id == player2_id:
                        p2_score = score
                
                # Get beatmap details - fix the beatmap ID access
                try:
                    beatmap_id = None

                    # try direct beatmap_id
                    if hasattr(playlist_item, 'beatmap_id'):
                        beatmap_id = playlist_item.beatmap_id
                    elif hasattr(playlist_item, 'beatmap'):
                        beatmap_obj = playlist_item.beatmap
                        if callable(beatmap_obj):
                            try:
                                beatmap_obj = beatmap_obj()
                            except Exception:
                                beatmap_obj = None
                        if beatmap_obj and hasattr(beatmap_obj, 'id'):
                            beatmap_id = beatmap_obj.id
                        elif isinstance(beatmap_obj, (int, str)):
                            beatmap_id = int(beatmap_obj)

                    # alternative attributes
                    if not beatmap_id:
                        for attr_name in ['map_id', 'beatmap_id', 'id']:
                            if hasattr(playlist_item, attr_name):
                                val = getattr(playlist_item, attr_name)
                                if isinstance(val, (int, str)) and str(val).isdigit():
                                    beatmap_id = int(val)
                                    break

                    if beatmap_id:
                        try:
                            beatmap = api.beatmap(beatmap_id)
                            if not hasattr(beatmap, 'id') or not hasattr(beatmap, 'beatmapset'):
                                beatmap_dict = None
                            else:
                                # Convert beatmap to dict for JSON serialization
                                beatmap_dict = {
                                    'id': beatmap.id,
                                    'beatmapset_id': getattr(beatmap, 'beatmapset_id', None),
                                    'mode': str(getattr(beatmap, 'mode', None)),  # Convert GameMode to string
                                    'difficulty_rating': getattr(beatmap, 'difficulty_rating', None),
                                    'version': getattr(beatmap, 'version', 'Unknown'),
                                    'total_length': getattr(beatmap, 'total_length', None),
                                    'hit_length': getattr(beatmap, 'hit_length', None),
                                    'bpm': getattr(beatmap, 'bpm', None),
                                    'cs': getattr(beatmap, 'cs', None),
                                    'ar': getattr(beatmap, 'ar', None),
                                    'od': getattr(beatmap, 'accuracy', None),
                                    'hp': getattr(beatmap, 'drain', None),
                                    'count_circles': getattr(beatmap, 'count_circles', None),
                                    'count_sliders': getattr(beatmap, 'count_sliders', None),
                                    'count_spinners': getattr(beatmap, 'count_spinners', None),
                                }
                                
                                # Handle beatmapset safely
                                if hasattr(beatmap, 'beatmapset') and beatmap.beatmapset:
                                    try:
                                        beatmapset_covers = {}
                                        if hasattr(beatmap.beatmapset, 'covers'):
                                            # Convert covers to dict safely
                                            covers_obj = beatmap.beatmapset.covers
                                            if hasattr(covers_obj, '_asdict'):
                                                beatmapset_covers = covers_obj._asdict()
                                            elif hasattr(covers_obj, '__dict__'):
                                                beatmapset_covers = {k: v for k, v in covers_obj.__dict__.items() if not k.startswith('_')}
                                            else:
                                                # Try to convert common cover attributes
                                                for attr in ['cover', 'cover@2x', 'card', 'card@2x', 'list', 'list@2x', 'slimcover', 'slimcover@2x']:
                                                    if hasattr(covers_obj, attr.replace('@', '_')):  # Handle @2x -> _2x
                                                        safe_attr = attr.replace('@', '_')
                                                        beatmapset_covers[attr] = getattr(covers_obj, safe_attr, None)
                                        
                                        beatmap_dict['beatmapset'] = {
                                            'id': getattr(beatmap._beatmapset, 'id', None),
                                            'title': getattr(beatmap._beatmapset, 'title', 'Unknown'),
                                            'artist': getattr(beatmap._beatmapset, 'artist', 'Unknown'),
                                            'creator': getattr(beatmap._beatmapset, 'creator', 'Unknown'),
                                            'covers': beatmapset_covers
                                        }
                                    except Exception as beatmapset_e:
                                        print(f"Error processing beatmapset: {beatmapset_e}")
                                        beatmap_dict['beatmapset'] = {
                                            'id': None,
                                            'title': 'Unknown',
                                            'artist': 'Unknown', 
                                            'creator': 'Unknown',
                                            'covers': {}
                                        }
                                else:
                                    beatmap_dict['beatmapset'] = {
                                        'id': None,
                                        'title': 'Unknown',
                                        'artist': 'Unknown',
                                        'creator': 'Unknown', 
                                        'covers': {}
                                    }
                                
                        except Exception as beatmap_e:
                            print(f"Error calling api.beatmap({beatmap_id}): {beatmap_e}")
                            beatmap_dict = None
                    else:
                        beatmap_dict = None
                        beatmap_id = 'unknown'
                        
                except Exception as e:
                    print(f"Error in beatmap processing section: {e}")
                    beatmap_dict = None
                
                # Convert scores to dict for JSON serialization
                p1_score_dict = None
                p2_score_dict = None
                
                if p1_score:
                    # Handle statistics object safely
                    statistics_dict = None
                    if p1_score.statistics:
                        try:
                            statistics_dict = {
                                'count_300': getattr(p1_score.statistics, 'great', 0),
                                'count_100': getattr(p1_score.statistics, 'ok', 0), 
                                'count_50': getattr(p1_score.statistics, 'meh', 0),
                                'count_miss': getattr(p1_score.statistics, 'miss', 0)
                            }
                        except Exception as e:
                            print(f"Error processing player 1 statistics: {e}")
                            # Try alternative attribute names
                            try:
                                statistics_dict = {
                                    'count_300': getattr(p1_score.statistics, 'perfect', 0),
                                    'count_100': getattr(p1_score.statistics, 'great', 0),
                                    'count_50': getattr(p1_score.statistics, 'good', 0),
                                    'count_miss': getattr(p1_score.statistics, 'miss', 0)
                                }
                            except Exception:
                                statistics_dict = None
                    
                    # Extract mod acronyms from mod objects
                    mods_list = []
                    if p1_score.mods:
                        for mod in p1_score.mods:
                            if isinstance(mod, dict) and 'acronym' in mod:
                                statistics_dict = None
                    if p1_score.statistics:
                        try:
                            statistics_dict = {
                                'count_300': getattr(p1_score.statistics, 'great', 0),
                                'count_100': getattr(p1_score.statistics, 'ok', 0), 
                                'count_50': getattr(p1_score.statistics, 'meh', 0),
                                'count_miss': getattr(p1_score.statistics, 'miss', 0)
                            }
                        except Exception as e:
                            print(f"Error processing player 1 statistics: {e}")
                            # Try alternative attribute names
                            try:
                                statistics_dict = {
                                    'count_300': getattr(p1_score.statistics, 'perfect', 0),
                                    'count_100': getattr(p1_score.statistics, 'great', 0),
                                    'count_50': getattr(p1_score.statistics, 'good', 0),
                                    'count_miss': getattr(p1_score.statistics, 'miss', 0)
                                }
                            except Exception:
                                statistics_dict = None
                    
                    # Extract mod acronyms from mod objects
                    mods_list = []
                    if p1_score.mods:
                        for mod in p1_score.mods:
                            if isinstance(mod, dict) and 'acronym' in mod:
                                mods_list.append(mod['acronym'])
                            elif hasattr(mod, 'acronym'):
                                mods_list.append(mod.acronym)
                            elif hasattr(mod, 'mod'):  # Some versions might have mod.mod
                                mods_list.append(str(mod.mod))
                            else:
                                mods_list.append(str(mod))
                    
                    p1_score_dict = {
                        'user_id': p1_score.user_id,
                        'total_score': p1_score.total_score,
                        'accuracy': p1_score.accuracy,
                        'max_combo': p1_score.max_combo,
                        'mods': mods_list,
                        'statistics': statistics_dict
                    }
                
                if p2_score:
                    # Handle statistics object safely
                    statistics_dict = None
                    if p2_score.statistics:
                        try:
                            statistics_dict = {
                                'count_300': getattr(p2_score.statistics, 'count_300', 0),
                                'count_100': getattr(p2_score.statistics, 'count_100', 0),
                                'count_50': getattr(p2_score.statistics, 'count_50', 0),
                                'count_miss': getattr(p2_score.statistics, 'count_miss', 0)
                            }
                        except Exception as e:
                            print(f"Error processing player 2 statistics: {e}")
                            # Try alternative attribute names
                            try:
                                statistics_dict = {
                                    'count_300': getattr(p2_score.statistics, 'perfect', 0),
                                    'count_100': getattr(p2_score.statistics, 'great', 0),
                                    'count_50': getattr(p2_score.statistics, 'good', 0),
                                    'count_miss': getattr(p2_score.statistics, 'miss', 0)
                                }
                            except Exception:
                                statistics_dict = None
                    
                    # Extract mod acronyms from mod objects
                    mods_list = []
                    if p2_score.mods:
                        for mod in p2_score.mods:
                            if isinstance(mod, dict) and 'acronym' in mod:
                                mods_list.append(mod['acronym'])
                            elif hasattr(mod, 'acronym'):
                                mods_list.append(mod.acronym)
                            elif hasattr(mod, 'mod'):  # Some versions might have mod.mod
                                mods_list.append(str(mod.mod))
                            else:
                                mods_list.append(str(mod))
                    
                    p2_score_dict = {
                        'user_id': p2_score.user_id,
                        'total_score': p2_score.total_score,
                        'accuracy': p2_score.accuracy,
                        'max_combo': p2_score.max_combo,
                        'mods': mods_list,
                        'statistics': statistics_dict
                    }
                
                # Determine map winner
                map_winner = None
                if p1_score and p2_score:
                    if p1_score.total_score > p2_score.total_score:
                        map_winner = 'player1'
                        player1_wins += 1
                    elif p2_score.total_score > p1_score.total_score:
                        map_winner = 'player2'
                        player2_wins += 1
                elif p1_score and not p2_score:
                    map_winner = 'player1'
                    player1_wins += 1
                elif p2_score and not p1_score:
                    map_winner = 'player2'
                    player2_wins += 1
                
                map_result = {
                    'map_number': i + 1,
                    'beatmap': beatmap_dict,
                    'playlist_item_id': playlist_item.id,
                    'beatmap_id': beatmap_id,
                    'player1_score': p1_score_dict,
                    'player2_score': p2_score_dict,
                    'winner': map_winner,
                    'completed': bool(p1_score or p2_score)
                }
                
                map_results.append(map_result)
                
            except Exception as e:
                print(f"Error processing map {i+1}: {e}")
                # Add empty result for failed map
                map_results.append({
                    'map_number': i + 1,
                    'beatmap': None,
                    'playlist_item_id': playlist_item.id,
                    'beatmap_id': 'error',
                    'player1_score': None,
                    'player2_score': None,
                    'winner': None,
                    'completed': False,
                    'error': str(e)
                })
                continue
        
        # Convert player objects to dicts for JSON serialization
        player1_dict = {
            'id': player1.id if hasattr(player1, 'id') else player1.get('id'),
            'username': player1.username if hasattr(player1, 'username') else player1.get('username'),
            'avatar_url': player1.avatar_url if hasattr(player1, 'avatar_url') else player1.get('avatar_url'),
            'statistics': {
                'pp': player1.statistics.pp,
                'global_rank': player1.statistics.global_rank
            } if hasattr(player1, 'statistics') and player1.statistics else None
        }
        
        player2_dict = {
            'id': player2.id if hasattr(player2, 'id') else player2.get('id'),
            'username': player2.username if hasattr(player2, 'username') else player2.get('username'),
            'avatar_url': player2.avatar_url if hasattr(player2, 'avatar_url') else player2.get('avatar_url'),
            'statistics': {
                'pp': player2.statistics.pp,
                'global_rank': player2.statistics.global_rank
            } if hasattr(player2, 'statistics') and player2.statistics else None
        }
        
        return {
            'room_id': room_id,
            'room_name': room.name if hasattr(room, 'name') else f'Room {room_id}',
            'player1': player1_dict,
            'player2': player2_dict,
            'player1_wins': player1_wins,
            'player2_wins': player2_wins,
            'map_results': map_results,
            'match_completed': player1_wins >= 4 or player2_wins >= 4,
            'last_updated': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Error fetching detailed match results: {e}")
        return None
