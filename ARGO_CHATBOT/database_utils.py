import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# This dictionary holds your predefined locations for the search bar
LOCATIONS = {
    "arabian sea": "AND \"latitude\" BETWEEN 5 AND 25 AND \"longitude\" BETWEEN 50 AND 75",
    "bay of bengal": "AND \"latitude\" BETWEEN 5 AND 22 AND \"longitude\" BETWEEN 80 AND 95",
    "equator": "AND \"latitude\" BETWEEN -2 AND 2",
    "chennai": "AND \"latitude\" BETWEEN 12.5 AND 13.5 AND \"longitude\" BETWEEN 80 AND 80.5",
    "mumbai": "AND \"latitude\" BETWEEN 18.5 AND 19.5 AND \"longitude\" BETWEEN 72.5 AND 73",
    "sri lanka": "AND \"latitude\" BETWEEN 5 AND 10 AND \"longitude\" BETWEEN 79 AND 82"
}

def get_db_engine():
    """Creates and returns a SQLAlchemy database engine."""
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found in .env file.")
        return None
    try:
        engine = create_engine(db_url)
        with engine.connect() as connection:
            print("Database connection successful for map utilities.")
        return engine
    except Exception as e:
        print(f"Error creating database engine: {e}")
        return None

engine = get_db_engine()

# --- Other database functions can be added here if needed ---