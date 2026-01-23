# 🌊 FloatChart

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**Query ocean data using plain English.**

[Live Demo](https://argofloat-chart.onrender.com) · [Report Bug](https://github.com/Anbu-2006/ARGOFLOAT-CHART/issues) · [Request Feature](https://github.com/Anbu-2006/ARGOFLOAT-CHART/issues)

</div>

---

## About

FloatChart lets you explore ARGO float oceanographic data through natural language queries. Instead of writing complex SQL, just ask questions like *"What's the average temperature in the Bay of Bengal?"* and get instant visualizations.

**What are ARGO floats?** They're autonomous instruments drifting across the world's oceans, diving to 2000m depth to measure temperature, salinity, and pressure. Over 4,000 are currently deployed, generating millions of data points for climate research.

---

## Demo

**→ [argofloat-chart.onrender.com](https://argofloat-chart.onrender.com)**

The demo includes 1.5M+ records covering global oceans from 2020-2026.

> **Note:** The demo runs on Render's free tier, so there may be a ~30s cold start delay if the server has been idle.

---

## Cloud vs Local

| | Cloud Demo | Run Locally |
|---|:---:|:---:|
| **Setup required** | None | 10-15 min |
| **Data** | Static snapshot (2020-2026) | Fetch anytime from ERDDAP |
| **Update data** | ❌ | ✅ |
| **Custom regions** | ❌ | ✅ Any ocean region |
| **Database limit** | 500MB (Supabase free) | Unlimited |
| **Best for** | Quick exploration | Research, custom data |

**Why run locally?**
- Fetch real-time ARGO data from any ocean region
- No storage limits — load millions of records
- Update data anytime using the GUI or CLI tools
- Full control over your database

---

## Features

- **Natural language queries** — Ask questions in plain English
- **Interactive maps** — Visualize float positions and trajectories
- **Multiple chart types** — Time series, scatter plots, depth profiles
- **Voice input** — Speak your queries (Chrome/Edge)
- **Dark/Light themes** — Easy on the eyes
- **Keyboard shortcuts** — Press `?` to see all shortcuts
- **Export data** — Download as CSV or JSON
- **Works offline** — Installable as a PWA

---

## Quick Start

### Option 1: Use the Demo

Just visit [argofloat-chart.onrender.com](https://argofloat-chart.onrender.com) — no setup needed.

### Option 2: Run Locally

**Prerequisites:** Python 3.10+, PostgreSQL 14+

#### Step 1: Clone and setup

```bash
# Clone the repo
git clone https://github.com/Anbu-2006/ARGOFLOAT-CHART.git
cd ARGOFLOAT-CHART
```

#### Step 2: Create PostgreSQL database

```sql
-- In psql or pgAdmin
CREATE DATABASE argo_db;
```

#### Step 3: Setup environment

```bash
cd ARGO_CHATBOT

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

Edit `.env` with your settings:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/argo_db
GROQ_API_KEY=your_groq_api_key  # Free at groq.com
```

#### Step 4: Initialize database and fetch data

```bash
cd ../DATA_GENERATOR
pip install -r requirements.txt

# Setup database tables
python setup_local_db.py

# Fetch ARGO data (choose one):
python fetch_argo_data.py --region "Bay of Bengal" --days 30
# OR use the GUI:
python gui.py
```

#### Step 5: Run the web app

```bash
cd ../ARGO_CHATBOT
python app.py
```

Open [localhost:5000](http://localhost:5000) in your browser.

---

## Fetching Data (Local Only)

The `DATA_GENERATOR` folder contains tools to fetch real ARGO data from NOAA's ERDDAP server.

### Using the GUI

```bash
cd DATA_GENERATOR
python gui.py
```

A desktop window opens where you can:
- Select ocean regions (Bay of Bengal, Arabian Sea, etc.)
- Choose date ranges
- Preview and download data
- Automatically load into your database

### Using the CLI

```bash
# Fetch from a specific region
python fetch_argo_data.py --region "Arabian Sea" --days 60

# Fetch from multiple regions
python fetch_argo_data.py --regions "Bay of Bengal" "Arabian Sea" --days 30

# Fetch all available regions
python fetch_argo_data.py --all-regions --days 7
```

### Supported Regions

| Region | Coverage |
|--------|----------|
| Bay of Bengal | 5-22°N, 80-95°E |
| Arabian Sea | 5-25°N, 50-75°E |
| Indian Ocean | 40°S-25°N, 30-120°E |
| Pacific Ocean | 60°S-60°N, 100-180°E |
| Atlantic Ocean | 60°S-60°N, 80°W-0° |
| Mediterranean Sea | 30-46°N, 6°W-36°E |
| Caribbean Sea | 10-22°N, 88-60°W |

---

## Configuration

Create a `.env` file in the `ARGO_CHATBOT` folder:

```env
# Database (required)
DATABASE_URL=postgresql://user:password@localhost:5432/argo_db

# AI Provider (at least one required)
GROQ_API_KEY=your_key_here
# or
OPENAI_API_KEY=your_key_here
# or
GOOGLE_API_KEY=your_key_here
```

The app supports multiple LLM providers and will automatically use whichever key you provide.

---

## Project Structure

```
ARGOFLOAT-CHART/
├── ARGO_CHATBOT/           # Web application
│   ├── app.py              # Flask server
│   ├── brain.py            # AI query processing
│   ├── sql_builder.py      # SQL generation
│   ├── requirements.txt
│   └── static/             # Frontend assets
│       ├── index.html
│       ├── css/
│       └── js/
│
└── DATA_GENERATOR/         # Tools for fetching ARGO data
    ├── gui.py              # Desktop GUI
    ├── fetch_argo_data.py  # CLI tool
    └── setup_local_db.py   # Database setup
```

---

## Sample Queries

Try these in the app:

| Type | Example |
|------|---------|
| **Location** | "Show floats near Chennai" |
| **Statistics** | "Average temperature in Arabian Sea" |
| **Time-based** | "Temperature trends in 2024" |
| **Specific float** | "Trajectory of float 2902115" |
| **Comparison** | "Salinity vs temperature in Bay of Bengal" |

---

## API

The app exposes a simple REST API:

```
GET  /api/status          # Health check
POST /api/query           # Natural language query
GET  /api/nearest_floats  # Find floats near coordinates
GET  /api/float_trajectory/<id>  # Get float path
```

Example:
```bash
curl -X POST https://argofloat-chart.onrender.com/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "average temperature in indian ocean"}'
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + Enter` | Send query |
| `Ctrl + K` | Command palette |
| `Ctrl + D` | Toggle theme |
| `Ctrl + E` | Export data |
| `?` | Show all shortcuts |

---

## Deployment

### Render (Recommended)

Best free platform for Flask apps — already configured!

**Step 1: Create Render Account**
1. Go to [render.com](https://render.com) → Sign up with GitHub
2. Authorize Render to access your repos

**Step 2: Create Web Service**
1. Click **New** → **Web Service**
2. Connect your GitHub repo: `ARGOFLOAT-CHART`
3. Configure:
   - **Name**: `floatchart`
   - **Root Directory**: `ARGO_CHATBOT`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`

**Step 3: Add Environment Variables**
Go to **Environment** → Add:
```
DATABASE_URL = your_supabase_connection_string
GROQ_API_KEY = your_groq_api_key
```

**Step 4: Deploy**
- Click **Create Web Service**
- Wait ~3-5 minutes for build
- Your app: `https://floatchart.onrender.com`

> **Tip:** Free tier sleeps after 15 min idle. Use [UptimeRobot](https://uptimerobot.com) to ping every 5 min and prevent cold starts.

---

### Alternative Platforms

<details>
<summary><strong>🎓 GitHub Student Pack (Premium Free)</strong></summary>

If you have a student email (.edu, .ac.in):
1. Go to [education.github.com/pack](https://education.github.com/pack)
2. Get verified → Unlock:
   - **Railway**: $5/month free credits
   - **DigitalOcean**: $200 credits
   - **Azure**: $100 credits

</details>

<details>
<summary><strong>Hugging Face Spaces</strong></summary>

1. [huggingface.co/new-space](https://huggingface.co/new-space)
2. Select **Docker** SDK
3. Upload files and add secrets
4. Auto-deploys on push

</details>

---

### Platform Comparison

| Platform | Card Required | Cold Start | Performance | Best For |
|----------|--------------|------------|-------------|----------|
| **Render** | ❌ No | ~30s* | ⭐⭐⭐⭐ | Everyone |
| **Railway (Student)** | ❌ No | None | ⭐⭐⭐⭐⭐ | Students |
| **Hugging Face** | ❌ No | ~10s | ⭐⭐⭐ | Quick demos |

*With UptimeRobot, cold start is eliminated

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, Flask, SQLAlchemy |
| AI | LangChain + Groq/OpenAI/Gemini |
| Database | PostgreSQL (Supabase for cloud) |
| Frontend | Vanilla JS, Leaflet.js, Chart.js |
| Data Source | NOAA ERDDAP |

---

## Known Limitations

- **Demo data is static** — The live demo uses a snapshot of ARGO data
- **GPS accuracy** — Some float markers may appear near coastlines due to ~10-50m GPS error
- **Cold starts** — Free tier hosting has idle timeouts

For real-time data updates, run locally with the DATA_GENERATOR tools.

---

## Contributing

Contributions welcome! Feel free to:

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Open a pull request

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [ARGO Program](https://argo.ucsd.edu/) for the ocean observation network
- [ERDDAP](https://coastwatch.pfeg.noaa.gov/erddap/) for data access
- [Groq](https://groq.com/) for fast LLM inference

---

<div align="center">

Built by [@Anbu-2006](https://github.com/Anbu-2006)

If this helped you, consider giving it a ⭐

</div>
