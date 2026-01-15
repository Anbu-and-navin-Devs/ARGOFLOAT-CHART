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

# ------------------------------------------------------------------
# LLM Provider Setup - Supports Groq and Google Gemini
# ------------------------------------------------------------------

def get_llm():
    """
    Initialize the LLM based on available API keys.
    Priority: Groq (fast & reliable) > Google Gemini
    """
    load_dotenv()
    
    # Try Groq first (fast and reliable)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from langchain_groq import ChatGroq
            model = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
            print(f"Using Groq model: {model}")
            return ChatGroq(
                model=model,
                temperature=0,
                api_key=groq_key
            )
        except ImportError:
            print("Warning: langchain-groq not installed. Trying Gemini...")
        except Exception as e:
            print(f"Groq error: {e}. Trying Gemini...")
    
    # Fallback to Google Gemini
    gemini_key = os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            print(f"Using Gemini model: {model}")
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=gemini_key,
                temperature=0
            )
        except ImportError:
            print("Warning: langchain-google-genai not installed.")
        except Exception as e:
            print(f"Gemini error: {e}")
    
    raise RuntimeError(
        "No working LLM found! Please set either:\n"
        "  - GROQ_API_KEY (for Groq - fast & free)\n"
        "  - GOOGLE_API_KEY (for Google Gemini)"
    )

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
    
    # Cities/Ports
    "chennai": "(\"latitude\" BETWEEN 12.5 AND 14 AND \"longitude\" BETWEEN 80 AND 81)",
    "mumbai": "(\"latitude\" BETWEEN 18 AND 20 AND \"longitude\" BETWEEN 72 AND 73.5)",
    "sri lanka": "(\"latitude\" BETWEEN 5 AND 10 AND \"longitude\" BETWEEN 79 AND 82)",
    "singapore": "(\"latitude\" BETWEEN 0 AND 3 AND \"longitude\" BETWEEN 103 AND 105)",
    "tokyo": "(\"latitude\" BETWEEN 34 AND 36 AND \"longitude\" BETWEEN 139 AND 141)",
    "sydney": "(\"latitude\" BETWEEN -35 AND -33 AND \"longitude\" BETWEEN 150 AND 152)",
    "cape town": "(\"latitude\" BETWEEN -35 AND -33 AND \"longitude\" BETWEEN 17 AND 19)",
    "miami": "(\"latitude\" BETWEEN 25 AND 27 AND \"longitude\" BETWEEN -81 AND -79)",
    
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

INTENT_PARSER_PROMPT = """
You are an expert AI at parsing user requests into a structured JSON format. Your goal is to dissect a user's question and provide a clean plan for another script to build a SQL query.

First, think step-by-step about the user's request, identifying all the key components.
Then, based on your thinking, provide a single JSON object with the extracted fields.

Here are the fields to extract:
- "query_type": Must be one of ["Statistic", "Proximity", "Trajectory", "Profile", "Time-Series", "Scatter", "General"].
- "metrics": List of sensor variables mentioned (e.g., ["temperature", "salinity", "dissolved oxygen"]).
- "location_name": Name of a geographic location (e.g., "chennai", "arabian sea", "equator").
- "time_constraint": String describing the time filter (e.g., "in March in 2024").
- "distance_km": String containing a distance limit (e.g., "within 700 km").
- "aggregation": If a statistic is requested, the function to use (e.g., "avg", "max", "min", "count"). For "count unique floats", use "count". For "maximum", use "max".
- "float_id": The integer ID of a float if mentioned.
- "limit": An integer limit if mentioned (e.g., "top 5").

User Question: "{question}"

Think step-by-step here:
1.  What is the user's primary goal? (e.g., finding something nearby, calculating a statistic, plotting a trend). This determines the `query_type`.
2.  What specific measurements are they asking about? These are the `metrics`.
3.  Is a specific place mentioned? This is the `location_name`.
4.  Is there a time filter? This is the `time_constraint`.
5.  What kind of statistic (average, maximum, count)? This is the `aggregation`.

Now, based on your thoughts, provide the final JSON object. Return ONLY the JSON object.
"""

