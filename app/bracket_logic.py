import uuid
import copy
from .data_manager import get_tournament_data, save_tournament_data

def generate_bracket():
    """Generates the initial bracket from the list of competitors."""
    data = get_tournament_data()

    # full‐reset of any in-flight state
    data.pop('pending_upper_losers', None)
    data.pop('eliminated', None)

    competitors = data.get('competitors', [])
    num_competitors = len(competitors)
    
    if num_competitors < 2:
        data['brackets'] = {'upper': [], 'lower': []}
        save_tournament_data(data)
        return

    # Sort by qualifier placement (1 is best), then by PP
    def seed_key(c):
        return (c.get('placement') if c.get('placement') is not None else float('inf'),
                -(c.get('pp') or 0))
    seeded_players = sorted(competitors, key=seed_key)

    # pad to power of two
    next_pow2 = 1 << (num_competitors - 1).bit_length()
    for _ in range(next_pow2 - num_competitors):
        seeded_players.append({'name': 'BYE', 'id': None})

    # snake‐seed
    half = len(seeded_players)//2
    top, bottom = seeded_players[:half], list(reversed(seeded_players[half:]))

    # round 0, upper bracket
    matches = []
    for i, (p1, p2) in enumerate(zip(top, bottom)):
        match = {
            'id': str(uuid.uuid4()),
            'bracket': 'upper',
            'round_index': 0,
            'player1': p1,
            'player2': p2,
            'winner': p1 if p2.get('name')=='BYE' else None,
            'score_p1': 4 if p2.get('name')=='BYE' else 0,  # Auto-win BYE matches
            'score_p2': 0,
            'mp_room_url': None,
            'status': 'completed' if p2.get('name')=='BYE' else 'next_up'  # BYEs are auto-completed
        }
        matches.append(match)

    data['brackets'] = {'upper': [matches], 'lower': []}
    # Clean up old state
    for key in ['grand_finals', 'pending_upper_losers', 'eliminated']:
        data.pop(key, None)
    save_tournament_data(data)


