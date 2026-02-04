"""
Run script for the AI-Digest Web GUI.
Starts the Quart web server with proper configuration.
Can be run from project root or src directory.
"""
import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Determine project root and src path
# This script is at: <project_root>/src/gui/run_gui.py
script_path = Path(__file__).resolve()
src_path = script_path.parent.parent  # src/
project_root = src_path.parent  # project root

# Add src to path for imports
sys.path.insert(0, str(src_path))

# Change to project root directory so relative paths work consistently
os.chdir(project_root)

from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(project_root / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_path() -> str:
    """Get database path, ensuring it's relative to project root."""
    db_path = os.environ.get('GUI_DATABASE_PATH', 'data/gui.db')
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"Created directory: {db_dir}")
    return db_path


def create_admin_user():
    """Create an admin user interactively."""
    from gui.models import UserDatabase

    db_path = get_db_path()
    db = UserDatabase(db_path)

    async def create():
        await db.init_tables()

        email = input("Enter admin email: ").strip().lower()
        password = input("Enter admin password: ").strip()

        if len(password) < 8:
            print("Error: Password must be at least 8 characters")
            return

        # Check if user exists
        existing = await db.get_user_by_email(email)
        if existing:
            # Update to admin
            await db.set_admin(email, True)
            await db.verify_user(email)
            print(f"User {email} updated to admin status")
        else:
            # Create new admin user
            user_id = await db.create_user(email, password, is_admin=True)
            if user_id:
                await db.verify_user(email)
                print(f"Admin user created: {email}")
            else:
                print("Failed to create admin user")

    asyncio.run(create())


def init_database():
    """Initialize the GUI database tables."""
    from gui.models import UserDatabase

    db_path = get_db_path()
    db = UserDatabase(db_path)

    async def init():
        await db.init_tables()
        print(f"Database initialized at: {os.path.abspath(db_path)}")

    asyncio.run(init())


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """Run the web server."""
    from gui.app import app

    logger.info(f"Starting AI-Digest Web GUI on http://{host}:{port}")

    # Use hypercorn for production-like async server
    try:
        import hypercorn
        from hypercorn.config import Config
        from hypercorn.asyncio import serve

        config = Config()
        config.bind = [f"{host}:{port}"]
        config.use_reloader = debug
        config.accesslog = '-'
        config.errorlog = '-'

        asyncio.run(serve(app, config))
    except ImportError:
        # Fallback to Quart's built-in server
        logger.warning("Hypercorn not installed, using Quart's development server")
        app.run(host=host, port=port, debug=debug)


def main():
    parser = argparse.ArgumentParser(description='AI-Digest Web GUI')
    parser.add_argument('command', nargs='?', default='run',
                        choices=['run', 'init-db', 'create-admin'],
                        help='Command to execute')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')

    args = parser.parse_args()

    logger.info(f"Project root: {project_root}")

    if args.command == 'init-db':
        init_database()
    elif args.command == 'create-admin':
        create_admin_user()
    else:
        run_server(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
