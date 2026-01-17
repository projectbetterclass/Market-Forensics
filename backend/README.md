# Stock Drop Forensic Analysis - Backend

## Philosophy: Prepare, Don't Predict

This backend provides forensic analysis of stock price movements using:
- Historical pattern recognition
- Evidence-based hypothesis generation
- Market regime and context analysis
- **Strict guardrails**: No predictions, no advice

## Setup

### Prerequisites
- Python 3.10+
- pip

### Installation

1. Create virtual environment:
```bash
python -m venv venv
```

2. Activate virtual environment:
- Windows: `.\venv\Scripts\Activate.ps1`
- Linux/Mac: `source venv/bin/activate`

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Server

```bash
cd backend
python -m app.main
```

Server will start on `http://localhost:8000`

API docs available at `http://localhost:8000/docs`

## Architecture

- **FastAPI** framework
- **Pydantic** schemas with strict validation
- **SWR caching** (60s chart data, 5-10min context)
- **Evidence-driven**: every fact tied to a source

## Key Endpoints

- `GET /api/chart/{ticker}` - Historical price data
- `POST /api/analyze-range` - Analyze a selected date range
- `GET /api/context/regime` - Market regime (Stage 1-4)
- `GET /api/context/valuation` - CAPE/Buffett/breadth
- `GET /api/context/crowd` - Crowd behavior indicators
- `GET /api/context/rotation` - Sector rotation
- `POST /api/pattern/analogs` - Find historical analogs
- `GET /api/cache/stats` - Cache performance

## Language Guardrails

The renderer enforces forbidden phrases:
- ❌ "crash coming", "guaranteed", "should buy/sell"
- ✅ "historically", "associated with", "outcomes varied"

## Data Sources

- Yahoo Finance (prices, splits, dividends)
- SEC EDGAR (filings) - placeholder, needs ticker→CIK mapping
- GDELT (news)
- FRED (macro) - placeholder, needs API key
- Shiller data (CAPE) - placeholder
- Wilshire/FRED (Buffett Indicator) - placeholder

## Development

### Adding a new data source

1. Create client in `app/retrieval/`
2. Return list of `Evidence` objects
3. Call from `routes.py`
4. Add to MCP server (optional)

### Adding a new context panel

1. Create analyzer in `app/context/`
2. Define Pydantic schema in `app/models/schemas.py`
3. Add endpoint in `routes.py`
4. Include in `AnalysisFullResponse`

## License

[Your License]
