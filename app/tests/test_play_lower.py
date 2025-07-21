#!/usr/bin/env python3
"""
Test the theory: after upper bracket completion, play the auto-created lower bracket matches.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
sys.path.insert(0, project_root)

from app.bracket_logic import generate_bracket, advance_round_if_ready
from app.data_manager import get_tournament_data, save_tournament_data

def test_play_autocreated_lower():
    """Test playing the auto-created lower bracket matches."""
    print("=== Testing Playing Auto-Created Lower Bracket ===")
    
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
        
        # Complete upper bracket with advancement after each round
        # Upper Round 0
        for match in data['brackets']['upper'][0]:
            if match['player2'].get('name') == 'BYE':
                continue
            elif match['player1']['name'] == 'fungus664':
                match['winner'] = match['player1']
            elif match['player1']['name'] == 'Santa Claus':
                match['winner'] = match['player1']
            
            if match.get('winner'):
                match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
                match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
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
        
        # Upper Round 2
        for match in data['brackets']['upper'][2]:
            match['winner'] = match['player1']  # African Stride wins
            match['score_p1'] = 4
            match['score_p2'] = 2
            match['status'] = 'completed'
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print("After completing upper bracket:")
        print(f"Lower bracket has {len(data['brackets'].get('lower', []))} rounds")
        
        # NOW play the lower bracket matches that were auto-created
        print("\n=== Playing Lower Bracket Round 0 ===")
        if data['brackets'].get('lower') and len(data['brackets']['lower']) > 0:
            for match in data['brackets']['lower'][0]:
                print(f"Playing: {match['player1']['name']} vs {match['player2']['name']}")
                # XBisch_LasagnaX beats incomplet
                if match['player1']['name'] == 'XBisch_LasagnaX':
                    match['winner'] = match['player1']
                elif match['player2']['name'] == 'XBisch_LasagnaX':
                    match['winner'] = match['player2']
                
                match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
                match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
                match['status'] = 'completed'
                print(f"  -> {match['winner']['name']} wins")
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"\nAfter lower round 0: Eliminated = {[p['name'] for p in data.get('eliminated', [])]}")
        
        print("\n=== Playing Lower Bracket Round 1 ===")
        if len(data['brackets'].get('lower', [])) > 1:
            for match in data['brackets']['lower'][1]:
                print(f"Playing: {match['player1']['name']} vs {match['player2']['name']}")
                # fungus664 beats Santa Claus
                if match['player1']['name'] == 'fungus664':
                    match['winner'] = match['player1']
                elif match['player2']['name'] == 'fungus664':
                    match['winner'] = match['player2']
                
                match['score_p1'] = 4 if match['winner']['id'] == match['player1']['id'] else 0
                match['score_p2'] = 4 if match['winner']['id'] == match['player2']['id'] else 0
                match['status'] = 'completed'
                print(f"  -> {match['winner']['name']} wins")
        
        save_tournament_data(data)
        advance_round_if_ready(data)
        data = get_tournament_data()
        
        print(f"\nAfter lower round 1: Eliminated = {[p['name'] for p in data.get('eliminated', [])]}")
        
        # Check final state
        all_players = set()
        
        # Check all brackets and states
        for round_matches in data['brackets'].get('upper', []):
            for match in round_matches:
                if match.get('winner'):
                    all_players.add(match['winner']['name'])
        
        for round_matches in data['brackets'].get('lower', []):
            for match in round_matches:
                if match['player1'].get('name'):
                    all_players.add(match['player1']['name'])
                if match['player2'].get('name'):
                    all_players.add(match['player2']['name'])
        
        for p in data.get('pending_upper_losers', []):
            all_players.add(p['name'])
        for p in data.get('eliminated', []):
            all_players.add(p['name'])
        
        if 'grand_finals' in data['brackets']:
            gf = data['brackets']['grand_finals']
            all_players.add(gf['player1']['name'])
            all_players.add(gf['player2']['name'])
        
        expected = {'African Stride', 'finnduino', 'fungus664', 'Santa Claus', 'XBisch_LasagnaX', 'incomplet'}
        missing = expected - all_players
        
        print(f"\nAll players found: {sorted(all_players)}")
        print(f"Expected players: {sorted(expected)}")
        
        if missing:
            print(f"❌ MISSING: {missing}")
            return False
        else:
            print("✅ All players accounted for")
            return True
        
    finally:
        save_tournament_data(current_data)
        print("\n(Original data restored)")

if __name__ == '__main__':
    success = test_play_autocreated_lower()
    print(f"\nAuto-Created Lower Test: {'PASSED' if success else 'FAILED'}")
