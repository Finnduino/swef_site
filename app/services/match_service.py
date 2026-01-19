import re
from datetime import datetime
from ..models import db, Match, Competitor, Tournament
from ..utils.match_utils import get_detailed_match_results
from .. import api

class MatchService:
    def __init__(self):
        self.api = api
    
    def find_match(self, match_id):
        """Find a match by ID using SQLAlchemy"""
        return db.session.get(Match, match_id)
    
    def start_match(self, match_id):
        """Start a match by setting its status to in_progress"""
        match = self.find_match(match_id)
        if match:
            match.status = 'in_progress'
            db.session.commit()
            return True
        return False
    
    def reset_match(self, match_id):
        """Reset a match to next_up status"""
        match = self.find_match(match_id)
        if match:
            match.status = 'next_up'
            match.winner_id = None
            match.score_p1 = 0
            match.score_p2 = 0
            match.mp_room_url = None
            db.session.commit()
            return True
        return False
    
    def set_match_score(self, match_id, score_p1, score_p2, mp_room_url=None, manual=False):
        """Set match score and update status. If manual=True, sets manual_override."""
        try:
            score_p1 = int(score_p1)
            score_p2 = int(score_p2)
        except ValueError:
            return {'message': 'Invalid score values.', 'type': 'error'}
        
        match = self.find_match(match_id)
        if not match:
            return {'message': 'Match not found.', 'type': 'error'}
        
        # dynamic BO check
        win_needed = (match.bo_size // 2) + 1
        
        if score_p1 < 0 or score_p2 < 0 or score_p1 > win_needed or score_p2 > win_needed:
            return {'message': f'Scores must be between 0-{win_needed} (Best of {match.bo_size} format).', 'type': 'error'}
        
        if score_p1 == win_needed and score_p2 == win_needed:
            return {'message': f'Both players cannot have {win_needed} points.', 'type': 'error'}
        
        # Flag manual override if explicitly set or if administrator is forcing a score
        if manual:
            match.manual_override = True
        
        prev_score_p1 = match.score_p1
        prev_score_p2 = match.score_p2
        
        match.score_p1 = score_p1
        match.score_p2 = score_p2
        
        if mp_room_url:
            match.mp_room_url = mp_room_url
            
        # Handle turn order changes (if match state exists)
        if match.state and (score_p1 != prev_score_p1 or score_p2 != prev_score_p2):
            picked_maps = match.state.get('picked_maps', [])
            if picked_maps:
                if score_p1 > prev_score_p1:
                    match.state['current_turn'] = 'player2'
                elif score_p2 > prev_score_p2:
                    match.state['current_turn'] = 'player1'
                
                if score_p1 < win_needed and score_p2 < win_needed:
                    match.state['phase'] = 'pick'
            # Trigger JSON update
            db.session.flag_modified(match, "state")
        
        # Determine winner
        if score_p1 == win_needed:
            match.winner_id = match.player1_id
            match.status = 'completed'
        elif score_p2 == win_needed:
            match.winner_id = match.player2_id
            match.status = 'completed'
        else:
            match.winner_id = None
            match.status = 'in_progress' if (score_p1 > 0 or score_p2 > 0) else 'next_up'
            
        db.session.commit()
        
        # Push real-time update to overlay clients
        try:
            from ..websocket_events import broadcast_match_update
            broadcast_match_update(match)
        except Exception as e:
            print(f"[WS] Failed to broadcast match update: {e}")
        
        # Note: advance_round_if_ready will need to be refactored too
        # For now we'll just commit the match update.
        return {'message': 'Match score updated successfully.', 'type': 'success'}

    def set_winner(self, match_id, winner_id):
        """Set match winner directly and flag manual override"""
        match = self.find_match(match_id)
        if not match:
            return {'message': 'Match not found.', 'type': 'error'}
        
        win_needed = (match.bo_size // 2) + 1
        
        if match.player1_id == winner_id:
            match.winner_id = match.player1_id
            match.score_p1 = win_needed
            match.score_p2 = 0
        elif match.player2_id == winner_id:
            match.winner_id = match.player2_id
            match.score_p1 = 0
            match.score_p2 = win_needed
        else:
            return {'message': 'Invalid winner ID.', 'type': 'error'}
        
        match.status = 'completed'
        match.manual_override = True
        db.session.commit()
        return {'message': 'Winner set successfully (Manual Override enabled).', 'type': 'success'}

    def refresh_match_scores(self, match_id):
        """Automatically refresh match scores from multiplayer room unless manual_override is set"""
        match = self.find_match(match_id)
        if not match:
            return {'message': 'Match not found.', 'type': 'error'}
        
        if match.manual_override:
            return {'message': 'Match is under manual override. Auto-refresh disabled.', 'type': 'info'}
            
        room_id = self.extract_room_id(match.mp_room_url)
        if not room_id:
            return {'message': 'Invalid or missing multiplayer room URL.', 'type': 'error'}
        
        # Get osu! user IDs
        p1_osu_id = match.p1.user_id if match.p1 else None
        p2_osu_id = match.p2.user_id if match.p2 else None
        
        if not p1_osu_id or not p2_osu_id:
            return {'message': 'Player IDs not found.', 'type': 'error'}
            
        # Fetch results
        winner_osu_id, score_p1, score_p2, status = self.get_match_results(room_id, p1_osu_id, p2_osu_id, match.bo_size)
        
        # Detailed results caching
        detailed = get_detailed_match_results(room_id, p1_osu_id, p2_osu_id)
        if detailed:
            if not match.state: match.state = {}
            match.state['detailed_results'] = detailed
            db.session.flag_modified(match, "state")
            
        # Update scores
        match.score_p1 = score_p1
        match.score_p2 = score_p2
        
        win_needed = (match.bo_size // 2) + 1
        
        if status == 'completed' and winner_osu_id:
            match.winner_id = match.player1_id if winner_osu_id == p1_osu_id else match.player2_id
            match.status = 'completed'
            db.session.commit()
            return {'message': f'Match completed! Final: {score_p1}-{score_p2}', 'type': 'success'}
        else:
            match.status = 'in_progress' if status == 'in_progress' else match.status
            db.session.commit()
            return {'message': f'Match sync complete. Score: {score_p1}-{score_p2}', 'type': 'info'}

    def extract_room_id(self, url):
        if not url: return None
        patterns = [r'osu\.ppy\.sh/multiplayer/rooms/(\d+)', r'osu\.ppy\.sh/mp/(\d+)']
        for p in patterns:
            m = re.search(p, url)
            if m: return int(m.group(1))
        return None

    def get_match_results(self, room_id, p1_id, p2_id, bo_size):
        try:
            room = self.api.room(room_id)
            win_needed = (bo_size // 2) + 1
            p1_wins, p2_wins = 0, 0
            
            for item in room.playlist:
                try:
                    scores = self.api.multiplayer_scores(room_id, item.id).scores
                    s1 = next((s for s in scores if s.user_id == p1_id), None)
                    s2 = next((s for s in scores if s.user_id == p2_id), None)
                    
                    if s1 and s2:
                        if s1.total_score > s2.total_score: p1_wins += 1
                        else: p2_wins += 1
                    elif s1: p1_wins += 1
                    elif s2: p2_wins += 1
                except: continue
                
            if p1_wins >= win_needed: return p1_id, p1_wins, p2_wins, 'completed'
            if p2_wins >= win_needed: return p2_id, p1_wins, p2_wins, 'completed'
            return None, p1_wins, p2_wins, 'in_progress' if (p1_wins+p2_wins) > 0 else 'no_scores'
        except:
            return None, 0, 0, 'error'

    def cache_all_match_details(self):
        # Implementation to scan active matches and cache (can be optimized)
        return {'messages': [('Detail caching will be updated in next pass.', 'info')]}

    def set_match_room(self, match_id, mp_room_url):
        match = self.find_match(match_id)
        if not match: return {'message': 'Match not found.', 'type': 'error'}
        match.mp_room_url = mp_room_url
        db.session.commit()
        return {'message': 'Room URL updated.', 'type': 'success'}
