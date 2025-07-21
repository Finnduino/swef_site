#!/usr/bin/env python3
"""
Test the current tournament state to see if XBisch_LasagnaX should still be in the tournament.
"""

import sys
import os
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)

from app.bracket_logic import advance_round_if_ready
from app.data_manager import get_tournament_data, save_tournament_data

def analyze_current_tournament():
    """Analyze the current tournament state."""
    print("=== Analyzing Current Tournament State ===")
    
    data = get_tournament_data()
    
    print("Current eliminated players:")
    for player in data.get('eliminated', []):
        print(f"  - {player['name']}: eliminated in round {player.get('eliminated_in_round')} of {player.get('bracket')} bracket")
    
    print(f"\nPending upper losers: {len(data.get('pending_upper_losers', []))}")
    for player in data.get('pending_upper_losers', []):
        print(f"  - {player['name']}: dropped from round {player.get('dropped_from_round')}")
    
    # Check what should happen next
    print("\nAnalyzing bracket progression:")
    
    # Look for XBisch_LasagnaX in all matches
    found_xbisch = False
    
    print("\nXBisch_LasagnaX appearances:")
    
    # Upper bracket
    for round_idx, round_matches in enumerate(data['brackets'].get('upper', [])):
        for match in round_matches:
            if match['player1'].get('name') == 'XBisch_LasagnaX':
                print(f"  Upper round {round_idx}: vs {match['player2']['name']} - {'WON' if match.get('winner', {}).get('name') == 'XBisch_LasagnaX' else 'LOST'}")
                found_xbisch = True
            elif match['player2'].get('name') == 'XBisch_LasagnaX':
                print(f"  Upper round {round_idx}: vs {match['player1']['name']} - {'WON' if match.get('winner', {}).get('name') == 'XBisch_LasagnaX' else 'LOST'}")
                found_xbisch = True
    
    # Lower bracket
    for round_idx, round_matches in enumerate(data['brackets'].get('lower', [])):
        for match in round_matches:
            if match['player1'].get('name') == 'XBisch_LasagnaX':
                print(f"  Lower round {round_idx}: vs {match['player2']['name']} - {'WON' if match.get('winner', {}).get('name') == 'XBisch_LasagnaX' else 'LOST'}")
                found_xbisch = True
            elif match['player2'].get('name') == 'XBisch_LasagnaX':
                print(f"  Lower round {round_idx}: vs {match['player1']['name']} - {'WON' if match.get('winner', {}).get('name') == 'XBisch_LasagnaX' else 'LOST'}")
                found_xbisch = True
    
    if not found_xbisch:
        print("  XBisch_LasagnaX not found in any matches beyond their initial appearances!")
    
    # Check what the next lower bracket round should contain
    print("\nExpected next lower bracket progression:")
    print("After lower round 0: XBisch_LasagnaX won vs incomplet")
    print("After upper round 1: Santa Claus and fungus664 dropped to lower bracket") 
    print("Lower round 1 should have been: XBisch_LasagnaX + Santa Claus + fungus664")
    print("But lower round 1 shows: Santa Claus vs fungus664 (XBisch_LasagnaX missing!)")
    
    return found_xbisch

if __name__ == '__main__':
    analyze_current_tournament()
