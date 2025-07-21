from flask import Flask
from flask_socketio import SocketIO
from config import SECRET_KEY, SOCKETIO_ASYNC_MODE, SOCKETIO_PING_TIMEOUT, SOCKETIO_PING_INTERVAL
from ossapi import Ossapi
from config import OSU_CLIENT_ID, OSU_CLIENT_SECRET

# Create an instance of the osu! API client to be used in other parts of the app
api = Ossapi(OSU_CLIENT_ID, OSU_CLIENT_SECRET)

# Global SocketIO instance
socketio = None

def create_app():
    """Create and configure an instance of the Flask application."""
    global socketio
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object('config')
    
    # Initialize SocketIO with polling fallback for shared hosting
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*", 
        async_mode=SOCKETIO_ASYNC_MODE,
        transports=['websocket', 'polling'],  # Allow both WebSocket and polling
        ping_timeout=SOCKETIO_PING_TIMEOUT,
        ping_interval=SOCKETIO_PING_INTERVAL,
        logger=True,  # Enable logging for debugging
        engineio_logger=True
    )

    with app.app_context():
        # Import routes after initializing the app to avoid circular imports
        from .routes import public_bp, admin_bp

        # Register blueprints
        app.register_blueprint(public_bp)
        app.register_blueprint(admin_bp)
        
        # Import WebSocket events
        from . import websocket_events

    return app, socketio
