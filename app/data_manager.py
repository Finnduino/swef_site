import json
from config import TOURNAMENT_FILE

def get_tournament_data():
    """Reads tournament data from the JSON file."""
    try:
        with open(TOURNAMENT_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Create a default structure if file doesn't exist or is empty
        return {'competitors': [], 'brackets': {'upper': [], 'lower': []}}

def save_tournament_data(data):
    """Saves tournament data to the JSON file, sorting competitors by PP."""
    # Sort competitors by pp before saving
    if 'competitors' in data:
        data['competitors'].sort(key=lambda x: x.get('pp', 0), reverse=True)
    with open(TOURNAMENT_FILE, 'w') as f:
        json.dump(data, f, indent=2)
