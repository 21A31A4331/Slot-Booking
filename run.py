import os
from app import create_app
from config import Config

app = create_app(Config)

# Auto-initialize database tables and demo seed data on server startup
with app.app_context():
    try:
        from init_db import seed_database
        seed_database(app)
    except Exception as e:
        print(f"[STARTUP] Notice during DB auto-initialization: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
    print(f"\n * Starting Slot Booking Web Application on http://127.0.0.1:{port}")
    print(" * Press CTRL+C to quit\n")
    app.run(host='127.0.0.1', port=port, debug=debug)
