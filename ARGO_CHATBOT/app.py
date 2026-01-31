"""
FloatChart - Chat Application
Flask API server for AI-powered ocean data queries.
This is the main chat interface - for data management, use DATA_GENERATOR/app.py
"""

import os
import json
import time
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory, Response, stream_with_context
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from flask_cors import CORS
import re
from datetime import datetime, timedelta
from pathlib import Path

# Import the brain module for intelligent queries
try:
    from brain import get_intelligent_answer
except ImportError:
    get_intelligent_answer = None

# Predefined locations for search queries
LOCATIONS = {
    "arabian sea": "AND \"latitude\" BETWEEN 5 AND 25 AND \"longitude\" BETWEEN 50 AND 75",
    "bay of bengal": "AND \"latitude\" BETWEEN 5 AND 22 AND \"longitude\" BETWEEN 80 AND 95",
    "equator": "AND \"latitude\" BETWEEN -2 AND 2",
    "chennai": "AND \"latitude\" BETWEEN 12.5 AND 13.5 AND \"longitude\" BETWEEN 80 AND 80.5",
    "mumbai": "AND \"latitude\" BETWEEN 18.5 AND 19.5 AND \"longitude\" BETWEEN 72.5 AND 73",
    "sri lanka": "AND \"latitude\" BETWEEN 5 AND 10 AND \"longitude\" BETWEEN 79 AND 82"
}

# Load .env from multiple possible locations
def load_environment():
    """Load .env from current directory or project root."""
    env_paths = [
        Path(".env"),
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
    ]
    for p in env_paths:
        if p.exists():
            load_dotenv(p, override=False)
            return
    load_dotenv()

load_environment()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("⚠️  WARNING: DATABASE_URL not set - app will run but database features will be unavailable")
    DATABASE_URL = None

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
CORS(app)

# =============================================
# CACHING
# =============================================
_cache = {}
_cache_expiry = {}
CACHE_TTL = 300  # 5 minutes

def cache_response(key, data, ttl=CACHE_TTL):
    """Store data in cache with expiry."""
    _cache[key] = data
    _cache_expiry[key] = time.time() + ttl

def get_cached(key):
    """Get cached data if not expired."""
    if key in _cache:
        if time.time() < _cache_expiry.get(key, 0):
            return _cache[key]
        else:
            del _cache[key]
            del _cache_expiry[key]
    return None

def cached(ttl=CACHE_TTL):
    """Decorator for caching endpoint responses."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = f"{f.__name__}:{request.full_path}"
            cached_data = get_cached(cache_key)
            if cached_data:
                return jsonify(cached_data)
            result = f(*args, **kwargs)
            if isinstance(result, tuple):
                data, status = result
            else:
                data = result
                status = 200
            if status == 200:
                cache_response(cache_key, data.get_json() if hasattr(data, 'get_json') else data, ttl)
            return result
        return decorated_function
    return decorator

# =============================================
# DATABASE CONNECTION
# =============================================
_engine = None

def get_db_engine():
    """Get or create database engine with lazy initialization."""
    global _engine
    
    if not DATABASE_URL:
        return None
    
    # Convert postgresql:// to cockroachdb:// for proper CockroachDB support
    db_url = DATABASE_URL
    if db_url.startswith("postgresql://") and "cockroach" in db_url:
        db_url = db_url.replace("postgresql://", "cockroachdb://", 1)
    
    if _engine is not None:
        try:
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return _engine
        except Exception as e:
            print(f"Database connection lost, reconnecting... ({e})")
            _engine = None
    
    # Prepare connect_args for SSL if using CockroachDB Cloud
    connect_args = {
        "connect_timeout": 30,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
    
    # CockroachDB Cloud requires SSL - use system certificates
    if "cockroach" in db_url.lower():
        # Use 'require' instead of 'verify-full' if no local cert
        if "sslmode=verify-full" in db_url:
            db_url = db_url.replace("sslmode=verify-full", "sslmode=require")
        connect_args["sslmode"] = "require"
    
    try:
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=3,
            pool_recycle=280,
            pool_timeout=20,
            connect_args=connect_args
        )
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connected successfully.")
        return _engine
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        _engine = None
        return None

# =============================================
# STATIC FILE ROUTES
# =============================================

@app.route('/')
def serve_index():
    """Serve the main chat interface."""
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/map')
def serve_map():
    """Serve the interactive map explorer."""
    return send_from_directory(STATIC_DIR, 'map.html')

@app.route('/dashboard')
def serve_dashboard():
    """Serve the analytics dashboard."""
    return send_from_directory(STATIC_DIR, 'dashboard.html')

@app.route('/sw.js')
def serve_sw():
    """Serve service worker."""
    return send_from_directory(STATIC_DIR, 'sw.js')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files."""
    return send_from_directory(STATIC_DIR, path)

