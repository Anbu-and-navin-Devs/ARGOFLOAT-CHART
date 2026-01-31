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
# CACHING - Optimized with LRU eviction & endpoint-specific TTLs
# =============================================
_cache = {}
_cache_expiry = {}
_cache_access = {}  # Track last access for LRU
CACHE_TTL = 300  # Default 5 minutes
MAX_CACHE_SIZE = 100  # Limit cache entries to prevent memory bloat

# Endpoint-specific TTLs (seconds)
CACHE_TTLS = {
    'get_status': 60,        # Status changes slowly
    'get_stats': 300,        # Stats cached 5 min (uses sampling now)
    'get_floats': 600,       # Float list rarely changes
    'get_map_points': 180,   # Map points cached 3 min
    'get_data': 60,          # Data queries - moderate cache
    'handle_query': 180,     # AI queries - cache for repeated questions
}

def _normalize_cache_key(key: str) -> str:
    """Normalize cache key by sorting query params for consistency."""
    if '?' in key:
        base, params = key.split('?', 1)
        # Sort params alphabetically
        sorted_params = '&'.join(sorted(params.split('&')))
        return f"{base}?{sorted_params}"
    return key

def _evict_lru():
    """Evict least recently used cache entries if over limit."""
    if len(_cache) >= MAX_CACHE_SIZE:
        # Find and remove least recently accessed
        if _cache_access:
            oldest_key = min(_cache_access.keys(), key=lambda k: _cache_access.get(k, 0))
            _cache.pop(oldest_key, None)
            _cache_expiry.pop(oldest_key, None)
            _cache_access.pop(oldest_key, None)

def cache_response(key, data, ttl=CACHE_TTL):
    """Store data in cache with expiry and LRU tracking."""
    key = _normalize_cache_key(key)
    _evict_lru()
    _cache[key] = data
    _cache_expiry[key] = time.time() + ttl
    _cache_access[key] = time.time()

def get_cached(key):
    """Get cached data if not expired, with LRU update."""
    key = _normalize_cache_key(key)
    if key in _cache:
        if time.time() < _cache_expiry.get(key, 0):
            _cache_access[key] = time.time()  # Update LRU
            return _cache[key]
        else:
            # Expired - clean up
            _cache.pop(key, None)
            _cache_expiry.pop(key, None)
            _cache_access.pop(key, None)
    return None

