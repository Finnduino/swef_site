import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

# Create the Flask application instance without SocketIO for Namecheap compatibility
app = create_app()

# Namecheap hosting - no SocketIO support
application = app

if __name__ == "__main__":
    app.run(debug=True)