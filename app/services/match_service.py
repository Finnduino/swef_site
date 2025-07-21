import re
from datetime import datetime
from ..data_manager import get_tournament_data, save_tournament_data
from ..bracket_logic import advance_round_if_ready
from ..utils.match_utils import get_detailed_match_results
from .. import api


class MatchService:
    def __init__(self):
        self.api = api
    
    def find_match(self, match_id):
        """Find a match by ID across all brackets"""
        data = get_tournament_data()
        
        for bracket_type in ['upper', 'lower', 'grand_finals']:
            if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
                if bracket_type == 'grand_finals':
                    matches_to_check = [data['brackets'][bracket_type]]
                    if data['brackets'][bracket_type].get('previous_gf'):
                        matches_to_check.append(data['brackets'][bracket_type]['previous_gf'])
                else:
                    matches_to_check = []
                    for round_matches in data['brackets'][bracket_type]:
                        matches_to_check.extend(round_matches)
                
                for match in matches_to_check:
                    if match and match.get('id') == match_id:
                        return match, data
        return None, None
    
    def start_match(self, match_id):
        """Start a match by setting its status to in_progress"""
        match, data = self.find_match(match_id)
        if match:
            match['status'] = 'in_progress'
            save_tournament_data(data)
            return True
        return False
    
    def reset_match(self, match_id):
        """Reset a match to next_up status"""
        match, data = self.find_match(match_id)
        if match:
            match['status'] = 'next_up'
            match['winner'] = None
            match['score_p1'] = 0
            match['score_p2'] = 0
            match['mp_room_url'] = None
            save_tournament_data(data)
            return True
        return False
    
    def set_match_score(self, match_id, score_p1, score_p2, mp_room_url):
        """Set match score and update status"""
        try:
            score_p1 = int(score_p1)
            score_p2 = int(score_p2)
        except ValueError:
            return {'message': 'Invalid score values.', 'type': 'error'}
        
        if score_p1 < 0 or score_p2 < 0 or score_p1 > 4 or score_p2 > 4:
            return {'message': 'Scores must be between 0-4 (Best of 7 format).', 'type': 'error'}
        
        if score_p1 == 4 and score_p2 == 4:
            return {'message': 'Both players cannot have 4 points.', 'type': 'error'}
        
        match, data = self.find_match(match_id)
        if not match:
            return {'message': 'Match not found.', 'type': 'error'}
        
        match['score_p1'] = score_p1
        match['score_p2'] = score_p2
        
        if mp_room_url:
            if 'osu.ppy.sh/multiplayer/rooms/' in mp_room_url:
                match['mp_room_url'] = mp_room_url
            else:
                return {'message': 'Invalid multiplayer room URL format.', 'type': 'error'}
        else:
            match['mp_room_url'] = None
        
        # Determine winner and status
        if score_p1 == 4:
            match['winner'] = match['player1']
            match['status'] = 'completed'
        elif score_p2 == 4:
            match['winner'] = match['player2']
            match['status'] = 'completed'
        else:
            match['winner'] = None
            if score_p1 > 0 or score_p2 > 0:
                match['status'] = 'in_progress'
            else:
                match['status'] = match.get('status', 'next_up')
        
        advance_round_if_ready(data)
        return {'message': 'Match score updated successfully.', 'type': 'success'}
    
    def set_winner(self, match_id, winner_id):
        """Set match winner directly"""
        match, data = self.find_match(match_id)
        if not match:
            return {'message': 'Match not found.', 'type': 'error'}
        
        if match.get('player1', {}).get('id') and str(match['player1']['id']) == winner_id:
            match['winner'] = match['player1']
            match['score_p1'] = 4
            match['score_p2'] = 0
        elif match.get('player2', {}).get('id') and str(match['player2']['id']) == winner_id:
            match['winner'] = match['player2']
            match['score_p1'] = 0
            match['score_p2'] = 4
        else:
            return {'message': 'Invalid winner ID.', 'type': 'error'}
        
        match['status'] = 'completed'
        advance_round_if_ready(data)
        return {'message': 'Winner set successfully.', 'type': 'success'}
    
    def extract_room_id(self, url):
        """Extract room ID from multiplayer URL"""
        if not url:
            return None
        
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
    
    def get_match_results(self, room_id, player1_id, player2_id):
        """Fetch match results from API"""
        try:
            room = self.api.room(room_id)
            
            if not room.playlist:
                return None, 0, 0, 'no_playlist'
            
            player1_wins = 0
            player2_wins = 0
            
            for playlist_item in room.playlist:
                try:
                    scores_data = self.api.multiplayer_scores(room_id, playlist_item.id)
                    
                    p1_score = None
                    p2_score = None
                    
                    for score in scores_data.scores:
                        if score.user_id == player1_id:
                            p1_score = score
                        elif score.user_id == player2_id:
                            p2_score = score
                    
                    if p1_score and p2_score:
                        if p1_score.total_score > p2_score.total_score:
                            player1_wins += 1
                        elif p2_score.total_score > p1_score.total_score:
                            player2_wins += 1
                    elif p1_score and not p2_score:
                        player1_wins += 1
                    elif p2_score and not p1_score:
                        player2_wins += 1
                        
                except Exception as e:
                    print(f"Error fetching scores for playlist item {playlist_item.id}: {e}")
                    continue
            
            if player1_wins >= 4:
                return player1_id, player1_wins, player2_wins, 'completed'
            elif player2_wins >= 4:
                return player2_id, player1_wins, player2_wins, 'completed'
            elif player1_wins > 0 or player2_wins > 0:
                return None, player1_wins, player2_wins, 'in_progress'
            else:
                return None, 0, 0, 'no_scores'
        
        except Exception as e:
            print(f"Error fetching match results for room {room_id}: {e}")
            return None, 0, 0, 'error'
    
    def refresh_match_scores(self, match_id):
        """Automatically refresh match scores from multiplayer room"""
        match, data = self.find_match(match_id)
        if not match:
            return {'message': 'Match not found.', 'type': 'error'}
        
        room_id = self.extract_room_id(match.get('mp_room_url'))
        if not room_id:
            return {'message': 'Invalid or missing multiplayer room URL.', 'type': 'error'}
        
        player1_id = match.get('player1', {}).get('id')
        player2_id = match.get('player2', {}).get('id')
        
        if not player1_id or not player2_id:
            return {'message': 'Player IDs not found in match data.', 'type': 'error'}
        
        # Fetch basic results
        winner_id, score_p1, score_p2, status = self.get_match_results(room_id, player1_id, player2_id)
        
        # Fetch and cache detailed results
        detailed_results = get_detailed_match_results(room_id, player1_id, player2_id)
        if detailed_results:
            match['detailed_results'] = detailed_results
        
        # Update match
        match['score_p1'] = score_p1
        match['score_p2'] = score_p2
        
        if status == 'completed' and winner_id:
            if winner_id == player1_id:
                match['winner'] = match['player1']
            else:
                match['winner'] = match['player2']
            match['status'] = 'completed'
            advance_round_if_ready(data)
            return {'message': f'Match completed! Final score: {score_p1}-{score_p2}. Detailed results cached.', 'type': 'success'}
        elif status == 'in_progress':
            match['winner'] = None
            match['status'] = 'in_progress'
            save_tournament_data(data)
            return {'message': f'Match in progress. Current score: {score_p1}-{score_p2}. Detailed results cached.', 'type': 'info'}
        elif status == 'no_scores':
            return {'message': 'No scores found yet in the multiplayer room.', 'type': 'info'}
        else:
            return {'message': 'Error fetching scores from the multiplayer room.', 'type': 'error'}
    
    def cache_all_match_details(self):
        """Cache detailed results for all matches with multiplayer room URLs"""
        data = get_tournament_data()
        cached_count = 0
        error_count = 0
        messages = []
        
        # Process all brackets
        for bracket_type in ['upper', 'lower', 'grand_finals']:
            if bracket_type in data['brackets'] and data['brackets'][bracket_type]:
                if bracket_type == 'grand_finals':
                    matches_to_check = [data['brackets'][bracket_type]]
                    if data['brackets'][bracket_type].get('previous_gf'):
                        matches_to_check.append(data['brackets'][bracket_type]['previous_gf'])
                else:
                    matches_to_check = []
                    for round_matches in data['brackets'][bracket_type]:
                        matches_to_check.extend(round_matches)
                
                for match in matches_to_check:
                    if not match or not match.get('mp_room_url'):
                        continue
                        
                    room_id = self.extract_room_id(match.get('mp_room_url'))
                    if not room_id:
                        continue
                    
                    player1_id = match.get('player1', {}).get('id')
                    player2_id = match.get('player2', {}).get('id')
                    
                    if not player1_id or not player2_id:
                        continue
                    
                    try:
                        detailed_results = get_detailed_match_results(room_id, player1_id, player2_id)
                        if detailed_results:
                            match['detailed_results'] = detailed_results
                            cached_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        print(f"Error caching match details: {e}")
                        error_count += 1
        
        save_tournament_data(data)
        
        if cached_count > 0:
            messages.append((f'Successfully cached detailed results for {cached_count} matches!', 'success'))
        if error_count > 0:
            messages.append((f'Failed to cache {error_count} matches.', 'warning'))
        if cached_count == 0 and error_count == 0:
            messages.append(('No matches with multiplayer room URLs found.', 'info'))
        
        return {'messages': messages}
    
    def set_match_room(self, match_id, mp_room_url):
        """Set the multiplayer room URL for a match"""
        match, data = self.find_match(match_id)
        if not match:
            return {'message': 'Match not found.', 'type': 'error'}
        
        if mp_room_url and 'osu.ppy.sh/multiplayer/rooms/' not in mp_room_url:
            return {'message': 'Invalid multiplayer room URL format. Must be an osu! multiplayer room link.', 'type': 'error'}
        
        match['mp_room_url'] = mp_room_url
        save_tournament_data(data)
        
        if mp_room_url:
            return {'message': 'Match room URL set successfully.', 'type': 'success'}
        else:
            return {'message': 'Match room URL cleared.', 'type': 'success'}
