"""Quick helper to print current argo_data max(timestamp) and row count.

Run from PowerShell in the DATA_GENERATOR folder after activating your venv:

cd "e:\\VS code\\FloatChart\\DATA_GENERATOR"
.venv\Scripts\Activate
python check_db_max.py
"""
from __future__ import annotations

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def main() -> None:
    # Try to load local .env first, then parent ARGO_CHATBOT .env as fallback
    env_paths = [".env", os.path.join("..", "ARGO_CHATBOT", ".env")]
    for p in env_paths:
        if os.path.exists(p):
            load_dotenv(p)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not found in .env files. Please set it and try again.")
        return

    engine = create_engine(database_url)
    with engine.connect() as conn:
        try:
            r = conn.execute(text('SELECT COUNT(*) AS cnt, MIN("timestamp") AS min_ts, MAX("timestamp") AS max_ts FROM argo_data')).fetchone()
            if r is None:
                print("No results returned; is the 'argo_data' table present?")
                return
            cnt, min_ts, max_ts = r
            print(f"argo_data rows: {cnt}")
            print(f"min(timestamp): {min_ts}")
            print(f"max(timestamp): {max_ts}")
            # Show latest 5 rows for quick inspection
            sample = conn.execute(text('SELECT "float_id","timestamp","latitude","longitude" FROM argo_data ORDER BY "timestamp" DESC LIMIT 5')).fetchall()
            print("\nLatest 5 rows:")
            for row in sample:
                print(row)
        except Exception as e:
            print(f"Error querying database: {e}")


if __name__ == "__main__":
    main()