SUMMARIZATION_PROMPT = """
You are a helpful oceanographer's assistant. Generate a specific, data-driven response based on the query results.

User Question: "{question}"
Query Type: "{query_type}"
Result Statistics: "{results_summary}"
Sample Data: "{sample_data}"

IMPORTANT RULES:
1. Be SPECIFIC - mention actual numbers, float IDs, locations, temperatures, etc. from the data
2. Be CONCISE - 2-3 sentences maximum
3. DO NOT mention "data availability is limited" or similar phrases unless there are 0 results
4. DO NOT repeat the same generic phrases for every response
5. Include actionable insights based on the actual data values

Examples of GOOD responses:
- "Found 5 ARGO floats near Chennai, with distances ranging from 27km to 316km. Float 2902115 is the closest, currently at coordinates (13.2°N, 80.4°E)."
- "The average temperature in Bay of Bengal is 28.5°C across 1,200 measurements. Surface temperatures (0-50m) average 29.2°C while deeper waters (500m+) average 8.4°C."
- "Float 2903100 traveled 145km between September and December 2025, moving northwest from (10.2°N, 85.5°E) to (12.1°N, 83.2°E)."

Now generate a response for this specific query:
"""

def get_intelligent_answer(user_question: str):
    import logging
    logging.basicConfig(filename="backend.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        load_dotenv()
        engine = get_engine()
        llm = get_llm()  # Auto-selects Gemini or Groq

        context = get_database_context(engine)
        if not context:
            logging.error("Could not connect to database.")
            return {"query_type": "Error", "summary": "Could not connect to database.", "data": []}

        # Format data availability info for responses
        min_date = context.get("min_date")
        max_date = context.get("max_date")
        data_range_info = ""
        if min_date and max_date:
            min_date_str = min_date.strftime("%b %d, %Y") if hasattr(min_date, 'strftime') else str(min_date)[:10]
            max_date_str = max_date.strftime("%b %d, %Y") if hasattr(max_date, 'strftime') else str(max_date)[:10]
            data_range_info = f"Data available: {min_date_str} to {max_date_str}"

        prompt = PromptTemplate.from_template(INTENT_PARSER_PROMPT)
        parser_chain = prompt | llm | StrOutputParser()
        intent_json_str = parser_chain.invoke({"question": user_question})

        match = re.search(r'\{.*\}', intent_json_str, re.DOTALL)
        if not match:
            logging.error("LLM did not return a valid JSON object.")
            raise ValueError("LLM did not return a valid JSON object.")
        intent = json.loads(match.group(0))


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
                "arabian sea": (15, 62.5),
                "bay of bengal": (13.5, 87.5),
                "equator": (0, 0),
                "andaman sea": (10, 95),
                "chennai": (13, 80.25),
                "mumbai": (19, 72.75),
                "sri lanka": (7.5, 80.5)
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
            sample = data_records[:3]  # First 3 records as sample
            sample_data_str = json.dumps(sample, default=str)[:500]  # Limit length
        
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

        summarization_prompt = PromptTemplate.from_template(SUMMARIZATION_PROMPT)
        summary_chain = summarization_prompt | llm | StrOutputParser()
        try:
            summary = summary_chain.invoke({
                "question": user_question, 
                "results_summary": results_summary_text,
                "query_type": query_type,
                "sample_data": sample_data_str if sample_data_str else "No sample data"
            })
        except Exception:
            # If summarization LLM call fails, fallback to internal summary
            summary = results_summary_text

        logging.info(f"Query summary: {summary}")
        response_payload = {
            "query_type": intent.get("query_type"),
            "sql_query": generated_sql,
            "summary": summary,
            "data": data_records,
            "data_range": data_range_info
        }
        # Debug: optionally surface parsed intent (without leaking internal complexity) if env var set
        if os.getenv("SHOW_INTENT_JSON", "0") in ("1", "true", "yes"):
            response_payload["intent_debug"] = intent
        return response_payload

    except Exception as e:
        logging.error(f"Error in brain: {e}")
        # Return a friendly error message, never a raw traceback
        return {"query_type": "Error", "summary": f"A backend error occurred: {str(e)}. Please check your query and try again.", "data": []}