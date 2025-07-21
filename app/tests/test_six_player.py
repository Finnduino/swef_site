#!/usr/bin/env python3
"""
Test to reproduce the XBisch_LasagnaX disappearing bug.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
sys.path.insert(0, project_root)

from app.bracket_logic import generate_bracket, advance_round_if_ready
from app.data_manager import get_tournament_data, save_tournament_data

def test_six_player_tournament():
    """Test 6-player tournament to reproduce the missing player bug."""
    print("=== Testing 6-Player Tournament (XBisch_LasagnaX Bug) ===")
    
    # Backup current data
    current_data = get_tournament_data()
    
    try:
        # Create the exact scenario from the tournament
        test_data = {
            'competitors': [
                {'id': 1, 'name': 'African Stride', 'pp': 6091.17},
                {'id': 2, 'name': 'finnduino', 'pp': 5980.92},
                {'id': 3, 'name': 'fungus664', 'pp': 5117.25},
                {'id': 4, 'name': 'Santa Claus', 'pp': 4649.93},
                {'id': 5, 'name': 'XBisch_LasagnaX', 'pp': 2339.37},
                {'id': 6, 'name': 'incomplet', 'pp': 589.761}
            ]
        }
        
        save_tournament_data(test_data)
        
        # Step 1: Generate initial bracket
        print("Step 1: Generate initial bracket")
        generate_bracket()
        data = get_tournament_data()
        
        print(f"Upper bracket round 0 has {len(data['brackets']['upper'][0])} matches")
        
        # Step 2: Complete round 0 upper bracket matches
        print("\nStep 2: Complete round 0 upper bracket")
        for i, match in enumerate(data['brackets']['upper'][0]):
            print(f"Match {i}: {match['player1']['name']} vs {match['player2']['name']}")
            if match['player2'].get('name') == 'BYE':
                # Already completed
                continue
            # Simulate the results from the actual tournament
            if match['player1']['name'] == 'fungus664' and match['player2']['name'] == 'incomplet':
                match['winner'] = match['player1']  # fungus664 wins
            elif match['player1']['name'] == 'Santa Claus' and match['player2']['name'] == 'XBisch_LasagnaX':
                match['winner'] = match['player1']  # Santa Claus wins
            else:
                # Default to player1 winning
                match['winner'] = match['player1']
            
            match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
            match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
            match['status'] = 'completed'
        
        save_tournament_data(data)
        
        # Step 3: Advance bracket (should create lower bracket round 0)
        print("\nStep 3: Advance to create lower bracket round 0")
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"Lower bracket has {len(data['brackets'].get('lower', []))} rounds")
        if data['brackets'].get('lower'):
            print(f"Lower round 0 has {len(data['brackets']['lower'][0])} matches")
            for match in data['brackets']['lower'][0]:
                print(f"  {match['player1']['name']} vs {match['player2']['name']}")
        
        # Step 4: Complete lower bracket round 0
        print("\nStep 4: Complete lower bracket round 0")
        if data['brackets'].get('lower'):
            for match in data['brackets']['lower'][0]:
                # XBisch_LasagnaX beats incomplet
                if 'XBisch_LasagnaX' in [match['player1']['name'], match['player2']['name']]:
                    match['winner'] = match['player1'] if match['player1']['name'] == 'XBisch_LasagnaX' else match['player2']
                    match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
                    match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
                    match['status'] = 'completed'
        
        save_tournament_data(data)
        
        # Step 5: Complete upper bracket round 1
        print("\nStep 5: Complete upper bracket round 1")
        if len(data['brackets']['upper']) > 1:
            for match in data['brackets']['upper'][1]:
                # African Stride beats Santa Claus, finnduino beats fungus664
                if match['player1']['name'] == 'African Stride':
                    match['winner'] = match['player1']
                elif match['player1']['name'] == 'finnduino':
                    match['winner'] = match['player1']
                match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
                match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
                match['status'] = 'completed'
        
        save_tournament_data(data)
        
        # Step 6: Advance bracket (should create lower bracket round 1)
        print("\nStep 6: Advance to create lower bracket round 1")
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"Lower bracket now has {len(data['brackets'].get('lower', []))} rounds")
        if len(data['brackets'].get('lower', [])) > 1:
            print(f"Lower round 1 has {len(data['brackets']['lower'][1])} matches")
            for match in data['brackets']['lower'][1]:
                print(f"  {match['player1']['name']} vs {match['player2']['name']}")
        
        # Check if XBisch_LasagnaX is still in the tournament
        all_players_in_brackets = set()
        
        # Check all brackets for XBisch_LasagnaX
        for round_matches in data['brackets'].get('upper', []):
            for match in round_matches:
                if match['player1'].get('name'):
                    all_players_in_brackets.add(match['player1']['name'])
                if match['player2'].get('name'):
                    all_players_in_brackets.add(match['player2']['name'])
        
        for round_matches in data['brackets'].get('lower', []):
            for match in round_matches:
                if match['player1'].get('name'):
                    all_players_in_brackets.add(match['player1']['name'])
                if match['player2'].get('name'):
                    all_players_in_brackets.add(match['player2']['name'])
        
        print(f"\nPending upper losers: {[p['name'] for p in data.get('pending_upper_losers', [])]}")
        print(f"Eliminated players: {[p['name'] for p in data.get('eliminated', [])]}")
        
        if 'XBisch_LasagnaX' not in all_players_in_brackets and 'XBisch_LasagnaX' not in [p['name'] for p in data.get('pending_upper_losers', [])]:
            print("❌ BUG REPRODUCED: XBisch_LasagnaX disappeared from the tournament!")
            return False
        else:
            print("✅ XBisch_LasagnaX is still in the tournament")
            return True
            
    finally:
        # Restore original data
        save_tournament_data(current_data)
        print("\n(Original tournament data restored)")

if __name__ == '__main__':
    success = test_six_player_tournament()
    print(f"\n6-Player Tournament Test: {'PASSED' if success else 'FAILED'}")
