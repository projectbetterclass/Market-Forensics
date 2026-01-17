# IMPLEMENTATION SUMMARY

## Technical Architecture

### Backend (FastAPI)

**Entry Point:** `backend/app/main.py`
- FastAPI app with CORS middleware
- Routes included from `app.api.routes`
- Health check at `/health`
- API docs at `/docs`

**API Routes:** `backend/app/api/routes.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chart/{ticker}` | GET | Fetch historical chart data (SWR cached, 60s) |
| `/api/analyze-range` | POST | Analyze a selected date range |
| `/api/analyze` | POST | Legacy endpoint (time window → date range) |
| `/api/context/regime` | GET | Current market regime (Stage 1-4) |
| `/api/context/valuation` | GET | Valuation stress (CAPE/Buffett/breadth) |
| `/api/context/crowd` | GET | Crowd behavior indicators |
| `/api/context/rotation` | GET | Sector rotation context |
| `/api/pattern/analogs` | POST | Find pattern analogs |
| `/api/cache/stats` | GET | Cache performance stats |

**Data Flow (analyze-range):**

1. Parse request → timezone-aware datetimes
2. Fetch price data (Yahoo Finance)
3. Check corporate actions (splits/dividends)
4. Abort if split pattern detected
5. Analyze market context (S&P 500, sector, peers)
6. Retrieve evidence in ±10 day window:
   - SEC filings (`edgar.py`)
   - News (`news.py` via GDELT)
   - Macro (`macro.py` via FRED)
7. Generate hypotheses (`hypothesis.py`)
   - Cluster evidence by type
   - Create hypothesis from each cluster
   - Score using 5-factor rubric:
     - Timing (30%)
     - Authority (25%)
     - Specificity (20%)
     - Magnitude (15%)
     - Corroboration (10%)
   - Rank by score
8. Build timeline (chronological evidence)
9. Fetch context panels:
   - Regime (`regime.py`)
   - Valuation (`valuation.py`)
   - Crowd (`crowd.py`)
   - Rotation (`rotation.py`)
10. Find pattern analogs (`analog_search.py`)
    - Sliding window on historical data
    - Cosine similarity on returns
    - Calculate multi-horizon outcomes
11. Render response (`renderer.py`)
    - Build chat answer + script
    - Apply language guardrails (forbidden phrase check)
12. Return `AnalysisFullResponse`

**Key Modules:**

- **`normalizer.py`**: Validates events, checks for splits
- **`market_context.py`**: Analyzes market/sector/peer, classifies move type
- **`hypothesis.py`**: Generates + scores hypotheses, builds timeline
- **`renderer.py`**: Renders responses, enforces guardrails
- **`prices.py`**: Yahoo Finance client with SWR cache
- **`edgar.py`**: SEC EDGAR client (placeholder, needs CIK mapping)
- **`news.py`**: GDELT news client
- **`macro.py`**: FRED macro client (placeholder, needs API key)
- **`valuation.py`**: CAPE/Buffett/breadth providers (placeholders)
- **`regime.py`**: Market regime analyzer (simplified)
- **`crowd.py`**: Crowd behavior analyzer (mostly unavailable markers)
- **`rotation.py`**: Sector rotation analyzer (uses sector ETFs)
- **`analog_search.py`**: Pattern matching engine

**Caching:** `backend/app/cache/swr_cache.py`
- Stale-While-Revalidate pattern
- Returns cached data instantly
- Refreshes in background if stale
- Chart cache: 60s
- Context caches: 5-10min
- Pattern cache: 10min

**Schemas:** `backend/app/models/schemas.py`
- All Pydantic models with strict validation
- `Evidence`: timestamp, source_type, source_url, headline, snippet, authority_score, group, relevance_score, why_this_matters, what_it_explains
- `Hypothesis`: rank, title, probability, confidence, explanation, evidence[], mechanism, confirmation_check
- `AnalysisFullResponse`: chat_answer, script, regime, valuation, crowd, rotation, pattern_analogs

**Language Guardrails:** `renderer.py`
- Forbidden phrases list
- Checks all hypothesis + script text
- Raises ValueError if violation detected
- Ensures "Prepare, Don't Predict" compliance

