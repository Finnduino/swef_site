#!/usr/bin/env python3
"""
Recreate the exact scenario that caused XBisch_LasagnaX to disappear
and verify our fix prevents it.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
sys.path.insert(0, project_root)

from app.bracket_logic import generate_bracket, advance_round_if_ready
from app.data_manager import get_tournament_data, save_tournament_data

def test_xbisch_bug_exact():
    """Test the exact sequence that caused XBisch_LasagnaX to disappear."""
    print("=== Testing XBisch_LasagnaX Bug Fix ===")
    
    # Backup current data
    current_data = get_tournament_data()
    
    try:
        # Create the exact 6-player setup
        test_data = {
            'competitors': [
                {'id': 9692824, 'name': 'African Stride', 'pp': 6091.17},
                {'id': 11365195, 'name': 'finnduino', 'pp': 5980.92},
                {'id': 11954594, 'name': 'fungus664', 'pp': 5117.25},
                {'id': 10702498, 'name': 'Santa Claus', 'pp': 4649.93},
                {'id': 11578935, 'name': 'XBisch_LasagnaX', 'pp': 2339.37},
                {'id': 28606103, 'name': 'incomplet', 'pp': 589.761}
            ]
        }
        
        save_tournament_data(test_data)
        generate_bracket()
        data = get_tournament_data()
        
        # Step 1: Complete upper bracket round 0 exactly as in real tournament
        print("Step 1: Complete upper bracket round 0")
        for match in data['brackets']['upper'][0]:
            if match['player1']['name'] == 'fungus664':
                match['winner'] = match['player1']  # fungus664 beats incomplet
            elif match['player1']['name'] == 'Santa Claus':
                match['winner'] = match['player1']  # Santa Claus beats XBisch_LasagnaX
            # African Stride and finnduino already have BYE wins
            
            match['score_p1'] = 4 if match.get('winner', {}).get('id') == match['player1']['id'] else 0
            match['score_p2'] = 4 if match.get('winner', {}).get('id') == match['player2']['id'] else 0
            match['status'] = 'completed'
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"After upper round 0: Lower bracket has {len(data['brackets'].get('lower', []))} rounds")
        
        # Step 2: Complete lower bracket round 0
        print("\nStep 2: Complete lower bracket round 0") 
        if data['brackets'].get('lower'):
            for match in data['brackets']['lower'][0]:
                print(f"  Match: {match['player1']['name']} vs {match['player2']['name']}")
                if match['player1']['name'] == 'XBisch_LasagnaX':
                    match['winner'] = match['player1']  # XBisch_LasagnaX beats incomplet
                match['score_p1'] = 4 if match.get('winner', {}).get('id') == match['player1']['id'] else 0
                match['score_p2'] = 4 if match.get('winner', {}).get('id') == match['player2']['id'] else 0
                match['status'] = 'completed'
        
        save_tournament_data(data)
        
        # Step 3: Complete upper bracket round 1
        print("\nStep 3: Complete upper bracket round 1")
        for match in data['brackets']['upper'][1]:
            print(f"  Match: {match['player1']['name']} vs {match['player2']['name']}")
            if match['player1']['name'] == 'African Stride':
                match['winner'] = match['player1']  # African Stride beats Santa Claus
            elif match['player1']['name'] == 'finnduino':
                match['winner'] = match['player1']  # finnduino beats fungus664
            
            match['score_p1'] = 4 if match.get('winner', {}).get('id') == match['player1']['id'] else 0
            match['score_p2'] = 4 if match.get('winner', {}).get('id') == match['player2']['id'] else 0
            match['status'] = 'completed'
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        # Step 4: Check if XBisch_LasagnaX is in lower bracket round 1
        print(f"\nAfter upper round 1: Lower bracket has {len(data['brackets'].get('lower', []))} rounds")
        
        if len(data['brackets'].get('lower', [])) > 1:
            print("Lower bracket round 1 matches:")
            for match in data['brackets']['lower'][1]:
                print(f"  {match['player1']['name']} vs {match['player2']['name']}")
        
        # Check if XBisch_LasagnaX is anywhere in the tournament
        xbisch_found = False
        
        # Check all lower bracket rounds
        for round_idx, round_matches in enumerate(data['brackets'].get('lower', [])):
            for match in round_matches:
                if match['player1'].get('name') == 'XBisch_LasagnaX' or match['player2'].get('name') == 'XBisch_LasagnaX':
                    print(f"XBisch_LasagnaX found in lower round {round_idx}")
                    xbisch_found = True
        
        # Check pending upper losers
        for player in data.get('pending_upper_losers', []):
            if player.get('name') == 'XBisch_LasagnaX':
                print("XBisch_LasagnaX found in pending upper losers")
                xbisch_found = True
        
        # Check eliminated
        for player in data.get('eliminated', []):
            if player.get('name') == 'XBisch_LasagnaX':
                print(f"XBisch_LasagnaX found in eliminated (round {player.get('eliminated_in_round')})")
                xbisch_found = True
        
        if not xbisch_found:
            print("❌ BUG: XBisch_LasagnaX completely disappeared from tournament!")
            return False
        else:
            print("✅ XBisch_LasagnaX properly tracked in tournament")
            return True
            
    finally:
        # Restore original data
        save_tournament_data(current_data)
        print("\n(Original tournament data restored)")

if __name__ == '__main__':
    success = test_xbisch_bug_exact()
    print(f"\nXBisch_LasagnaX Bug Fix Test: {'PASSED' if success else 'FAILED'}")
