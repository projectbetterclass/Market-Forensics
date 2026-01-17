# Market Forensics

**Prepare, don't predict. Recognize patterns. Understand context.**

A forensic analysis tool for understanding stock price movements through historical pattern recognition and evidence-based analysis.

## Features

- 📊 **Price Pattern Matching**: Find similar historical patterns in price movements
- 🔍 **Evidence Curation**: Validated, classified, and scored news sources
- 📈 **Market State Analysis**: Track key market indicators and cycles
- 🎯 **Forensic Reports**: Institutional-grade analysis reports
- ⚖️ **No Predictions**: Focus on understanding context, not forecasting

## Tech Stack

- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.10+
- **Data Sources**: Yahoo Finance, GDELT News, Market Indicators

## Local Development

### Backend

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
python -m app.main
```

Backend runs on `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`

## Deployment

- **Frontend**: Vercel
- **Backend**: Render, Fly.io, or Railway
- Connect via `NEXT_PUBLIC_API_URL` environment variable

## Philosophy

This tool helps you recognize risk and understand market context. It does not predict future movements or provide investment advice.

## License

MIT
