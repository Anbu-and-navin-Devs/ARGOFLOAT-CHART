# 🌊 FloatChart

**AI-Powered Ocean Data Intelligence** - Chat with 46 million ARGO float records using natural language.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Flask](https://img.shields.io/badge/Flask-2.0+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- 🤖 **AI Chat** - Ask questions about ocean data in natural language
- 🧠 **Smart AI Routing** - Groq for fast queries, DeepSeek for complex analysis
- 🗺️ **Interactive Map** - Explore float positions worldwide
- 📊 **Dashboard** - Visualize temperature, salinity trends
- ⬇️ **Data Manager** - Download ARGO data from ERDDAP servers

## � Team

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/Anbu-2006">
        <img src="https://github.com/Anbu-2006.png" width="100px;" alt="Anbuselvan T"/>
        <br />
        <sub><b>Anbuselvan T</b></sub>
      </a>
      <br />
      <sub>🧠 AI & Backend</sub>
    </td>
    <td align="center">
      <a href="https://github.com/navin18-cmd">
        <img src="https://github.com/navin18-cmd.png" width="100px;" alt="Navin"/>
        <br />
        <sub><b>Navin</b></sub>
      </a>
      <br />
      <sub>🎨 Frontend</sub>
    </td>
  </tr>
</table>

### Contributions

| Contributor | Role | Work Done |
|-------------|------|-----------|
| **[Anbuselvan T](https://github.com/Anbu-2006)** | AI & Data Engineer | 🔹 AI/LLM integration & smart routing<br>🔹 Database architecture (CockroachDB)<br>🔹 Data pipeline (ERDDAP → DB)<br>🔹 Backend logic & SQL builder<br>🔹 Data Manager tool |
| **[Navin](https://github.com/navin18-cmd)** | Frontend Developer | 🔹 Chat interface UI<br>🔹 Interactive map design<br>🔹 Dashboard visualizations<br>🔹 CSS styling & responsiveness<br>🔹 User experience design |

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/Anbu-Navin-Devs/ARGOFLOAT-CHART.git
cd ARGOFLOAT-CHART

# Run setup
python local_setup.py

# Edit credentials in .env (created at project root)

# Start the chat app
cd ARGO_CHATBOT
python app.py
# → Opens at http://localhost:5000
```

## 🧠 Smart AI Routing

FloatChart uses intelligent query routing for the best experience:

| Query Type | AI Used | Why |
|------------|---------|-----|
| "Hi", "Hello", "Help" | **Groq ⚡** | Lightning fast responses |
| Simple questions | **Groq ⚡** | Speed matters |
| Ocean data queries | **DeepSeek 🧠** | Excellent reasoning |
| Complex analysis | **DeepSeek 🧠** | Reliable accuracy |

### 🔑 Getting FREE API Keys

**1. DeepSeek (Recommended - Best for ocean queries)**
   - Go to: https://platform.deepseek.com/api_keys
   - Sign up (email + phone verification)
   - Click "Create API Key"
   - Copy the key → Add to `.env` as `DEEPSEEK_API_KEY`

**2. Groq (Recommended - Fast for simple queries)**
   - Go to: https://console.groq.com/keys
   - Sign up with Google/GitHub
   - Click "Create API Key"
   - Copy the key → Add to `.env` as `GROQ_API_KEY`

**💡 Both are FREE with generous limits!**

## 📂 Project Structure

```
FloatChart/
├── ARGO_CHATBOT/          # Chat Application
│   ├── app.py             # Flask server
│   ├── brain.py           # AI query logic (smart routing)
│   ├── sql_builder.py     # SQL generation
│   └── static/            # Web UI (HTML, CSS, JS)
│
├── DATA_GENERATOR/        # Data Management
│   ├── app.py             # Web-based data manager
│   ├── data_manager.py    # Data fetch API
│   ├── database_utils.py  # Database operations
│   ├── bulk_fetch.py      # CLI bulk fetcher
│   └── static/            # Data manager UI
│
├── requirements.txt       # Python dependencies
├── local_setup.py         # One-click setup
└── .env.example           # Configuration template
```

## 🔧 Configuration

### 🏠 Local Development (PostgreSQL - UNLIMITED Storage!)

```bash
# 1. Install PostgreSQL: https://www.postgresql.org/download/
# 2. Create database:
psql -U postgres
CREATE DATABASE floatchart;
\q

# 3. Run setup
python local_setup.py

# 4. Edit .env at project root:
```

```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/floatchart
DEEPSEEK_API_KEY=your_deepseek_key
GROQ_API_KEY=your_groq_key
```

**✅ Benefits of Local PostgreSQL:**
- 📦 **Unlimited storage** - Download ALL ARGO data (46M+ records)
- ⚡ **Faster queries** - Local = no network latency
- 💰 **100% Free** - No cloud limits

### ☁️ Cloud Deployment (CockroachDB - 10GB Free)

For Render/cloud deployment, use `ARGO_CHATBOT/.env`:

```env
DATABASE_URL=postgresql://user:pass@host:26257/db?sslmode=verify-full
DEEPSEEK_API_KEY=your_deepseek_key
GROQ_API_KEY=your_groq_key
```

**Note:** CockroachDB has 10GB free tier - suitable for demo/production with limited data.

| Environment | Database | Storage | Best For |
|-------------|----------|---------|----------|
| **Local** | PostgreSQL | based on user 
storage| Full data exploration |
| **Cloud** | CockroachDB | 10GB | Demo, production |

## 📥 Getting Data

### Option 1: Web Interface
```bash
cd DATA_GENERATOR
python app.py
# → Opens at http://localhost:5001
```

### Option 2: Command Line
```bash
cd DATA_GENERATOR
python bulk_fetch.py --fetch-all          # All data from 2002
python bulk_fetch.py --fetch-year 2024    # Specific year
python bulk_fetch.py --stats              # Database stats
```

## 🖥️ Running the Apps

### Chat App (Main Interface)
```bash
cd ARGO_CHATBOT
python app.py
```
- **http://localhost:5000** - Chat Interface
- **http://localhost:5000/map** - Interactive Map
- **http://localhost:5000/dashboard** - Analytics

### Data Manager
```bash
cd DATA_GENERATOR
python app.py
```
- **http://localhost:5001** - Data Management UI

## 💬 Example Queries

- "What's the average temperature in Bay of Bengal?"
- "Show me floats near Chennai from 2024"
- "Compare salinity between Arabian Sea and Indian Ocean"
- "How many floats are active this month?"

## 🔗 Resources

- [ARGO Program](https://argo.ucsd.edu) - Global ocean observation
- [CockroachDB](https://cockroachlabs.cloud) - Free 10GB database
- [DeepSeek](https://platform.deepseek.com) - Free AI (excellent reasoning)
- [Groq](https://console.groq.com) - Free AI (lightning fast)
- [ERDDAP](https://erddap.ifremer.fr) - ARGO data source

## 📄 License

MIT License - feel free to use and modify!

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/Anbu-2006">Anbuselvan T</a> & <a href="https://github.com/navin18-cmd">Navin</a>
</p>
