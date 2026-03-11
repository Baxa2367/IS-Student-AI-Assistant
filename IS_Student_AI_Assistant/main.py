import sys
from dotenv import load_dotenv

from config import get_settings
from db.database import init_db
from db.repository import Repository
from ui.app_gui import AppGUI


def main() -> None:
    """Entry point: loads env, initializes DB, runs the GUI."""
    load_dotenv()
    settings = get_settings()

    # Initialize local application DB (projects/artifacts/runs)
    session_factory = init_db(settings.APP_DB_PATH)
    repo = Repository(session_factory=session_factory)

    app = AppGUI(settings=settings, repo=repo)
    app.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)