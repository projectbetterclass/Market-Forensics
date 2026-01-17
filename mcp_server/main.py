"""MCP Tool Server for Stock Analysis."""

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List, Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.retrieval.prices import PriceClient
from backend.app.retrieval.edgar import EdgarClient
from backend.app.retrieval.news import NewsClient
from backend.app.retrieval.macro import MacroClient
from backend.app.retrieval.valuation import ValuationProvider
from backend.app.context.regime import RegimeAnalyzer
from backend.app.context.crowd import CrowdAnalyzer
from backend.app.context.rotation import RotationAnalyzer
from backend.app.pattern.analog_search import PatternAnalogEngine

app = FastAPI(title="Stock Analysis MCP Server", version="1.0.0")


class ToolRequest(BaseModel):
    """Generic MCP tool request."""
    params: dict


@app.post("/tools/get_chart_data")
async def tool_get_chart_data(request: ToolRequest):
    """MCP tool: Get chart data."""
    client = PriceClient()
    data = await client.get_chart_data_range(
        request.params["ticker"],
        request.params.get("range", "max"),
        request.params.get("interval", "1d")
    )
    return {"result": [{"time": d.time, "value": d.value} for d in data]}


@app.post("/tools/search_filings")
async def tool_search_filings(request: ToolRequest):
    """MCP tool: Search SEC filings."""
    client = EdgarClient()
    start_date = datetime.fromisoformat(request.params["start_date"])
    end_date = datetime.fromisoformat(request.params["end_date"])
    filings = await client.search_filings(
        request.params["ticker"],
        start_date,
        end_date
    )
    return {"result": [f.dict() for f in filings]}


@app.post("/tools/search_news")
async def tool_search_news(request: ToolRequest):
    """MCP tool: Search news via GDELT."""
    client = NewsClient()
    start_date = datetime.fromisoformat(request.params["start_date"])
    end_date = datetime.fromisoformat(request.params["end_date"])
    news = await client.search_news(
        request.params["ticker"],
        request.params.get("company_name"),
        start_date,
        end_date
    )
    return {"result": [n.dict() for n in news]}


@app.post("/tools/get_macro_context")
async def tool_get_macro_context(request: ToolRequest):
    """MCP tool: Get macroeconomic context."""
    client = MacroClient()
    start_date = datetime.fromisoformat(request.params["start_date"])
    end_date = datetime.fromisoformat(request.params["end_date"])
    macro = await client.get_macro_context(start_date, end_date)
    return {"result": [m.dict() for m in macro]}


@app.post("/tools/get_valuation_context")
async def tool_get_valuation_context(request: ToolRequest):
    """MCP tool: Get valuation indicators."""
    provider = ValuationProvider()
    cape = await provider.get_cape_ratio()
    buffett = await provider.get_buffett_indicator()
    breadth = await provider.get_breadth_reading()
    return {
        "result": {
            "cape": cape,
            "buffett": buffett,
            "breadth": breadth
        }
    }


@app.post("/tools/find_pattern_analogs")
async def tool_find_pattern_analogs(request: ToolRequest):
    """MCP tool: Find pattern analogs."""
    engine = PatternAnalogEngine()
    start_date = datetime.fromisoformat(request.params["start_date"])
    end_date = datetime.fromisoformat(request.params["end_date"])
    analogs = await engine.find_analogs(
        request.params["ticker"],
        start_date,
        end_date,
        request.params.get("max_analogs", 10)
    )
    return {"result": [a.dict() for a in analogs]}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Stock Analysis MCP Server",
        "version": "1.0.0",
        "tools": [
            "get_chart_data",
            "search_filings",
            "search_news",
            "get_macro_context",
            "get_valuation_context",
            "find_pattern_analogs"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
