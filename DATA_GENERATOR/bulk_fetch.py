"""
FloatChart - Bulk Data Fetcher
Fetches large amounts of ARGO data from 2018+ with proper missing value handling.
Designed for cloud databases with better error handling and chunked uploads.

Usage:
    python bulk_fetch.py --setup-neon           # Setup Neon database
    python bulk_fetch.py --fetch-all            # Fetch all data from 2018
    python bulk_fetch.py --migrate-from-supabase # Migrate existing data
"""

import os
import sys
import argparse
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from typing import Optional, List
from io import StringIO
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from DATA_GENERATOR.env_utils import load_environment

# ERDDAP Servers - Ifremer is primary (most reliable), NOAA as backup
ERDDAP_SERVERS = {
    "ifremer": "https://erddap.ifremer.fr/erddap/tabledap",
    "noaa": "https://coastwatch.pfeg.noaa.gov/erddap/tabledap",
}
DATASET_ID = "ArgoFloats"
# Ifremer uses different column names
IFREMER_COLUMNS = "platform_number,time,latitude,longitude,temp,psal,pres"

# All ocean regions for comprehensive data
REGIONS = {
    "indian_ocean": (-40, 25, 30, 120),
    "bay_of_bengal": (5, 22, 80, 95),
    "arabian_sea": (5, 25, 50, 75),
    "north_pacific": (0, 60, 100, 180),
    "south_pacific": (-60, 0, 100, 180),
    "north_atlantic": (0, 60, -80, 0),
    "south_atlantic": (-60, 0, -80, 0),
    "mediterranean": (30, 46, -6, 36),
    "south_china_sea": (0, 25, 100, 121),
    "caribbean": (10, 22, -88, -60),
    "arctic": (60, 85, -180, 180),
    "southern_ocean": (-80, -60, -180, 180),
}


def get_db_engine(db_url: str = None):
    """Create database engine compatible with CockroachDB."""
    if db_url:
        return create_engine(db_url, connect_args={"sslmode": "verify-full"})
    
    load_environment()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")
    
    # CockroachDB compatibility - disable version check
    from sqlalchemy.dialects import postgresql
    return create_engine(
        database_url,
        isolation_level="AUTOCOMMIT",  # CockroachDB works best with autocommit
    )