---

### Frontend (Next.js + TypeScript)

**Entry Point:** `frontend/app/page.tsx`
- Main page component
- State management for ticker, chartData, result, loading, analyzing
- Onboarding modal with "Prepare, Don't Predict" framing
- Orchestrates search → chart → analysis → results flow

**Components:**

| Component | Purpose |
|-----------|---------|
| `TickerSearch.tsx` | react-select dropdown (SSR disabled) |
| `StockChart.tsx` | lightweight-charts line chart, 2-click selection, range buttons |
| `ResultView.tsx` | Renders analysis results, grouped evidence (Top 3-5 + "Show all") |
| `ContextPanels.tsx` | Displays regime, valuation, crowd, rotation panels |
| `PatternAnalogs.tsx` | Shows pattern analogs + outcome dispersion + "Pattern ≠ Outcome" warning |

**API Client:** `frontend/lib/api.ts`
- TypeScript interfaces matching backend schemas
- `StockDropAPI` class
- Methods: `getChartData`, `analyzeByDateRange`, `healthCheck`

**Styling:**
- Tailwind CSS
- Dark theme (slate-900 background)
- Responsive design

**User Flow:**

1. User opens app → sees onboarding modal
2. User selects ticker → `api.getChartData()` → chart renders
3. User clicks 2 points → `onPointsSelected` → `api.analyzeByDateRange()`
4. Results render:
   - Summary card
   - Market context
   - Ranked hypotheses with grouped evidence
   - Timeline
   - Unknowns
   - Next steps
5. Scroll to context panels:
   - Regime, valuation, crowd, rotation
6. Scroll to pattern analogs:
   - Analog list with outcomes + "Pattern ≠ Outcome" banner

**Evidence UX:**

- Evidence grouped by: SEC, News, Macro, CorporateActions, Other
- Default: Top 3-5 per group
- "Show more" button to expand
- Each evidence item shows:
  - Headline (link to source)
  - Snippet (if available)
  - "Why this matters" (if available)

---

### MCP Server

**Entry Point:** `mcp_server/main.py`
- Separate FastAPI app on port 8001
- Exposes tools for LLM agents
- Imports backend modules directly

**Tools:**

| Tool | Params | Returns |
|------|--------|---------|
| `get_chart_data` | ticker, range, interval | ChartDataPoint[] |
| `search_filings` | ticker, start_date, end_date | Evidence[] |
| `search_news` | ticker, company_name, start_date, end_date | Evidence[] |
| `get_macro_context` | start_date, end_date | Evidence[] |
| `get_valuation_context` | - | {cape, buffett, breadth} |
| `find_pattern_analogs` | ticker, start_date, end_date, max_analogs | PatternAnalog[] |

---

## Data Sources

### Yahoo Finance (Implemented)
- **Endpoint:** `https://query1.finance.yahoo.com/v8/finance/chart/{ticker}`
- **Params:** range, interval, period1, period2, events
- **Returns:** timestamps, OHLCV, splits, dividends
- **Rate Limiting:** Yes (429 errors possible)
- **Mitigation:** SWR cache (60s), User-Agent headers

### SEC EDGAR (Placeholder)
- **Endpoint:** `https://data.sec.gov/submissions/CIK##########.json`
- **Requirement:** Ticker → CIK mapping (not yet implemented)
- **Filings:** 8-K, 10-Q, 10-K, S-3, S-1
- **Returns:** Evidence objects with filing URLs

### GDELT (Implemented)
- **Endpoint:** `https://api.gdeltproject.org/api/v2/doc/doc`
- **Params:** query, mode=artlist, startdatetime, enddatetime
- **Returns:** Articles with title, domain, URL, seendate
- **Authority Scoring:** Based on domain (WSJ/FT/Bloomberg = 0.90, etc.)
- **Deduplication:** By URL

### FRED (Placeholder)
- **Endpoint:** `https://api.stlouisfed.org/fred/series/observations`
- **Requirement:** Free API key (not yet configured)
- **Series:** DGS10, VIXCLS, DEXUSEU, DCOILWTICO
- **Returns:** Evidence for significant macro moves

