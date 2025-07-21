import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

# Create the Flask application instance
app, socketio = create_app()

# For Namecheap hosting, we need to use the app directly
# SocketIO will automatically handle HTTP polling fallback
application = app

# Make socketio accessible for manual integration if needed
app.socketio = socketio

if __name__ == "__main__":
    socketio.run(app)