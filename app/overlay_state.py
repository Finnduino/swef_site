"""
Overlay state management for Namecheap hosting (no SocketIO)
Simple file-based state management for overlay events
"""
import json
import os
from datetime import datetime
from typing import Dict, Any

OVERLAY_STATE_FILE = 'overlay_state.json'

def get_overlay_state() -> Dict[str, Any]:
    """Get current overlay state"""
    try:
        if os.path.exists(OVERLAY_STATE_FILE):
            with open(OVERLAY_STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error reading overlay state: {e}")
    
    # Return default state
    return {
        'afk_mode': False,
        'victory_screen_hidden': False,
        'last_updated': datetime.utcnow().isoformat(),
        'events': []
    }

def update_overlay_state(updates: Dict[str, Any]):
    """Update overlay state"""
    try:
        state = get_overlay_state()
        state.update(updates)
        state['last_updated'] = datetime.utcnow().isoformat()
        
        with open(OVERLAY_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error updating overlay state: {e}")
        return False

def add_overlay_event(event_type: str, data: Dict[str, Any] = None):
    """Add an event to the overlay state"""
    try:
        state = get_overlay_state()
        
        # Keep only the last 10 events
        if 'events' not in state:
            state['events'] = []
        
        event = {
            'type': event_type,
            'data': data or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        state['events'].append(event)
        state['events'] = state['events'][-10:]  # Keep last 10 events
        state['last_updated'] = datetime.utcnow().isoformat()
        
        with open(OVERLAY_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error adding overlay event: {e}")
        return False

def clear_overlay_events():
    """Clear all overlay events"""
    try:
        state = get_overlay_state()
        state['events'] = []
        state['last_updated'] = datetime.utcnow().isoformat()
        
        with open(OVERLAY_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error clearing overlay events: {e}")
        return False
