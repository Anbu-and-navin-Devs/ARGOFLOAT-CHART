"""
FloatChat API Server - Web Application Backend
Serves the web interface and provides REST API endpoints for ocean data queries.
"""

import os
from flask import Flask, jsonify, request, send_from_directory
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from flask_cors import CORS
import re
from database_utils import LOCATIONS

# Import the brain module for intelligent queries
try:
    from brain import get_intelligent_answer
except ImportError:
    get_intelligent_answer = None

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required!")

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)  # Enable Cross-Origin Resource Sharing

# --- DATABASE CONNECTION ---
_engine = None

def get_db_engine():
    """Get or create database engine with lazy initialization and reconnection."""
    global _engine
    
    # If we have an engine, test if it's still working
    if _engine is not None:
        try:
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return _engine
        except Exception as e:
            print(f"Database connection lost, reconnecting... ({e})")
            _engine = None
    
    # Create new engine
    try:
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=3,
            pool_recycle=280,
            pool_timeout=20,
            connect_args={
                "connect_timeout": 30,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5
            }
        )
        # Test the connection
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connected successfully.")
        return _engine
    except Exception as e:
        print(f"Database connection error: {e}")
        _engine = None
        return None

# Legacy compatibility
engine = None  # Will be lazy-loaded

# =============================================
# STATIC FILE ROUTES - Serve Web Application
# =============================================

@app.route('/')
def serve_index():
    """Serve the main web application."""
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files (CSS, JS, images)."""
    return send_from_directory(STATIC_DIR, path)

@app.route('/static/css/<path:path>')
def serve_css(path):
    """Serve CSS files."""
    return send_from_directory(os.path.join(STATIC_DIR, 'css'), path)

@app.route('/static/js/<path:path>')
def serve_js(path):
    """Serve JavaScript files."""
    return send_from_directory(os.path.join(STATIC_DIR, 'js'), path)

# =============================================
# API ENDPOINTS
# =============================================

@app.route('/api/status')
def get_status():
    """Check API and database connection status."""
    db = get_db_engine()
    if not db:
        return jsonify({
            "status": "error", 
            "database": "disconnected",
            "hint": "Check DATABASE_URL environment variable"
        }), 500
    try:
        with db.connect() as connection:
            result = connection.execute(text("""
                SELECT COUNT(*), 
                       COUNT(DISTINCT float_id),
                       MIN(timestamp), 
                       MAX(timestamp) 
                FROM argo_data
            """))
            row = result.fetchone()
            count, floats, min_date, max_date = row
        
        # Format dates
        min_str = min_date.strftime("%Y-%m-%d") if min_date else None
        max_str = max_date.strftime("%Y-%m-%d") if max_date else None
        
        return jsonify({
            "status": "online", 
            "database": "connected",
            "records": count,
            "unique_floats": floats,
            "data_range": {
                "start": min_str,
                "end": max_str
            }
        })
    except Exception as e:
        return jsonify({
            "status": "online", 
            "database": "error", 
            "message": str(e)
        }), 500


@app.route('/api/query')
def handle_query():
    """
    Main query endpoint - processes natural language questions about ocean data.
    Uses the brain module for intelligent parsing and SQL generation.
    
    Query Parameters:
        - question: The natural language question (required)
        - year: Optional year filter
        - month: Optional month filter
    
    Returns:
        JSON with query_type, sql_query, summary, and data
    """
    question = request.args.get('question', '').strip()
    
    if not question:
        return jsonify({"error": "Missing 'question' parameter"}), 400
    
    if not get_intelligent_answer:
        return jsonify({"error": "Query processing module not available"}), 500
    
    try:
        # Add year/month context to the question if provided
        year = request.args.get('year')
        month = request.args.get('month')
        
        enhanced_question = question
        if year and month:
            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            month_name = month_names[int(month) - 1] if 1 <= int(month) <= 12 else month
            enhanced_question = f"{question} in {month_name} {year}"
        elif year:
            enhanced_question = f"{question} in {year}"
        
        # Get intelligent answer from brain module
        result = get_intelligent_answer(enhanced_question)
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Query error: {e}")
        return jsonify({
            "query_type": "Error",
            "summary": f"An error occurred while processing your query: {str(e)}",
            "data": [],
            "sql_query": "N/A"
        }), 500


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
    db = get_db_engine()
    if not db:
        return jsonify({"error": "Database connection not available"}), 500
    query = text("""
        SELECT DISTINCT EXTRACT(YEAR FROM "timestamp")::INT AS yr,
                        EXTRACT(MONTH FROM "timestamp")::INT AS mo
        FROM argo_data
        ORDER BY yr DESC, mo DESC;
    """)
    try:
        with db.connect() as connection:
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
    db = get_db_engine()
    if not db: return jsonify({"error": "Database connection not available"}), 500
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
        with db.connect() as connection:
            result = connection.execute(query, params)
            floats = [dict(row) for row in result.mappings()]
            return jsonify(floats)
    except Exception as e:
        return jsonify({"error": f"Database query failed: {e}"}), 500

@app.route('/api/float_profile/<int:float_id>')
def get_float_profile(float_id):
    db = get_db_engine()
    if not db: return jsonify({"error": "Database connection not available"}), 500
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
        with db.connect() as connection:
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
    db = get_db_engine()
    if not db: return jsonify({"error": "Database connection not available"}), 500
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
        with db.connect() as connection:
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


@app.route('/api/statistics')
def get_statistics():
    """Get overall statistics about the dataset."""
    db = get_db_engine()
    if not db:
        return jsonify({"error": "Database connection not available"}), 500
    
    query = text("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT "float_id") as unique_floats,
            MIN("timestamp") as earliest_record,
            MAX("timestamp") as latest_record,
            AVG("temperature") as avg_temperature,
            AVG("salinity") as avg_salinity
        FROM argo_data;
    """)
    
    try:
        with db.connect() as connection:
            result = connection.execute(query).mappings().first()
            stats = dict(result)
            # Format timestamps
            for key in ['earliest_record', 'latest_record']:
                if stats[key] and hasattr(stats[key], 'isoformat'):
                    stats[key] = stats[key].isoformat()
            return jsonify(stats)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch statistics: {e}"}), 500


# =============================================
# SERVER STARTUP
# =============================================

def start_api_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    """
    Start the Flask API server.
    
    Exposed as a function so it can be launched programmatically.
    The debug mode includes auto-reload which is useful for development.
    """
    print(f"\n{'='*60}")
    print(f"  FloatChat - Ocean Intelligence Web Application")
    print(f"{'='*60}")
    print(f"  Server starting at: http://{host}:{port}")
    print(f"  Open this URL in your browser to use the application")
    print(f"{'='*60}\n")
    
    # Disable the auto reloader explicitly to avoid double-start issues
    app.run(host=host, port=port, debug=debug, use_reloader=False)


# --- RUN THE SERVER ---
if __name__ == '__main__':
    # Use PORT from environment (for deployment) or default to 5000
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    start_api_server(host="0.0.0.0", port=port, debug=debug)

