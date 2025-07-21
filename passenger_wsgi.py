import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

# Create the Flask application instance
app, socketio = create_app()

# Passenger WSGI expects an 'application' object
application = socketio

if __name__ == "__main__":
    socketio.run(app)