@app.route('/static/css/<path:path>')
def serve_css(path):
    """Serve CSS files."""
    response = send_from_directory(os.path.join(STATIC_DIR, 'css'), path)
    response.headers['Content-Type'] = 'text/css; charset=utf-8'
    return response

@app.route('/static/js/<path:path>')
def serve_js(path):
    """Serve JavaScript files."""
    response = send_from_directory(os.path.join(STATIC_DIR, 'js'), path)
    response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    return response

# =============================================
# LOCAL MODE DETECTION
# =============================================

def is_local_mode():
    """Check if running in local mode (not cloud deployment)."""
    cloud_indicators = [
        "RENDER", "RAILWAY_ENVIRONMENT", "HEROKU_APP_ID",
        "VERCEL", "FLY_APP_NAME", "K_SERVICE", "DYNO"
    ]
    for indicator in cloud_indicators:
        if os.getenv(indicator):
            return False
    
    if os.getenv("LOCAL_MODE", "").lower() == "true":
        return True
    
    # Default to local if no cloud indicators found
    return True

# =============================================
# API ENDPOINTS
# =============================================

@app.route('/api/local-mode')
def check_local_mode():
    """Check if running in local mode (data manager available)."""
    return jsonify({
        "local_mode": is_local_mode(),
        "data_manager_url": "http://localhost:5001" if is_local_mode() else None
    })