def cached(ttl=None):
    """Decorator for caching endpoint responses with endpoint-specific TTLs."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Use endpoint-specific TTL or provided TTL or default
            cache_ttl = ttl or CACHE_TTLS.get(f.__name__, CACHE_TTL)
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
                cache_response(cache_key, data.get_json() if hasattr(data, 'get_json') else data, cache_ttl)
            return result
        return decorated_function
    return decorator

# =============================================
# DATABASE CONNECTION - Optimized for CockroachDB
# =============================================
_engine = None
_db_warmed = False

def get_db_engine():
    """Get or create database engine with eager initialization."""
    global _engine
    
    if not DATABASE_URL:
        return None
    
    # Return existing healthy engine
    if _engine is not None:
        return _engine
    
    # Convert postgresql:// to cockroachdb:// for proper CockroachDB support
    db_url = DATABASE_URL
    if db_url.startswith("postgresql://") and "cockroach" in db_url:
        db_url = db_url.replace("postgresql://", "cockroachdb://", 1)
    
    # Prepare connect_args for CockroachDB Cloud
    connect_args = {
        "connect_timeout": 10,      # Faster timeout
        "keepalives": 1,
        "keepalives_idle": 10,      # More aggressive keepalive
        "keepalives_interval": 5,
        "keepalives_count": 3,
    }
    
    # CockroachDB Cloud requires SSL
    if "cockroach" in db_url.lower():
        if "sslmode=verify-full" in db_url:
            db_url = db_url.replace("sslmode=verify-full", "sslmode=require")
        connect_args["sslmode"] = "require"
    
    try:
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,      # Check connection health
            pool_size=5,              # More connections ready
            max_overflow=10,          # Allow burst
            pool_recycle=120,         # Recycle every 2 min
            pool_timeout=15,          # Fail fast
            connect_args=connect_args,
            echo=False,
        )
        # Eagerly create connections
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connected")
        return _engine
    except Exception as e:
        print(f"❌ Database error: {e}")
        _engine = None
        return None

def warm_db_connection():
    """Warm up database connection and cache common queries."""
    global _db_warmed
    if _db_warmed:
        return
    
    engine = get_db_engine()
    if not engine:
        return
    
    try:
        with engine.connect() as conn:
            # Warm up connection pool with multiple connections
            conn.execute(text("SELECT 1"))
            # Pre-cache table statistics (makes subsequent queries faster)
            conn.execute(text("SELECT COUNT(*) FROM argo_data LIMIT 1"))
        _db_warmed = True
        print("✅ Database warmed up")
    except Exception as e:
        print(f"⚠️ Warm-up failed: {e}")

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
@cached()  # Uses CACHE_TTLS['get_status'] = 60s
def get_status():
    """Get application status with cached record count."""
    engine = get_db_engine()
    
    if not engine:
        return jsonify({
            "status": "offline",
            "database": "disconnected",
            "database_connected": False,
            "total_records": 0,
            "records": 0
        })
    
    try:
        with engine.connect() as conn:
            # Get approximate count (cached for 60 seconds)
            result = conn.execute(text("SELECT COUNT(*) FROM argo_data"))
            record_count = result.scalar() or 0
            
            return jsonify({
                "status": "online",
                "database": "connected",
                "database_connected": True,
                "total_records": record_count,
                "records": record_count
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
@cached()  # Uses CACHE_TTLS['get_stats'] = 120s
def get_stats():
    """Get database statistics for dashboard - OPTIMIZED with sampling."""
    engine = get_db_engine()
    
    if not engine:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        with engine.connect() as conn:
            # OPTIMIZATION: Use approximate count for huge tables (CockroachDB compatible)
            # Get count from table statistics (instant) instead of full scan
            count_result = conn.execute(text("""
                SELECT 
                    (SELECT reltuples::bigint FROM pg_class WHERE relname = 'argo_data') as approx_count,
                    (SELECT COUNT(DISTINCT float_id) FROM (
                        SELECT float_id FROM argo_data 
                        WHERE timestamp >= NOW() - INTERVAL '1 year'
                        LIMIT 100000
                    ) recent) as unique_floats_sample
            """))
            count_row = count_result.fetchone()
            approx_count = count_row[0] if count_row and count_row[0] else 0
            
            # Get date range and averages from recent sample (fast)
            result = conn.execute(text("""
                SELECT 
                    MIN(timestamp) as min_date,
                    MAX(timestamp) as max_date,
                    ROUND(AVG(temperature)::numeric, 2) as avg_temp,
                    ROUND(AVG(salinity)::numeric, 2) as avg_salinity
                FROM (
                    SELECT timestamp, temperature, salinity 
                    FROM argo_data 
                    WHERE timestamp >= NOW() - INTERVAL '6 months'
                    LIMIT 500000
                ) recent_sample
            """))
            row = result.fetchone()
            
            # Get actual float count (cached query is fast)
            float_result = conn.execute(text("""
                SELECT COUNT(DISTINCT float_id) FROM argo_data
                WHERE timestamp >= NOW() - INTERVAL '2 years'
            """))
            float_count = float_result.fetchone()[0] or 0
            
            return jsonify({
                "total_records": int(approx_count) if approx_count else 45800000,  # Fallback
                "unique_floats": float_count,
                "min_date": row[0].isoformat() if row[0] else None,
                "max_date": row[1].isoformat() if row[1] else None,
                "avg_temperature": float(row[2]) if row[2] else None,
                "avg_salinity": float(row[3]) if row[3] else None
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# AI Query cache - separate from endpoint cache for smarter matching
_query_cache = {}
_query_cache_expiry = {}
QUERY_CACHE_TTL = 300  # 5 minutes for repeated identical queries

def _normalize_query(query: str) -> str:
    """Normalize query for cache key matching."""
    import re
    # Lowercase, remove extra spaces, strip punctuation at end
    normalized = query.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'[?.!]+$', '', normalized)
    return normalized

def get_cached_query(query: str):
    """Get cached AI query result."""
    key = _normalize_query(query)
    if key in _query_cache:
        if time.time() < _query_cache_expiry.get(key, 0):
            return _query_cache[key]
        else:
            _query_cache.pop(key, None)
            _query_cache_expiry.pop(key, None)
    return None

def cache_query_result(query: str, result: dict):
    """Cache AI query result."""
    key = _normalize_query(query)
    # Only cache successful results with data
    if result and 'error' not in result:
        _query_cache[key] = result
        _query_cache_expiry[key] = time.time() + QUERY_CACHE_TTL
        # Limit cache size
        if len(_query_cache) > 50:
            oldest = min(_query_cache_expiry.keys(), key=lambda k: _query_cache_expiry[k])
            _query_cache.pop(oldest, None)
            _query_cache_expiry.pop(oldest, None)

@app.route('/api/query', methods=['GET', 'POST'])
def handle_query():
    """Handle natural language queries using AI - with intelligent caching."""
    if not get_intelligent_answer:
        return jsonify({"error": "AI module not available"}), 500
    
    # Support both GET (from map) and POST (from chat)
    if request.method == 'GET':
        user_query = request.args.get('question', '') or request.args.get('query', '')
    else:
        data = request.get_json() or {}
        user_query = data.get('query', '') or data.get('question', '')
    
    if not user_query:
        return jsonify({"error": "No query provided"}), 400
    
    # Check query cache first for instant response on repeated questions
    cached_result = get_cached_query(user_query)
    if cached_result:
        cached_result['cached'] = True  # Mark as cached response
        return jsonify(cached_result)
    
    try:
        response = get_intelligent_answer(user_query)
        # Cache successful responses
        cache_query_result(user_query, response)
        return jsonify(response)
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Query error: {error_detail}")
        return jsonify({"error": str(e), "detail": error_detail}), 500

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
@cached()  # Uses CACHE_TTLS['get_data'] = 60s
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
@cached()  # Uses CACHE_TTLS['get_floats'] = 600s (10 min)
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
@cached()  # Uses CACHE_TTLS['get_map_points'] = 120s
def get_map_points():
    """Get float positions for map visualization - OPTIMIZED for speed."""
    engine = get_db_engine()
    
    if not engine:
        return jsonify({"error": "Database not connected"}), 500
    
    limit = min(int(request.args.get('limit', 5000)), 10000)
    # Allow optional time filter for faster queries (default: last 2 years)
    years = int(request.args.get('years', 2))
    
    try:
        with engine.connect() as conn:
            # OPTIMIZED: Filter by recent timestamp first (uses idx_argo_timestamp index)
            # This dramatically reduces rows scanned from 45M to ~5-10M
            result = conn.execute(text("""
                SELECT DISTINCT ON (float_id) 
                    float_id, latitude, longitude, timestamp, temperature
                FROM argo_data
                WHERE latitude IS NOT NULL 
                  AND longitude IS NOT NULL
                  AND timestamp >= NOW() - INTERVAL ':years years'
                ORDER BY float_id, timestamp DESC
                LIMIT :limit
            """.replace(':years', str(years))), {"limit": limit})
            
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

# Health check endpoint for Render to keep app warm
@app.route('/health')
def health_check():
    """Health check endpoint - also keeps connection warm."""
    engine = get_db_engine()
    if engine:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return jsonify({"status": "healthy", "database": "connected"}), 200
        except:
            pass
    return jsonify({"status": "healthy", "database": "disconnected"}), 200

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  FloatChart - AI-Powered Ocean Data Chat")
    print("="*50)
    
    # Warm up database on startup
    print("\n🔄 Warming up database connection...")
    warm_db_connection()
    
    print(f"\n🌐 Opening at: http://localhost:5000")
    print("\n📋 Pages:")
    print("   /           - Chat Interface")
    print("   /map        - Interactive Map")
    print("   /dashboard  - Analytics Dashboard")
    print("\n💡 For data management, run:")
    print("   cd DATA_GENERATOR && python app.py")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