def advance_round_if_ready(data):
    """Advances the bracket; tracks and eliminates lower-bracket losers."""
    # build a lookup for competitors
    comps = {c['id']: c for c in data.get('competitors', []) if c.get('id')}

    # persistent queue of upper-bracket losers awaiting a lower-bracket match
    data.setdefault('pending_upper_losers', [])

    eliminated = []
    upper_advanced = False

    # --- Upper Bracket ---
    if data['brackets'].get('upper'):
        ui = len(data['brackets']['upper']) - 1
        ur = data['brackets']['upper'][ui]
        if all(m.get('winner') for m in ur):
            upper_advanced = True
            win_ids = [m['winner']['id'] for m in ur if m['winner'].get('id')]

            # collect this round's upper losers (skip BYEs)
            current_losers = []
            for m in ur:
                if not m.get('winner'):
                    continue
                p1_id = m['player1'].get('id') if m.get('player1') else None
                p2_id = m['player2'].get('id') if m.get('player2') else None
                winner_id = m['winner']['id']
                
                loser_id = p2_id if winner_id == p1_id else p1_id
                if loser_id and loser_id in comps:
                    l = comps[loser_id].copy()
                    l.update({'dropped_from_round': ui, 'bracket': 'upper'})
                    current_losers.append(l)

            # enqueue them
            data['pending_upper_losers'].extend(current_losers)

            if len(win_ids) > 1:
                # build next upper
                wins = [comps[w].copy() for w in win_ids if w in comps]
                wins.sort(key=lambda p: -(p.get('pp') or 0))
                # pad & snake
                np2 = 1 << (len(wins)-1).bit_length() if wins else 2
                for _ in range(max(0, np2 - len(wins))):
                    wins.append({'name':'BYE','id':None})
                h = len(wins)//2
                top, bot = wins[:h], list(reversed(wins[h:]))
                nxt = []
                for p1,p2 in zip(top,bot):
                    match = {
                        'id': str(uuid.uuid4()),
                        'bracket': 'upper',
                        'round_index': ui+1,
                        'player1': p1,
                        'player2': p2,
                        'winner': p1 if p2.get('name')=='BYE' else None,
                        'score_p1': 4 if p2.get('name')=='BYE' else 0,
                        'score_p2': 0,
                        'mp_room_url': None,
                        'status': 'next_up'  # New matches are next up
                    }
                    nxt.append(match)
                data['brackets']['upper'].append(nxt)

    # --- Lower Bracket ---
    lower_advanced = False
    if data['brackets'].get('lower'):
        li = len(data['brackets']['lower']) - 1
        lr = data['brackets']['lower'][li]
        if all(m.get('winner') for m in lr):
            lower_advanced = True
            # collect lower losers → eliminated
            for m in lr:
                if not m.get('winner'):
                    continue
                winner_id = m['winner']['id']
                p1_id = m['player1'].get('id') if m.get('player1') else None
                p2_id = m['player2'].get('id') if m.get('player2') else None
                
                loser_id = p2_id if winner_id == p1_id else p1_id
                if loser_id and loser_id in comps:
                    e = comps[loser_id].copy()
                    e.update({
                        'status': 'eliminated',
                        'eliminated_in_round': li,
                        'bracket': 'lower'
                    })
                    eliminated.append(e)

    # --- Build next lower only if either bracket advanced ---
    if upper_advanced or lower_advanced:
        wins_lower = []
        if lower_advanced and data['brackets'].get('lower'):
            wins_lower = [comps[m['winner']['id']].copy()
                          for m in data['brackets']['lower'][-1]
                          if m.get('winner') and m['winner'].get('id') and m['winner']['id'] in comps]
        
        # now combine all waiting upper losers + new lower winners
        pool = wins_lower + data['pending_upper_losers']

        # Remove eliminated players and dedupe
        eliminated_ids = {e['id'] for e in eliminated}
        pool = [p for p in pool if p.get('id') and p['id'] not in eliminated_ids]

        # dedupe by competitor id
        unique = {}
        for p in pool:
            pid = p.get('id')
            if pid and pid not in unique:
                unique[pid] = p
        pool = list(unique.values())

        if len(pool) >= 2:
            # Sort for fair matchups
            pool.sort(key=lambda p: (p.get('dropped_from_round', 999), -(p.get('pp') or 0)))
            
            # pad & snake
            np2 = 1 << (len(pool)-1).bit_length()
            for _ in range(np2 - len(pool)):
                pool.append({'name':'BYE','id':None})
            half = len(pool)//2
            top, bot = pool[:half], list(reversed(pool[half:]))
            nxt = []
            for p1, p2 in zip(top, bot):
                match = {
                    'id': str(uuid.uuid4()),
                    'bracket': 'lower',
                    'round_index': len(data['brackets'].get('lower', [])),
                    'player1': p1,
                    'player2': p2,
                    'winner': p1 if p2.get('name')=='BYE' else None,
                    'score_p1': 4 if p2.get('name')=='BYE' else 0,
                    'score_p2': 0,
                    'mp_room_url': None,
                    'status': 'next_up'  # New matches are next up
                }
                nxt.append(match)

            data['brackets'].setdefault('lower', []).append(nxt)

            # remove those just matched from the pending queue
            matched_ids = {
                m['player1']['id'] for m in nxt if m['player1'].get('id')
            } | {
                m['player2']['id'] for m in nxt if m['player2'].get('id')
            }
            data['pending_upper_losers'] = [
                p for p in data['pending_upper_losers']
                if p.get('id') not in matched_ids
            ]

    # --- Grand Finals ---
    upper_w, lower_w = None, None
    if data['brackets'].get('upper'):
        fu = data['brackets']['upper'][-1]
        if len(fu)==1 and fu[0].get('winner'):
            upper_w = fu[0]['winner']
    if data['brackets'].get('lower'):
        fl = data['brackets']['lower'][-1]
        if len(fl)==1 and fl[0].get('winner'):
            lower_w = fl[0]['winner']
    
    # Create initial grand finals if both winners are ready
    if upper_w and lower_w and 'grand_finals' not in data['brackets']:
        data['brackets']['grand_finals'] = {
            'id': str(uuid.uuid4()),
            'bracket': 'grand_finals',
            'round_index': 0,
            'player1': upper_w,
            'player2': lower_w,
            'winner': None,
            'is_grand_finals': True,
            'is_bracket_reset': False,
            'score_p1': 0,
            'score_p2': 0,
            'mp_room_url': None
        }
    
    # Handle bracket reset scenario
    elif 'grand_finals' in data['brackets']:
        gf = data['brackets']['grand_finals']
        if gf.get('winner') and not gf.get('is_bracket_reset'):
            # If lower bracket winner won the first grand finals match
            if gf['winner']['id'] == gf['player2']['id']:
                # Bracket reset! Create second grand finals match
                data['brackets']['grand_finals'] = {
                    'id': str(uuid.uuid4()),
                    'bracket': 'grand_finals',
                    'round_index': 1,
                    'player1': gf['player1'],  # Upper bracket winner gets another chance
                    'player2': gf['player2'],  # Lower bracket winner
                    'winner': None,
                    'is_grand_finals': True,
                    'is_bracket_reset': True,
                    'previous_gf': gf,  # Store the first match for reference
                    'score_p1': 0,
                    'score_p2': 0,
                    'mp_room_url': None
                }

    # --- Persist eliminated list ---
    if eliminated:
        data.setdefault('eliminated', [])
        # Avoid duplicates
        existing_ids = {e['id'] for e in data['eliminated']}
        new_eliminated = [e for e in eliminated if e['id'] not in existing_ids]
        data['eliminated'].extend(new_eliminated)

    save_tournament_data(data)