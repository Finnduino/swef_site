"""
WebSocket events for real-time overlay updates.
Uses SQLAlchemy models instead of JSON file-based storage.
"""
from flask_socketio import emit, join_room, leave_room
from flask import request
from . import socketio
from .models import Match, Tournament, Competitor, db


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'[WS] Client connected: {request.sid}')
    # Send current match data immediately on connect
    emit('match_update', get_current_match_data())


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'[WS] Client disconnected: {request.sid}')


@socketio.on('join_overlay')
def handle_join_overlay():
    """Join the overlay room to receive match updates"""
    join_room('overlay')
    print(f'[WS] Client {request.sid} joined overlay room')
    # Send current match data
    emit('match_update', get_current_match_data())


@socketio.on('leave_overlay')
def handle_leave_overlay():
    """Leave the overlay room"""
    leave_room('overlay')
    print(f'[WS] Client {request.sid} left overlay room')


@socketio.on('request_match_data')
def handle_request_match_data():
    """Manual request for current match data"""
    emit('match_update', get_current_match_data())


@socketio.on('show_map_victory')
def handle_show_map_victory(data):
    """Broadcast map victory screen to overlay clients"""
    socketio.emit('map_victory', data, room='overlay')


@socketio.on('show_match_victory')
def handle_show_match_victory(data):
    """Broadcast match victory screen to overlay clients"""
    socketio.emit('match_victory', data, room='overlay')


@socketio.on('toggle_afk')
def handle_toggle_afk():
    """Broadcast AFK screen toggle to overlay clients"""
    socketio.emit('toggle_afk', room='overlay')


@socketio.on('exit_afk')
def handle_exit_afk():
    """Broadcast exit AFK screen event to overlay clients"""
    socketio.emit('exit_afk', room='overlay')


@socketio.on('flip_players')
def handle_flip_players():
    """Broadcast flip players event to overlay clients"""
    print('[WS] Broadcasting flip_players event')
    socketio.emit('flip_players', {}, room='overlay')


def get_current_match_data():
    """Get current match data for overlay from database"""
    try:
        # Find active tournament
        tournament = Tournament.query.filter_by(status='active').first()
        if not tournament:
            return {'match_found': False, 'message': 'No active tournament'}
        
        # Priority order: in_progress > next_up
        current_match = None
        bracket_type = None
        
        # Check grand finals first
        current_match = Match.query.filter_by(
            tournament_id=tournament.id,
            bracket='grand_finals'
        ).filter(Match.status.in_(['in_progress', 'next_up'])).first()
        
        if current_match:
            bracket_type = 'Grand Finals'
        
        # Check upper bracket
        if not current_match:
            current_match = Match.query.filter_by(
                tournament_id=tournament.id,
                bracket='upper'
            ).filter(Match.status.in_(['in_progress', 'next_up'])).order_by(
                Match.round_index, Match.match_idx
            ).first()
            if current_match:
                bracket_type = 'Upper'
        
        # Check lower bracket
        if not current_match:
            current_match = Match.query.filter_by(
                tournament_id=tournament.id,
                bracket='lower'
            ).filter(Match.status.in_(['in_progress', 'next_up'])).order_by(
                Match.round_index, Match.match_idx
            ).first()
            if current_match:
                bracket_type = 'Lower'
        
        if current_match:
            return serialize_match(current_match, bracket_type)
        
        return {'match_found': False, 'message': 'No active or upcoming matches'}
    
    except Exception as e:
        print(f'[WS] Error getting match data: {e}')
        return {'match_found': False, 'message': f'Error: {str(e)}'}


def serialize_match(match, bracket_type=None):
    """Serialize a Match object to dict for WebSocket transmission"""
    # Get competitor info
    p1_data = {'name': 'TBD', 'id': '', 'avatar_url': '', 'seed': '?'}
    p2_data = {'name': 'TBD', 'id': '', 'avatar_url': '', 'seed': '?'}
    
    if match.p1:
        user1 = match.p1.user if hasattr(match.p1, 'user') else None
        p1_data = {
            'name': user1.username if user1 else f'Player {match.p1.user_id}',
            'id': match.p1.user_id,
            'avatar_url': user1.avatar_url if user1 else f'https://a.ppy.sh/{match.p1.user_id}',
            'seed': match.p1.placement or '?'
        }
    
    if match.p2:
        user2 = match.p2.user if hasattr(match.p2, 'user') else None
        p2_data = {
            'name': user2.username if user2 else f'Player {match.p2.user_id}',
            'id': match.p2.user_id,
            'avatar_url': user2.avatar_url if user2 else f'https://a.ppy.sh/{match.p2.user_id}',
            'seed': match.p2.placement or '?'
        }
    
    # Determine bracket type if not provided
    if not bracket_type:
        bracket_type = {
            'upper': 'Upper',
            'lower': 'Lower', 
            'grand_finals': 'Grand Finals'
        }.get(match.bracket, match.bracket)
    
    return {
        'match_found': True,
        'match_id': match.id,
        'player1': p1_data,
        'player2': p2_data,
        'score_p1': match.score_p1 or 0,
        'score_p2': match.score_p2 or 0,
        'bracket': bracket_type,
        'round_index': match.round_index,
        'status': match.status,
        'mp_room_url': match.mp_room_url or '',
        'bo_size': match.bo_size,
        # Include match state for interface data
        'phase': (match.state or {}).get('phase', 'ban'),
        'current_turn': (match.state or {}).get('current_turn'),
        'banned_maps': (match.state or {}).get('banned_maps', []),
        'picked_maps': (match.state or {}).get('picked_maps', []),
    }


# --- Broadcast functions for use by other modules ---

def broadcast_match_update(match=None):
    """Broadcast match update to all connected overlay clients"""
    if match:
        data = serialize_match(match)
    else:
        data = get_current_match_data()
    socketio.emit('match_update', data, room='overlay')


def broadcast_map_victory(winner_name, map_info=None):
    """Broadcast map victory screen"""
    socketio.emit('map_victory', {
        'winner': winner_name,
        'map_info': map_info or {'title': 'Map Complete'}
    }, room='overlay')


def broadcast_match_victory(winner_name, final_score, advancement_info=""):
    """Broadcast match victory screen"""
    socketio.emit('match_victory', {
        'winner': winner_name,
        'final_score': final_score,
        'advancement': advancement_info
    }, room='overlay')


def broadcast_exit_afk():
    """Broadcast exit AFK screen event"""
    socketio.emit('exit_afk', room='overlay')


def broadcast_toggle_afk():
    """Broadcast toggle AFK screen event"""
    socketio.emit('toggle_afk', room='overlay')


def broadcast_flip_players():
    """Broadcast flip players event"""
    socketio.emit('flip_players', {}, room='overlay')
