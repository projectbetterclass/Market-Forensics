# Testing Guide

## Manual Testing Checklist

### Backend Tests

#### 1. **Health Check**
```bash
curl http://localhost:8000/health
```
Expected: `{"status": "healthy"}`

#### 2. **API Docs**
Open http://localhost:8000/docs
- Should see Swagger UI with `/api/analyze` endpoint

#### 3. **Simple Analysis Test**
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "time_window_hours": 24}'
```

Expected:
- Returns JSON with `chat_answer` and `script`
- `chat_answer` contains `hypotheses`, `timeline`, `market_context`
- All `evidence` items have `source_url` (citations)

### Frontend Tests

#### 1. **UI Loads**
- Open http://localhost:3000
- See title "Stock Drop Research Agent"
- See form with Ticker, Drop %, Time Window fields

#### 2. **Form Validation**
- Try submitting empty ticker → Should be prevented
- Enter "AAPL" → Should submit

#### 3. **Loading State**
- Click "Analyze Drop"
- Should see spinner and "Analyzing stock drop..." message

#### 4. **Results Display**
- Should show summary card with drop %, price, volume, move type
- Should show "Ranked Causes" with hypotheses (rank, probability, confidence)
- Should see "Market Context" with interpretation
- Toggle to "YouTube Script" → Should show sections

### Historical Drop Test Cases

Test with known historical events to validate accuracy:

#### Case 1: Regional Bank Crisis (March 2023)
```json
{
  "ticker": "SIVB",
  "time_window_hours": 72
}
```
**Expected top cause**: 8-K filing or news about liquidity issues

#### Case 2: Tech Stock Offering
```json
{
  "ticker": "TSLA",
  "drop_percent": 10,
  "time_window_hours": 48
}
```
**Expected**: Check for S-3 filing if offering occurred

#### Case 3: Earnings Miss
Pick a recent earnings miss, test within 24h of earnings release
**Expected**: 8-K or news about guidance cut / earnings miss

### Evaluation Metrics (Manual)

For each test case, record:

1. **Top-1 Match**: Did the correct cause appear as #1 hypothesis?
2. **Top-3 Match**: Did it appear in top 3?
3. **Citation Correctness**: All hypotheses have valid evidence links?
4. **Hallucination Check**: Any claims without supporting evidence?
5. **Latency**: Time from submit to results displayed?

### Expected Behavior

✅ **Good Results:**
- All hypotheses cite evidence (SEC filings, news)
- Probabilities sum to ≤1.0
- "Unknowns" section populated when evidence is thin
- Market context correctly classifies move type
- No made-up filings or news

⚠️ **Known Limitations (OK):**
- News API is placeholder (limited news coverage without API key)
- Peer comparison not implemented yet (sector-only)
- Some tickers may have limited SEC data

❌ **Bad Results (Fix These):**
- Hypotheses with no evidence
- Confidence=high but probability=low (inconsistent)
- Claims about filings that don't exist
- Crash or error without clear message

## Automated Testing (Future)

Create `backend/tests/test_agent.py`:

```python
import pytest
from app.agent.normalizer import EventNormalizer
from app.agent.hypothesis import HypothesisGenerator
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_event_normalizer():
    normalizer = EventNormalizer()
    result = await normalizer.validate_and_normalize(
        "AAPL", None, 24
    )
    assert result is not None
    assert result["ticker"] == "AAPL"
    assert "drop_percent" in result

@pytest.mark.asyncio
async def test_hypothesis_scoring():
    # Mock evidence and test scoring
    pass
```

Run tests:
```bash
cd backend
pytest
```

## Performance Benchmarks

Target metrics:
- API latency: <10s for typical query
- Evidence retrieval: <5s total
- Frontend render: <1s after receiving data

## Deployment Testing (Future)

1. Docker build test
2. API key rotation
3. Rate limiting verification
4. CORS configuration
