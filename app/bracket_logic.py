import uuid
import copy
from .data_manager import get_tournament_data, save_tournament_data

def generate_bracket():
    """Generates the initial bracket from the list of competitors."""
    data = get_tournament_data()
    competitors = data.get('competitors', [])
    num_competitors = len(competitors)
    
    if num_competitors < 2:
        # Preserve existing lower bracket if it exists
        existing_lower = data.get('brackets', {}).get('lower', [])
        data['brackets'] = {'upper': [], 'lower': existing_lower}
        save_tournament_data(data)
        return

    # Sort by PP (seed 1 = highest PP)
    seeded_players = sorted(competitors, key=lambda c: -(c.get('pp') or 0))
    next_power_of_2 = 1 << (num_competitors - 1).bit_length()
    num_byes = next_power_of_2 - num_competitors

    # Add BYEs
    for _ in range(num_byes):
        seeded_players.append({'name': 'BYE', 'id': None})

    # Snake seeding
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
    
    # Preserve existing lower bracket if it exists
    existing_lower = data.get('brackets', {}).get('lower', [])
    data['brackets'] = {'upper': [matches], 'lower': existing_lower}
    if 'grand_finals' in data['brackets']:
        del data['brackets']['grand_finals']
    save_tournament_data(data)

def advance_round_if_ready(data):
    """Advances the bracket to the next stage if rounds are complete."""
    import uuid
    competitors_by_id = {c['id']: c for c in data.get('competitors', []) if c.get('id')}
    losers_from_this_advancement = []
    upper_round_advanced = False

    # Initialize lower bracket if it doesn't exist
    if not data['brackets'].get('lower'):
        data['brackets']['lower'] = []

    # --- Process Upper Bracket ---
    if data['brackets'].get('upper'):
        last_upper_round_index = len(data['brackets']['upper']) - 1
        last_upper_round = data['brackets']['upper'][last_upper_round_index]
        
        if all(m.get('winner') for m in last_upper_round) and len(data['brackets']['upper']) == last_upper_round_index + 1:
            upper_round_advanced = True
            winner_ids = [m['winner']['id'] for m in last_upper_round if m.get('winner') and m['winner'].get('id')]
            
            for match in last_upper_round:
                if match.get('player1') and match['player1'].get('id') and match.get('player2') and match['player2'].get('id'):
                    loser_id = match['player2']['id'] if match['winner']['id'] == match['player1']['id'] else match['player1']['id']
                    if loser_id in competitors_by_id:
                        loser = competitors_by_id[loser_id].copy()
                        loser['dropped_from_round'] = last_upper_round_index
                        losers_from_this_advancement.append(loser)
            
            if len(winner_ids) > 1:
                # --- PATCHED: seed-aware snake pairing for upper round ---
                winner_objs = [competitors_by_id[wid].copy() for wid in winner_ids if wid in competitors_by_id]
                winner_objs.sort(key=lambda p: -(p.get('pp') or 0))  # Higher PP = higher seed

                next_power = 1 << (len(winner_objs) - 1).bit_length()
                num_byes = next_power - len(winner_objs)
                for _ in range(num_byes):
                    winner_objs.append({'name': 'BYE', 'id': None})

                half_len = len(winner_objs) // 2
                top_half = winner_objs[:half_len]
                bottom_half = winner_objs[half_len:]
                bottom_half.reverse()

                next_upper_matches = []
                for i in range(half_len):
                    p1 = top_half[i]
                    p2 = bottom_half[i]
                    match = {
                        'id': str(uuid.uuid4()),
                        'player1': p1,
                        'player2': p2,
                        'winner': p1 if p2.get('name') == 'BYE' else None
                    }
                    next_upper_matches.append(match)

                data['brackets']['upper'].append(next_upper_matches)

    # --- Process Lower Bracket ---
    lower_round_advanced = False
    if data['brackets'].get('lower') and len(data['brackets']['lower']) > 0:
        last_lower_round = data['brackets']['lower'][-1]
        if all(m.get('winner') for m in last_lower_round):
            lower_round_advanced = True

    # --- EARLY GRAND FINALS CREATION ---
    if upper_round_advanced and lower_round_advanced:
        final_upper = data['brackets']['upper'][-1]
        final_lower = data['brackets']['lower'][-1]
        if len(final_upper) == 1 and len(final_lower) == 1:
            up_w = final_upper[0].get('winner')
            low_w = final_lower[0].get('winner')
            if up_w and up_w.get('id') and low_w and low_w.get('id') and not data['brackets'].get('grand_finals'):
                data['brackets']['grand_finals'] = {
                    'id': str(uuid.uuid4()),
                    'player1': up_w,
                    'player2': low_w,
                    'winner': None,
                    'is_grand_finals': True
                }
                save_tournament_data(data)
                return

    # Create lower bracket rounds when needed
    if upper_round_advanced or lower_round_advanced:
        winners_from_lower = []
        if lower_round_advanced and data['brackets']['lower']:
            winner_ids = [m['winner']['id'] for m in data['brackets']['lower'][-1] if m.get('winner') and m['winner'].get('id')]
            winners_from_lower = [competitors_by_id[wid].copy() for wid in winner_ids if wid in competitors_by_id]

        # Filter out BYE players from losers
        real_losers = [loser for loser in losers_from_this_advancement if loser.get('name') != 'BYE' and loser.get('id')]
        
        next_pool = winners_from_lower + real_losers
        unique_players = {}
        for player in next_pool:
            if player.get('id'):
                unique_players[player['id']] = player
        next_pool = list(unique_players.values())

        if len(next_pool) >= 2:
            next_pool.sort(key=lambda p: (p.get('dropped_from_round', 999), -(p.get('pp') or 0)))
            next_lower_matches = []
            num_players = len(next_pool)
            num_byes = (1 << (num_players - 1).bit_length()) - num_players

            for _ in range(num_byes):
                next_pool.append({'name': 'BYE', 'id': None})

            half_len = len(next_pool) // 2
            top_half = next_pool[:half_len]
            bottom_half = next_pool[half_len:]
            bottom_half.reverse()

            for i in range(half_len):
                p1 = top_half[i]
                p2 = bottom_half[i]
                match = {
                    'id': str(uuid.uuid4()),
                    'player1': p1,
                    'player2': p2,
                    'winner': p1 if p2.get('name') == 'BYE' else None
                }
                next_lower_matches.append(match)

            # Check if this would be a duplicate round
            should_add_round = True
            if data['brackets']['lower']:
                last_lower_round_players = []
                for match in data['brackets']['lower'][-1]:
                    p1_id = match['player1'].get('id') if match.get('player1') else None
                    p2_id = match['player2'].get('id') if match.get('player2') else None
                    last_lower_round_players.append(tuple(sorted((str(p1_id) if p1_id else 'BYE', str(p2_id) if p2_id else 'BYE'))))

                new_lower_round_players = []
                for match in next_lower_matches:
                    p1_id = match['player1'].get('id') if match.get('player1') else None
                    p2_id = match['player2'].get('id') if match.get('player2') else None
                    new_lower_round_players.append(tuple(sorted((str(p1_id) if p1_id else 'BYE', str(p2_id) if p2_id else 'BYE'))))

                if sorted(last_lower_round_players) == sorted(new_lower_round_players):
                    should_add_round = False

            if should_add_round:
                data['brackets']['lower'].append(next_lower_matches)
        elif len(next_pool) == 1:
            # Single player only: duplicate them so no BYE appears
            player = next_pool[0]
            next_lower_matches = [{
                'id': str(uuid.uuid4()),
                'player1': player,
                'player2': player,
                'winner': player
            }]
            data['brackets']['lower'].append(next_lower_matches)

    # --- Process Grand Finals (fallback) ---
    upper_winner, lower_winner = None, None
    
    # Check for upper bracket winner
    if data['brackets'].get('upper'):
        final_upper_round = data['brackets']['upper'][-1]
        if len(final_upper_round) == 1 and final_upper_round[0].get('winner') and final_upper_round[0]['winner'].get('id'):
            upper_winner = final_upper_round[0]['winner']

    # Check for lower bracket winner
    if data['brackets'].get('lower'):
        final_lower_round = data['brackets']['lower'][-1]
        if len(final_lower_round) == 1 and final_lower_round[0].get('winner') and final_lower_round[0]['winner'].get('id'):
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