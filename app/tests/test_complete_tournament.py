#!/usr/bin/env python3
"""
Play through a complete 6-player tournament to ensure all eliminations are tracked correctly.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
sys.path.insert(0, project_root)

from app.bracket_logic import generate_bracket, advance_round_if_ready
from app.data_manager import get_tournament_data, save_tournament_data

def test_complete_tournament():
    """Play through a complete tournament to verify all eliminations."""
    print("=== Complete 6-Player Tournament Test ===")
    
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
        
        def complete_round(bracket_type, round_idx, results):
            """Complete a round with given results."""
            print(f"\nCompleting {bracket_type} round {round_idx}:")
            rounds = data['brackets'][bracket_type]
            if round_idx < len(rounds):
                for i, match in enumerate(rounds[round_idx]):
                    if match['player2'].get('name') == 'BYE':
                        continue
                    
                    winner_name = results.get(i, match['player1']['name'])  # Default to player1
                    if winner_name == match['player1']['name']:
                        match['winner'] = match['player1']
                    else:
                        match['winner'] = match['player2']
                    
                    match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
                    match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
                    match['status'] = 'completed'
                    
                    loser = match['player2'] if match['winner']['id'] == match['player1']['id'] else match['player1']
                    print(f"  {match['winner']['name']} beats {loser['name']}")
        
        # Play through the tournament
        # Upper Round 0
        complete_round('upper', 0, {0: 'fungus664', 1: 'Santa Claus'})  # fungus664 beats incomplet, Santa beats XBisch
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        # Lower Round 0  
        complete_round('lower', 0, {0: 'XBisch_LasagnaX'})  # XBisch beats incomplet
        save_tournament_data(data)
        
        # Upper Round 1
        complete_round('upper', 1, {0: 'African Stride', 1: 'finnduino'})  # African beats Santa, finnduino beats fungus
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        # Lower Round 1
        complete_round('lower', 1, {0: 'XBisch_LasagnaX', 1: 'fungus664'})  # XBisch beats BYE, fungus beats Santa
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        # Lower Round 2
        complete_round('lower', 2, {0: 'fungus664'})  # fungus beats XBisch
        save_tournament_data(data)
        
        # Upper Round 2 (Finals)
        complete_round('upper', 2, {0: 'African Stride'})  # African beats finnduino
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        # Lower Finals
        if len(data['brackets'].get('lower', [])) > 2:
            complete_round('lower', 3, {0: 'fungus664'})  # fungus beats finnduino
            save_tournament_data(data)
            advance_round_if_ready(data)
            data = get_tournament_data()
        
        # Grand Finals
        if 'grand_finals' in data['brackets']:
            gf = data['brackets']['grand_finals']
            gf['winner'] = gf['player1']  # African Stride wins
            gf['score_p1'] = 4
            gf['score_p2'] = 2
            gf['status'] = 'completed'
            save_tournament_data(data)
            advance_round_if_ready(data)
            data = get_tournament_data()
        
        # Check final results
        eliminated = [p['name'] for p in data.get('eliminated', [])]
        print(f"\nFinal eliminated players: {eliminated}")
        
        expected_eliminated = ['incomplet', 'Santa Claus', 'XBisch_LasagnaX', 'finnduino', 'fungus664']
        
        all_accounted = all(name in eliminated for name in expected_eliminated)
        correct_count = len(eliminated) == 5  # Everyone except winner
        
        print(f"All 5 players eliminated: {'✅' if correct_count else '❌'}")
        print(f"All expected players eliminated: {'✅' if all_accounted else '❌'}")
        
        if not all_accounted:
            missing = [name for name in expected_eliminated if name not in eliminated]
            print(f"Missing from eliminated list: {missing}")
        
        return all_accounted and correct_count
        
    finally:
        save_tournament_data(current_data)
        print("\n(Original data restored)")

if __name__ == '__main__':
    success = test_complete_tournament()
    print(f"\nComplete Tournament Test: {'PASSED' if success else 'FAILED'}")
