#!/usr/bin/env python3
"""
Test specifically for 2-player tournament to verify it works correctly.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
sys.path.insert(0, project_root)

from app.bracket_logic import generate_bracket, advance_round_if_ready
from app.data_manager import get_tournament_data, save_tournament_data

def test_two_player_double_elim():
    """Test a complete 2-player double elimination tournament."""
    print("=== Testing 2-Player Double Elimination ===")
    
    # Backup current data
    current_data = get_tournament_data()
    
    try:
        # Create a 2-player tournament
        test_data = {
            'competitors': [
                {'id': 100, 'name': 'Alice', 'pp': 6000},
                {'id': 200, 'name': 'Bob', 'pp': 5000}
            ]
        }
        
        save_tournament_data(test_data)
        
        # Step 1: Generate initial bracket
        print("Step 1: Generate initial bracket")
        generate_bracket()
        data = get_tournament_data()
        
        print(f"Upper bracket has {len(data['brackets']['upper'])} rounds")
        print(f"Match: {data['brackets']['upper'][0][0]['player1']['name']} vs {data['brackets']['upper'][0][0]['player2']['name']}")
        
        # Step 2: Alice wins upper bracket finals
        print("\nStep 2: Alice wins upper bracket")
        match = data['brackets']['upper'][0][0]
        match['winner'] = {'id': 100, 'name': 'Alice', 'pp': 6000}
        match['score_p1'] = 4
        match['score_p2'] = 2
        match['status'] = 'completed'
        save_tournament_data(data)
        
        # Step 3: Advance bracket (should create grand finals or set up lower bracket)
        print("\nStep 3: Advance bracket")
        print(f"Before advance - Pending upper losers: {data.get('pending_upper_losers', [])}")
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"After advance - Pending upper losers: {len(data.get('pending_upper_losers', []))}")
        for p in data.get('pending_upper_losers', []):
            print(f"  - {p['name']}")
        print(f"Lower bracket rounds: {len(data['brackets'].get('lower', []))}")
        print(f"Grand finals exists: {'grand_finals' in data['brackets']}")
        
        if 'grand_finals' in data['brackets']:
            gf = data['brackets']['grand_finals']
            print(f"Grand finals: {gf['player1']['name']} vs {gf['player2']['name']}")
            
            # Step 4a: Test bracket reset (Bob wins first grand finals)
            print("\nStep 4a: Bob wins first grand finals (bracket reset)")
            gf['winner'] = gf['player2']  # Bob wins
            gf['score_p1'] = 2
            gf['score_p2'] = 4
            gf['status'] = 'completed'
            save_tournament_data(data)
            
            advance_round_if_ready(data)
            data = get_tournament_data()
            
            if data['brackets']['grand_finals'].get('is_bracket_reset'):
                print("✓ Bracket reset created correctly")
                
                # Step 5: Alice wins bracket reset
                print("\nStep 5: Alice wins bracket reset")
                gf = data['brackets']['grand_finals']
                gf['winner'] = gf['player1']  # Alice wins
                gf['score_p1'] = 4
                gf['score_p2'] = 1
                gf['status'] = 'completed'
                save_tournament_data(data)
                
                advance_round_if_ready(data)
                data = get_tournament_data()
                
                eliminated = data.get('eliminated', [])
                print(f"Eliminated players: {[p['name'] for p in eliminated]}")
                
                if len(eliminated) == 1 and eliminated[0]['name'] == 'Bob':
                    print("✓ Tournament completed correctly - Bob eliminated as runner-up")
                    return True
                else:
                    print("✗ Elimination not tracked correctly")
                    return False
            else:
                print("✗ Bracket reset not created")
                return False
        else:
            print("✗ Grand finals not created")
            return False
            
    finally:
        # Restore original data
        save_tournament_data(current_data)
        print("\n(Original tournament data restored)")
    
    return False

if __name__ == '__main__':
    success = test_two_player_double_elim()
    print(f"\n2-Player Tournament Test: {'PASSED' if success else 'FAILED'}")
