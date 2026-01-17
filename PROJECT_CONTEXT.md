# PROJECT CONTEXT - Living Document

**Last Updated:** 2026-01-11

## Mission

Build a forensic market-context and pattern-recognition tool that helps users avoid wealth-destroying mistakes - especially near market extremes - without predicting or giving advice.

## Core Principles (Non-Negotiable)

1. **Prepare, Don't Predict**
   - We recognize patterns and provide context
   - We DO NOT forecast future prices
   - We DO NOT recommend actions

2. **Loss-Avoidance Framing**
   - Most wealth is lost *before* crashes, not during
   - Overconfidence, leverage, and timing errors are the real risks
   - Our goal: help users recognize risk, not chase returns

3. **Strict Evidence Policy**
   - Every factual claim must have a cited source (`Evidence` object)
   - Uncertain claims must be explicitly labeled as hypotheses with probabilities
   - No uncited speculation allowed

4. **Language Guardrails**
   - Forbidden: "crash coming", "guaranteed", "should buy/sell", etc.
   - Allowed: "historically", "associated with", "outcomes varied"
   - Server-side validation enforces this

## Product Identity

**"A professional-grade pattern and market-context intelligence tool designed to help investors recognize risk, avoid emotional mistakes, and understand history — not chase returns."**

## Architecture

### Tech Stack
- **Backend:** FastAPI (Python 3.10+)
- **Frontend:** Next.js 14 + TypeScript + Tailwind
- **Charts:** lightweight-charts v4.1+
- **Caching:** SWR (stale-while-revalidate)
- **MCP:** FastAPI tool server for LLM agents

### Data Flow

```
User selects 2 points on chart
  ↓
POST /api/analyze-range
  ↓
Price truth (Yahoo Finance) ← SWR cache
  ↓
Corporate actions check (splits/dividends)
  ↓
Evidence retrieval (EDGAR, GDELT, FRED) ← tight ±10 day window
  ↓
Market context (S&P 500, sectors, peers)
  ↓
Hypothesis generation + scoring
  ↓
Context panels (regime, valuation, crowd, rotation)
  ↓
Pattern analog search + outcome dispersion
  ↓
Language guardrail validation
  ↓
Return AnalysisFullResponse
  ↓
Frontend renders grouped evidence + context
```

### Evidence Schema

```typescript
interface Evidence {
  timestamp: datetime;
  source_type: "sec_filing" | "news" | "macro" | "corporate_action" | ...;
  source_url: string;
  headline: string;
  snippet?: string;
  authority_score: 0.0-1.0;
  group: "SEC" | "News" | "Macro" | "CorporateActions" | "Other";
  relevance_score: 0.0-1.0;
  why_this_matters?: string;
  what_it_explains?: string;
}
```

## Current Status

### ✅ Implemented

- Full backend + frontend + MCP server
- Search → chart → 2-click selection → analyze-range flow
- Ranked hypothesis generation with 5-factor scoring
- Evidence grouping (SEC/News/Macro/CorporateActions)
- Top 3-5 per group + "Show all" accordion UI
- Market regime (Stage 1-4) + volatility regime
- Valuation context (CAPE/Buffett/breadth) with percentiles
- Crowd behavior panel (with "unavailable" markers for premium data)
- Sector rotation + leadership concentration warnings
- Pattern analog search + outcome dispersion (1w/1m/3m/6m/12m)
- "Pattern ≠ Outcome" guardrail
- SWR caching (60s chart, 5-10min context)
- Onboarding modal with "Prepare, Don't Predict" + loss-avoidance framing
- Forbidden language validation in renderer
- Disclaimer banner
- Timeline with source links

### 🚧 Placeholders / TODOs

- **EDGAR:** Needs ticker → CIK mapping + actual API calls
- **FRED:** Needs free API key + series fetch implementation
- **CAPE:** Needs Shiller dataset fetch
- **Buffett Indicator:** Needs Wilshire 5000 / GDP series from FRED
- **Breadth:** Needs constituent data or proxy index
- **Peer Lookup:** Needs ticker → peers mapping
- **Sector Lookup:** Needs ticker → sector mapping
- **Pattern Analog:** Basic sliding window implemented, needs refinement + sentiment/narrative extraction from GDELT

### 📁 File Locations

- **Backend:** `C:\Users\Gebruiker\Documents\StockApp\backend\`
- **Frontend:** `C:\Users\Gebruiker\Documents\StockApp\frontend\`
- **MCP:** `C:\Users\Gebruiker\Documents\StockApp\mcp_server\`
- **Docs:** `C:\Users\Gebruiker\Documents\StockApp\` (root)

## Known Issues

- **Windows Permissions:** `D:\Stock app\` requires admin; fallback to `Documents\StockApp\`
- **Yahoo Finance Rate Limits:** 429 errors possible; SWR caching mitigates
- **Timezone Awareness:** All datetimes are UTC-aware to prevent comparison errors

## Roadmap

### Phase 1 (Current)
- ✅ Core UI loop
- ✅ Evidence UX overhaul
- ✅ Context panels
- ✅ Pattern analogs
- ✅ Guardrails everywhere

### Phase 2 (Next)
- [ ] Implement EDGAR ticker→CIK + filing fetch
- [ ] Integrate FRED API key + macro series
- [ ] Add Shiller CAPE fetch
- [ ] Add Buffett Indicator provider
- [ ] Automated peer/sector lookup

### Phase 3 (Future)
- [ ] YouTube video ingestion for narrative learning
- [ ] Sentiment extraction from GDELT headlines
- [ ] More granular pattern features (volatility clustering, vol regime transitions)
- [ ] Multi-ticker batch analysis

## Maintenance

### Adding a New Data Source

1. Create client in `backend/app/retrieval/`
2. Return `List[Evidence]` objects
3. Call from `routes.py` in evidence window
4. Add to MCP server (optional)
5. Update docs

### Adding a New Context Panel

1. Create analyzer in `backend/app/context/`
2. Define Pydantic schema in `schemas.py`
3. Add endpoint in `routes.py`
4. Include in `AnalysisFullResponse`
5. Add UI component in `frontend/components/`
6. Render in `page.tsx`

## Testing

- Manual testing via UI (http://localhost:3000)
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- Cache stats: http://localhost:8000/api/cache/stats

## Support

For questions, check:
- `README.md` (this file)
- `HOW_TO_USE.md` (user guide)
- `IMPLEMENTATION_SUMMARY.md` (technical deep-dive)
- `CHANGELOG.md` (version history)
