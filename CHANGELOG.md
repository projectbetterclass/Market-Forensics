# CHANGELOG

All notable changes to the Stock Drop Forensic Analysis project.

## [1.0.0] - 2026-01-11

### Added - Full Production Build

**Philosophy & Positioning**
- ✅ "Prepare, Don't Predict" doctrine embedded throughout
- ✅ Loss-avoidance framing: "Wealth is lost before crashes, not during"
- ✅ Onboarding modal explaining non-prediction/non-advice stance
- ✅ Disclaimer banner on all results
- ✅ Language guardrails (server-side validation)

**Core Analysis Flow**
- ✅ Interactive line chart with 2-click selection
- ✅ Long history support (MAX range, daily interval by default)
- ✅ Price truth validation (Yahoo Finance)
- ✅ Corporate action detection (splits/dividends) with abort on fake drops
- ✅ Evidence retrieval in tight ±10 day window
- ✅ Market/sector/peer context analysis
- ✅ Move type classification (company-specific / sector-wide / market-wide)
- ✅ Ranked hypothesis generation with 5-factor scoring
- ✅ Chronological timeline
- ✅ Unknowns & next steps (monitoring, not advice)

**Evidence UX Improvements**
- ✅ Evidence grouped by: SEC / News / Macro / CorporateActions / Other
- ✅ Top 3-5 per group + "Show all" accordion
- ✅ Relevance scoring (timing, authority, specificity, magnitude, corroboration)
- ✅ Purpose labels: `why_this_matters`, `what_it_explains` (schema ready)
- ✅ Authority scoring by source domain (WSJ/FT/Bloomberg = 0.90, etc.)

**Context Panels**
- ✅ Market Regime (Stage 1-4) + volatility regime
- ✅ Valuation Stress (CAPE/Buffett/breadth with percentiles)
  - Schema + endpoints ready
  - Providers are placeholders (need Shiller data, FRED series, breadth index)
- ✅ Crowd Behavior (retail inflow, options activity, leadership, speculation)
  - Clearly marks "unavailable with free sources" where applicable
- ✅ Sector Rotation (sector ETF performance + leadership concentration warnings)
  - Uses historical associations language only

**Pattern Analogs**
- ✅ Pattern matching via sliding window + cosine similarity
- ✅ Multi-horizon outcome dispersion (1w/1m/3m/6m/12m)
- ✅ "Pattern ≠ Outcome" guardrail (banner + warning)
- ✅ Sentiment/narrative section (schema ready, GDELT integration pending)
- ✅ Similarity scoring

**Caching & Performance**
- ✅ SWR (Stale-While-Revalidate) caching
  - Chart data: 60s refresh
  - Context data: 5-10min refresh
  - Pattern data: 10min refresh
- ✅ Cache stats endpoint (`/api/cache/stats`)
- ✅ Background refresh (serve stale instantly, refresh async)

**MCP Tool Server**
- ✅ Separate FastAPI server on port 8001
- ✅ Tools: get_chart_data, search_filings, search_news, get_macro_context, get_valuation_context, find_pattern_analogs
- ✅ Evidence-rich outputs for LLM agents

**Documentation**
- ✅ README.md (setup, features, philosophy)
- ✅ PROJECT_CONTEXT.md (living architecture doc)
- ✅ HOW_TO_USE.md (step-by-step user guide)
- ✅ IMPLEMENTATION_SUMMARY.md (technical deep-dive)
- ✅ CHANGELOG.md (this file)

**Data Sources**
- ✅ Yahoo Finance (prices, splits, dividends) - fully implemented
- ✅ GDELT (news) - fully implemented
- ⚠️ SEC EDGAR (filings) - placeholder, needs ticker→CIK mapping
- ⚠️ FRED (macro) - placeholder, needs API key
- ⚠️ Shiller (CAPE) - placeholder
- ⚠️ Wilshire/FRED (Buffett Indicator) - placeholder

**Tech Stack**
- Backend: FastAPI + Python 3.10+
- Frontend: Next.js 14 + TypeScript + Tailwind CSS
- Charts: lightweight-charts v4.1+
- Validation: Pydantic
- Caching: Custom SWR implementation

**Language Guardrails**
- Forbidden: "crash coming", "guaranteed", "should buy/sell", "smart money knows", "obvious opportunity", "must rebound", etc.
- Allowed: "historically", "associated with", "risk has increased", "outcomes varied", "similar conditions"
- Server-side validation raises error if forbidden phrases detected

### Fixed
- ✅ Windows permission issues (fallback to Documents\StockApp)
- ✅ Yahoo Finance rate limiting (SWR cache + User-Agent headers)
- ✅ Timezone comparison errors (all datetimes now UTC-aware)
- ✅ React hydration errors (react-select SSR disabled)
- ✅ lightweight-charts v5 API compatibility (addLineSeries → addSeries)
- ✅ Split detection false positives (corporate actions check)

### Known Issues
- ⚠️ EDGAR not fully functional (needs CIK mapping)
- ⚠️ FRED not fully functional (needs API key)
- ⚠️ Valuation providers are placeholders
- ⚠️ Pattern analog sentiment extraction not yet implemented
- ⚠️ Yahoo Finance can still hit rate limits under heavy load

### Roadmap for v1.1
- [ ] Implement EDGAR ticker→CIK mapping + filing fetch
- [ ] Integrate FRED API key + macro series fetch
- [ ] Add Shiller CAPE data provider
- [ ] Add Buffett Indicator (Wilshire 5000 + GDP from FRED)
- [ ] Implement breadth index provider
- [ ] Automate peer/sector lookup
- [ ] Extract sentiment/narrative from GDELT for pattern analogs
- [ ] Add WebSocket support for real-time updates
- [ ] Add user accounts + saved analyses

---

## [0.1.0] - Initial Development (Pre-Release)

### Added
- Basic backend structure
- Basic frontend structure
- Manual testing only

---

## Version Numbering

- **Major.Minor.Patch** (Semantic Versioning)
- **Major** = Breaking changes or major feature additions
- **Minor** = New features, no breaking changes
- **Patch** = Bug fixes, minor improvements

---

## Maintenance Notes

**Location:** `C:\Users\Gebruiker\Documents\StockApp\`

**Startup:**
1. Backend: `cd backend; .\venv\Scripts\Activate.ps1; python -m app.main`
2. Frontend: `cd frontend; npm run dev`
3. MCP (optional): `cd mcp_server; python main.py`

**Health Checks:**
- Backend: http://localhost:8000/health
- Frontend: http://localhost:3000
- MCP: http://localhost:8001

**Cache Stats:**
- http://localhost:8000/api/cache/stats

**API Docs:**
- http://localhost:8000/docs
