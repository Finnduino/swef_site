from flask import Flask
from config import SECRET_KEY
from ossapi import Ossapi
from config import OSU_CLIENT_ID, OSU_CLIENT_SECRET
# Create an instance of the osu! API client to be used in other parts of the app
api = Ossapi(OSU_CLIENT_ID, OSU_CLIENT_SECRET)

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object('config')

    with app.app_context():
        # Import routes after initializing the app to avoid circular imports
        
        from . import routes

        # Register blueprints
        app.register_blueprint(routes.public_bp)
        app.register_blueprint(routes.admin_bp)

    return app
