from app import create_app
from config import OSU_CALLBACK_URL

app = create_app()

if __name__ == '__main__':
    # Extract port from the callback URL for development consistency
    try:
        port = int(OSU_CALLBACK_URL.split(':')[-1].split('/')[0])
    except (ValueError, IndexError):
        port = 5000 # Default port if parsing fails
    app.run(debug=True, port=port)
