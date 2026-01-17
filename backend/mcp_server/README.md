# MCP Tool Server - Stock Drop Agent

This is a **Model Context Protocol (MCP)** tool server that exposes the Stock Drop Agent's capabilities as callable tools for LLM agents.

## What is MCP?

Model Context Protocol (MCP) is a protocol for connecting LLM agents to external tools and data sources. It allows Claude, GPT-4, or other LLMs to:
- Call specific tools with structured parameters
- Receive structured responses
- Build complex workflows by chaining tool calls

## Tools Exposed

### 1. `market.getChartHistory`
Get historical price data for a ticker.

**Parameters:**
- `ticker` (string, required): Stock ticker symbol
- `range` (string, optional): "1d", "5d", "1mo", "3mo", "6mo", "1y", "5y", "10y", "max" (default: "max")
- `interval` (string, optional): "1m", "5m", "15m", "1h", "1d", "1wk", "1mo" (default: "1d")

**Returns:** Array of `{time, value}` data points

---

### 2. `market.getCorporateActions`
Get stock splits and dividends.

**Parameters:**
- `ticker` (string, required)
- `start_date` (string, required): ISO format
- `end_date` (string, required): ISO format

**Returns:** `{splits: [...], dividends: [...]}`

---

### 3. `sec.searchFilings`
Search SEC EDGAR for filings.

**Parameters:**
- `ticker` (string, required)
- `start_date` (string, required): ISO format
- `end_date` (string, required): ISO format
- `forms` (array, optional): ["8-K", "10-Q", etc.]

**Returns:** Array of filing evidence objects with citations

---

### 4. `news.search`
Search news via GDELT (free).

**Parameters:**
- `ticker` (string, required)
- `company_name` (string, optional)
- `start_date` (string, required): ISO format
- `end_date` (string, required): ISO format

**Returns:** Array of news evidence objects with URLs

---

### 5. `macro.getContext`
Get macro economic events via FRED.

**Parameters:**
- `start_date` (string, required): ISO format
- `end_date` (string, required): ISO format

**Returns:** Array of macro event evidence (rates, VIX, FX, oil)

---

### 6. `analysis.explainDrop`
Complete drop analysis with ranked hypotheses.

**Parameters:**
- `ticker` (string, required)
- `start_date` (string, required): ISO format
- `end_date` (string, required): ISO format

**Returns:** Full analysis object with:
- Hypotheses (ranked, with probabilities & confidence)
- Timeline (chronological events)
- Market context
- Citations for all claims

---

## Running the MCP Server

### Standalone (stdio mode):
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python -m mcp_server.main
```

### With Claude Desktop or other MCP clients:

Add to your MCP client config (e.g., Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "stock-drop-agent": {
      "command": "python",
      "args": ["-m", "mcp_server.main"],
      "cwd": "C:\\Users\\Gebruiker\\Documents\\StockApp\\backend",
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

Then restart Claude Desktop. The tools will appear in the MCP tools menu.

---

## Example Tool Usage (from LLM agent)

**Agent prompt:**
> "Use the stock-drop-agent MCP tools to explain why AAPL dropped from Dec 1 to Dec 15, 2023."

**Agent workflow:**
1. Call `market.getChartHistory(ticker="AAPL", range="1y")`
2. Call `sec.searchFilings(ticker="AAPL", start_date="2023-11-25", end_date="2023-12-20")`
3. Call `news.search(ticker="AAPL", start_date="2023-11-25", end_date="2023-12-20")`
4. Call `macro.getContext(start_date="2023-11-25", end_date="2023-12-20")`
5. Call `analysis.explainDrop(ticker="AAPL", start_date="2023-12-01", end_date="2023-12-15")`

**Agent gets back:**
- Ranked hypotheses with probabilities
- All evidence with citations (SEC filings, news URLs)
- Market context
- Explicit unknowns

The agent can then generate a narrative explanation while maintaining strict citations.

---

## Benefits of MCP Integration

1. **Structured evidence** - All data comes with timestamps, URLs, authority scores
2. **No hallucinations** - LLM can only cite returned evidence
3. **Composable** - Agent can chain tools (get filings → read specific filing → analyze)
4. **Reusable** - Same tools work in web app, CLI, or other LLM agents
5. **Transparent** - Tool calls are logged and visible

---

## Requirements

Same as main backend:
- Python 3.11+
- Dependencies from `backend/requirements.txt`
- Optional: FRED API key for macro context

---

## Testing MCP Tools

You can test tools manually by sending JSON-RPC requests:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"market.getChartHistory","arguments":{"ticker":"AAPL","range":"1y"}}}' | python -m mcp_server.main
```

---

## Future Enhancements

- Add `sec.getFilingText` to extract full filing text for LLM summarization
- Add `company.getProfile` for sector/industry/peers
- Add caching layer for frequently accessed data
- Add rate limiting and error retry logic
