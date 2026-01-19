"""
Replacement for websocket_events.py - using overlay state instead of SocketIO
These functions are kept for compatibility but now use HTTP polling system
"""

from .data_manager import get_tournament_data

def get_current_match_data():
    """Get current match data for overlay (used by HTTP polling API)"""
    try:
        data = get_tournament_data()
        
        # Find current live match or next upcoming match with round priority
        current_match = None
        bracket_type = None
        round_index = 0
        
        # Determine max rounds to search through
        max_rounds = 10
        if 'upper' in data.get('brackets', {}):
            max_rounds = len(data['brackets']['upper'])
        if 'lower' in data.get('brackets', {}) and len(data['brackets']['lower']) > max_rounds:
            max_rounds = len(data['brackets']['lower'])
        
        # First look for in_progress matches with round priority
        for round_num in range(1, max_rounds + 1):
            if current_match:
                break
                
            # Check upper bracket round first
            if 'upper' in data.get('brackets', {}) and len(data['brackets']['upper']) >= round_num:
                round_matches = data['brackets']['upper'][round_num - 1]
                for match in round_matches:
                    if match and match.get('status') == 'in_progress':
                        current_match = match
                        bracket_type = 'Upper'
                        round_index = round_num - 1
                        break
            
            # Then check lower bracket round
            if not current_match and 'lower' in data.get('brackets', {}) and len(data['brackets']['lower']) >= round_num:
                round_matches = data['brackets']['lower'][round_num - 1]
                for match in round_matches:
                    if match and match.get('status') == 'in_progress':
                        current_match = match
                        bracket_type = 'Lower'
                        round_index = round_num - 1
                        break
        
        # Check grand finals for in_progress
        if not current_match and 'grand_finals' in data.get('brackets', {}):
            match = data['brackets']['grand_finals']
            if match and match.get('status') == 'in_progress':
                current_match = match
                bracket_type = 'Grand Finals'
        
        # If no in_progress match found, look for next_up matches with same round priority
        if not current_match:
            for round_num in range(1, max_rounds + 1):
                if current_match:
                    break
                    
                # Check upper bracket round first
                if 'upper' in data.get('brackets', {}) and len(data['brackets']['upper']) >= round_num:
                    round_matches = data['brackets']['upper'][round_num - 1]
                    for match in round_matches:
                        if match and match.get('status') == 'next_up':
                            current_match = match
                            bracket_type = 'Upper'
                            round_index = round_num - 1
                            break
                
                # Then check lower bracket round
                if not current_match and 'lower' in data.get('brackets', {}) and len(data['brackets']['lower']) >= round_num:
                    round_matches = data['brackets']['lower'][round_num - 1]
                    for match in round_matches:
                        if match and match.get('status') == 'next_up':
                            current_match = match
                            bracket_type = 'Lower'
                            round_index = round_num - 1
                            break
            
            # Check grand finals for next_up
            if not current_match and 'grand_finals' in data.get('brackets', {}):
                match = data['brackets']['grand_finals']
                if match and match.get('status') == 'next_up':
                    current_match = match
                    bracket_type = 'Grand Finals'
        
        if current_match:
            # Find current/last picked map for display
            current_map = None
            match_state = current_match.get('match_state', {})
            picked_maps = match_state.get('picked_maps', [])
            
            if picked_maps:
                # Get the last picked map details
                last_picked = picked_maps[-1]
                map_id = last_picked.get('map_id')
                
                # Find the map details from player mappools
                player1_mappool = current_match.get('player1', {}).get('mappool_details', [])
                player2_mappool = current_match.get('player2', {}).get('mappool_details', [])
                combined_mappool = player1_mappool + player2_mappool
                
                for map_details in combined_mappool:
                    if str(map_details.get('id')) == str(map_id):
                        current_map = map_details
                        break
            
            return {
                'match_found': True,
                'player1': current_match.get('player1', {}),
                'player2': current_match.get('player2', {}),
                'score_p1': current_match.get('score_p1', 0),
                'score_p2': current_match.get('score_p2', 0),
                'status': current_match.get('status', 'unknown'),
                'bracket': bracket_type,
                'round_index': round_index,
                'tiebreaker_map_url': current_match.get('tiebreaker_map_url'),
                'is_tiebreaker': current_match.get('score_p1', 0) == 3 and current_match.get('score_p2', 0) == 3,
                'current_map': current_map,
                'picked_maps': picked_maps,
                'phase': match_state.get('phase', 'waiting'),
                'interface_locked': len(picked_maps) > 0 and (current_match.get('score_p1', 0) + current_match.get('score_p2', 0)) < len(picked_maps)
            }
        
        return {
            'match_found': False,
            'message': 'No active or upcoming matches found'
        }
    
    except (KeyError, AttributeError, TypeError) as e:
        print(f"Error getting match data: {e}")
        return {
            'match_found': False,
            'message': f'Error loading match data: {str(e)}'
        }

# Legacy compatibility functions - now emit both WebSocket and file-based events
def broadcast_match_update():
    """Broadcast match update via WebSocket and file-based system"""
    from .overlay_state import add_overlay_event
    add_overlay_event('match_update')
    
    # Also emit WebSocket event
    try:
        from .websocket_events import broadcast_match_update as ws_broadcast
        ws_broadcast()
    except Exception as e:
        print(f"[WS] Failed to broadcast match_update: {e}")

def broadcast_map_victory(winner_name, map_info=None):
    """Broadcast map victory via WebSocket and file-based system"""
    from .overlay_state import add_overlay_event
    data = {
        'winner': winner_name,
        'map_info': map_info or {'title': 'Map Complete'}
    }
    add_overlay_event('map_victory', data)
    
    # Also emit WebSocket event
    try:
        from .websocket_events import broadcast_map_victory as ws_broadcast
        ws_broadcast(winner_name, map_info)
    except Exception as e:
        print(f"[WS] Failed to broadcast map_victory: {e}")

def broadcast_match_victory(winner_name, final_score, advancement_info=""):
    """Broadcast match victory via WebSocket and file-based system"""
    from .overlay_state import add_overlay_event
    add_overlay_event('match_victory', {
        'winner': winner_name,
        'final_score': final_score,
        'advancement': advancement_info
    })
    
    # Also emit WebSocket event
    try:
        from .websocket_events import broadcast_match_victory as ws_broadcast
        ws_broadcast(winner_name, final_score, advancement_info)
    except Exception as e:
        print(f"[WS] Failed to broadcast match_victory: {e}")

def broadcast_exit_afk():
    """Broadcast exit AFK via WebSocket and file-based system"""
    from .overlay_state import add_overlay_event
    add_overlay_event('exit_afk')
    
    # Also emit WebSocket event
    try:
        from .websocket_events import broadcast_exit_afk as ws_broadcast
        ws_broadcast()
    except Exception as e:
        print(f"[WS] Failed to broadcast exit_afk: {e}")

def broadcast_flip_players():
    """Broadcast flip players via WebSocket and file-based system"""
    from .overlay_state import add_overlay_event
    add_overlay_event('flip_players')
    
    # Also emit WebSocket event
    try:
        from .websocket_events import broadcast_flip_players as ws_broadcast
        ws_broadcast()
    except Exception as e:
        print(f"[WS] Failed to broadcast flip_players: {e}")
