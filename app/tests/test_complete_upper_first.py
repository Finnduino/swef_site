#!/usr/bin/env python3
"""
Test the complete upper-first workflow including playing the lower bracket to completion.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
sys.path.insert(0, project_root)

from app.bracket_logic import generate_bracket, advance_round_if_ready
from app.data_manager import get_tournament_data, save_tournament_data

def test_complete_upper_first():
    """Test complete upper-first workflow including lower bracket completion."""
    print("=== Testing Complete Upper-First Workflow ===")
    
    current_data = get_tournament_data()
    
    try:
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
        generate_bracket()
        data = get_tournament_data()
        
        print("=== PHASE 1: Play Upper Bracket to Completion ===")
        
        # Upper Round 0
        for match in data['brackets']['upper'][0]:
            if match['player2'].get('name') == 'BYE':
                continue
            elif match['player1']['name'] == 'fungus664':
                match['winner'] = match['player1']
                match['score_p1'] = 4
                match['score_p2'] = 0
                match['status'] = 'completed'
            elif match['player1']['name'] == 'Santa Claus':
                match['winner'] = match['player1']
                match['score_p1'] = 4
                match['score_p2'] = 0
                match['status'] = 'completed'
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        # Upper Round 1
        for match in data['brackets']['upper'][1]:
            if match['player1']['name'] == 'African Stride':
                match['winner'] = match['player1']
            elif match['player1']['name'] == 'finnduino':
                match['winner'] = match['player1']
            
            match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
            match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
            match['status'] = 'completed'
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        # Upper Finals
        for match in data['brackets']['upper'][2]:
            match['winner'] = match['player1']  # African beats finnduino
            match['score_p1'] = 4
            match['score_p2'] = 0
            match['status'] = 'completed'
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print("=== PHASE 2: Play Lower Bracket to Completion ===")
        
        # Lower Round 0: XBisch_LasagnaX vs incomplet
        print("\nLower Round 0:")
        for match in data['brackets']['lower'][0]:
            print(f"  {match['player1']['name']} vs {match['player2']['name']}")
            match['winner'] = match['player1']  # XBisch beats incomplet
            match['score_p1'] = 4
            match['score_p2'] = 0
            match['status'] = 'completed'
            print(f"    -> {match['winner']['name']} wins")
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"After lower round 0: {len(data.get('eliminated', []))} eliminated")
        for p in data.get('eliminated', []):
            print(f"  - {p['name']}")
        
        # Lower Round 1: fungus664 vs Santa Claus
        print("\nLower Round 1:")
        for match in data['brackets']['lower'][1]:
            print(f"  {match['player1']['name']} vs {match['player2']['name']}")
            match['winner'] = match['player1']  # fungus beats Santa
            match['score_p1'] = 4
            match['score_p2'] = 0
            match['status'] = 'completed'
            print(f"    -> {match['winner']['name']} wins")
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"After lower round 1: {len(data.get('eliminated', []))} eliminated")
        for p in data.get('eliminated', []):
            print(f"  - {p['name']}")
        
        # Check if next lower round was created
        if len(data['brackets']['lower']) > 2:
            print("\nLower Round 2:")
            for match in data['brackets']['lower'][2]:
                print(f"  {match['player1']['name']} vs {match['player2']['name']}")
                match['winner'] = match['player1']  # Assume first player wins
                match['score_p1'] = 4
                match['score_p2'] = 0
                match['status'] = 'completed'
                print(f"    -> {match['winner']['name']} wins")
            
            save_tournament_data(data)
            advance_round_if_ready(data)
            data = get_tournament_data()
            
            print(f"After lower round 2: {len(data.get('eliminated', []))} eliminated")
            for p in data.get('eliminated', []):
                print(f"  - {p['name']}")
        
        # Check if grand finals was created
        if 'grand_finals' in data['brackets']:
            print("\nGrand Finals created!")
            gf = data['brackets']['grand_finals']
            print(f"  {gf['player1']['name']} vs {gf['player2']['name']}")
        else:
            print("\nNo grand finals yet")
        
        # Count eliminations
        eliminated_count = len(data.get('eliminated', []))
        expected_eliminations = 4  # All except top 2
        
        print(f"\nEliminations: {eliminated_count}/{expected_eliminations}")
        if eliminated_count >= expected_eliminations:
            print("✅ Elimination tracking working correctly")
            return True
        else:
            print("❌ Missing eliminations")
            return False
        
    finally:
        save_tournament_data(current_data)
        print("\n(Original data restored)")

if __name__ == '__main__':
    success = test_complete_upper_first()
    print(f"\nComplete Upper-First Test: {'PASSED' if success else 'FAILED'}")
