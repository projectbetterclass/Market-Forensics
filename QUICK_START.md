# Stock Drop Forensic Analysis - Quick Start

## Prerequisites

Ensure you have installed:
- Python 3.10+ (with pip)
- Node.js 18+ (with npm)

## First Time Setup

### 1. Backend Setup
```bash
cd C:\Users\Gebruiker\Documents\StockApp\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Frontend Setup
```bash
cd C:\Users\Gebruiker\Documents\StockApp\frontend
npm install
```

## Running the Application

### Terminal 1: Backend
```bash
cd C:\Users\Gebruiker\Documents\StockApp\backend
.\venv\Scripts\Activate.ps1
python -m app.main
```

✅ Backend will run on **http://localhost:8000**

### Terminal 2: Frontend
```bash
cd C:\Users\Gebruiker\Documents\StockApp\frontend
npm run dev
```

✅ Frontend will run on **http://localhost:3000**

### Terminal 3 (Optional): MCP Server
```bash
cd C:\Users\Gebruiker\Documents\StockApp\mcp_server
python main.py
```

✅ MCP server will run on **http://localhost:8001**

## Verify Installation

1. Open **http://localhost:3000** in your browser
2. You should see the onboarding modal
3. After dismissing it, search for a ticker (e.g., AAPL)
4. Chart should load
5. Click two points on the chart to analyze

## Health Checks

- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Cache stats: http://localhost:8000/api/cache/stats

## Troubleshooting

### "Python not found"
- Ensure Python is installed and in PATH
- Restart your terminal after installation

### "npm not found"
- Ensure Node.js is installed
- Restart your terminal after installation

### "Port 8000 already in use"
- Kill any existing Python processes
- Or change port in `backend/app/config.py`

### "Port 3000 already in use"
- Kill any existing Node processes
- Or run `npm run dev -- -p 3001`

### "Failed to fetch chart data"
- Check backend is running
- Wait 60s if hitting Yahoo Finance rate limits
- Check network connection

## Next Steps

1. Read `HOW_TO_USE.md` for detailed user guide
2. Read `PROJECT_CONTEXT.md` for architecture overview
3. Read `IMPLEMENTATION_SUMMARY.md` for technical details
4. Read `CHANGELOG.md` for version history

## Philosophy Reminder

**Prepare, Don't Predict**

This tool helps you recognize patterns and understand context. It does NOT predict market direction or recommend actions.

Enjoy exploring! 🚀
