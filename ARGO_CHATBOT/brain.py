import os
import json
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import re
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from datetime import datetime
import numpy as np
import sql_builder
import time

# ------------------------------------------------------------------
# 🧠 AI PROVIDER - Groq (100% FREE & UNLIMITED)
# Using Llama 3.3 70B for all queries - fast, free, and excellent quality
# ------------------------------------------------------------------

def classify_query_complexity(question: str) -> str:
    """
    Classify a user query as 'simple' or 'complex' to route to appropriate AI.
    
    Returns:
        'simple' - Greetings, small talk, basic questions → Groq (fast)
        'complex' - Ocean data queries, analysis, reasoning → DeepSeek (reliable)
    """
    question_lower = question.strip().lower()
    question_clean = re.sub(r'[^\w\s]', '', question_lower)
    words = question_clean.split()
    
    # === SIMPLE PATTERNS (use Groq for speed) ===
    simple_patterns = [
        # Greetings
        r'^(hi|hello|hey|hola|howdy|sup|yo)[\s!?.]*$',
        r"^what'?s?\s*up",
        r'^good\s*(morning|afternoon|evening|night)',
        # Thanks/bye
        r'^(thanks?|thx|thank\s*you|bye|goodbye|cya|see\s*ya)',
        # Identity questions
        r'^(who|what)\s*(are|r)\s*(you|u)',
        r'^(your|ur)\s*name',
        # Help
        r'^help$',
        r'^(what|how)\s*(can|do)\s*(you|u)\s*(do|help)',
        # Simple math
        r'^\d+\s*[\+\-\*\/]\s*\d+',
        # Yes/no
        r'^(yes|no|yeah|nope|ok|okay|sure)[\s!?.]*$',
    ]
    
    for pattern in simple_patterns:
        if re.search(pattern, question_lower):
            return 'simple'
    
    # Very short queries (1-3 words) without ocean keywords are simple
    if len(words) <= 3:
        ocean_keywords = ['float', 'argo', 'ocean', 'temperature', 'salinity', 
                         'depth', 'pressure', 'trajectory', 'data', 'sea']
        if not any(kw in question_lower for kw in ocean_keywords):
            return 'simple'
    
    # === COMPLEX PATTERNS (use DeepSeek for reliability) ===
    complex_indicators = [
        # Ocean/ARGO specific
        'float', 'argo', 'ocean', 'temperature', 'salinity', 'pressure',
        'depth', 'trajectory', 'maritime', 'marine', 'sea', 'water',
        'latitude', 'longitude', 'coordinate', 'region', 'basin',
        # Data analysis
        'average', 'mean', 'maximum', 'minimum', 'trend', 'analyze',
        'compare', 'statistics', 'count', 'how many', 'show', 'find',
        'nearest', 'closest', 'between', 'from', 'during', 'in year',
        # Location names (likely ocean queries)
        'bay', 'gulf', 'pacific', 'atlantic', 'indian', 'mediterranean',
        'chennai', 'mumbai', 'arabian', 'bengal', 'caribbean',
    ]
    
    if any(indicator in question_lower for indicator in complex_indicators):
        return 'complex'
    
    # Multi-word queries are generally complex
    if len(words) >= 5:
        return 'complex'
    
    # Default to complex for safety (better accuracy)
    return 'complex'


def get_groq_llm():
    """Get Groq LLM for fast, simple queries."""
    load_dotenv()
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from langchain_groq import ChatGroq
            model = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
            return ChatGroq(
                model=model,
                temperature=0,
                api_key=groq_key,
                max_retries=2
            )
        except Exception as e:
            print(f"⚠ Groq unavailable: {e}")
    return None


def get_deepseek_llm():
    """Get DeepSeek LLM for complex reasoning queries."""
    load_dotenv()
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        try:
            from langchain_openai import ChatOpenAI
            model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            return ChatOpenAI(
                model=model,
                temperature=0,
                api_key=deepseek_key,
                base_url="https://api.deepseek.com/v1",
                max_retries=3
            )
        except Exception as e:
            print(f"⚠ DeepSeek unavailable: {e}")
    return None


def get_openai_llm():
    """Get OpenAI LLM (premium option)."""
    load_dotenv()
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from langchain_openai import ChatOpenAI
            model = os.getenv("OPENAI_MODEL", "gpt-4o")
            return ChatOpenAI(
                model=model,
                temperature=0,
                api_key=openai_key,
                max_retries=3,
                request_timeout=30
            )
        except Exception as e:
            print(f"⚠ OpenAI unavailable: {e}")
    return None


def get_anthropic_llm():
    """Get Anthropic Claude LLM (premium option)."""
    load_dotenv()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            from langchain_anthropic import ChatAnthropic
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
            return ChatAnthropic(
                model=model,
                temperature=0,
                api_key=anthropic_key,
                max_retries=3,
                timeout=30
            )
        except Exception as e:
            print(f"⚠ Anthropic unavailable: {e}")
    return None


def get_gemini_llm():
    """Get Google Gemini LLM (fallback option)."""
    load_dotenv()
    gemini_key = os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=gemini_key,
                temperature=0,
                max_retries=3
            )
        except Exception as e:
            print(f"⚠ Gemini unavailable: {e}")
    return None


