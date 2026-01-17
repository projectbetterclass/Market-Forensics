# HOW TO USE - Stock Drop Forensic Analysis

## Step 1: Start the Application

### Backend
```bash
cd C:\Users\Gebruiker\Documents\StockApp\backend
.\venv\Scripts\Activate.ps1
python -m app.main
```
✅ Backend running on **http://localhost:8000**

### Frontend
```bash
cd C:\Users\Gebruiker\Documents\StockApp\frontend
npm run dev
```
✅ Frontend running on **http://localhost:3000**

---

## Step 2: First Time? Read the Onboarding

When you visit **http://localhost:3000**, you'll see an onboarding modal explaining:
- **This tool recognizes patterns and provides context**
- **It does NOT predict or recommend actions**
- **Most wealth is lost *before* crashes** due to overconfidence/leverage/timing

Click "I Understand" to continue.

---

## Step 3: Search for a Ticker

Use the search box to select a ticker symbol or company. Popular options are pre-loaded (AAPL, MSFT, GOOGL, etc.).

Example: Select **AAPL** (Apple Inc.)

---

## Step 4: View the Chart

You'll see:
- A **line chart** showing historical prices
- **Range buttons**: 1Y / 5Y / 10Y / MAX (default: MAX)
- Instructions: "Click on the chart to select the START of the drop"

The chart displays:
- Daily closing prices
- Blue line
- Crosshair for precision
- Time scale at bottom
- Price scale on right

---

## Step 5: Select Two Points

**To analyze a price movement:**

1. **Click once** on the chart where the drop (or move) **starts**
   - You'll see: "✓ Start point selected: [date]"

2. **Click again** where the drop **ends**
   - The system immediately sends the analysis request

**The app now:**
- Calculates price change %
- Checks for splits/dividends
- Retrieves evidence (±10 days around the window)
- Analyzes market context
- Generates hypotheses
- Finds pattern analogs

This takes 5-15 seconds depending on evidence volume.

---

## Step 6: Review the Results

### A) Summary Card
- Ticker + drop %
- Date range
- Price change
- Volume vs average
- Move type (company-specific / sector-wide / market-wide)

### B) Market Context
- S&P 500 return for the same period
- Interpretation (was market up/down/flat?)

### C) Ranked Causes (Hypotheses)
Each hypothesis shows:
- **Rank**: 1-5 (most to least likely)
- **Title**: e.g., "Earnings/Financial Results"
- **Probability**: 0-100%
- **Confidence**: High / Medium / Low
- **Explanation**: Key evidence bullets
- **Mechanism**: How many sources, what type
- **Evidence**: Grouped by SEC / News / Macro / CorporateActions
  - Default: **Top 3-5 per group**
  - Click "Show more" to expand
  - Each link is clickable to primary source
- **Next steps**: What to monitor (not advice!)

### D) Timeline
Chronological list of all evidence sorted by timestamp:
- Date/time
- Description
- [source] link

### E) Unknowns & Limitations
What we don't know:
- Limited public information?
- Timing gaps?
- High volume unexplained?

### F) Monitoring Steps (Not Advice)
Suggestions for further research:
- Watch for upcoming filings
- Track peer companies
- Review earnings calls

---

## Step 7: Context Panels (Advanced)

Scroll down to see:

### Market Regime
- **Stage 1-4**: Rational Growth / Acceleration / Euphoria / Panic
- **Volatility regime**: Low / Medium / High
- Description of current stage

### Valuation Stress Indicators
- **CAPE ratio** + percentile
- **Buffett Indicator** + percentile
- **Breadth** reading
- Context statement (e.g., "Elevated percentiles have historically been associated with increased volatility risk")

### Crowd Behavior
- Retail inflow proxy
- Options activity
- Leadership narrowing
- Speculative asset performance
- Interpretation

*Note: Many crowd metrics require premium data. Free proxies are marked as "unavailable".*

### Sector Rotation
- Top 5 sector performances (ETFs)
- Leadership concentration warning (if applicable)
- Interpretation (defensive vs cyclical leadership)

---

## Step 8: Pattern Analogs (Optional)

If historical patterns were found, you'll see:

### Pattern ≠ Outcome Warning
**⚠️ Similar patterns have led to varied outcomes in the past.**

### Analog List
Each analog shows:
- **Pattern description** (e.g., "Similar 10-day pattern from 2020-03-15")
- **Similarity score** (0-100%)
- **Forward returns** at multiple horizons:
  - 1w / 1m / 3m / 6m / 12m
  - Each shows actual return % for that analog
- **Sentiment at the time** (if available)
- **Narrative tags** (if available)

**Key insight:** You can see that similar patterns led to very different outcomes. This reinforces that **pattern ≠ outcome**.

---

## Step 9: Reset or Try Another Ticker

- Click **Reset Selection** to clear chart selection
- Select a new ticker to start fresh
- Change range (1Y/5Y/10Y/MAX) to adjust chart scope

---

## Tips & Best Practices

### ✅ Do:
- Use this to recognize patterns and understand context
- Read the evidence carefully and follow source links
- Consider multiple hypotheses (not just the top one)
- Pay attention to unknowns and limitations
- Use outcome dispersion to calibrate expectations

### ❌ Don't:
- Don't treat this as a prediction or trading signal
- Don't assume the top hypothesis is "the answer"
- Don't ignore the disclaimer and guardrail warnings
- Don't confuse probability with certainty
- Don't use this as your only research tool

---

## Troubleshooting

### "Failed to fetch chart data"
- Check backend is running (`http://localhost:8000/health`)
- Yahoo Finance may be rate-limiting (wait 60s, try again)
- Check network connection

### "Price change matches a stock split pattern"
- The app detected a split (e.g., 2:1)
- This is not a "real" price decline
- Try a different period

### "No significant public information available"
- The evidence window (±10 days) had no filings, news, or macro events
- Try a larger drop or a different ticker
- Consider this may be a technical/algorithmic move

### "Insufficient forward data" in pattern analogs
- The analog is too recent to have 12-month forward returns
- Earlier horizons (1w, 1m) may still be available

---

## Advanced: MCP Server

If you're using an LLM agent (e.g., Claude, GPT), you can point it to the MCP server:

```bash
cd C:\Users\Gebruiker\Documents\StockApp\mcp_server
python main.py
```

MCP server runs on **http://localhost:8001**

Available tools:
- `get_chart_data`
- `search_filings`
- `search_news`
- `get_macro_context`
- `get_valuation_context`
- `find_pattern_analogs`

Agent can call these tools to retrieve evidence-rich, citation-ready data.

---

## Need Help?

- Check `README.md` for setup
- Check `PROJECT_CONTEXT.md` for architecture
- Check `IMPLEMENTATION_SUMMARY.md` for technical details
- Check `CHANGELOG.md` for version history
