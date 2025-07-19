import uuid
import copy
from .data_manager import get_tournament_data, save_tournament_data

def generate_bracket():
    """Generates the initial bracket from the list of competitors."""
    data = get_tournament_data()
    competitors = data.get('competitors', [])
    num_competitors = len(competitors)
    
    if num_competitors < 2:
        data['brackets'] = {'upper': [], 'lower': []}
        save_tournament_data(data)
        return

    next_power_of_2 = 1 << (num_competitors - 1).bit_length()
    seeded_players = list(competitors)
    num_byes = next_power_of_2 - num_competitors
    for _ in range(num_byes):
        seeded_players.append({'name': 'BYE', 'id': None})

    half_len = len(seeded_players) // 2
    top_half = seeded_players[:half_len]
    bottom_half = seeded_players[half_len:]
    bottom_half.reverse()

    matches = []
    for i in range(half_len):
        p1 = top_half[i]
        p2 = bottom_half[i]
        match = {
            'id': str(uuid.uuid4()),
            'player1': p1,
            'player2': p2,
            'winner': p1 if p2.get('name') == 'BYE' else None
        }
        matches.append(match)
    
    data['brackets'] = {'upper': [matches], 'lower': []}
    if 'grand_finals' in data['brackets']:
        del data['brackets']['grand_finals']
    save_tournament_data(data)

def advance_round_if_ready(data):
    """Advances the bracket to the next stage if rounds are complete."""
    # Create a lookup for full competitor data by ID for easy access
    competitors_by_id = {c['id']: c for c in data.get('competitors', []) if c.get('id')}

    # --- Process Upper Bracket ---
    losers_from_this_advancement = []
    upper_round_advanced = False
    if data['brackets'].get('upper'):
        last_upper_round_index = len(data['brackets']['upper']) - 1
        last_upper_round = data['brackets']['upper'][last_upper_round_index]
        
        if all(m.get('winner') for m in last_upper_round) and len(data['brackets']['upper']) == last_upper_round_index + 1:
            upper_round_advanced = True
            winner_ids = [m['winner']['id'] for m in last_upper_round]
            
            for match in last_upper_round:
                if match.get('player1') and match['player1'].get('id') and match.get('player2') and match['player2'].get('id'):
                    loser_id = match['player2']['id'] if match['winner']['id'] == match['player1']['id'] else match['player1']['id']
                    if loser_id in competitors_by_id:
                        loser = competitors_by_id[loser_id].copy() # Use a fresh copy
                        loser['dropped_from_round'] = last_upper_round_index 
                        losers_from_this_advancement.append(loser)
            
            if len(winner_ids) > 1:
                next_upper_matches = []
                for i in range(0, len(winner_ids), 2):
                    p1_id = winner_ids[i]
                    p2_id = winner_ids[i+1] if i + 1 < len(winner_ids) else None
                    
                    p1 = competitors_by_id.get(p1_id)
                    p2 = competitors_by_id.get(p2_id) if p2_id else {'name': 'BYE', 'id': None}

                    if p1: # Ensure player1 exists
                        match = {'id': str(uuid.uuid4()), 'player1': p1, 'player2': p2, 'winner': p1 if not p2 or p2.get('name') == 'BYE' else None}
                        next_upper_matches.append(match)
                data['brackets']['upper'].append(next_upper_matches)

    # --- Process Lower Bracket ---
    lower_round_advanced = False
    if data['brackets'].get('lower'):
        last_lower_round = data['brackets']['lower'][-1]
        if all(m.get('winner') for m in last_lower_round):
            lower_round_advanced = True

    # Only create the next lower round if an upper round OR a lower round just finished
    if upper_round_advanced or lower_round_advanced:
        winners_from_lower = []
        if lower_round_advanced:
            # Get fresh winner objects from the main competitors list
            winner_ids = [m['winner']['id'] for m in data['brackets']['lower'][-1] if m.get('winner') and m['winner'].get('id')]
            winners_from_lower = [competitors_by_id[wid].copy() for wid in winner_ids if wid in competitors_by_id]

        next_pool = winners_from_lower + losers_from_this_advancement

        unique_players = {}
        for player in next_pool:
            if player.get('id'):
                unique_players[player['id']] = player
        
        next_pool = list(unique_players.values())

        if len(next_pool) >= 2:
            # Sort by which upper round they dropped from, then by PP.
            next_pool.sort(key=lambda p: (p.get('dropped_from_round', 999), -(p.get('pp') or 0)))
            
            # --- Corrected Snake Seeding for Lower Bracket ---
            next_lower_matches = []
            num_players = len(next_pool)
            num_byes = (1 << (num_players - 1).bit_length()) - num_players
            
            # Pad with byes for correct pairing
            for _ in range(num_byes):
                next_pool.append({'name': 'BYE', 'id': None})

            half_len = len(next_pool) // 2
            top_half = next_pool[:half_len]
            bottom_half = next_pool[half_len:]
            bottom_half.reverse() # Reverse the bottom half for snake seeding

            for i in range(half_len):
                p1 = top_half[i]
                p2 = bottom_half[i]
                match = {'id': str(uuid.uuid4()), 'player1': p1, 'player2': p2, 'winner': p1 if p2.get('name') == 'BYE' else None}
                next_lower_matches.append(match)
            
            # Check if the new round is different from the last one based on players
            last_lower_round_players = []
            if data['brackets'].get('lower'):
                for match in data['brackets']['lower'][-1]:
                    p1_id = match['player1'].get('id') if match.get('player1') else None
                    p2_id = match['player2'].get('id') if match.get('player2') else None
                    # Convert all IDs to strings for safe sorting
                    last_lower_round_players.append(tuple(sorted((str(p1_id) if p1_id else 'BYE', str(p2_id) if p2_id else 'BYE'))))

            new_lower_round_players = []
            for match in next_lower_matches:
                p1_id = match['player1'].get('id') if match.get('player1') else None
                p2_id = match['player2'].get('id') if match.get('player2') else None
                # Convert all IDs to strings for safe sorting
                new_lower_round_players.append(tuple(sorted((str(p1_id) if p1_id else 'BYE', str(p2_id) if p2_id else 'BYE'))))

            if sorted(last_lower_round_players) != sorted(new_lower_round_players):
                data['brackets']['lower'].append(next_lower_matches)

    # --- Process Grand Finals ---
    upper_winner, lower_winner = None, None
    if data['brackets'].get('upper'):
        final_upper_round = data['brackets']['upper'][-1]
        if len(final_upper_round) == 1 and final_upper_round[0].get('winner'):
            upper_winner = final_upper_round[0]['winner']

    if data['brackets'].get('lower'):
        final_lower_round = data['brackets']['lower'][-1]
        if len(final_lower_round) == 1 and final_lower_round[0].get('winner'):
            lower_winner = final_lower_round[0]['winner']

    if upper_winner and lower_winner and not data['brackets'].get('grand_finals'):
        data['brackets']['grand_finals'] = {
            'id': str(uuid.uuid4()),
            'player1': upper_winner,
            'player2': lower_winner,
            'winner': None,
            'is_grand_finals': True
        }

    save_tournament_data(data)