def clean_and_fill_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean data and fill missing values intelligently.
    
    Strategy:
    - latitude/longitude: Required, drop if missing
    - temperature: Forward/backward fill by float_id, then regional mean
    - salinity: Forward/backward fill by float_id, then regional mean  
    - pressure: Forward/backward fill, then 0 (surface)
    - timestamp: Required, drop if missing
    """
    if df.empty:
        return df
    
    print(f"  Cleaning data: {len(df)} records...")
    original_count = len(df)
    
    # Required columns - drop if missing
    df = df.dropna(subset=["latitude", "longitude", "timestamp"])
    
    # Sort by float and time for proper interpolation
    df = df.sort_values(["float_id", "timestamp"])
    
    # Fill temperature - by float first, then global mean
    if "temperature" in df.columns:
        # Forward/backward fill within each float
        df["temperature"] = df.groupby("float_id")["temperature"].transform(
            lambda x: x.fillna(method='ffill').fillna(method='bfill')
        )
        # Fill remaining with regional mean
        temp_mean = df["temperature"].mean()
        if pd.notna(temp_mean):
            df["temperature"] = df["temperature"].fillna(temp_mean)
        else:
            df["temperature"] = df["temperature"].fillna(20.0)  # Default ocean temp
    
    # Fill salinity - same strategy
    if "salinity" in df.columns:
        df["salinity"] = df.groupby("float_id")["salinity"].transform(
            lambda x: x.fillna(method='ffill').fillna(method='bfill')
        )
        sal_mean = df["salinity"].mean()
        if pd.notna(sal_mean):
            df["salinity"] = df["salinity"].fillna(sal_mean)
        else:
            df["salinity"] = df["salinity"].fillna(35.0)  # Default ocean salinity
    
    # Fill pressure - 0 for surface readings
    if "pressure" in df.columns:
        df["pressure"] = df.groupby("float_id")["pressure"].transform(
            lambda x: x.fillna(method='ffill').fillna(method='bfill')
        )
        df["pressure"] = df["pressure"].fillna(0)
    
    # Remove any remaining NaN in critical columns
    df = df.dropna(subset=["temperature", "salinity"])
    
    # Remove extreme outliers
    df = df[(df["temperature"] > -5) & (df["temperature"] < 40)]
    df = df[(df["salinity"] > 0) & (df["salinity"] < 45)]
    
    cleaned_count = len(df)
    print(f"  Cleaned: {original_count} → {cleaned_count} records ({cleaned_count/original_count*100:.1f}% retained)")
    
    return df


def create_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"Accept-Encoding": "gzip"})
    return session


def fetch_chunk(lat_min: float, lat_max: float, lon_min: float, lon_max: float,
                start_date: datetime, end_date: datetime, base_url: str,
                session: Optional[requests.Session] = None, retries: int = 3) -> Optional[pd.DataFrame]:
    """Fetch a single chunk of data with retries."""
    
    start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
    end_str = end_date.strftime("%Y-%m-%dT23:59:59Z")
    
    # Use correct column names for Ifremer
    if "ifremer" in base_url:
        columns = "platform_number,time,latitude,longitude,temp,psal,pres"
    else:
        columns = "float_id,time,latitude,longitude,temp,psal,pres"
    
    url = (
        f"{base_url}/{DATASET_ID}.csv?"
        f"{columns}"
        f"&time>={start_str}&time<={end_str}"
        f"&latitude>={lat_min}&latitude<={lat_max}"
        f"&longitude>={lon_min}&longitude<={lon_max}"
        f"&orderBy(%22time%22)"
    )
    
    for attempt in range(retries):
        try:
            client = session or requests
            response = client.get(url, timeout=180)
            
            if response.status_code == 404:
                return None  # No data for this query
            
            response.raise_for_status()
            
            df = pd.read_csv(StringIO(response.text), skiprows=[1])
            
            if df.empty:
                return None
            
            # Rename columns (handle both Ifremer and NOAA naming)
            df = df.rename(columns={
                "platform_number": "float_id",  # Ifremer
                "float_id": "float_id",         # NOAA
                "time": "timestamp",
                "latitude": "latitude",
                "longitude": "longitude",
                "temp": "temperature",
                "psal": "salinity",
                "pres": "pressure"
            })
            
            # Extract numeric float_id
            df["float_id"] = df["float_id"].astype(str).str.extract(r'(\d+)')
            df["float_id"] = pd.to_numeric(df["float_id"], errors='coerce')
            
            return df
            
        except requests.exceptions.Timeout:
            print(f"    Timeout (attempt {attempt + 1}/{retries})")
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            print(f"    Error (attempt {attempt + 1}/{retries}): {e}")
            time.sleep(5 * (attempt + 1))
    
    return None


def fetch_region_data(region_name: str, bounds: tuple, start_year: int = 2018,
                      end_year: Optional[int] = None, chunk_days: int = 90,
                      base_url: str = ERDDAP_SERVERS["noaa"],
                      sleep_seconds: float = 0.5) -> pd.DataFrame:
    """
    Fetch all data for a region from start_year to now, in monthly chunks.
    """
    lat_min, lat_max, lon_min, lon_max = bounds
    
    print(f"\n🌊 Fetching: {region_name.replace('_', ' ').title()}")
    print(f"   Bounds: ({lat_min}, {lat_max}) x ({lon_min}, {lon_max})")
    
    all_data = []
    
    # Fetch data in chunks to avoid timeouts
    current_date = datetime(start_year, 1, 1)
    if end_year is None:
        end_date = datetime.now()
    else:
        end_date = datetime(end_year, 12, 31)
    session = create_session()
    
    while current_date < end_date:
        chunk_end = min(current_date + timedelta(days=chunk_days), end_date)
        
        print(f"   Fetching: {current_date.strftime('%Y-%m')} to {chunk_end.strftime('%Y-%m')}...", end=" ")
        
        df = fetch_chunk(lat_min, lat_max, lon_min, lon_max, current_date, chunk_end, base_url, session=session)
        
        if df is not None and not df.empty:
            print(f"✓ {len(df)} records")
            all_data.append(df)
        else:
            print("- no data")
        
        current_date = chunk_end + timedelta(days=1)
        time.sleep(sleep_seconds)  # Be nice to the server
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.drop_duplicates(subset=["float_id", "timestamp", "latitude", "longitude"])
        return combined
    
    return pd.DataFrame()


def upload_to_database(df: pd.DataFrame, engine, chunk_size: int = 5000) -> int:
    """Upload data to database in chunks (CockroachDB compatible)."""
    
    if df.empty:
        return 0
    
    # Clean and fill missing values
    df = clean_and_fill_missing(df)
    
    if df.empty:
        return 0
    
    print(f"  Uploading {len(df)} records to database...")
    
    # Use psycopg2 directly for CockroachDB compatibility
    import psycopg2
    from psycopg2.extras import execute_values
    
    load_environment()
    db_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    total_uploaded = 0
    columns = ["float_id", "timestamp", "latitude", "longitude", "temperature", "salinity", "pressure"]
    
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i + chunk_size]
        try:
            # Prepare data tuples
            values = [tuple(row[col] for col in columns) for _, row in chunk.iterrows()]
            
            # Use UPSERT for CockroachDB (simpler than ON CONFLICT)
            insert_sql = """
                UPSERT INTO argo_data (float_id, timestamp, latitude, longitude, temperature, salinity, pressure)
                VALUES %s
            """
            execute_values(cursor, insert_sql, values, page_size=1000)
            conn.commit()
            total_uploaded += len(chunk)
            print(f"    Uploaded {total_uploaded}/{len(df)} records")
        except Exception as e:
            print(f"    Error uploading chunk: {e}")
            conn.rollback()
    
    cursor.close()
    conn.close()
    return total_uploaded


def setup_neon_database():
    """Guide user through Neon database setup."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           🐘 NEON DATABASE SETUP (0.5GB FREE)                    ║
