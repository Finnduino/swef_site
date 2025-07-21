#!/usr/bin/env python3
"""
Test playing upper bracket to completion WITHOUT advancing bracket logic,
then advance all at once. This might be how tournaments are actually run.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
sys.path.insert(0, project_root)

from app.bracket_logic import generate_bracket, advance_round_if_ready
from app.data_manager import get_tournament_data, save_tournament_data

def test_upper_no_advance():
    """Test completing upper bracket without calling advance_round_if_ready."""
    print("=== Testing Upper Bracket Completion Without Advancing ===")
    
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
        
        print("=== Complete ALL Upper Bracket Matches First ===")
        
        # Upper Round 0
        print("\nCompleting Upper Round 0:")
        for match in data['brackets']['upper'][0]:
            if match['player2'].get('name') == 'BYE':
                continue
            elif match['player1']['name'] == 'fungus664':
                match['winner'] = match['player1']  # fungus664 beats incomplet
                print(f"  {match['player1']['name']} beats {match['player2']['name']}")
            elif match['player1']['name'] == 'Santa Claus':
                match['winner'] = match['player1']  # Santa beats XBisch
                print(f"  {match['player1']['name']} beats {match['player2']['name']}")
            
            if match.get('winner'):
                match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
                match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
                match['status'] = 'completed'
        
        # DON'T advance yet - save and continue with upper bracket
        save_tournament_data(data)
        # NO advance_round_if_ready call here!
        
        # Upper Round 1
        print("\nCompleting Upper Round 1:")
        for match in data['brackets']['upper'][1]:
            if match['player1']['name'] == 'African Stride':
                match['winner'] = match['player1']  # African beats Santa
                print(f"  {match['player1']['name']} beats {match['player2']['name']}")
            elif match['player1']['name'] == 'finnduino':
                match['winner'] = match['player1']  # finnduino beats fungus
                print(f"  {match['player1']['name']} beats {match['player2']['name']}")
            
            match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
            match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
            match['status'] = 'completed'
        
        # Still don't advance
        save_tournament_data(data)
        
        # Upper Round 2 (Finals)
        print("\nCompleting Upper Round 2 (Finals):")
        for match in data['brackets']['upper'][2]:
            match['winner'] = match['player1']  # African beats finnduino
            print(f"  {match['player1']['name']} beats {match['player2']['name']}")
            
            match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
            match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
            match['status'] = 'completed'
        
        save_tournament_data(data)
        
        print("\n=== NOW Advance Bracket Logic ===")
        # Now advance the bracket logic all at once
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"Pending upper losers: {len(data.get('pending_upper_losers', []))}")
        for p in data.get('pending_upper_losers', []):
            print(f"  - {p['name']}")
        
        print(f"Lower bracket has {len(data['brackets'].get('lower', []))} rounds")
        if data['brackets'].get('lower'):
            for round_idx, round_matches in enumerate(data['brackets']['lower']):
                print(f"Lower Round {round_idx}:")
                for match in round_matches:
                    print(f"  {match['player1']['name']} vs {match['player2']['name']}")
        
        print(f"Eliminated: {[p['name'] for p in data.get('eliminated', [])]}")
        
        # Check for missing players
        all_players = set()
        
        # Upper bracket (winner)
        for round_matches in data['brackets'].get('upper', []):
            for match in round_matches:
                if match.get('winner'):
                    all_players.add(match['winner']['name'])
        
        # Lower bracket
        for round_matches in data['brackets'].get('lower', []):
            for match in round_matches:
                if match['player1'].get('name'):
                    all_players.add(match['player1']['name'])
                if match['player2'].get('name'):
                    all_players.add(match['player2']['name'])
        
        # Pending and eliminated
        for p in data.get('pending_upper_losers', []):
            all_players.add(p['name'])
        for p in data.get('eliminated', []):
            all_players.add(p['name'])
        
        expected = {'African Stride', 'finnduino', 'fungus664', 'Santa Claus', 'XBisch_LasagnaX', 'incomplet'}
        missing = expected - all_players
        
        if missing:
            print(f"\n❌ MISSING PLAYERS: {missing}")
            return False
        else:
            print(f"\n✅ All players accounted for")
            return True
        
    finally:
        save_tournament_data(current_data)
        print("\n(Original data restored)")

if __name__ == '__main__':
    success = test_upper_no_advance()
    print(f"\nNo-Advance Test: {'PASSED' if success else 'FAILED'}")
