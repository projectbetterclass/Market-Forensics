# Quick Start Guide

## 🚀 Get Up and Running in 5 Minutes

### Step 1: Start the Backend

```bash
cd C:\Users\Gebruiker\Documents\StockApp\backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python -m app.main
```

✅ Backend running at **http://localhost:8000**
📚 API docs at **http://localhost:8000/docs**

---

### Step 2: Start the Frontend

**Open a new terminal:**

```bash
cd C:\Users\Gebruiker\Documents\StockApp\frontend

# Install dependencies (first time only)
npm install

# Run development server
npm run dev
```

✅ Frontend running at **http://localhost:3000**

---

### Step 3: Try It Out

1. Open **http://localhost:3000** in your browser
2. Enter a ticker (e.g., `AAPL`, `TSLA`, `NVDA`)
3. Select time window (default: 24 hours)
4. Click **"Analyze Drop"**
5. View results in **Chat Answer** or **YouTube Script** mode

---

## 📁 Project Location

Your project is at: `C:\Users\Gebruiker\Documents\StockApp\`

---

## 🧪 Quick Test

**Test the backend directly:**
```bash
curl http://localhost:8000/health
```

Should return: `{"status": "healthy"}`

**Test an analysis:**
```bash
curl -X POST http://localhost:8000/api/analyze ^
  -H "Content-Type: application/json" ^
  -d "{\"ticker\": \"AAPL\", \"time_window_hours\": 24}"
```

---

## 📖 Documentation

- **README.md**: Full setup + features
- **docs/ai-agent-research.md**: Research methodology
- **docs/architecture.md**: System design
- **TESTING.md**: Testing guide

---

## ⚠️ Important Notes

1. **Free Data Sources**: Uses SEC EDGAR (free) and Yahoo Finance (unofficial API)
2. **Rate Limits**: SEC EDGAR has rate limits; don't spam requests
3. **News**: News API is a placeholder (needs API key for production)
4. **Disclaimer**: Not financial advice; educational purposes only

---

## 🎯 What It Does

- **Strict Citations**: Every fact backed by SEC filings or news sources
- **Explicit Probabilities**: Hypotheses ranked with p-values (e.g., p=0.65)
- **Market Context**: Decomposes move into market/sector/company factors
- **Dual Modes**: Chat answer + YouTube-style script (emulates your favorite finance YouTubers)

---

## 🐛 Troubleshooting

**Backend won't start:**
- Check Python version: `python --version` (need 3.11+)
- Activate venv: `venv\Scripts\activate`

**Frontend won't start:**
- Check Node version: `node --version` (need 18+)
- Try: `npm install --legacy-peer-deps`

**"Could not find price data" error:**
- Yahoo Finance API may be rate-limited
- Try a different ticker or wait a minute

**No filings found:**
- Not all tickers have recent SEC filings
- Try larger time window (48-72 hours)

---

## 🎥 Next Steps

1. **Test with real drops**: Find a recent stock drop and analyze it
2. **Read the research doc**: `docs/ai-agent-research.md`
3. **Explore YouTube integration**: See video ingestion plan for future
4. **Add news API**: Get a free NewsAPI key at https://newsapi.org

---

## 📬 Support

Check the main README.md for full documentation and architecture details.
