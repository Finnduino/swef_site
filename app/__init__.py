from flask import Flask
from ossapi import Ossapi
from config import OSU_CLIENT_ID, OSU_CLIENT_SECRET
from .models import db
from flask_socketio import SocketIO

# Create an instance of the osu! API client to be used in other parts of the app
api = Ossapi(OSU_CLIENT_ID, OSU_CLIENT_SECRET)
socketio = SocketIO()

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object('config')
    
    # Ensure SQLALCHEMY_DATABASE_URI is set, fallback to sqlite for now
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Import routes after initializing the app to avoid circular imports
        from .routes import public_bp, admin_bp, host_bp, dev_bp, player_bp
        
        # Register WebSocket event handlers
        from . import websocket_events  # noqa: F401

        # Register blueprints
        app.register_blueprint(public_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(host_bp)
        app.register_blueprint(dev_bp)
        app.register_blueprint(player_bp)

    return app
