import re
from ..data_manager import get_tournament_data, save_tournament_data


class StreamingService:
    def __init__(self):
        pass
    
    def set_stream_channel(self, twitch_channel):
        """Set Twitch channel for streaming"""
        if not twitch_channel:
            return {'message': 'Twitch channel name is required.', 'type': 'error'}
        
        # Clean channel name (remove twitch.tv/ if included)
        if 'twitch.tv/' in twitch_channel:
            twitch_channel = twitch_channel.split('twitch.tv/')[-1]
        
        # Remove any extra characters
        twitch_channel = re.sub(r'[^a-zA-Z0-9_]', '', twitch_channel)
        
        if not twitch_channel:
            return {'message': 'Invalid Twitch channel name.', 'type': 'error'}
        
        data = get_tournament_data()
        data['twitch_channel'] = twitch_channel
        
        save_tournament_data(data)
        return {'message': f'Twitch channel set to: {twitch_channel}', 'type': 'success'}
    
    def toggle_stream(self):
        """Toggle stream live status"""
        data = get_tournament_data()
        
        if not data.get('twitch_channel'):
            return {'message': 'No Twitch channel configured.', 'type': 'error'}
        
        current_status = data.get('stream_live', False)
        data['stream_live'] = not current_status
        
        save_tournament_data(data)
        
        if data['stream_live']:
            return {'message': '🔴 Stream is now LIVE on the tournament page!', 'type': 'success'}
        else:
            return {'message': '⚫ Stream has been stopped and hidden from the tournament page.', 'type': 'info'}
    
    def clear_stream(self):
        """Clear stream settings"""
        data = get_tournament_data()
        
        data.pop('twitch_channel', None)
        data.pop('stream_live', None)
        
        save_tournament_data(data)
        return {'message': 'Stream settings cleared.', 'type': 'success'}
