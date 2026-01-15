"""
Generate ARGO float data for global ocean coverage and upload to Supabase.
Covers: Pacific Ocean, Atlantic Ocean, Southern Ocean, Mediterranean, etc.
"""

import requests
import random
import json
from datetime import datetime, timedelta

# Supabase REST API config
SUPABASE_URL = "https://khrqbfssaanpcxdnnplc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtocnFiZnNzYWFucGN4ZG5ucGxjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg0NTQxMTAsImV4cCI6MjA4NDAzMDExMH0.1M6nzLx67qy6Ash92k3jHxpuJ8QvyCyKt2m5w_L_M7s"

# New ocean regions to add (not already in database)
NEW_REGIONS = {
    # Pacific Ocean
    "pacific_central": {"lat": (-10, 10), "lon": (160, 180), "floats": 15, "base_temp": 28},
    "pacific_north": {"lat": (20, 45), "lon": (140, 180), "floats": 15, "base_temp": 18},
    "pacific_south": {"lat": (-45, -20), "lon": (150, 180), "floats": 12, "base_temp": 14},
    "south_china_sea": {"lat": (5, 22), "lon": (105, 120), "floats": 10, "base_temp": 27},
    "philippine_sea": {"lat": (10, 30), "lon": (125, 140), "floats": 10, "base_temp": 26},
    "coral_sea": {"lat": (-22, -12), "lon": (148, 162), "floats": 8, "base_temp": 25},
    "tasman_sea": {"lat": (-42, -32), "lon": (152, 172), "floats": 8, "base_temp": 16},
    
    # Atlantic Ocean
    "atlantic_north": {"lat": (30, 55), "lon": (-60, -10), "floats": 15, "base_temp": 15},
    "atlantic_central": {"lat": (-10, 20), "lon": (-40, 0), "floats": 12, "base_temp": 26},
    "atlantic_south": {"lat": (-45, -20), "lon": (-50, 10), "floats": 10, "base_temp": 14},
    "caribbean": {"lat": (12, 22), "lon": (-85, -62), "floats": 10, "base_temp": 28},
    "gulf_of_mexico": {"lat": (20, 28), "lon": (-96, -82), "floats": 8, "base_temp": 26},
    "mediterranean": {"lat": (32, 44), "lon": (-4, 34), "floats": 12, "base_temp": 20},
    "north_sea": {"lat": (52, 60), "lon": (-3, 8), "floats": 6, "base_temp": 10},
    
    # Southern Ocean & Others
    "southern_ocean": {"lat": (-62, -45), "lon": (-60, 60), "floats": 10, "base_temp": 2},
    "red_sea": {"lat": (14, 28), "lon": (34, 42), "floats": 6, "base_temp": 28},
    "persian_gulf": {"lat": (25, 30), "lon": (49, 55), "floats": 5, "base_temp": 30},
    "mozambique": {"lat": (-23, -12), "lon": (36, 44), "floats": 6, "base_temp": 25},
    
    # Near major cities/ports
    "tokyo_waters": {"lat": (34, 36), "lon": (139, 142), "floats": 5, "base_temp": 18},
    "sydney_coast": {"lat": (-35, -33), "lon": (150, 153), "floats": 5, "base_temp": 20},
    "cape_town": {"lat": (-35, -33), "lon": (16, 20), "floats": 5, "base_temp": 16},
    "miami_atlantic": {"lat": (24, 27), "lon": (-81, -78), "floats": 5, "base_temp": 26},
    "singapore_strait": {"lat": (0, 3), "lon": (103, 106), "floats": 5, "base_temp": 29},
}

# Float ID ranges for each region
FLOAT_ID_START = 2950000