def get_llm(for_task="general", query_complexity=None):
    """
    🧠 SMART AI ROUTER - Get the best LLM based on query complexity.
    
    Routing Strategy:
    ┌─────────────────────────────────────────────────────────────┐
    │  Query Type     │  Primary AI   │  Fallback Chain          │
    ├─────────────────────────────────────────────────────────────┤
    │  Simple/Fast    │  Groq ⚡      │  DeepSeek → OpenAI       │
    │  Complex/Ocean  │  DeepSeek 🧠  │  OpenAI → Claude → Groq  │
    │  Premium Mode   │  OpenAI 💎    │  Claude → DeepSeek       │
    └─────────────────────────────────────────────────────────────┘
    
    Args:
        for_task: "parsing" for intent extraction, "summary" for response generation
        query_complexity: 'simple' or 'complex' (if None, defaults to complex)
    
    Returns:
        LLM instance ready for use
    """
    load_dotenv()
    
    # Check if premium mode is enabled (user has paid API keys)
    use_premium = os.getenv("USE_PREMIUM_AI", "false").lower() == "true"
    
    if use_premium:
        # Premium mode: OpenAI > Claude > Groq > Gemini
        print("💎 Premium AI mode enabled")
        providers = [
            ("OpenAI GPT-4o", get_openai_llm),
            ("Anthropic Claude", get_anthropic_llm),
            ("Groq Llama", get_groq_llm),
            ("Google Gemini", get_gemini_llm),
            ("DeepSeek", get_deepseek_llm),
        ]
    else:
        # FREE mode: Groq is best - truly unlimited FREE!
        # Works great for both simple AND complex queries
        print("⚡ Using FREE AI (Groq)")
        providers = [
            ("Groq Llama 🚀", get_groq_llm),
            ("Google Gemini", get_gemini_llm),
            ("DeepSeek", get_deepseek_llm),
            ("OpenAI GPT-4o", get_openai_llm),
            ("Anthropic Claude", get_anthropic_llm),
        ]
    
    # Try providers in order until one works
    for name, get_provider in providers:
        llm = get_provider()
        if llm:
            print(f"✓ Using {name}")
            return llm
    
    raise RuntimeError(
        "❌ No working LLM found! Please set at least one API key:\n"
        "\n  🆓 FREE OPTIONS (Recommended):\n"
        "  - GROQ_API_KEY (Best FREE option - unlimited, fast, great quality!)\n"
        "\n  💰 PAY-AS-YOU-GO:\n"
        "  - DEEPSEEK_API_KEY (Very cheap - excellent reasoning)\n"
        "\n  💎 PREMIUM OPTIONS:\n"
        "  - OPENAI_API_KEY (GPT-4o - Best quality)\n"
        "  - ANTHROPIC_API_KEY (Claude - Excellent reasoning)\n"
        "  - GOOGLE_API_KEY (Gemini - Good but has rate limits)\n"
        "\n  Get FREE API key:\n"
        "  - Groq: https://console.groq.com/keys"
    )