### Shiller Data (Placeholder)
- **Source:** http://www.econ.yale.edu/~shiller/data.htm
- **Requirement:** Download + parse CSV
- **Returns:** CAPE ratio + historical percentile

### Wilshire 5000 / Buffett Indicator (Placeholder)
- **Source:** FRED series for market cap + GDP
- **Requirement:** FRED API key + series IDs
- **Returns:** Buffett Indicator + percentile

---

## Caching Strategy

### Chart Data (SWR, 60s)
- **Cache Key:** `chart:{ticker}:{range}:{interval}`
- **Behavior:**
  - First request: fetch → cache → return
  - Subsequent requests < 60s: return cache immediately
  - Requests > 60s: return stale cache + refresh in background

### Context Data (SWR, 5-10min)
- **Cache Keys:**
  - `valuation:cape`, `valuation:buffett`, `valuation:breadth`
  - Regime, crowd, rotation (per session)
- **Behavior:** Same as chart, but longer refresh intervals

### Pattern Analogs (SWR, 10min)
- **Cache Key:** `pattern:{ticker}:{start}:{end}`
- **Behavior:** Same as chart

**Cache Stats Endpoint:** `/api/cache/stats`
- Returns: total_entries, fresh, stale, refresh_interval

---

## Timezone Handling

**All datetimes are timezone-aware (UTC).**

- `datetime.now(timezone.utc)`
- `datetime.fromtimestamp(ts, tz=timezone.utc)`
- `datetime.fromisoformat(...).replace(tzinfo=timezone.utc)`

This prevents:
- `can't subtract offset-naive and offset-aware datetimes` errors

---

## Testing

### Manual Testing
1. Start backend + frontend
2. Select ticker → verify chart loads
3. Click 2 points → verify analysis runs
4. Check evidence grouping, links, snippets
5. Check context panels render
6. Check pattern analogs (if found)
7. Check onboarding modal
8. Check disclaimer banner

### API Testing
- Visit `http://localhost:8000/docs`
- Test endpoints directly via Swagger UI
- Check `/health` and `/api/cache/stats`

### Edge Cases
- Split detection (AAPL 4:1, NVDA 10:1, etc.)
- No evidence found (returns "Insufficient Public Information" hypothesis)
- Rate limiting (429 → error message)
- Timezone-naive inputs (auto-converted to UTC)

---

## Known Limitations

1. **EDGAR:** Not fully implemented (no CIK mapping)
2. **FRED:** Not fully implemented (no API key)
3. **CAPE/Buffett/Breadth:** Placeholders
4. **Peer/Sector Lookup:** Manual for now
5. **Pattern Analogs:** Basic sliding window (needs refinement)
6. **Sentiment Extraction:** Not yet pulling from GDELT for analogs
7. **Yahoo Finance Rate Limits:** Can be hit with repeated requests

---

## Security Considerations

- **CORS:** Currently allows all origins (tighten in production)
- **Rate Limiting:** Not implemented (add for production)
- **Authentication:** Not implemented (add if exposing publicly)
- **Input Validation:** Pydantic handles this
- **SQL Injection:** N/A (no SQL database)
- **XSS:** React + TypeScript handles this

---

## Performance

- **Chart Load:** < 1s (cached) / 1-3s (uncached)
- **Analysis:** 5-15s (depends on evidence volume)
- **Pattern Search:** 2-5s (depends on history length)
- **Context Panels:** 1-2s (cached) / 3-5s (uncached)

---

## Deployment Notes

- **Backend:** Uvicorn ASGI server (production: Gunicorn + Uvicorn workers)
- **Frontend:** Next.js SSR (production: Vercel / Netlify / Docker)
- **Environment Variables:**
  - `NEXT_PUBLIC_API_URL` (frontend)
  - Optional: FRED API key, EDGAR headers, etc.
- **HTTPS:** Required for production
- **Monitoring:** Add Sentry / logging / analytics

---

## Future Enhancements

- WebSocket for real-time updates
- User accounts + saved analyses
- Export to PDF / CSV
- Multi-ticker comparison
- Backtesting framework
- More granular pattern features
- Automated peer/sector lookup via third-party APIs