╚══════════════════════════════════════════════════════════════════╝

1. Go to: https://neon.tech
2. Click "Sign Up" (use GitHub for easy signup)
3. Create a new project:
   - Name: "floatchart" 
   - Region: Choose nearest to you (Singapore for India)
4. Copy the connection string from the dashboard

Your connection string will look like:
postgresql://user:password@ep-xxxx.region.aws.neon.tech/neondb

5. Update your .env file:
   DATABASE_URL=postgresql://user:password@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require

6. Update Render environment variable with the same URL

Then run: python bulk_fetch.py --init-db
""")


def setup_cockroachdb():
    """Guide user through CockroachDB Serverless setup - RECOMMENDED for large data."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║     🪳 COCKROACHDB SERVERLESS SETUP (10GB FREE!) - RECOMMENDED   ║
╚══════════════════════════════════════════════════════════════════╝

✅ Best choice for global ARGO data (2020-2026, ~10GB)

1. Go to: https://cockroachlabs.cloud/
2. Click "Sign Up" (use GitHub/Google for easy signup)
3. Create a new cluster:
   - Plan: "Serverless" (FREE)
   - Cloud: AWS or GCP
   - Region: Choose nearest (ap-south-1 for India)
   - Cluster name: "floatchart"
4. Create SQL user:
   - Username: "floatchart_user"
   - Generate password and SAVE IT
5. Download CA certificate (or use sslmode=verify-full)
6. Copy connection string from "Connect" → "Connection parameters"

Your connection string will look like:
postgresql://floatchart_user:PASSWORD@floatchart-xxx.xxx.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full

7. Update your .env file:
   DATABASE_URL=postgresql://floatchart_user:PASSWORD@floatchart-xxx.xxx.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full

Free tier includes:
  • 10 GB storage (vs 0.5GB Neon)
  • 50M request units/month
  • Auto-scaling
  • No cold starts

Then run: python bulk_fetch.py --init-db
""")


def init_database(engine):
    """Initialize database with proper schema (CockroachDB compatible)."""
    print("Creating database table...")
    
    # CockroachDB compatible - use INT8 instead of SERIAL
    statements = [
        """CREATE TABLE IF NOT EXISTS argo_data (
            id INT8 DEFAULT unique_rowid() PRIMARY KEY,
            float_id INT8,
            timestamp TIMESTAMP,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            temperature DOUBLE PRECISION,
            salinity DOUBLE PRECISION,
            pressure DOUBLE PRECISION,
            UNIQUE(float_id, timestamp, latitude, longitude)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_argo_timestamp ON argo_data(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_argo_float ON argo_data(float_id)",
        "CREATE INDEX IF NOT EXISTS idx_argo_location ON argo_data(latitude, longitude)",
    ]
    
    try:
        # Use psycopg2 directly to bypass SQLAlchemy version detection issue
        import psycopg2
        load_environment()
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        for stmt in statements:
            try:
                cursor.execute(stmt)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"  Warning: {e}")
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False