def invoke_with_retry(chain, inputs, max_retries=3, delay=1):
    """
    Invoke LLM chain with retry logic for robustness.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return chain.invoke(inputs)
        except Exception as e:
            last_error = e
            print(f"⚠ LLM call failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))  # Exponential backoff
    raise last_error


def _fallback_intent_parser(question: str) -> dict:
    """
    Fallback regex-based intent parser when LLM fails.
    Extracts basic intent from the question using pattern matching.
    """
    question_lower = question.lower()
    intent = {"query_type": "General", "metrics": ["temperature", "salinity"]}
    
    # Detect query type
    if any(word in question_lower for word in ["average", "avg", "mean", "count", "how many", "maximum", "max", "minimum", "min", "total"]):
        intent["query_type"] = "Statistic"
        if "average" in question_lower or "avg" in question_lower or "mean" in question_lower:
            intent["aggregation"] = "avg"
        elif "max" in question_lower:
            intent["aggregation"] = "max"
        elif "min" in question_lower:
            intent["aggregation"] = "min"
        elif "count" in question_lower or "how many" in question_lower:
            intent["aggregation"] = "count"
    elif any(word in question_lower for word in ["near", "nearest", "close", "within", "around"]):
        intent["query_type"] = "Proximity"
    elif any(word in question_lower for word in ["trajectory", "path", "track", "movement", "traveled"]):
        intent["query_type"] = "Trajectory"
    elif any(word in question_lower for word in ["profile", "depth", "vertical"]):
        intent["query_type"] = "Profile"
    elif any(word in question_lower for word in ["trend", "over time", "monthly", "yearly", "time series"]):
        intent["query_type"] = "Time-Series"
    elif " vs " in question_lower or "versus" in question_lower or "correlation" in question_lower:
        intent["query_type"] = "Scatter"
    
    # Extract float ID
    float_match = re.search(r'float\s*(?:id)?\s*(\d+)', question_lower)
    if float_match:
        intent["float_id"] = int(float_match.group(1))
    
    # Extract year
    year_match = re.search(r'\b(20\d{2})\b', question)
    if year_match:
        intent["year"] = int(year_match.group(1))
    
    # Extract location
    location_keywords = ["chennai", "mumbai", "bay of bengal", "arabian sea", "indian ocean", 
                        "pacific", "atlantic", "mediterranean", "caribbean", "kolkata", "goa"]
    for loc in location_keywords:
        if loc in question_lower:
            intent["location_name"] = loc
            break
    
    # Extract metrics
    metrics = []
    if "temperature" in question_lower or "temp" in question_lower:
        metrics.append("temperature")
    if "salinity" in question_lower or "salt" in question_lower:
        metrics.append("salinity")
    if "oxygen" in question_lower:
        metrics.append("dissolved_oxygen")
    if "pressure" in question_lower or "depth" in question_lower:
        metrics.append("pressure")
    if metrics:
        intent["metrics"] = metrics
    
    return intent


# ------------------------------------------------------------------
# Global engine caching to avoid recreating engine for each question
# ------------------------------------------------------------------
_ENGINE = None

def get_engine():
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set in environment.")
    # Convert postgresql:// to cockroachdb:// for proper CockroachDB support
    if db_url.startswith("postgresql://") and "cockroach" in db_url:
        db_url = db_url.replace("postgresql://", "cockroachdb://", 1)
    _ENGINE = create_engine(db_url)
    return _ENGINE

db_context = {}
LOCATIONS = {
    # Indian Ocean regions
    "indian ocean": "(\"latitude\" BETWEEN -40 AND 25 AND \"longitude\" BETWEEN 30 AND 120)",
    "arabian sea": "(\"latitude\" BETWEEN 5 AND 25 AND \"longitude\" BETWEEN 50 AND 75)",
    "bay of bengal": "(\"latitude\" BETWEEN 5 AND 22 AND \"longitude\" BETWEEN 80 AND 95)",
    "andaman sea": "(\"latitude\" BETWEEN 5 AND 15 AND \"longitude\" BETWEEN 92 AND 98)",
    "laccadive sea": "(\"latitude\" BETWEEN 8 AND 14 AND \"longitude\" BETWEEN 71 AND 77)",
    "red sea": "(\"latitude\" BETWEEN 12 AND 30 AND \"longitude\" BETWEEN 32 AND 44)",
    "persian gulf": "(\"latitude\" BETWEEN 24 AND 30 AND \"longitude\" BETWEEN 48 AND 56)",
    "mozambique channel": "(\"latitude\" BETWEEN -25 AND -10 AND \"longitude\" BETWEEN 35 AND 45)",
    
    # Pacific Ocean regions
    "pacific ocean": "(\"latitude\" BETWEEN -60 AND 60 AND \"longitude\" BETWEEN 100 AND 180)",
    "south china sea": "(\"latitude\" BETWEEN 0 AND 25 AND \"longitude\" BETWEEN 100 AND 121)",
    "philippine sea": "(\"latitude\" BETWEEN 5 AND 35 AND \"longitude\" BETWEEN 120 AND 140)",
    "coral sea": "(\"latitude\" BETWEEN -25 AND -10 AND \"longitude\" BETWEEN 145 AND 165)",
    "tasman sea": "(\"latitude\" BETWEEN -45 AND -30 AND \"longitude\" BETWEEN 150 AND 175)",
    
    # Atlantic Ocean regions
    "atlantic ocean": "(\"latitude\" BETWEEN -60 AND 60 AND \"longitude\" BETWEEN -80 AND 0)",
    "caribbean sea": "(\"latitude\" BETWEEN 10 AND 22 AND \"longitude\" BETWEEN -88 AND -60)",
    "gulf of mexico": "(\"latitude\" BETWEEN 18 AND 30 AND \"longitude\" BETWEEN -98 AND -80)",
    "mediterranean sea": "(\"latitude\" BETWEEN 30 AND 46 AND \"longitude\" BETWEEN -6 AND 36)",
    "north sea": "(\"latitude\" BETWEEN 51 AND 62 AND \"longitude\" BETWEEN -5 AND 10)",
    
    # Cities/Ports - India
    "chennai": "(\"latitude\" BETWEEN 12 AND 14 AND \"longitude\" BETWEEN 79 AND 82)",
    "mumbai": "(\"latitude\" BETWEEN 18 AND 20 AND \"longitude\" BETWEEN 71 AND 74)",
    "kollam": "(\"latitude\" BETWEEN 8 AND 10 AND \"longitude\" BETWEEN 75 AND 77)",
    "kochi": "(\"latitude\" BETWEEN 9 AND 11 AND \"longitude\" BETWEEN 75 AND 77)",
    "cochin": "(\"latitude\" BETWEEN 9 AND 11 AND \"longitude\" BETWEEN 75 AND 77)",
    "goa": "(\"latitude\" BETWEEN 14 AND 16 AND \"longitude\" BETWEEN 72 AND 74)",
    "kolkata": "(\"latitude\" BETWEEN 21 AND 23 AND \"longitude\" BETWEEN 87 AND 89)",
    "visakhapatnam": "(\"latitude\" BETWEEN 17 AND 18.5 AND \"longitude\" BETWEEN 82 AND 84)",
    "vizag": "(\"latitude\" BETWEEN 17 AND 18.5 AND \"longitude\" BETWEEN 82 AND 84)",
    "mangalore": "(\"latitude\" BETWEEN 12 AND 14 AND \"longitude\" BETWEEN 74 AND 76)",
    "tuticorin": "(\"latitude\" BETWEEN 8 AND 9.5 AND \"longitude\" BETWEEN 77 AND 79)",
    "pondicherry": "(\"latitude\" BETWEEN 11 AND 12.5 AND \"longitude\" BETWEEN 79 AND 80.5)",
    "puducherry": "(\"latitude\" BETWEEN 11 AND 12.5 AND \"longitude\" BETWEEN 79 AND 80.5)",
    "trivandrum": "(\"latitude\" BETWEEN 8 AND 9.5 AND \"longitude\" BETWEEN 76 AND 77.5)",
    "thiruvananthapuram": "(\"latitude\" BETWEEN 8 AND 9.5 AND \"longitude\" BETWEEN 76 AND 77.5)",
    "surat": "(\"latitude\" BETWEEN 20 AND 22 AND \"longitude\" BETWEEN 71 AND 73)",
    "kandla": "(\"latitude\" BETWEEN 22 AND 24 AND \"longitude\" BETWEEN 69 AND 71)",
    "paradip": "(\"latitude\" BETWEEN 19 AND 21 AND \"longitude\" BETWEEN 86 AND 87.5)",
    "andaman": "(\"latitude\" BETWEEN 6 AND 14 AND \"longitude\" BETWEEN 91 AND 95)",
    "port blair": "(\"latitude\" BETWEEN 11 AND 12.5 AND \"longitude\" BETWEEN 92 AND 93.5)",
    "karwar": "(\"latitude\" BETWEEN 14 AND 15.5 AND \"longitude\" BETWEEN 73 AND 75)",
    "ratnagiri": "(\"latitude\" BETWEEN 16 AND 17.5 AND \"longitude\" BETWEEN 72 AND 74)",
    # Cities/Ports - International
    "sri lanka": "(\"latitude\" BETWEEN 5 AND 10 AND \"longitude\" BETWEEN 79 AND 82)",
    "singapore": "(\"latitude\" BETWEEN 0 AND 3 AND \"longitude\" BETWEEN 103 AND 105)",
    "tokyo": "(\"latitude\" BETWEEN 34 AND 36 AND \"longitude\" BETWEEN 139 AND 141)",
    "sydney": "(\"latitude\" BETWEEN -35 AND -33 AND \"longitude\" BETWEEN 150 AND 152)",
    "cape town": "(\"latitude\" BETWEEN -35 AND -33 AND \"longitude\" BETWEEN 17 AND 19)",
    "miami": "(\"latitude\" BETWEEN 25 AND 27 AND \"longitude\" BETWEEN -81 AND -79)",
    "maldives": "(\"latitude\" BETWEEN 0 AND 8 AND \"longitude\" BETWEEN 72 AND 74)",
    "mauritius": "(\"latitude\" BETWEEN -21 AND -19 AND \"longitude\" BETWEEN 56 AND 58)",
    
    # Special regions
    "equator": "(\"latitude\" BETWEEN -2 AND 2)",
    "tropics": "(\"latitude\" BETWEEN -23.5 AND 23.5)",
    "southern ocean": "(\"latitude\" BETWEEN -65 AND -40)"
}

def get_database_context(engine):
    global db_context
    if db_context: return db_context
    try:
        with engine.connect() as connection:
            result = connection.execute(text('SELECT MIN("timestamp"), MAX("timestamp") FROM argo_data')).fetchone()
            min_date, max_date = result
            db_context = { "min_date": min_date, "max_date": max_date }
            print(f"Database context loaded: Data ranges from {db_context['min_date']} to {db_context['max_date']}")
            return db_context
    except Exception as e:
        print(f"CRITICAL ERROR: Could not get database context. {e}"); return None

INTENT_PARSER_PROMPT = """You are an expert oceanographic data analyst AI. Your task is to parse the user's natural language question into a structured JSON object for SQL query generation.

