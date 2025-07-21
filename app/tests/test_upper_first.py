#!/usr/bin/env python3
"""
Test the exact sequence: play upper bracket to completion FIRST, then lower bracket.
This might reveal the bug where players disappear.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
sys.path.insert(0, project_root)

from app.bracket_logic import generate_bracket, advance_round_if_ready
from app.data_manager import get_tournament_data, save_tournament_data

def test_upper_first_then_lower():
    """Test playing upper bracket to completion first, then lower bracket."""
    print("=== Testing Upper Bracket First, Then Lower Bracket ===")
    
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
        print("\nUpper Round 0:")
        for match in data['brackets']['upper'][0]:
            print(f"  {match['player1']['name']} vs {match['player2']['name']}")
            if match['player2'].get('name') == 'BYE':
                continue
            elif match['player1']['name'] == 'fungus664':
                match['winner'] = match['player1']  # fungus664 beats incomplet
                print(f"    -> {match['player1']['name']} wins")
            elif match['player1']['name'] == 'Santa Claus':
                match['winner'] = match['player1']  # Santa beats XBisch
                print(f"    -> {match['player1']['name']} wins")
            
            if match.get('winner'):
                match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
                match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
                match['status'] = 'completed'
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"After upper round 0: Pending upper losers = {len(data.get('pending_upper_losers', []))}")
        for p in data.get('pending_upper_losers', []):
            print(f"  - {p['name']}")
        
        # Upper Round 1
        print("\nUpper Round 1:")
        for match in data['brackets']['upper'][1]:
            print(f"  {match['player1']['name']} vs {match['player2']['name']}")
            if match['player1']['name'] == 'African Stride':
                match['winner'] = match['player1']  # African beats Santa
                print(f"    -> {match['player1']['name']} wins")
            elif match['player1']['name'] == 'finnduino':
                match['winner'] = match['player1']  # finnduino beats fungus
                print(f"    -> {match['player1']['name']} wins")
            
            match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
            match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
            match['status'] = 'completed'
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"After upper round 1: Pending upper losers = {len(data.get('pending_upper_losers', []))}")
        for p in data.get('pending_upper_losers', []):
            print(f"  - {p['name']}")
        
        # Upper Round 2 (Finals)
        print("\nUpper Round 2 (Finals):")
        for match in data['brackets']['upper'][2]:
            print(f"  {match['player1']['name']} vs {match['player2']['name']}")
            match['winner'] = match['player1']  # African beats finnduino
            print(f"    -> {match['player1']['name']} wins")
            
            match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
            match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
            match['status'] = 'completed'
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"After upper finals: Pending upper losers = {len(data.get('pending_upper_losers', []))}")
        for p in data.get('pending_upper_losers', []):
            print(f"  - {p['name']}")
        
        print(f"Lower bracket has {len(data['brackets'].get('lower', []))} rounds")
        
        print("\n=== PHASE 2: Now Play Lower Bracket ===")
        
        # Check what's in the lower bracket
        if data['brackets'].get('lower'):
            for round_idx, round_matches in enumerate(data['brackets']['lower']):
                print(f"\nLower Round {round_idx}:")
                for match in round_matches:
                    print(f"  {match['player1']['name']} vs {match['player2']['name']}")
        
        # Check if incomplet and XBisch_LasagnaX are anywhere
        all_players_in_tournament = set()
        
        # Check upper bracket
        for round_matches in data['brackets'].get('upper', []):
            for match in round_matches:
                if match['player1'].get('name'):
                    all_players_in_tournament.add(match['player1']['name'])
                if match['player2'].get('name'):
                    all_players_in_tournament.add(match['player2']['name'])
                if match.get('winner') and match['winner'].get('name'):
                    all_players_in_tournament.add(match['winner']['name'])
        
        # Check lower bracket
        for round_matches in data['brackets'].get('lower', []):
            for match in round_matches:
                if match['player1'].get('name'):
                    all_players_in_tournament.add(match['player1']['name'])
                if match['player2'].get('name'):
                    all_players_in_tournament.add(match['player2']['name'])
                if match.get('winner') and match['winner'].get('name'):
                    all_players_in_tournament.add(match['winner']['name'])
        
        # Check grand finals
        if 'grand_finals' in data['brackets']:
            gf = data['brackets']['grand_finals']
            if gf.get('player1', {}).get('name'):
                all_players_in_tournament.add(gf['player1']['name'])
            if gf.get('player2', {}).get('name'):
                all_players_in_tournament.add(gf['player2']['name'])
            if gf.get('winner') and gf['winner'].get('name'):
                all_players_in_tournament.add(gf['winner']['name'])
        
        # Check pending
        for p in data.get('pending_upper_losers', []):
            all_players_in_tournament.add(p['name'])
        
        # Check eliminated
        eliminated_names = [p['name'] for p in data.get('eliminated', [])]
        for name in eliminated_names:
            all_players_in_tournament.add(name)
        
        print(f"\nEliminated players: {eliminated_names}")
        print(f"Players found in tournament: {sorted(all_players_in_tournament)}")
        
        missing_players = []
        expected_players = ['African Stride', 'finnduino', 'fungus664', 'Santa Claus', 'XBisch_LasagnaX', 'incomplet']
        
        for player in expected_players:
            if player not in all_players_in_tournament:
                missing_players.append(player)
        
        if missing_players:
            print(f"❌ MISSING PLAYERS: {missing_players}")
            return False
        else:
            print("✅ All players accounted for")
            return True
        
    finally:
        save_tournament_data(current_data)
        print("\n(Original data restored)")

if __name__ == '__main__':
    success = test_upper_first_then_lower()
    print(f"\nUpper-First Test: {'PASSED' if success else 'FAILED'}")