def get_stats(engine):
    """Get database statistics (CockroachDB compatible)."""
    try:
        import psycopg2
        load_environment()
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT float_id) as floats,
                MIN(timestamp) as min_date,
                MAX(timestamp) as max_date,
                ROUND(AVG(temperature)::numeric, 2) as avg_temp,
                ROUND(AVG(salinity)::numeric, 2) as avg_sal
            FROM argo_data
        """)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return {
            "total_records": result[0],
            "unique_floats": result[1],
            "date_range": f"{result[2]} to {result[3]}",
            "avg_temperature": result[4],
            "avg_salinity": result[5]
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Bulk ARGO data fetcher for FloatChart")
    
    parser.add_argument("--setup-neon", action="store_true", help="Show Neon setup guide (0.5GB free)")
    parser.add_argument("--setup-cockroach", action="store_true", help="Show CockroachDB setup guide (10GB free) - RECOMMENDED")
    parser.add_argument("--init-db", action="store_true", help="Initialize database schema")
    parser.add_argument("--fetch-all", action="store_true", help="Fetch all data from 2020")
    parser.add_argument("--fetch-region", type=str, help="Fetch specific region")
    parser.add_argument("--start-year", type=int, default=2020, help="Start year (default: 2020)")
    parser.add_argument("--end-year", type=int, default=None, help="End year (default: current year)")
    parser.add_argument("--chunk-days", type=int, default=90, help="Days per request chunk (default: 90)")
    parser.add_argument("--server", type=str, default="noaa", choices=["noaa", "ifremer"], help="ERDDAP server")
    parser.add_argument("--parallel", type=int, default=3, help="Parallel regions to fetch (default: 3)")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--test-connection", action="store_true", help="Test database connection")
    
    args = parser.parse_args()
    
    if args.setup_neon:
        setup_neon_database()
        return 0
    
    if args.setup_cockroach:
        setup_cockroachdb()
        return 0
    
    # Connect to database
    try:
        engine = get_db_engine()
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nRun: python bulk_fetch.py --setup-neon")
        return 1
    
    if args.test_connection:
        print("Testing connection...")
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                print("✅ Connection successful!")
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
        return 0
    
    if args.stats:
        stats = get_stats(engine)
        print("\n📊 Database Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        return 0
    
    if args.init_db:
        init_database(engine)
        return 0
    
    if args.fetch_all:
        print(f"\n🚀 Starting bulk fetch from {args.start_year}...")
        print(f"   This will take a while. Fetching from {len(REGIONS)} regions.\n")
        
        # Initialize database first
        init_database(engine)
        
        total_records = 0
        
        base_url = ERDDAP_SERVERS[args.server]
        with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as executor:
            futures = {
                executor.submit(
                    fetch_region_data,
                    region_name,
                    bounds,
                    args.start_year,
                    args.end_year,
                    args.chunk_days,
                    base_url,
                    0.5 if args.server == "noaa" else 0.8,
                ): region_name
                for region_name, bounds in REGIONS.items()
            }
            for future in as_completed(futures):
                region_name = futures[future]
                try:
                    df = future.result()
                except Exception as e:
                    print(f"   ❌ {region_name}: fetch failed ({e})")
                    continue

                if not df.empty:
                    uploaded = upload_to_database(df, engine)
                    total_records += uploaded
                    print(f"   ✅ {region_name}: {uploaded} records uploaded")

                # Show progress
                stats = get_stats(engine)
                print(f"   📊 Total in database: {stats.get('total_records', 0):,} records")
        
        print(f"\n🎉 Complete! Total records uploaded: {total_records:,}")
        
        final_stats = get_stats(engine)
        print("\n📊 Final Statistics:")
        for key, value in final_stats.items():
            print(f"   {key}: {value}")
        
        return 0
    
    if args.fetch_region:
        region_key = args.fetch_region.lower().replace(" ", "_")
        if region_key not in REGIONS:
            print(f"❌ Unknown region: {args.fetch_region}")
            print(f"   Available: {', '.join(REGIONS.keys())}")
            return 1
        
        init_database(engine)
        base_url = ERDDAP_SERVERS[args.server]
        df = fetch_region_data(region_key, REGIONS[region_key], args.start_year, args.end_year, args.chunk_days, base_url)
        
        if not df.empty:
            uploaded = upload_to_database(df, engine)
            print(f"\n✅ Uploaded {uploaded} records from {region_key}")
        
        return 0
    
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