@app.route('/api/health')
def health_check():
    """Health check endpoint with diagnostic info."""
    db_status = "disconnected"
    db_error = None
    table_exists = False
    record_count = 0
    engine = get_db_engine()
    
    if engine:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
            
            # Check if argo_data table exists and has data
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_name = 'argo_data'
                        )
                    """)).fetchone()
                    table_exists = result[0] if result else False
                    
                    if table_exists:
                        count_result = conn.execute(text("SELECT COUNT(*) FROM argo_data LIMIT 1")).fetchone()
                        record_count = count_result[0] if count_result else 0
            except Exception as e:
                db_error = f"Table check error: {e}"
        except Exception as e:
            db_error = str(e)
    
    # Check environment variables (don't expose secrets)
    env_check = {
        "DATABASE_URL_set": bool(os.getenv("DATABASE_URL")),
        "GROQ_API_KEY_set": bool(os.getenv("GROQ_API_KEY")),
        "DATABASE_URL_prefix": os.getenv("DATABASE_URL", "")[:30] + "..." if os.getenv("DATABASE_URL") else None
    }
    
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "database_error": db_error,
        "table_exists": table_exists,
        "record_count": record_count,
        "env_check": env_check,
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/test-ai')
def test_ai():
    """Test AI connection."""
    try:
        from brain import get_llm
        llm = get_llm()
        result = llm.invoke("Say hello in one word")
        return jsonify({"status": "ok", "response": result.content[:100]})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/status')
def get_status():
    """Get application status - fast version."""
    engine = get_db_engine()
    
    if not engine:
        return jsonify({
            "status": "offline",
            "database": "disconnected",
            "database_connected": False,
            "total_records": 0
        })
    
    try:
        with engine.connect() as conn:
            # Just verify connection - don't count records (too slow on free tier)
            conn.execute(text("SELECT 1"))
            
            return jsonify({
                "status": "online",
                "database": "connected",
                "database_connected": True,
                "total_records": "available"
            })
    except Exception as e:
        print(f"Status check error: {e}")
        return jsonify({
            "status": "offline",
            "database": "disconnected",
            "database_connected": False,
            "total_records": 0,
            "error": str(e)
        })

@app.route('/api/stats')
@cached(ttl=60)
def get_stats():
    """Get database statistics for dashboard."""
    engine = get_db_engine()
    
    if not engine:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT float_id) as unique_floats,
                    MIN(timestamp) as min_date,
                    MAX(timestamp) as max_date,
                    ROUND(AVG(temperature)::numeric, 2) as avg_temp,
                    ROUND(AVG(salinity)::numeric, 2) as avg_salinity
                FROM argo_data
            """))
            row = result.fetchone()
            
            return jsonify({
                "total_records": row[0] or 0,
                "unique_floats": row[1] or 0,
                "min_date": row[2].isoformat() if row[2] else None,
                "max_date": row[3].isoformat() if row[3] else None,
                "avg_temperature": float(row[4]) if row[4] else None,
                "avg_salinity": float(row[5]) if row[5] else None
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/query', methods=['POST'])
def handle_query():
    """Handle natural language queries using AI."""
    if not get_intelligent_answer:
        return jsonify({"error": "AI module not available"}), 500
    
    data = request.get_json()
    user_query = data.get('query', '')
    
    if not user_query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        response = get_intelligent_answer(user_query)
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/query/stream', methods=['POST'])
def handle_query_stream():
    """Handle natural language queries with streaming response."""
    if not get_intelligent_answer:
        return jsonify({"error": "AI module not available"}), 500
    
    data = request.get_json()
    user_query = data.get('query', '')
    
    if not user_query:
        return jsonify({"error": "No query provided"}), 400
    
    def generate():
        try:
            response = get_intelligent_answer(user_query)
            
            # Send response in chunks
            if 'answer' in response:
                words = response['answer'].split(' ')
                for i, word in enumerate(words):
                    chunk = {'text': word + ' ', 'done': False}
                    yield f"data: {json.dumps(chunk)}\n\n"
                    time.sleep(0.02)
            
            # Send final chunk with full data
            response['done'] = True
            yield f"data: {json.dumps(response)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/api/data', methods=['GET'])
@cached(ttl=30)
def get_data():
    """Get ARGO float data with filtering."""
    engine = get_db_engine()
    
    if not engine:
        return jsonify({"error": "Database not connected"}), 500
    
    # Parse query parameters
    limit = min(int(request.args.get('limit', 1000)), 10000)
    offset = int(request.args.get('offset', 0))
    float_id = request.args.get('float_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    lat_min = request.args.get('lat_min')
    lat_max = request.args.get('lat_max')
    lon_min = request.args.get('lon_min')
    lon_max = request.args.get('lon_max')
    
    # Build query
    conditions = []
    params = {}
    
    if float_id:
        conditions.append("float_id = :float_id")
        params['float_id'] = int(float_id)
    
    if start_date:
        conditions.append("timestamp >= :start_date")
        params['start_date'] = start_date
    
    if end_date:
        conditions.append("timestamp <= :end_date")
        params['end_date'] = end_date
    
    if lat_min:
        conditions.append("latitude >= :lat_min")
        params['lat_min'] = float(lat_min)
    
    if lat_max:
        conditions.append("latitude <= :lat_max")
        params['lat_max'] = float(lat_max)
    
    if lon_min:
        conditions.append("longitude >= :lon_min")
        params['lon_min'] = float(lon_min)
    
    if lon_max:
        conditions.append("longitude <= :lon_max")
        params['lon_max'] = float(lon_max)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT float_id, timestamp, latitude, longitude, temperature, salinity, pressure
        FROM argo_data
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT :limit OFFSET :offset
    """
    params['limit'] = limit
    params['offset'] = offset
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = result.fetchall()
            
            data = [
                {
                    "float_id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "latitude": float(row[2]) if row[2] else None,
                    "longitude": float(row[3]) if row[3] else None,
                    "temperature": float(row[4]) if row[4] else None,
                    "salinity": float(row[5]) if row[5] else None,
                    "pressure": float(row[6]) if row[6] else None,
                }
                for row in rows
            ]
            
            return jsonify({
                "data": data,
                "count": len(data),
                "limit": limit,
                "offset": offset
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/floats')
@cached(ttl=300)
def get_floats():
    """Get list of unique float IDs."""
    engine = get_db_engine()
    
    if not engine:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT float_id 
                FROM argo_data 
                ORDER BY float_id
                LIMIT 1000
            """))
            floats = [row[0] for row in result.fetchall()]
            
            return jsonify({"floats": floats, "count": len(floats)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/map/points')
@cached(ttl=60)
def get_map_points():
    """Get float positions for map visualization."""
    engine = get_db_engine()
    
    if not engine:
        return jsonify({"error": "Database not connected"}), 500
    
    limit = min(int(request.args.get('limit', 5000)), 10000)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT ON (float_id) 
                    float_id, latitude, longitude, timestamp, temperature
                FROM argo_data
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY float_id, timestamp DESC
                LIMIT :limit
            """), {"limit": limit})
            
            points = [
                {
                    "float_id": row[0],
                    "lat": float(row[1]),
                    "lng": float(row[2]),
                    "timestamp": row[3].isoformat() if row[3] else None,
                    "temperature": float(row[4]) if row[4] else None
                }
                for row in result.fetchall()
            ]
            
            return jsonify({"points": points, "count": len(points)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =============================================
# RUN SERVER
# =============================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  FloatChart - AI-Powered Ocean Data Chat")
    print("="*50)
    print(f"\n🌐 Opening at: http://localhost:5000")
    print("\n📋 Pages:")
    print("   /           - Chat Interface")
    print("   /map        - Interactive Map")
    print("   /dashboard  - Analytics Dashboard")
    print("\n💡 For data management, run:")
    print("   cd DATA_GENERATOR && python app.py")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