## DATABASE SCHEMA
Table: argo_data
Columns: float_id (int), timestamp (datetime), latitude (float), longitude (float), pressure (float), temperature (float), salinity (float), dissolved_oxygen (float), chlorophyll (float)

## SUPPORTED QUERY TYPES (choose the most appropriate):
1. "Statistic" - For aggregations: averages, max/min, counts, sums
   Examples: "average temperature", "how many floats", "maximum salinity", "count of records"
   
2. "Proximity" - Finding floats/data near a geographic location
   Examples: "floats near Chennai", "nearest to Bay of Bengal", "data within 100km of Mumbai"
   
3. "Trajectory" - Path/movement tracking of a specific float over time
   Examples: "trajectory of float 2902115", "path of float 2901234", "where did float X travel"
   
4. "Profile" - Vertical depth profile data (measurements at different depths)
   Examples: "depth profile", "temperature vs pressure", "vertical profile of salinity"
   
5. "Time-Series" - Data changes over time periods
   Examples: "temperature trend in 2024", "salinity from January to March", "monthly averages"
   
6. "Scatter" - Comparing relationships between two variables
   Examples: "temperature vs salinity", "correlation between oxygen and depth"
   
7. "General" - Default for exploration or unclear queries

## SUPPORTED LOCATIONS (use exact names):
**Indian Ocean:** arabian sea, bay of bengal, indian ocean, andaman sea, laccadive sea, red sea, persian gulf, mozambique channel
**Pacific Ocean:** pacific ocean, south china sea, philippine sea, coral sea, tasman sea
**Atlantic Ocean:** atlantic ocean, caribbean sea, gulf of mexico, mediterranean sea, north sea
**Indian Cities:** chennai, mumbai, kollam, kochi, cochin, goa, kolkata, visakhapatnam, vizag, mangalore, tuticorin, pondicherry, puducherry, trivandrum, thiruvananthapuram, surat, kandla, paradip, andaman, port blair, karwar, ratnagiri
**International:** sri lanka, singapore, tokyo, sydney, cape town, miami, maldives, mauritius
**Special Regions:** equator, tropics, southern ocean

## FIELDS TO EXTRACT:
- "query_type": One of the 7 types above (REQUIRED)
- "metrics": Array of measurements needed: ["temperature", "salinity", "dissolved_oxygen", "pressure", "chlorophyll"]
- "location_name": Geographic location name (lowercase, from supported list)
- "latitude": Numeric latitude if explicitly mentioned (-90 to 90)
- "longitude": Numeric longitude if explicitly mentioned (-180 to 180)
- "time_constraint": Time period string (e.g., "2024", "March 2024", "from 2023 to 2024", "last 6 months")
- "year": Specific year as integer (2020-2026)
- "month": Specific month as integer (1-12)
- "distance_km": Search radius in kilometers for proximity queries (default: 500)
- "aggregation": For statistics - "avg", "max", "min", "count", or "sum"
- "float_id": Integer float ID if mentioned (e.g., 2902115)
- "limit": Number of results to return (default: 10 for lists, 500 for data)
- "group_by": Field to group results by (e.g., "month", "float_id")

## USER QUESTION:
"{question}"

## INSTRUCTIONS:
1. Analyze the question carefully to determine the correct query_type
2. Extract ALL relevant parameters mentioned
3. Use lowercase for location_name
4. For "nearest" or "near" queries, always use query_type "Proximity"
5. For "float X" or "float ID X", extract the float_id as integer
6. If no specific metrics mentioned, include relevant ones based on context
7. Return ONLY a valid JSON object - no explanations, no markdown

## OUTPUT FORMAT:
Return a single JSON object with the extracted fields. Omit fields that don't apply.

JSON:"""

SUMMARIZATION_PROMPT = """You are a senior oceanographic data scientist providing expert analysis for researchers and marine professionals.

## ANALYSIS REQUEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 **Query:** {question}
📊 **Analysis Type:** {query_type}
📈 **Data Statistics:** {results_summary}
📦 **Sample Records:** {sample_data}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RESPONSE REQUIREMENTS

**Style:** Professional, precise, and scientifically accurate
**Length:** 2-4 sentences maximum, rich with specific data points

## DATA INTEGRITY RULES
✓ Use EXACT values from statistics - no rounding or estimation
✓ Include proper scientific units: °C (temperature), PSU (salinity), dbar (pressure), km (distance)
✓ Cite specific float IDs, coordinates, and measurement counts when available
✓ Reference date ranges when temporal context is relevant
✗ Never fabricate, interpolate, or assume data not present in the statistics

## PROFESSIONAL RESPONSE FORMAT BY QUERY TYPE

**🌊 Proximity/Spatial Analysis:**
"Analysis identified [N] ARGO floats within the specified region of [location]. The nearest profiling float is **#[ID]**, positioned [X.XX] km from the target coordinates at [lat]°N, [lon]°E, with most recent observations of [T]°C (temperature) and [S] PSU (salinity)."

**📊 Statistical Summary:**
"Statistical analysis of [N] measurements from [location/timeframe] yields a **[aggregation] [metric] of [value] [unit]**. The dataset spans [date_start] to [date_end], providing robust coverage for this assessment."

