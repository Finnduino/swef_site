#!/usr/bin/env python3
"""
Reproduce the exact tournament progression that caused players to disappear.
This simulates playing the tournament in the correct order: complete upper bracket rounds,
then advance lower bracket, step by step.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
sys.path.insert(0, project_root)

from app.bracket_logic import generate_bracket, advance_round_if_ready
from app.data_manager import get_tournament_data, save_tournament_data

def reproduce_missing_players_bug():
    """Reproduce the exact sequence that caused incomplet and XBisch_LasagnaX to disappear."""
    print("=== Reproducing Missing Players Bug ===")
    
    # Backup current data
    current_data = get_tournament_data()
    
    try:
        # Create the exact tournament setup
        test_data = {
            'competitors': [
                {'id': 9692824, 'name': 'African Stride', 'pp': 6091.17, 'rank': 52334},
                {'id': 11365195, 'name': 'finnduino', 'pp': 5980.92, 'rank': 55584},
                {'id': 11954594, 'name': 'fungus664', 'pp': 5117.25, 'rank': 89783},
                {'id': 10702498, 'name': 'Santa Claus', 'pp': 4649.93, 'rank': 115365},
                {'id': 11578935, 'name': 'XBisch_LasagnaX', 'pp': 2339.37, 'rank': 389837},
                {'id': 28606103, 'name': 'incomplet', 'pp': 589.761, 'rank': 1143856}
            ]
        }
        
        save_tournament_data(test_data)
        generate_bracket()
        data = get_tournament_data()
        
        print("=== STEP 1: Complete Upper Bracket Round 0 ===")
        print("Matches to complete:")
        for i, match in enumerate(data['brackets']['upper'][0]):
            print(f"  Match {i}: {match['player1']['name']} vs {match['player2']['name']}")
        
        # Complete upper bracket round 0 exactly as in the real tournament
        for match in data['brackets']['upper'][0]:
            if match['player2'].get('name') == 'BYE':
                continue  # Already completed
            elif match['player1']['name'] == 'fungus664' and match['player2']['name'] == 'incomplet':
                match['winner'] = match['player1']  # fungus664 beats incomplet
                print(f"    {match['player1']['name']} beats {match['player2']['name']}")
            elif match['player1']['name'] == 'Santa Claus' and match['player2']['name'] == 'XBisch_LasagnaX':
                match['winner'] = match['player1']  # Santa Claus beats XBisch_LasagnaX
                print(f"    {match['player1']['name']} beats {match['player2']['name']}")
            
            if match.get('winner'):
                match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
                match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
                match['status'] = 'completed'
        
        save_tournament_data(data)
        
        print("\n=== STEP 2: Advance Bracket (Create Lower Round 0) ===")
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"Lower bracket now has {len(data['brackets'].get('lower', []))} rounds")
        if data['brackets'].get('lower'):
            print("Lower bracket round 0 matches:")
            for match in data['brackets']['lower'][0]:
                print(f"  {match['player1']['name']} vs {match['player2']['name']}")
        
        print(f"Eliminated players so far: {[p['name'] for p in data.get('eliminated', [])]}")
        
        print("\n=== STEP 3: Complete Lower Bracket Round 0 ===")
        if data['brackets'].get('lower'):
            for match in data['brackets']['lower'][0]:
                if match['player1']['name'] == 'XBisch_LasagnaX':
                    match['winner'] = match['player1']  # XBisch_LasagnaX beats incomplet
                    print(f"    {match['player1']['name']} beats {match['player2']['name']}")
                elif match['player2']['name'] == 'XBisch_LasagnaX':
                    match['winner'] = match['player2']  # XBisch_LasagnaX beats incomplet
                    print(f"    {match['player2']['name']} beats {match['player1']['name']}")
                
                if match.get('winner'):
                    match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
                    match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
                    match['status'] = 'completed'
        
        save_tournament_data(data)
        
        print("\n=== STEP 4: Complete Upper Bracket Round 1 ===")
        print("Upper bracket round 1 matches:")
        for match in data['brackets']['upper'][1]:
            print(f"  {match['player1']['name']} vs {match['player2']['name']}")
            if match['player1']['name'] == 'African Stride':
                match['winner'] = match['player1']  # African Stride beats Santa Claus
                print(f"    {match['player1']['name']} beats {match['player2']['name']}")
            elif match['player1']['name'] == 'finnduino':
                match['winner'] = match['player1']  # finnduino beats fungus664
                print(f"    {match['player1']['name']} beats {match['player2']['name']}")
            
            match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
            match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
            match['status'] = 'completed'
        
        save_tournament_data(data)
        
        print("\n=== STEP 5: Advance Bracket (Create Lower Round 1) ===")
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"Lower bracket now has {len(data['brackets'].get('lower', []))} rounds")
        if len(data['brackets'].get('lower', [])) > 1:
            print("Lower bracket round 1 matches:")
            for match in data['brackets']['lower'][1]:
                print(f"  {match['player1']['name']} vs {match['player2']['name']}")
        
        print(f"\nEliminated players: {[p['name'] for p in data.get('eliminated', [])]}")
        print(f"Pending upper losers: {[p['name'] for p in data.get('pending_upper_losers', [])]}")
        
        # Check if both missing players are accounted for
        eliminated_names = [p['name'] for p in data.get('eliminated', [])]
        
        incomplet_found = 'incomplet' in eliminated_names
        xbisch_found = False
        
        # Check if XBisch_LasagnaX is in any bracket
        for round_matches in data['brackets'].get('lower', []):
            for match in round_matches:
                if match['player1'].get('name') == 'XBisch_LasagnaX' or match['player2'].get('name') == 'XBisch_LasagnaX':
                    xbisch_found = True
                    break
        
        if 'XBisch_LasagnaX' in eliminated_names:
            xbisch_found = True
        
        print(f"\n=== RESULTS ===")
        print(f"incomplet properly eliminated: {'✅' if incomplet_found else '❌'}")
        print(f"XBisch_LasagnaX properly tracked: {'✅' if xbisch_found else '❌'}")
        
        if not incomplet_found:
            print("❌ BUG: incomplet should be eliminated after losing to XBisch_LasagnaX in lower round 0!")
        
        if not xbisch_found:
            print("❌ BUG: XBisch_LasagnaX should advance to lower round 1 but disappeared!")
        
        return incomplet_found and xbisch_found
        
    finally:
        # Restore original data
        save_tournament_data(current_data)
        print("\n(Original tournament data restored)")

if __name__ == '__main__':
    success = reproduce_missing_players_bug()
    print(f"\nMissing Players Bug Test: {'PASSED' if success else 'FAILED'}")