def get_current_count():
    """Get current record count from Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Prefer": "count=exact"
    }
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/argo_data?select=count",
        headers=headers
    )
    if response.status_code == 200:
        count = response.headers.get('content-range', '*/0').split('/')[-1]
        return int(count)
    return 0

def generate_float_data(float_id, region_name, region_config, start_date, num_profiles=25):
    """Generate realistic ARGO float profiles"""
    records = []
    lat_min, lat_max = region_config["lat"]
    lon_min, lon_max = region_config["lon"]
    base_temp = region_config["base_temp"]
    
    # Start position
    lat = random.uniform(lat_min, lat_max)
    lon = random.uniform(lon_min, lon_max)
    
    # Standard pressure levels for ARGO floats
    pressure_levels = [5, 10, 20, 30, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000]
    
    current_time = start_date
    
    for profile_num in range(num_profiles):
        # Float drift (realistic movement)
        lat += random.uniform(-0.3, 0.3)
        lon += random.uniform(-0.3, 0.3)
        
        # Keep within region bounds
        lat = max(lat_min, min(lat_max, lat))
        lon = max(lon_min, min(lon_max, lon))
        
        # Time advances 5-12 days per profile (ARGO cycle)
        current_time += timedelta(days=random.randint(5, 12))
        
        # Generate profile at each pressure level
        for pressure in pressure_levels:
            # Temperature decreases with depth
            if pressure < 100:
                temp = base_temp + random.uniform(-1, 1)
            elif pressure < 500:
                temp = base_temp - (pressure / 50) + random.uniform(-0.5, 0.5)
            else:
                temp = max(2, 10 - (pressure / 200) + random.uniform(-0.3, 0.3))
            
            # Salinity varies by depth and region
            if pressure < 100:
                salinity = 34.5 + random.uniform(-0.3, 0.3)
            else:
                salinity = 34.8 + random.uniform(-0.2, 0.2)
            
            # Dissolved oxygen decreases with depth
            if pressure < 200:
                oxygen = 220 + random.uniform(-20, 20)
            else:
                oxygen = max(50, 200 - (pressure / 10) + random.uniform(-10, 10))
            
            record = {
                "float_id": float_id,
                "timestamp": current_time.isoformat(),
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "pressure": pressure,
                "temperature": round(temp, 2),
                "salinity": round(salinity, 3),
                "dissolved_oxygen": round(oxygen, 1)
            }
            records.append(record)
    
    return records

def upload_batch(records, batch_num, total_batches):
    """Upload a batch of records to Supabase"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/argo_data",
        headers=headers,
        json=records
    )
    
    if response.status_code in [200, 201]:
        print(f"  Batch {batch_num}/{total_batches}: Uploaded {len(records)} records ✓")
        return True
    else:
        print(f"  Batch {batch_num}/{total_batches}: FAILED - {response.status_code}: {response.text[:100]}")
        return False

def main():
    print("=" * 60)
    print("ARGO Float Global Data Expansion")
    print("=" * 60)
    
    # Check current count
    initial_count = get_current_count()
    print(f"\nCurrent records in Supabase: {initial_count:,}")
    
    # Date range: Sept 2025 - Jan 2026
    start_date = datetime(2025, 9, 1)
    
    all_records = []
    float_id = FLOAT_ID_START
    
    print(f"\nGenerating data for {len(NEW_REGIONS)} new ocean regions...")
    
    for region_name, config in NEW_REGIONS.items():
        num_floats = config["floats"]
        region_records = []
        
        for i in range(num_floats):
            float_records = generate_float_data(
                float_id=float_id,
                region_name=region_name,
                region_config=config,
                start_date=start_date + timedelta(days=random.randint(0, 30)),
                num_profiles=random.randint(15, 30)
            )
            region_records.extend(float_records)
            float_id += 1
        
        all_records.extend(region_records)
        print(f"  {region_name}: {len(region_records):,} records ({num_floats} floats)")
    
    print(f"\nTotal new records generated: {len(all_records):,}")
    
    # Upload in batches
    batch_size = 500
    batches = [all_records[i:i+batch_size] for i in range(0, len(all_records), batch_size)]
    
    print(f"\nUploading {len(batches)} batches to Supabase...")
    
    success_count = 0
    for i, batch in enumerate(batches, 1):
        if upload_batch(batch, i, len(batches)):
            success_count += len(batch)
    
    # Final count
    final_count = get_current_count()
    print(f"\n" + "=" * 60)
    print(f"Upload complete!")
    print(f"  Before: {initial_count:,} records")
    print(f"  Added:  {success_count:,} records")
    print(f"  After:  {final_count:,} records")
    print("=" * 60)

if __name__ == "__main__":
    main()
