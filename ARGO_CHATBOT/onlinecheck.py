import os
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, exc

# --- CONFIGURATION ---
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def check_postgres_connection():
    """Checks the connection to the PostgreSQL database and the existence of the argo_data table."""
    print("\n--- Checking PostgreSQL Database ---")
    if not DB_URL:
        print("❌ DATABASE_URL not found in your .env file.")
        return

    try:
        engine = create_engine(DB_URL)
        with engine.connect() as connection:
            # Check 1: Can we connect? The line above handles this.
            print("✅ Connection to PostgreSQL server successful.")

            # Check 2: Does the argo_data table exist and have data?
            query = text("SELECT COUNT(*) FROM argo_data;")
            result = connection.execute(query).scalar()
            print(f"✅ Found table 'argo_data' with {result} rows.")

    except exc.OperationalError as e:
        print(f"❌ Could not connect to PostgreSQL server. Is it running?")
        print(f"   Error details: {e}")
    except exc.ProgrammingError as e:
        print(f"❌ Connected to the database, but could not find the 'argo_data' table.")
        print(f"   Have you run the database_loader.py script?")
        print(f"   Error details: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred while checking the database: {e}")

def check_groq_api_status():
    """Checks the Groq API status and validates the API key."""
    print("\n--- Checking Groq API ---")
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY not found in your .env file.")
        return

    try:
        # We will ping the models endpoint, as it's a simple GET request.
        response = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=10 # Set a timeout of 10 seconds
        )
        response.raise_for_status()  # This will raise an HTTPError for bad responses (4xx or 5xx)
        
        print("✅ Groq API is online and your API key is valid.")
        
        # Optionally, list the available models to stay up-to-date
        models = [m.get('id') for m in response.json().get('data', [])]
        print(f"   Available models include: {models[:5]}...") # Print first 5 models

    except requests.exceptions.HTTPError as e:
         print(f"❌ Received an error from the Groq API. Your API key might be invalid or there could be an issue with your account.")
         print(f"   Status Code: {e.response.status_code}, Response: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not connect to the Groq API. There might be a network issue or the service may be down.")
        print(f"   Error details: {e}")

if __name__ == "__main__":
    print("Running service status checks...")
    check_postgres_connection()
    check_groq_api_status()
    print("\n--- Checks complete ---")
