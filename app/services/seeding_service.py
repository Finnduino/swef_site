import re
from ..data_manager import get_tournament_data, save_tournament_data
from ..bracket_logic import generate_bracket
from .. import api


class SeedingService:
    def __init__(self):
        self.api = api
    
    def extract_room_id(self, url):
        """Extract room ID from osu multiplayer room URL"""
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
    
    def get_seeding_scores(self, room_id, competitor_ids):
        """
        Fetch cumulative seeding scores for all competitors from a multiplayer room
        Returns: dict of {user_id: total_score}
        """
        try:
            print(f"Fetching seeding scores for room {room_id}")
            
            room = self.api.room(room_id)
            
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
                    
                    scores_data = self.api.multiplayer_scores(room_id, playlist_item.id)
                    
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
    
    def start_seeding(self, seeding_room_url):
        """Start seeding with a multiplayer room"""
        if not seeding_room_url:
            return {'message': 'Seeding room URL is required.', 'type': 'error'}
        
        room_id = self.extract_room_id(seeding_room_url)
        if not room_id:
            return {'message': 'Invalid multiplayer room URL format.', 'type': 'error'}
        
        # Test if we can access the room
        try:
            room = self.api.room(room_id)
            if not room:
                return {'message': 'Could not access the specified multiplayer room.', 'type': 'error'}
        except Exception as e:
            return {'message': f'Error accessing multiplayer room: {e}', 'type': 'error'}
        
        data = get_tournament_data()
        data['seeding_room_url'] = seeding_room_url
        data['seeding_room_id'] = room_id
        data['seeding_in_progress'] = True
        
        save_tournament_data(data)
        return {'message': 'Seeding room set! Players can now play seeding maps.', 'type': 'success'}
    
    def update_seeding_scores(self):
        """Update seeding scores from the multiplayer room"""
        data = get_tournament_data()
        room_id = data.get('seeding_room_id')
        
        if not room_id:
            return {'message': 'No seeding room configured.', 'type': 'error'}
        
        # Get competitor IDs
        competitor_ids = [c['id'] for c in data.get('competitors', []) if c.get('id')]
        
        if not competitor_ids:
            return {'message': 'No competitors found.', 'type': 'error'}
        
        # Fetch seeding scores
        player_scores = self.get_seeding_scores(room_id, competitor_ids)
        
        if not player_scores:
            return {'message': 'No seeding scores found in the multiplayer room.', 'type': 'error'}
        
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
        return {'message': f'Updated seeding scores for {len(seeded_players)} players.', 'type': 'success'}
    
    def finalize_seeding(self):
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
        
        return {'message': f'Seeding finalized for {finalized_count} players and bracket regenerated.', 'type': 'success'}
