import os
from flask import Flask, jsonify, request
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from flask_cors import CORS
import re
from database_utils import LOCATIONS

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:anbu2006@localhost:5432/argo_db")
app = Flask(__name__)
CORS(app) # Enable Cross-Origin Resource Sharing

# --- DATABASE CONNECTION ---
try:
    engine = create_engine(DATABASE_URL)
    print("API Server: Successfully connected to the database.")
except Exception as e:
    print(f"API Server: Error connecting to database: {e}")
    engine = None

# --- API ENDPOINTS ---
@app.route('/api/status')
def get_status():
    if not engine: return jsonify({"status": "error", "database": "disconnected"}), 500
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return jsonify({"status": "online", "database": "connected"})
    except Exception as e:
        return jsonify({"status": "online", "database": "error", "message": str(e)}), 500

@app.route('/api/locations')
def get_locations():
    location_data = []
    for name, clause in LOCATIONS.items():
        try:
            lat_match = re.search(r'latitude" BETWEEN (-?\d+\.?\d*) AND (-?\d+\.?\d*)', clause)
            lon_match = re.search(r'longitude" BETWEEN (-?\d+\.?\d*) AND (-?\d+\.?\d*)', clause)
            if lat_match and lon_match:
                center_lat = (float(lat_match.group(1)) + float(lat_match.group(2))) / 2
                center_lon = (float(lon_match.group(1)) + float(lon_match.group(2))) / 2
                location_data.append({"name": name.lower(), "lat": center_lat, "lon": center_lon})
        except Exception:
            continue
    return jsonify(location_data)

@app.route('/api/available_periods')
def get_available_periods():
    """Return distinct available years and months present in the dataset.
    Output example: {"periods": {"2023": [1,2,3], "2024": [5,6]}}"""
    if not engine:
        return jsonify({"error": "Database connection not available"}), 500
    query = text("""
        SELECT DISTINCT EXTRACT(YEAR FROM "timestamp")::INT AS yr,
                        EXTRACT(MONTH FROM "timestamp")::INT AS mo
        FROM argo_data
        ORDER BY yr DESC, mo DESC;
    """)
    try:
        with engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        periods = {}
        for r in rows:
            periods.setdefault(str(r['yr']), []).append(int(r['mo']))
        # ensure months sorted ascending for each year
        for y in periods:
            periods[y] = sorted(set(periods[y]))
        return jsonify({"periods": periods})
    except Exception as e:
        return jsonify({"error": f"Failed to fetch periods: {e}"}), 500


@app.route('/api/nearest_floats', methods=['GET'])
def get_nearest_floats():
    if not engine: return jsonify({"error": "Database connection not available"}), 500
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    limit = request.args.get('limit', default=4, type=int)
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if lat is None or lon is None:
        return jsonify({"error": "Missing 'lat' or 'lon' query parameters"}), 400

    # Build conditional month/year filter
    time_filter = ""
    params = {"lat": lat, "lon": lon, "limit": limit}
    if year and month:
        time_filter = "WHERE EXTRACT(YEAR FROM \"timestamp\") = :year AND EXTRACT(MONTH FROM \"timestamp\") = :month"
        params.update({"year": year, "month": month})

    query = text(f"""
        WITH base AS (
            SELECT * FROM argo_data {time_filter}
        ), ranked_floats AS (
            SELECT "float_id", "latitude", "longitude", "timestamp",
                   (6371 * acos(cos(radians(:lat)) * cos(radians("latitude")) * cos(radians("longitude") - radians(:lon)) + sin(radians(:lat)) * sin(radians("latitude")))) AS distance_km,
                   ROW_NUMBER() OVER(PARTITION BY "float_id" ORDER BY "timestamp" DESC) as rn
            FROM base
        )
        SELECT "float_id", "latitude", "longitude", "timestamp", distance_km
        FROM ranked_floats WHERE rn = 1 ORDER BY distance_km LIMIT :limit;
    """)
    try:
        with engine.connect() as connection:
            result = connection.execute(query, params)
            floats = [dict(row) for row in result.mappings()]
            return jsonify(floats)
    except Exception as e:
        return jsonify({"error": f"Database query failed: {e}"}), 500

@app.route('/api/float_profile/<int:float_id>')
def get_float_profile(float_id):
    if not engine: return jsonify({"error": "Database connection not available"}), 500
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    time_filter = ""
    params = {"fid": float_id}
    if year and month:
        time_filter = "AND EXTRACT(YEAR FROM \"timestamp\") = :year AND EXTRACT(MONTH FROM \"timestamp\") = :month"
        params.update({"year": year, "month": month})
    query = text(f"""
        SELECT "timestamp", "pressure", "temperature", "salinity", "chlorophyll", "dissolved_oxygen"
        FROM argo_data WHERE "float_id" = :fid {time_filter} AND "timestamp" = (
            SELECT MAX("timestamp") FROM argo_data WHERE "float_id" = :fid {time_filter}
        ) ORDER BY "pressure" ASC;
    """)
    try:
        with engine.connect() as connection:
            result = connection.execute(query, params)
            profile_data = [dict(row) for row in result.mappings()]
            if not profile_data: return jsonify({"error": "No data found for this float in selected period"}), 404
            return jsonify(profile_data)
    except Exception as e:
        return jsonify({"error": f"Database query failed: {e}"}), 500

@app.route('/api/float_trajectory/<int:float_id>')
def get_float_trajectory(float_id):
    """Return trajectory path plus start/end timestamps for the selected (optional) month/year.

    Response shape on success:
    {
        "path": [[lat, lon], ...],
        "start_timestamp": "YYYY-MM-DDTHH:MM:SSZ",
        "end_timestamp": "YYYY-MM-DDTHH:MM:SSZ",
        "num_points": N
    }
    """
    if not engine: return jsonify({"error": "Database connection not available"}), 500
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    time_filter = ""
    params = {"fid": float_id}
    if year and month:
        time_filter = "AND EXTRACT(YEAR FROM \"timestamp\") = :year AND EXTRACT(MONTH FROM \"timestamp\") = :month"
        params.update({"year": year, "month": month})
    query = text(f"""
        SELECT "latitude", "longitude", "timestamp" FROM argo_data
        WHERE "float_id" = :fid {time_filter} ORDER BY "timestamp" ASC;
    """)
    try:
        with engine.connect() as connection:
            rows = connection.execute(query, params).mappings().all()
            if not rows:
                return jsonify({"error": "No trajectory data found for this period"}), 404
            path = [[r['latitude'], r['longitude']] for r in rows]
            start_ts = rows[0]['timestamp']
            end_ts = rows[-1]['timestamp']
            return jsonify({
                "path": path,
                "start_timestamp": start_ts.isoformat() if hasattr(start_ts, 'isoformat') else str(start_ts),
                "end_timestamp": end_ts.isoformat() if hasattr(end_ts, 'isoformat') else str(end_ts),
                "num_points": len(rows)
            })
    except Exception as e:
        return jsonify({"error": f"Database query failed: {e}"}), 500

def start_api_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    """Start the Flask API server.

    Exposed as a function so the GUI can launch this in a background process
    without invoking the Flask reloader (which would spawn duplicate processes
    and cause port conflicts on Windows).
    """
    # Disable the auto reloader explicitly to avoid double-start.
    app.run(host=host, port=port, debug=debug, use_reloader=False)

# --- RUN THE SERVER DIRECTLY (stand‑alone use) ---
if __name__ == '__main__':
    # When run standalone we still avoid the reloader; debug toolbars/logging OK.
    start_api_server(debug=True)

