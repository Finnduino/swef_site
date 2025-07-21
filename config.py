import os
from dotenv import load_dotenv

load_dotenv()

# --- Flask Config ---
SECRET_KEY = os.getenv('FLASK_SECRET_KEY')

# --- SocketIO Config ---
SOCKETIO_ASYNC_MODE = 'threading'  # Use threading for shared hosting compatibility
SOCKETIO_PING_TIMEOUT = 60
SOCKETIO_PING_INTERVAL = 25

# --- osu! API Config ---
OSU_CLIENT_ID = int(os.getenv('OSU_CLIENT_ID'))
OSU_CLIENT_SECRET = os.getenv('OSU_CLIENT_SECRET')
OSU_CALLBACK_URL = os.getenv('OSU_CALLBACK_URL')
ADMIN_REDIRECT_URI = OSU_CALLBACK_URL.replace('/callback/osu', '/admin/callback')
ADMIN_OSU_ID = ['11365195', '11579864'] # Your osu! user ID

# --- API URLs ---
OSU_API_BASE_URL = 'https://osu.ppy.sh/api/v2'
TOKEN_URL = 'https://osu.ppy.sh/oauth/token'
AUTHORIZATION_URL = 'https://osu.ppy.sh/oauth/authorize'

# --- File Paths ---
TOURNAMENT_FILE = 'tournament.json'
COMPETITORS_FILE = 'competitors.json'
