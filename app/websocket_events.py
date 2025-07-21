from flask_socketio import emit, join_room, leave_room
from flask import request
from . import socketio
from .data_manager import get_tournament_data

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    # Send current match data immediately on connect
    emit('match_update', get_current_match_data())

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

@socketio.on('join_overlay')
def handle_join_overlay():
    """Join the overlay room to receive match updates"""
    join_room('overlay')
    print(f'Client {request.sid} joined overlay room')  # debug join
    # Send current match data
    emit('match_update', get_current_match_data(), room='overlay')

@socketio.on('leave_overlay')
def handle_leave_overlay():
    """Leave the overlay room"""
    leave_room('overlay')
    print(f'Client {request.sid} left overlay room')

@socketio.on('request_match_data')
def handle_request_match_data():
    """Manual request for current match data"""
    emit('match_update', get_current_match_data())

@socketio.on('show_map_victory')
def handle_show_map_victory(data):
    """Broadcast map victory screen"""
    socketio.emit('map_victory', data, room='overlay')

@socketio.on('show_match_victory')
def handle_show_match_victory(data):
    """Broadcast match victory screen"""
    socketio.emit('match_victory', data, room='overlay')

@socketio.on('toggle_afk')
def handle_toggle_afk():
    """Broadcast AFK screen toggle"""
    socketio.emit('toggle_afk', room='overlay')

@socketio.on('exit_afk')
def handle_exit_afk():
    """Broadcast exit AFK screen event"""
    socketio.emit('exit_afk', room='overlay')

@socketio.on('flip_players')
def handle_flip_players():
    """Handle flip players event and broadcast to overlay"""
    socketio.emit('flip_players', room='overlay')

def get_current_match_data():
    """Get current match data for overlay"""
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
                'player1': {
                    'name': current_match.get('player1', {}).get('name', 'Player 1'),
                    'id': current_match.get('player1', {}).get('id', ''),
                    'avatar_url': current_match.get('player1', {}).get('avatar_url', ''),
                    'seed': current_match.get('player1', {}).get('placement', '?')
                },
                'player2': {
                    'name': current_match.get('player2', {}).get('name', 'Player 2'),
                    'id': current_match.get('player2', {}).get('id', ''), 
                    'avatar_url': current_match.get('player2', {}).get('avatar_url', ''),
                    'seed': current_match.get('player2', {}).get('placement', '?')
                },
                'score_p1': current_match.get('score_p1', 0),
                'score_p2': current_match.get('score_p2', 0),
                'bracket': bracket_type,
                'round_index': round_index,
                'status': current_match.get('status', 'unknown'),
                'mp_room_url': current_match.get('mp_room_url', ''),
                'match_id': current_match.get('id', '')
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

def broadcast_match_update():
    """Broadcast match updates to all connected overlay clients"""
    if socketio:
        socketio.emit('match_update', get_current_match_data(), room='overlay')

def broadcast_map_victory(winner_name, map_info=None):
    """Broadcast map victory screen"""
    if socketio:
        socketio.emit('map_victory', {
            'winner': winner_name,
            'map_info': map_info or {'title': 'Map Complete'}
        }, room='overlay')

def broadcast_match_victory(winner_name, final_score, advancement_info=""):
    """Broadcast match victory screen"""
    if socketio:
        socketio.emit('match_victory', {
            'winner': winner_name,
            'final_score': final_score,
            'advancement': advancement_info
        }, room='overlay')

def broadcast_exit_afk():
    """Broadcast exit AFK screen to all connected overlay clients"""
    if socketio:
        socketio.emit('exit_afk', room='overlay')

def broadcast_flip_players():
    """Broadcast flip players event to all overlay clients"""
    if socketio:
        print('Broadcasting flip_players event from backend')
        # Include namespace to ensure clients on default namespace receive it
        socketio.emit('flip_players', {}, room='overlay', namespace='/')
