"""
Replacement for websocket_events.py - using overlay state instead of SocketIO
These functions are kept for compatibility but now use HTTP polling system
"""

from .data_manager import get_tournament_data

def get_current_match_data():
    """Get current match data for overlay (used by HTTP polling API)"""
    try:
        data = get_tournament_data()
        
        # Find current live match or next upcoming match
        current_match = None
        bracket_type = None
        round_index = 0
        
        # Check grand finals first
        if 'grand_finals' in data.get('brackets', {}):
            match = data['brackets']['grand_finals']
            if match and match.get('status') in ['in_progress', 'next_up']:
                current_match = match
                bracket_type = 'Grand Finals'
        
        # Check upper bracket
        if not current_match and 'upper' in data.get('brackets', {}):
            for round_idx, round_matches in enumerate(data['brackets']['upper']):
                for match in round_matches:
                    if match and match.get('status') in ['in_progress', 'next_up']:
                        current_match = match
                        bracket_type = 'Upper'
                        round_index = round_idx
                        break
                if current_match:
                    break
        
        # Check lower bracket
        if not current_match and 'lower' in data.get('brackets', {}):
            for round_idx, round_matches in enumerate(data['brackets']['lower']):
                for match in round_matches:
                    if match and match.get('status') in ['in_progress', 'next_up']:
                        current_match = match
                        bracket_type = 'Lower'
                        round_index = round_idx
                        break
                if current_match:
                    break
        
        if current_match:
            return {
                'match_found': True,
                'player1': current_match.get('player1', {}),
                'player2': current_match.get('player2', {}),
                'score_p1': current_match.get('score_p1', 0),
                'score_p2': current_match.get('score_p2', 0),
                'status': current_match.get('status', 'unknown'),
                'bracket': bracket_type,
                'round_index': round_index
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

# Legacy compatibility functions (no longer use SocketIO)
def broadcast_match_update():
    """Legacy function - now handled by overlay state system"""
    from .overlay_state import add_overlay_event
    add_overlay_event('match_update')

def broadcast_map_victory(winner_name, map_info=None):
    """Legacy function - now handled by overlay state system"""
    from .overlay_state import add_overlay_event
    add_overlay_event('map_victory', {
        'winner': winner_name,
        'map_info': map_info or {'title': 'Map Complete'}
    })

def broadcast_match_victory(winner_name, final_score, advancement_info=""):
    """Legacy function - now handled by overlay state system"""
    from .overlay_state import add_overlay_event
    add_overlay_event('match_victory', {
        'winner': winner_name,
        'final_score': final_score,
        'advancement': advancement_info
    })

def broadcast_exit_afk():
    """Legacy function - now handled by overlay state system"""
    from .overlay_state import add_overlay_event
    add_overlay_event('exit_afk')

def broadcast_flip_players():
    """Legacy function - now handled by overlay state system"""
    from .overlay_state import add_overlay_event
    add_overlay_event('flip_players')
