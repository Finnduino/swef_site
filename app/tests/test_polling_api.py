"""
Test script to verify HTTP polling works without SocketIO
"""
import requests
import json

def test_api_endpoints():
    base_url = "http://localhost:5000"  # Change to your actual URL
    
    print("Testing HTTP polling API endpoints...")
    
    # Test match data endpoint
    try:
        response = requests.get(f"{base_url}/api/match-data")
        print(f"Match Data API: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Match found: {data.get('match_found', False)}")
            print(f"  Last updated: {data.get('last_updated', 'N/A')}")
        else:
            print(f"  Error: {response.text}")
    except Exception as e:
        print(f"  Error testing match data: {e}")
    
    # Test overlay events endpoint
    try:
        response = requests.get(f"{base_url}/api/overlay-events")
        print(f"Overlay Events API: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Events count: {len(data.get('events', []))}")
            print(f"  AFK mode: {data.get('afk_mode', False)}")
        else:
            print(f"  Error: {response.text}")
    except Exception as e:
        print(f"  Error testing overlay events: {e}")

if __name__ == "__main__":
    test_api_endpoints()
