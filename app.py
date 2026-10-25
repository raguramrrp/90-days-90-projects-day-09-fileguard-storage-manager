"""
FileGuard — Intelligent Duplicate File Detection & Storage Manager.
Application Entry Point.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fileguard.database import Database
from fileguard.ui.main_window import MainWindow


def main():
    if "--version" in sys.argv:
        from fileguard import __version__
        print(f"FileGuard v{__version__}")
        sys.exit(0)

    # Initialize database
    db = Database()

    # Launch desktop application
    app = MainWindow(db=db)
    app.mainloop()


if __name__ == "__main__":
    main()
