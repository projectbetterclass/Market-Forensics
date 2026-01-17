"""
MCP (Model Context Protocol) Tool Server for Stock Drop Analysis.

This server exposes the stock analysis capabilities as MCP tools that can be
called by LLM agents following the Model Context Protocol specification.

Tools exposed:
- market.getChartHistory
- market.getCorporateActions
- sec.searchFilings
- news.search
- macro.getContext
- analysis.explainDrop
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

# Add parent directory to path to import app modules
sys.path.insert(0, '..')

from app.retrieval.edgar import EdgarClient
from app.retrieval.prices import PriceClient
from app.retrieval.news import NewsClient
from app.retrieval.macro import MacroClient
from app.agent.normalizer import EventNormalizer
from app.agent.market_context import MarketContextAnalyzer
from app.agent.hypothesis import HypothesisGenerator
from app.agent.renderer import ResponseRenderer


class MCPToolServer:
    """MCP Tool Server implementation."""
    
    def __init__(self):
        self.edgar_client = EdgarClient()
        self.price_client = PriceClient()
        self.news_client = NewsClient()
        self.macro_client = MacroClient()
        self.normalizer = EventNormalizer()
        self.market_analyzer = MarketContextAnalyzer()
        self.hypothesis_gen = HypothesisGenerator()
        self.renderer = ResponseRenderer()
    
    async def get_chart_history(self, ticker: str, range: str = "max", interval: str = "1d") -> List[Dict]:
        """
        Tool: market.getChartHistory
        Get historical price data for a ticker.
        """
        try:
            data = await self.price_client.get_chart_data_range(ticker, range, interval)
            return data or []
        except Exception as e:
            return {"error": str(e)}
    
    async def get_corporate_actions(self, ticker: str, start_date: str, end_date: str) -> Dict:
        """
        Tool: market.getCorporateActions
        Get splits and dividends for a ticker in a date range.
        """
        try:
            start_time = datetime.fromisoformat(start_date)
            end_time = datetime.fromisoformat(end_date)
            
            splits, dividends = await self.price_client.get_corporate_actions(
                ticker, start_time, end_time
            )
            
            return {
                "splits": splits,
                "dividends": dividends
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def search_sec_filings(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        forms: List[str] = None
    ) -> List[Dict]:
        """
        Tool: sec.searchFilings
        Search SEC EDGAR for filings in a date range.
        """
        try:
            start_time = datetime.fromisoformat(start_date)
            end_time = datetime.fromisoformat(end_date)
            
            filings = await self.edgar_client.search_filings(
                ticker, start_time, end_time, forms
            )
            
            # Convert Evidence objects to dicts
            return [
                {
                    "timestamp": f.timestamp.isoformat(),
                    "source_type": f.source_type.value,
                    "source_url": f.source_url,
                    "headline": f.headline,
                    "snippet": f.snippet,
                    "authority_score": f.authority_score
                }
                for f in filings
            ]
        except Exception as e:
            return [{"error": str(e)}]
    
    async def search_news(
        self,
        ticker: str,
        company_name: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        Tool: news.search
        Search news articles via GDELT.
        """
        try:
            start_time = datetime.fromisoformat(start_date)
            end_time = datetime.fromisoformat(end_date)
            
            news_items = await self.news_client.search_news(
                ticker, company_name, start_time, end_time
            )
            
            # Convert to dicts
            return [
                {
                    "timestamp": n.timestamp.isoformat(),
                    "source_type": n.source_type.value,
                    "source_url": n.source_url,
                    "headline": n.headline,
                    "authority_score": n.authority_score
                }
                for n in news_items
            ]
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_macro_context(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Tool: macro.getContext
        Get macro economic context via FRED.
        """
        try:
            start_time = datetime.fromisoformat(start_date)
            end_time = datetime.fromisoformat(end_date)
            
            macro_events = await self.macro_client.get_macro_context(start_time, end_time)
            
            return [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "headline": m.headline,
                    "snippet": m.snippet,
                    "source_url": m.source_url,
                    "authority_score": m.authority_score
                }
                for m in macro_events
            ]
        except Exception as e:
            return [{"error": str(e)}]
    
    async def explain_drop(self, ticker: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Tool: analysis.explainDrop
        Complete drop analysis with ranked hypotheses and citations.
        """
        try:
            start_time = datetime.fromisoformat(start_date)
            end_time = datetime.fromisoformat(end_date)
            
            # Get price data
            price_data = await self.price_client.get_price_data(ticker, start_time, end_time)
            
            if not price_data:
                return {"error": f"No price data found for {ticker}"}
            
            event_data = {
                "ticker": ticker,
                "start_time": start_time,
                "end_time": end_time,
                "start_price": price_data["start_price"],
                "end_price": price_data["end_price"],
                "drop_percent": price_data["drop_percent"],
                "volume_vs_average": price_data["volume_vs_average"],
                "session_type": price_data["session_type"],
                "is_likely_split": False,
                "avg_volume": None
            }
            
            # Market context
            market_context = await self.market_analyzer.analyze_context(
                ticker, start_time, end_time
            )
            
            move_type = self.market_analyzer.classify_move_type(
                event_data["drop_percent"],
                market_context.market_return_pct,
                market_context.sector_return_pct,
                market_context.peer_median_return_pct
            )
            
            # Evidence (focused window)
            evidence_window_days = 10
            evidence_start = start_time - timedelta(days=evidence_window_days)
            evidence_end = end_time + timedelta(days=evidence_window_days)
            
            evidence_list = []
            
            filings = await self.edgar_client.search_filings(ticker, evidence_start, evidence_end)
            evidence_list.extend(filings)
            
            news_items = await self.news_client.search_news(ticker, None, evidence_start, evidence_end)
            evidence_list.extend(news_items)
            
            macro_events = await self.macro_client.get_macro_context(evidence_start, evidence_end)
            evidence_list.extend(macro_events)
            
            # Generate hypotheses
            hypotheses = self.hypothesis_gen.generate_hypotheses(
                evidence_list, event_data, market_context
            )
            
            timeline = self.hypothesis_gen.build_timeline(evidence_list)
            
            # Build result dict
            return {
                "ticker": ticker,
                "drop_percent": event_data["drop_percent"],
                "hypotheses": [
                    {
                        "rank": h.rank,
                        "title": h.title,
                        "probability": h.probability,
                        "confidence": h.confidence.value,
                        "explanation": h.explanation,
                        "mechanism": h.mechanism,
                        "confirmation_check": h.confirmation_check,
                        "evidence_count": len(h.evidence)
                    }
                    for h in hypotheses
                ],
                "timeline": [
                    {
                        "timestamp": t.timestamp.isoformat(),
                        "description": t.description,
                        "source_url": t.evidence.source_url
                    }
                    for t in timeline
                ],
                "market_context": {
                    "market_return": market_context.market_return_pct,
                    "move_type": move_type,
                    "interpretation": market_context.interpretation
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_tool_definitions(self) -> List[Dict]:
        """Return MCP tool definitions."""
        return [
            {
                "name": "market.getChartHistory",
                "description": "Get historical price data for a ticker symbol",
                "parameters": {
                    "ticker": {"type": "string", "required": True},
                    "range": {"type": "string", "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y", "10y", "max"], "default": "max"},
                    "interval": {"type": "string", "enum": ["1m", "5m", "15m", "1h", "1d", "1wk", "1mo"], "default": "1d"}
                }
            },
            {
                "name": "market.getCorporateActions",
                "description": "Get stock splits and dividends for a ticker in a date range",
                "parameters": {
                    "ticker": {"type": "string", "required": True},
                    "start_date": {"type": "string", "required": True, "format": "ISO8601"},
                    "end_date": {"type": "string", "required": True, "format": "ISO8601"}
                }
            },
            {
                "name": "sec.searchFilings",
                "description": "Search SEC EDGAR for filings (8-K, 10-Q, 10-K, S-3, etc.)",
                "parameters": {
                    "ticker": {"type": "string", "required": True},
                    "start_date": {"type": "string", "required": True, "format": "ISO8601"},
                    "end_date": {"type": "string", "required": True, "format": "ISO8601"},
                    "forms": {"type": "array", "items": {"type": "string"}, "default": ["8-K", "10-Q", "10-K", "S-3"]}
                }
            },
            {
                "name": "news.search",
                "description": "Search news articles via GDELT with strict citations",
                "parameters": {
                    "ticker": {"type": "string", "required": True},
                    "company_name": {"type": "string", "required": False},
                    "start_date": {"type": "string", "required": True, "format": "ISO8601"},
                    "end_date": {"type": "string", "required": True, "format": "ISO8601"}
                }
            },
            {
                "name": "macro.getContext",
                "description": "Get macro economic events via FRED (rates, VIX, FX, oil)",
                "parameters": {
                    "start_date": {"type": "string", "required": True, "format": "ISO8601"},
                    "end_date": {"type": "string", "required": True, "format": "ISO8601"}
                }
            },
            {
                "name": "analysis.explainDrop",
                "description": "Complete analysis: ranked hypotheses with probabilities and citations",
                "parameters": {
                    "ticker": {"type": "string", "required": True},
                    "start_date": {"type": "string", "required": True, "format": "ISO8601"},
                    "end_date": {"type": "string", "required": True, "format": "ISO8601"}
                }
            }
        ]
    
    async def handle_tool_call(self, tool_name: str, parameters: Dict) -> Any:
        """Route tool calls to appropriate handlers."""
        handlers = {
            "market.getChartHistory": lambda: self.get_chart_history(**parameters),
            "market.getCorporateActions": lambda: self.get_corporate_actions(**parameters),
            "sec.searchFilings": lambda: self.search_sec_filings(**parameters),
            "news.search": lambda: self.search_news(**parameters),
            "macro.getContext": lambda: self.get_macro_context(**parameters),
            "analysis.explainDrop": lambda: self.explain_drop(**parameters),
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        
        return await handler()


async def main():
    """Run MCP server (stdio-based communication)."""
    server = MCPToolServer()
    
    # Print tool definitions on startup
    print(json.dumps({
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "serverInfo": {
                "name": "stock-drop-agent",
                "version": "0.2.0"
            },
            "capabilities": {
                "tools": server.get_tool_definitions()
            }
        }
    }), flush=True)
    
    # Listen for tool calls on stdin (MCP stdio protocol)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            if method == "tools/call":
                tool_name = params.get("name")
                tool_params = params.get("arguments", {})
                
                result = await server.handle_tool_call(tool_name, tool_params)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
                print(json.dumps(response), flush=True)
        
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if "id" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