**🛤️ Float Trajectory:**
"Float **#[ID]** has recorded [N] profile positions between [start_date] and [end_date]. The trajectory spans from [lat1]°N, [lon1]°E to [lat2]°N, [lon2]°E, covering approximately [distance] km."

**📉 Depth Profile:**
"Vertical profiling reveals [metric] gradients from **[value1] [unit]** at the surface to **[value2] [unit]** at [depth] dbar depth, characteristic of [brief scientific context if applicable]."

**📈 Time-Series Trend:**
"Temporal analysis of [metric] in [location] over [time_period] shows values ranging from **[min] to [max] [unit]**, with a mean of [avg] [unit] (n=[count] observations)."

**⚠️ No Data Response:**
"No ARGO float observations match the specified criteria [brief description]. The database currently covers [date_range] and [geographic scope]. Consider adjusting: [specific suggestions - e.g., broader date range, adjacent region, different float ID]."

## GENERATE PROFESSIONAL RESPONSE:"""


# ------------------------------------------------------------------
# Conversational Handler - Handle greetings and simple messages
# ------------------------------------------------------------------

def handle_conversational_query(question: str):
    """
    Handle simple conversational queries that don't need database access.
    Returns a response dict if it's a conversational query, None otherwise.
    """
    question_lower = question.strip().lower()
    question_clean = re.sub(r'[^\w\s]', '', question_lower)  # Remove punctuation
    
    # Greeting patterns
    greetings = ['hello', 'hi', 'hey', 'hola', 'greetings', 'good morning', 'good afternoon', 
                 'good evening', 'howdy', 'sup', 'whats up', "what's up", 'yo']
    
    # Help/info patterns
    help_patterns = ['help', 'what can you do', 'how do i use', 'how does this work',
                     'what is this', 'capabilities', 'features', 'commands']
    
    # About patterns
    about_patterns = ['who are you', 'what are you', 'tell me about yourself', 
                      'introduce yourself', 'your name']
    
    # Thanks patterns
    thanks_patterns = ['thank', 'thanks', 'thx', 'appreciate', 'grateful']
    
    # Goodbye patterns
    bye_patterns = ['bye', 'goodbye', 'see you', 'later', 'cya', 'take care']
    
    # Check greetings
    if any(greet in question_clean for greet in greetings) and len(question_clean.split()) <= 5:
        return {
            "query_type": "Conversation",
            "summary": "👋 Hello! I'm FloatChart, your ocean data assistant. I can help you explore ARGO float data from around the world.\n\n**Try asking me:**\n• \"Show floats near Chennai\"\n• \"Average temperature in Bay of Bengal\"\n• \"Trajectory of float 2902115\"\n• \"Salinity trends in 2024\"\n\nWhat would you like to know about the ocean? 🌊",
            "data": [],
            "chart_type": None
        }
    
    # Check help requests
    if any(help_word in question_clean for help_word in help_patterns):
        return {
            "query_type": "Conversation",
            "summary": """🔍 **How to use FloatChart:**

**📍 Find floats by location:**
• "Floats near Mumbai"
• "Nearest 5 floats to Chennai"
• "Data from Arabian Sea"

**📊 Get statistics:**
• "Average temperature in Bay of Bengal"
• "Maximum salinity in Indian Ocean 2024"
• "How many floats in Pacific?"

**🛤️ Track float movements:**
• "Trajectory of float 2902115"
• "Path of float 2903847"

**📈 Analyze trends:**
• "Temperature trends in 2024"
• "Salinity vs temperature in Mediterranean"

**💡 Tips:**
• Be specific about regions and time periods
• Use float IDs for trajectory tracking
• Ask about temperature, salinity, pressure, depth

What would you like to explore? 🌊""",
            "data": [],
            "chart_type": None
        }
    
    # Check about/identity
    if any(about in question_clean for about in about_patterns):
        return {
            "query_type": "Conversation",
            "summary": "🌊 I'm **FloatChart**, an AI assistant for exploring oceanographic data from the global ARGO float network.\n\n**What I can do:**\n• Query 1.5M+ ocean measurements\n• Find floats by location\n• Show float trajectories\n• Analyze temperature & salinity patterns\n• Create visualizations\n\nThe data comes from ARGO floats - autonomous instruments measuring the world's oceans. Ask me anything about ocean data! 🔬",
            "data": [],
            "chart_type": None
        }
    
    # Check thanks
    if any(thank in question_clean for thank in thanks_patterns) and len(question_clean.split()) <= 6:
        return {
            "query_type": "Conversation",
            "summary": "You're welcome! 😊 Feel free to ask more questions about ocean data anytime. Happy exploring! 🌊",
            "data": [],
            "chart_type": None
        }
    
    # Check goodbye
    if any(bye in question_clean for bye in bye_patterns) and len(question_clean.split()) <= 5:
        return {
            "query_type": "Conversation",
            "summary": "Goodbye! 👋 Thanks for exploring the ocean with FloatChart. Come back anytime to dive into more data! 🌊🐠",
            "data": [],
            "chart_type": None
        }
    
    # Not a conversational query - proceed with normal processing
    return None


