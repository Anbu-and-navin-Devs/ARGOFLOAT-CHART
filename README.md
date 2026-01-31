<div align="center">

# 🌊 ARGO FloatChart

### AI-Powered Ocean Data Intelligence Platform

*Transform 46 million ARGO float observations into actionable insights through natural language*

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![CockroachDB](https://img.shields.io/badge/CockroachDB-Serverless-6933FF?style=for-the-badge&logo=cockroachlabs&logoColor=white)](https://cockroachlabs.cloud)
[![Groq](https://img.shields.io/badge/Groq-LLama_3.3-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[🚀 Live Demo](https://argofloat-chart-hank.onrender.com) · [📖 Documentation](#-project-architecture) · [🐛 Report Bug](https://github.com/Anbu-Navin-Devs/ARGOFLOAT-CHART/issues)

</div>

---

## 📋 Table of Contents

- [About The Project](#-about-the-project)
- [Key Features](#-key-features)
- [Tech Stack](#%EF%B8%8F-tech-stack)
- [Project Architecture](#-project-architecture)
- [Getting Started](#-getting-started)
- [Local vs Cloud Deployment](#-local-vs-cloud-deployment)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Contributors](#-contributors)
- [Resources](#-resources)
- [License](#-license)

---

## 🎯 About The Project

**ARGO FloatChart** is a sophisticated ocean data intelligence platform that bridges the gap between complex oceanographic datasets and intuitive data exploration. By leveraging advanced AI/LLM capabilities, the platform enables researchers, students, and ocean enthusiasts to query **46+ million ARGO float records** using simple natural language—no SQL or programming knowledge required.

### 🌍 What is ARGO?

The [ARGO Program](https://argo.ucsd.edu) is a global array of **4,000+ autonomous profiling floats** that measure temperature, salinity, and currents in the ocean. These floats drift at depth and surface every 10 days to transmit data via satellite, providing unprecedented insights into ocean dynamics, climate patterns, and marine ecosystems.

### 💡 Why FloatChart?

| Challenge | Our Solution |
|-----------|--------------|
| Raw ARGO data is complex and scattered | Unified database with 46M+ records |
| Requires SQL/programming expertise | Natural language AI interface |
| Difficult to visualize spatial data | Interactive maps & dashboards |
| Time-consuming data analysis | Instant AI-powered insights |
| Limited accessibility for non-experts | User-friendly chat interface |

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🤖 AI-Powered Chat Interface
Ask questions in plain English and receive intelligent responses with data visualizations, statistical insights, and contextual follow-up suggestions.

**Example Queries:**
- *"What's the average temperature in Bay of Bengal?"*
- *"Show floats near Chennai from 2024"*
- *"Compare salinity between Arabian Sea and Indian Ocean"*

</td>
<td width="50%">

### 🗺️ Interactive Ocean Map
Explore float positions worldwide with real-time filtering. Visualize float trajectories, temperature gradients, and proximity searches on an interactive Leaflet.js map.

**Capabilities:**
- Cluster visualization for dense regions
- Distance circle overlays
- Float trajectory tracking

</td>
</tr>
<tr>
<td width="50%">

### 📊 Analytics Dashboard
Comprehensive data visualizations powered by Chart.js. Analyze temperature trends, salinity patterns, and float distribution across oceans and time periods.

**Visualizations:**
- Time-series charts
- Depth profiles
- Statistical summaries

</td>
<td width="50%">

### ⬇️ Data Manager Tool
Download and manage ARGO data directly from ERDDAP servers. Bulk fetch historical data or update with the latest observations through an intuitive web interface.

**Features:**
- Year-wise data fetching
- Progress tracking
- Database statistics

</td>
</tr>
</table>

### 🧠 Professional AI Output System

Our advanced AI system provides structured, data-driven responses:

| Component | Description |
|-----------|-------------|
| **Structured Insights** | Statistical summaries, key metrics, and data highlights |
| **Smart Visualizations** | AI recommends optimal chart types based on query context |
| **Contextual Suggestions** | Follow-up query recommendations for deeper exploration |
| **Data Provenance** | Source attribution and processing metadata |

---

## 🛠️ Tech Stack

<table>
<tr>
<th>Category</th>
<th>Technology</th>
<th>Purpose</th>
</tr>
<tr>
<td><strong>Backend</strong></td>
<td>

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![Gunicorn](https://img.shields.io/badge/Gunicorn-499848?style=flat&logo=gunicorn&logoColor=white)

</td>
<td>Server, API routing, request handling</td>
</tr>
<tr>
<td><strong>AI/LLM</strong></td>
<td>

![Groq](https://img.shields.io/badge/Groq-F55036?style=flat&logo=groq&logoColor=white)

</td>
<td>Natural language processing, intent parsing, response generation</td>
</tr>
<tr>
<td><strong>Database</strong></td>
<td>

![CockroachDB](https://img.shields.io/badge/CockroachDB-6933FF?style=flat&logo=cockroachlabs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)

</td>
<td>Cloud (CockroachDB) & Local (PostgreSQL) data storage</td>
</tr>
<tr>
<td><strong>Frontend</strong></td>
<td>

![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)

</td>
<td>User interface, responsive design, interactivity</td>
</tr>
<tr>
<td><strong>Visualization</strong></td>
<td>

![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=flat&logo=chartdotjs&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=flat&logo=leaflet&logoColor=white)

</td>
<td>Charts, graphs, interactive maps</td>
</tr>
<tr>
<td><strong>Deployment</strong></td>
<td>

![Render](https://img.shields.io/badge/Render-46E3B7?style=flat&logo=render&logoColor=white)

</td>
<td>Cloud hosting, CI/CD, SSL</td>
</tr>
</table>

---

## 📐 Project Architecture

```
ARGOFLOAT-CHART/
│
├── 📁 ARGO_CHATBOT/                 # Main Chat Application
│   ├── app.py                       # Flask server & API endpoints
│   ├── brain.py                     # AI logic, insights, recommendations
│   ├── sql_builder.py               # Dynamic SQL generation & optimization
│   ├── gunicorn.conf.py             # Production server configuration
│   ├── requirements.txt             # App-specific dependencies
│   └── 📁 static/
│       ├── index.html               # Chat interface
│       ├── map.html                 # Interactive map view
│       ├── dashboard.html           # Analytics dashboard
│       ├── 📁 css/styles.css        # Application styling
│       └── 📁 js/app.js             # Frontend logic & rendering
│
├── 📁 DATA_GENERATOR/               # Data Management Tool
│   ├── app.py                       # Data manager web interface
│   ├── data_manager.py              # ERDDAP data fetching API
│   ├── database_utils.py            # Database CRUD operations
│   ├── bulk_fetch.py                # CLI bulk data fetcher
│   └── 📁 static/index.html         # Data manager UI
│
├── requirements.txt                 # Global Python dependencies
├── local_setup.py                   # One-click local setup wizard
├── Procfile                         # Render deployment config
├── LICENSE                          # MIT License
└── README.md                        # Project documentation
```

### 🔄 Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ERDDAP API    │───▶│  DATA_GENERATOR │───▶│   Database      │
│  (ARGO Source)  │    │  (ETL Pipeline) │    │ (CockroachDB/   │
└─────────────────┘    └─────────────────┘    │  PostgreSQL)    │
                                              └────────┬────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     User        │◀──▶│  ARGO_CHATBOT   │◀──▶│    Groq AI      │
│  (Web Browser)  │    │  (Flask + API)  │    │  (LLM Engine)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+** - [Download](https://python.org/downloads)
- **PostgreSQL** (for local) - [Download](https://postgresql.org/download) *or*
- **CockroachDB account** (for cloud) - [Sign up FREE](https://cockroachlabs.cloud)
- **Groq API Key** (FREE) - [Get key](https://console.groq.com/keys)

### ⚡ Quick Start (3 Steps)

```bash
# 1️⃣ Clone the repository
git clone https://github.com/Anbu-Navin-Devs/ARGOFLOAT-CHART.git
cd ARGOFLOAT-CHART

# 2️⃣ Run the setup wizard
python local_setup.py

# 3️⃣ Start the application
cd ARGO_CHATBOT
python app.py
```

🎉 **That's it!** Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🏠 Local vs Cloud Deployment

Choose the deployment strategy that fits your needs:

<table>
<tr>
<th width="50%">🏠 Local Development</th>
<th width="50%">☁️ Cloud Production</th>
</tr>
<tr>
<td>

**Database:** PostgreSQL (Local)

**Best For:**
- 🔬 Research & experimentation
- 📊 Full dataset exploration (46M+ records)
- ⚡ Maximum query performance
- 🔒 Sensitive data handling

**Advantages:**
- ✅ Unlimited storage (based on disk)
- ✅ Zero network latency
- ✅ Complete data privacy
- ✅ No cloud costs

**Setup:**
```bash
# Install PostgreSQL locally
psql -U postgres
CREATE DATABASE floatchart;
\q

python local_setup.py
```

</td>
<td>

**Database:** CockroachDB Serverless

**Best For:**
- 🌐 Public demos & presentations
- 👥 Team collaboration
- 📱 Access from anywhere
- 🚀 Quick deployment

**Advantages:**
- ✅ No infrastructure management
- ✅ Auto-scaling & high availability
- ✅ 10GB free tier
- ✅ Built-in SSL security

**Setup:**
```bash
# Create account at cockroachlabs.cloud
# Get connection string
# Deploy to Render/Heroku
```

</td>
</tr>
<tr>
<td>

**Environment Variables:**
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/floatchart
GROQ_API_KEY=gsk_your_key_here
```

</td>
<td>

**Environment Variables:**
```env
DATABASE_URL=cockroachdb://user:pass@host:26257/db?sslmode=require
GROQ_API_KEY=gsk_your_key_here
```

</td>
</tr>
</table>

### 📊 Comparison Matrix

| Feature | Local (PostgreSQL) | Cloud (CockroachDB) |
|---------|-------------------|---------------------|
| **Storage Limit** | Unlimited (disk-based) | 10GB (free tier) |
| **Query Speed** | ⚡⚡⚡ Fastest | ⚡⚡ Fast |
| **Network Required** | ❌ No | ✅ Yes |
| **Setup Complexity** | Medium | Easy |
| **Cost** | Free | Free (10GB) |
| **Accessibility** | Local only | Anywhere |
| **Data Records** | 46M+ possible | ~5-10M recommended |
| **Best Use Case** | Research | Demo/Production |

---

## ⚙️ Configuration

### 🔑 API Keys Setup

#### Groq AI (Required - 100% FREE!)

1. Visit [console.groq.com/keys](https://console.groq.com/keys)
2. Sign up with Google/GitHub (30 seconds)
3. Click **"Create API Key"**
4. Copy and add to `.env` file

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

**Why Groq?**
| Benefit | Details |
|---------|---------|
| 💰 **Price** | FREE forever, no credit card |
| ⚡ **Speed** | ~500 tokens/second |
| 🧠 **Model** | Llama 3.3 70B |
| 📊 **Limits** | 14,400 requests/day |

---

## 📖 Usage

### 💬 Chat Interface

Access the main chat at [http://localhost:5000](http://localhost:5000)

**Example Queries:**

| Query Type | Example |
|------------|---------|
| **Proximity** | *"Show floats near Mumbai"* |
| **Statistics** | *"What's the average temperature in Arabian Sea?"* |
| **Temporal** | *"Floats from January 2024"* |
| **Comparison** | *"Compare Bay of Bengal vs Indian Ocean salinity"* |
| **Trajectory** | *"Track float 2900757"* |

### 🗺️ Interactive Map

Access at [http://localhost:5000/map](http://localhost:5000/map)

- Click clusters to zoom into regions
- Click individual floats for details
- Use filters to narrow by date/location

### 📊 Dashboard

Access at [http://localhost:5000/dashboard](http://localhost:5000/dashboard)

- View temperature/salinity trends
- Analyze depth profiles
- Export visualizations

### 📥 Data Manager

```bash
cd DATA_GENERATOR
python app.py  # Web interface at :5001
```

Or use CLI:
```bash
python bulk_fetch.py --fetch-all          # All historical data
python bulk_fetch.py --fetch-year 2024    # Specific year
python bulk_fetch.py --stats              # Database statistics
```

---

## 👥 Contributors

<div align="center">

<table>
<tr>
<td align="center" width="300">
<a href="https://github.com/Anbu-2006">
<img src="https://github.com/Anbu-2006.png" width="120px;" style="border-radius:50%;" alt="Anbuselvan T"/>
<br />
<h3>Anbuselvan T</h3>
</a>
<p><strong>🧠 AI & Data Engineer</strong></p>
<a href="https://github.com/Anbu-2006">
<img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"/>
</a>
</td>
<td align="center" width="300">
<a href="https://github.com/navin18-cmd">
<img src="https://github.com/navin18-cmd.png" width="120px;" style="border-radius:50%;" alt="Navin"/>
<br />
<h3>Navin</h3>
</a>
<p><strong>🎨 Frontend Developer</strong></p>
<a href="https://github.com/navin18-cmd">
<img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"/>
</a>
</td>
</tr>
</table>

</div>

### 📝 Detailed Contributions

<table>
<tr>
<th width="200">Contributor</th>
<th width="180">Role</th>
<th>Work Done</th>
</tr>
<tr>
<td>
<a href="https://github.com/Anbu-2006">
<img src="https://github.com/Anbu-2006.png" width="40" style="border-radius:50%;vertical-align:middle;"/> 
<strong>Anbuselvan T</strong>
</a>
</td>
<td><strong>AI & Data Engineer</strong></td>
<td>
◆ AI/LLM integration with Groq & smart query routing<br>
◆ Database architecture design (CockroachDB)<br>
◆ Data pipeline development (ERDDAP → Database)<br>
◆ Backend logic, API design & SQL query builder<br>
◆ Query optimization with bounding box filtering<br>
◆ Professional AI output system (insights, recommendations)<br>
◆ Data Manager tool development
</td>
</tr>
<tr>
<td>
<a href="https://github.com/navin18-cmd">
<img src="https://github.com/navin18-cmd.png" width="40" style="border-radius:50%;vertical-align:middle;"/>
<strong>Navin</strong>
</a>
</td>
<td><strong>Frontend Developer</strong></td>
<td>
◆ Chat interface UI/UX design<br>
◆ Interactive Leaflet.js map implementation<br>
◆ Dashboard visualizations with Chart.js<br>
◆ CSS styling & responsive design<br>
◆ User experience optimization<br>
◆ Frontend rendering for AI insights<br>
◆ Data Manager UI design
</td>
</tr>
</table>

---

## 🔗 Resources & References

| Resource | Description |
|----------|-------------|
| [🌊 ARGO Program](https://argo.ucsd.edu) | Global ocean observation network |
| [📡 ERDDAP Server](https://erddap.ifremer.fr) | ARGO data distribution service |
| [🗄️ CockroachDB](https://cockroachlabs.cloud) | Serverless distributed database |
| [🧠 Groq Console](https://console.groq.com) | AI/LLM API provider |
| [🐍 Flask Documentation](https://flask.palletsprojects.com) | Python web framework |
| [📊 Chart.js](https://chartjs.org) | JavaScript charting library |
| [🗺️ Leaflet.js](https://leafletjs.com) | Interactive map library |

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License - Free to use, modify, and distribute with attribution.
```

---

<div align="center">

### ⭐ Star this repository if you found it helpful!

<br>

**Built with ❤️ by [Anbuselvan T](https://github.com/Anbu-2006) & [Navin](https://github.com/navin18-cmd)**

<br>

[![GitHub Stars](https://img.shields.io/github/stars/Anbu-Navin-Devs/ARGOFLOAT-CHART?style=social)](https://github.com/Anbu-Navin-Devs/ARGOFLOAT-CHART)
[![GitHub Forks](https://img.shields.io/github/forks/Anbu-Navin-Devs/ARGOFLOAT-CHART?style=social)](https://github.com/Anbu-Navin-Devs/ARGOFLOAT-CHART)

</div>