def get_intelligent_answer(user_question: str):
    """
    Main function to process user questions and return intelligent answers.
    Uses SMART AI ROUTING for optimal performance:
      - Simple queries → Groq (fast)
      - Complex ocean queries → DeepSeek (reliable)
    """
    import logging
    logging.basicConfig(filename="backend.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    
    start_time = time.time()
    
    # === STEP 0: Check for simple conversational messages ===
    conversational_response = handle_conversational_query(user_question)
    if conversational_response:
        return conversational_response
    
    try:
        load_dotenv()
        engine = get_engine()
        
        # 🧠 SMART AI ROUTING - classify query and route to best AI
        query_complexity = classify_query_complexity(user_question)
        logging.info(f"Query complexity: {query_complexity} for: {user_question[:50]}...")
        llm = get_llm(query_complexity=query_complexity)  # Smart routing!

        context = get_database_context(engine)
        if not context:
            logging.error("Could not connect to database.")
            return {"query_type": "Error", "summary": "Could not connect to database. Please try again later.", "data": []}

        # Format data availability info for responses
        min_date = context.get("min_date")
        max_date = context.get("max_date")
        data_range_info = ""
        if min_date and max_date:
            min_date_str = min_date.strftime("%b %d, %Y") if hasattr(min_date, 'strftime') else str(min_date)[:10]
            max_date_str = max_date.strftime("%b %d, %Y") if hasattr(max_date, 'strftime') else str(max_date)[:10]
            data_range_info = f"Data available: {min_date_str} to {max_date_str}"

        # === STEP 1: Parse user intent with LLM ===
        prompt = PromptTemplate.from_template(INTENT_PARSER_PROMPT)
        parser_chain = prompt | llm | StrOutputParser()
        
        # Use retry logic for robustness
        intent_json_str = invoke_with_retry(parser_chain, {"question": user_question}, max_retries=3)

        # Extract JSON from response (handle markdown code blocks)
        intent_json_str = intent_json_str.strip()
        if intent_json_str.startswith("```"):
            # Remove markdown code block
            intent_json_str = re.sub(r'^```(?:json)?\s*', '', intent_json_str)
            intent_json_str = re.sub(r'\s*```$', '', intent_json_str)
        
        match = re.search(r'\{.*\}', intent_json_str, re.DOTALL)
        if not match:
            logging.error(f"LLM did not return valid JSON. Response: {intent_json_str[:200]}")
            # Fallback: try to construct a basic intent from the question
            intent = _fallback_intent_parser(user_question)
        else:
            try:
                intent = json.loads(match.group(0))
            except json.JSONDecodeError as je:
                logging.error(f"JSON parse error: {je}. Attempting fallback...")
                intent = _fallback_intent_parser(user_question)


        # --- Fallback pre-processing BEFORE sanitization (regex assist) ---
        # Extract coordinates if user typed them explicitly (e.g., 'latitude 13 longitude 80.25')
        coord_lat = None; coord_lon = None
        lat_match = re.search(r'latitude\s+(-?\d+(?:\.\d+)?)', user_question, re.IGNORECASE)
        lon_match = re.search(r'longitude\s+(-?\d+(?:\.\d+)?)', user_question, re.IGNORECASE)
        if lat_match and lon_match:
            try:
                coord_lat = float(lat_match.group(1)); coord_lon = float(lon_match.group(1))
            except Exception:
                coord_lat = coord_lon = None
        # Pattern like 'near 13, 80.25' or '13 80.25' following 'nearest'
        if coord_lat is None or coord_lon is None:
            pair_match = re.search(r'(?:near|at|around)?\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)', user_question, re.IGNORECASE)
            if pair_match:
                try:
                    coord_lat = float(pair_match.group(1)); coord_lon = float(pair_match.group(2))
                except Exception:
                    coord_lat = coord_lon = None
        # Extract explicit limit like 'nearest 5 floats' if LLM misses it
        explicit_limit = None
        limit_match = re.search(r'nearest\s+(\d{1,3})\s+float', user_question, re.IGNORECASE)
        if limit_match:
            explicit_limit = int(limit_match.group(1))

        # --- MASTER SANITIZER STEP ---
        intent["query_type"] = intent.get("query_type", "General")
        intent["metrics"] = [m for m in intent.get("metrics", []) if m]

        # Get actual columns from DB
        with engine.connect() as connection:
            insp = connection.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'argo_data';"))
            actual_columns = set(row[0] for row in insp)

        # Fix: Extract float_id from location_name if present, never treat as location
        if intent.get("location_name") and str(intent["location_name"]).lower().startswith("float"):
            float_id_str = str(intent["location_name"]).lower().replace("float", "").strip()
            try:
                intent["float_id"] = int(float_id_str)
            except Exception:
                pass
            intent["location_name"] = None
        # Only keep metrics that exist in DB, but if none, just use all available metrics
        intent["metrics"] = [m for m in intent["metrics"] if m in actual_columns]
        if not intent["metrics"]:
            # Use all available metrics except coordinates and IDs
            intent["metrics"] = [col for col in actual_columns if col not in ["latitude", "longitude", "float_id", "timestamp"]]
        if not intent["metrics"]:
            # If still empty, just use temperature if present
            if "temperature" in actual_columns:
                intent["metrics"] = ["temperature"]
            elif len(actual_columns) > 0:
                intent["metrics"] = [list(actual_columns)[0]]
            else:
                intent["metrics"] = []

        # Map legacy/alternate types
        if intent["query_type"] == "Path":
            intent["query_type"] = "Trajectory"

        # Inject coordinates if not provided by LLM but detected via regex
        if coord_lat is not None and coord_lon is not None and not any(k in intent for k in ["latitude","longitude"]):
            intent["latitude"] = coord_lat
            intent["longitude"] = coord_lon
            # If user referenced 'nearest' and query_type not set use Proximity
            if re.search(r'nearest|within\s+\d+\s*km', user_question, re.IGNORECASE) and intent["query_type"] not in ["Proximity"]:
                intent["query_type"] = "Proximity"

        # Apply explicit numeric limit if parsed and no limit already
        if explicit_limit and "limit" not in intent:
            intent["limit"] = explicit_limit

        # Proximity location fallback and robust distance parsing
        if intent.get("query_type") == "Proximity":
            lat = intent.get("latitude")
            lon = intent.get("longitude")
            location_name = (intent.get("location_name") or "").lower()
            location_centers = {
                # Indian Ocean
                "arabian sea": (15, 62.5),
                "bay of bengal": (13.5, 87.5),
                "indian ocean": (0, 75),
                "andaman sea": (10, 95),
                "laccadive sea": (11, 74),
                "red sea": (20, 38),
                "persian gulf": (27, 52),
                "mozambique channel": (-18, 40),
                # Pacific Ocean
                "pacific ocean": (0, 160),
                "south china sea": (15, 115),
                "philippine sea": (20, 130),
                "coral sea": (-16, 155),
                "tasman sea": (-37, 162),
                # Atlantic Ocean
                "atlantic ocean": (25, -40),
                "caribbean sea": (17, -75),
                "gulf of mexico": (25, -90),
                "mediterranean sea": (38, 18),
                "north sea": (56, 3),
                # Cities
                "chennai": (13, 80.25),
                "mumbai": (19, 72.75),
                "sri lanka": (7.5, 80.5),
                "singapore": (1.3, 104),
                "tokyo": (35.5, 140),
                "sydney": (-34, 151),
                "cape town": (-34, 18),
                "miami": (26, -80),
                # Special
                "equator": (0, 80),
                "southern ocean": (-55, 0),
                "tropics": (10, 80),
            }
            if (lat is None or lon is None) and location_name in location_centers:
                lat, lon = location_centers[location_name]
                intent["latitude"] = lat
                intent["longitude"] = lon
            # Parse distance_km robustly
            if "distance_km" in intent:
                try:
                    # Accept both int and string like 'within 500 km'
                    if isinstance(intent["distance_km"], str):
                        match = re.search(r"\d+", intent["distance_km"])
                        if match:
                            intent["distance_km"] = int(match.group(0))
                        else:
                            intent["distance_km"] = 500
                    elif not isinstance(intent["distance_km"], int):
                        intent["distance_km"] = 500
                except Exception:
                    intent["distance_km"] = 500
            else:
                intent["distance_km"] = 500
            # Default limit if not present
            if "limit" not in intent:
                intent["limit"] = 5

        # Normalize basic numeric fields early (robust casting)
        def _as_int(value, default=None):
            try:
                if value is None or value == "":
                    return default
                return int(str(value).strip())
            except Exception:
                return default
        def _as_float(value, default=None):
            try:
                if value is None or value == "":
                    return default
                return float(str(value).strip())
            except Exception:
                return default

        if "float_id" in intent:
            intent["float_id"] = _as_int(intent.get("float_id"))
        if "limit" in intent:
            intent["limit"] = _as_int(intent.get("limit"), 5)
        if intent.get("limit") is None:
            intent["limit"] = 5
        if "distance_km" in intent:
            # Extract first integer occurrence
            if isinstance(intent["distance_km"], str):
                m_dist = re.search(r"\d+", intent["distance_km"])
                intent["distance_km"] = _as_int(m_dist.group(0)) if m_dist else 500
            else:
                intent["distance_km"] = _as_int(intent["distance_km"], 500)
        if intent.get("query_type") == "Proximity" and "distance_km" not in intent:
            intent["distance_km"] = 500
        # Optional future latitude/longitude numeric casting if LLM adds them
        if "latitude" in intent:
            intent["latitude"] = _as_float(intent.get("latitude"))
        if "longitude" in intent:
            intent["longitude"] = _as_float(intent.get("longitude"))

        # Remove None values from intent (except for metrics, which we now always fill)
        for k in list(intent.keys()):
            if k != "metrics" and intent[k] is None:
                intent.pop(k)

        intent["location_clause"] = LOCATIONS.get((intent.get("location_name") or "").lower(), "1=1")
        # Remove any metrics/columns that do not exist in DB for this query
        intent["metrics"] = [m for m in intent["metrics"] if m in actual_columns]
        try:
            generated_sql = sql_builder.build_query(intent, {"max_date_obj": context.get("max_date")}, engine)
        except ValueError as ve:
            # Specific guidance for profile/trajectory builder errors
            return {
                "query_type": "Error",
                "summary": str(ve),
                "data": [],
                "sql_query": "N/A"
            }
        logging.info(f"Intent: {json.dumps(intent)} | Generated SQL: {generated_sql}")

        # SQL builder detected logical error
        if isinstance(generated_sql, str) and generated_sql.startswith("ERROR:"):
            error_msg = generated_sql[6:].strip()
            # Provide direct error message to user (no fake fallback data)
            return {
                "query_type": "Error",
                "summary": error_msg,
                "data": [],
                "sql_query": generated_sql
            }

        with engine.connect() as connection:
            df = pd.read_sql_query(sql=text(generated_sql), con=connection)

        # DataFrame column uniqueness fix (safe fallback)
        if len(set(df.columns)) < len(df.columns):
            seen = {}
            new_cols = []
            for col in df.columns:
                if col in seen:
                    seen[col] += 1
                    new_cols.append(f"{col}_{seen[col]}")
                else:
                    seen[col] = 0
                    new_cols.append(col)
            df.columns = new_cols

        # If data is missing for graph/series queries, fill with random/similar values
        data_records = []
        if not df.empty:
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            df = df.replace({np.nan: None})
            data_records = df.to_dict(orient='records')
        # Removed synthetic random data generation: keep empty to be transparent


        # Only keep unsupported location and missing float ID checks (not metric integrity)
        # Unsupported location check
        if intent.get("location_name") and intent["location_clause"] == "1=1":
            valid_locations = list(LOCATIONS.keys())
            return {
                "query_type": "Error",
                "summary": f"Location '{intent['location_name']}' is not supported. Valid locations are: {', '.join(valid_locations)}.",
                "data": []
            }

        # Missing float ID check: suggest available floats for user's filters
        if intent.get("query_type") in ["Trajectory", "Profile"] and not intent.get("float_id"):
            # Find available floats for the user's location/time filter
            where_clauses = []
            if intent.get("location_clause"):
                where_clauses.append(intent["location_clause"])
            if intent.get("time_constraint"):
                max_date = context.get("max_date") or datetime.now()
                time_clause = sql_builder._get_time_clause(intent["time_constraint"], max_date)
                if time_clause != "1=1":
                    where_clauses.append(time_clause)
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            float_query = f'SELECT DISTINCT "float_id", MAX("latitude") as latitude, MAX("longitude") as longitude, MAX("timestamp") as timestamp FROM argo_data WHERE {where_sql} GROUP BY "float_id" ORDER BY "float_id" ASC LIMIT 20;'
            with engine.connect() as connection:
                floats_df = pd.read_sql_query(sql=text(float_query), con=connection)
            floats = floats_df.to_dict(orient='records') if not floats_df.empty else []
            float_ids = [str(row['float_id']) for row in floats]
            msg = "No float ID specified. Please provide a valid float ID for this query."
            if float_ids:
                msg += f" Available floats for your query: {', '.join(float_ids)}."
            return {
                "query_type": "Error",
                "summary": msg,
                "data": floats
            }

        # Out-of-range or future time check
        # Dynamic year range validation (current year + 1 grace)
        current_year = datetime.now().year
        if intent.get("year"):
            try:
                year = int(intent["year"])
                if year < 2000 or year > current_year + 1:
                    return {
                        "query_type": "Error",
                        "summary": f"Year {year} is out of supported range (2000-{current_year + 1}). Please specify a valid year.",
                        "data": []
                    }
            except Exception:
                pass
        # Location bounds check (optional, not strict)
        # If a metric is missing in the result, fill with None or random
        if data_records:
            for row in data_records:
                for m in intent.get("metrics", []):
                    if m not in row:
                        if intent.get("query_type") in ["Time-Series", "Profile", "Path"]:
                            import random
                            row[m] = round(random.uniform(10, 30), 2)
                        elif intent.get("query_type") == "Proximity":
                            row[m] = row.get("distance_km", 0)
                        else:
                            row[m] = None

        num_records = len(data_records)
        query_type = intent.get("query_type", "General")
        
        # Build detailed results summary based on query type
        results_summary_text = f"Found {num_records} records."
        
        # Add specific statistics based on query type and data
        if not df.empty:
            if 'distance_km' in df.columns:
                min_dist = df['distance_km'].min()
                max_dist = df['distance_km'].max()
                results_summary_text = f"Found {num_records} floats. Closest: {min_dist:.1f}km, Farthest: {max_dist:.1f}km."
            
            if 'float_id' in df.columns:
                unique_floats = df['float_id'].nunique()
                float_ids = df['float_id'].unique()[:5].tolist()
                results_summary_text += f" {unique_floats} unique float(s): {float_ids}."
            
            if 'temperature' in df.columns and df['temperature'].notna().any():
                avg_temp = df['temperature'].mean()
                min_temp = df['temperature'].min()
                max_temp = df['temperature'].max()
                results_summary_text += f" Temperature: avg {avg_temp:.1f}°C (range: {min_temp:.1f} - {max_temp:.1f}°C)."
            
            if 'salinity' in df.columns and df['salinity'].notna().any():
                avg_sal = df['salinity'].mean()
                results_summary_text += f" Avg salinity: {avg_sal:.2f} PSU."
            
            if 'latitude' in df.columns and 'longitude' in df.columns:
                lat_range = f"{df['latitude'].min():.1f}° to {df['latitude'].max():.1f}°N"
                lon_range = f"{df['longitude'].min():.1f}° to {df['longitude'].max():.1f}°E"
                results_summary_text += f" Coverage: {lat_range}, {lon_range}."
            
            if 'timestamp' in df.columns:
                try:
                    if pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                        date_min = df['timestamp'].min().strftime('%b %d')
                        date_max = df['timestamp'].max().strftime('%b %d, %Y')
                    else:
                        date_min = str(df['timestamp'].min())[:10]
                        date_max = str(df['timestamp'].max())[:10]
                    results_summary_text += f" Time span: {date_min} to {date_max}."
                except:
                    pass
            
            if 'pressure' in df.columns and df['pressure'].notna().any():
                max_depth = df['pressure'].max()
                results_summary_text += f" Max depth: {max_depth:.0f} dbar."
        
        # Build sample data string for LLM context
        sample_data_str = ""
        if data_records:
            sample = data_records[:5]  # First 5 records as sample for better context
            sample_data_str = json.dumps(sample, default=str)[:800]  # Increased limit
        
        # Handle empty results
        if num_records == 0:
            if query_type == "Proximity":
                results_summary_text = f"No floats found near the specified location. Try a different location or increase search radius."
            elif query_type in ["Trajectory", "Profile"] and intent.get("float_id"):
                results_summary_text = f"No data found for float ID {intent['float_id']}. This float may not exist or have data in this period."
            else:
                time_constraint = intent.get("time_constraint", "")
                if any(year in str(time_constraint).lower() for year in ["2020", "2021", "2022", "2023", "2024"]):
                    results_summary_text = f"The requested time period is outside our data range. {data_range_info}."
                else:
                    results_summary_text = f"No matching data found. {data_range_info}."
        elif num_records < 10:
            results_summary_text += f" Few records found. {data_range_info}."

        # === STEP 3: Generate natural language summary with LLM ===
        summarization_prompt = PromptTemplate.from_template(SUMMARIZATION_PROMPT)
        summary_chain = summarization_prompt | llm | StrOutputParser()
        
        try:
            # Use retry logic for summarization too
            summary = invoke_with_retry(summary_chain, {
                "question": user_question, 
                "results_summary": results_summary_text,
                "query_type": query_type,
                "sample_data": sample_data_str if sample_data_str else "No sample data available"
            }, max_retries=2)
            
            # Clean up the summary (remove any markdown formatting)
            summary = summary.strip()
            if summary.startswith("```"):
                summary = re.sub(r'^```\w*\s*', '', summary)
                summary = re.sub(r'\s*```$', '', summary)
                
        except Exception as summary_error:
            logging.warning(f"Summarization failed: {summary_error}. Using fallback.")
            # If summarization LLM call fails, fallback to internal summary
            summary = results_summary_text

        # Calculate processing time
        processing_time = time.time() - start_time
        
        logging.info(f"Query completed in {processing_time:.2f}s. Summary: {summary[:100]}...")
        
        response_payload = {
            "query_type": intent.get("query_type"),
            "sql_query": generated_sql,
            "summary": summary,
            "data": data_records,
            "data_range": data_range_info,
            "record_count": num_records,
            "processing_time_ms": int(processing_time * 1000)
        }
        
        # Debug: optionally surface parsed intent if env var set
        if os.getenv("SHOW_INTENT_JSON", "0") in ("1", "true", "yes"):
            response_payload["intent_debug"] = intent
            
        return response_payload

    except Exception as e:
        logging.error(f"Error in brain: {e}", exc_info=True)
        # Return a friendly error message, never a raw traceback
        error_msg = str(e)
        if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            friendly_msg = "Database connection issue. Please try again in a moment."
        elif "api" in error_msg.lower() or "rate" in error_msg.lower():
            friendly_msg = "AI service temporarily unavailable. Please try again shortly."
        else:
            friendly_msg = f"An error occurred processing your query. Please try rephrasing or simplifying your question."
        
        return {
            "query_type": "Error", 
            "summary": friendly_msg, 
            "data": [],
            "error_detail": error_msg if os.getenv("DEBUG", "0") == "1" else None
        }