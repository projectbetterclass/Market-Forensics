"""Market and peer context analysis."""

from datetime import datetime
from typing import List, Optional
import statistics
from app.retrieval.prices import PriceClient
from app.models.schemas import MarketContext


class MarketContextAnalyzer:
    """Analyzes market, sector, and peer context for a stock move."""
    
    def __init__(self):
        self.price_client = PriceClient()
        
        # Default indices
        self.default_market_index = "^GSPC"  # S&P 500
        
        # Sector mapping (simplified - in production use a sector API)
        self.sector_etfs = {
            "Technology": "XLK",
            "Financials": "XLF",
            "Healthcare": "XLV",
            "Energy": "XLE",
            "Consumer Discretionary": "XLY",
            "Industrials": "XLI",
            "Consumer Staples": "XLP",
            "Utilities": "XLU",
            "Real Estate": "XLRE",
            "Materials": "XLB",
            "Communication Services": "XLC"
        }
    
    async def analyze_context(
        self,
        ticker: str,
        start_time: datetime,
        end_time: datetime,
        sector: Optional[str] = None,
        peers: Optional[List[str]] = None
    ) -> MarketContext:
        """
        Analyze market/sector/peer context for a stock move.
        
        Args:
            ticker: Stock ticker
            start_time: Start of the period
            end_time: End of the period
            sector: Sector name (optional)
            peers: List of peer tickers (optional)
        
        Returns:
            MarketContext object
        """
        # Get market index return
        market_return = await self.price_client.get_market_index_data(
            self.default_market_index,
            start_time,
            end_time
        )
        
        if market_return is None:
            market_return = 0.0
        
        # Get sector return if sector provided
        sector_return = None
        if sector and sector in self.sector_etfs:
            sector_etf = self.sector_etfs[sector]
            sector_return = await self.price_client.get_market_index_data(
                sector_etf,
                start_time,
                end_time
            )
        
        # Get peer returns if peers provided
        peer_median_return = None
        if peers:
            peer_returns = await self.price_client.get_peer_returns(
                peers,
                start_time,
                end_time
            )
            if peer_returns:
                peer_median_return = statistics.median(peer_returns)
        
        # Interpret the context
        interpretation = self._interpret_context(
            market_return,
            sector_return,
            peer_median_return
        )
        
        return MarketContext(
            market_index="S&P 500",
            market_return_pct=market_return,
            sector_name=sector,
            sector_return_pct=sector_return,
            peer_median_return_pct=peer_median_return,
            interpretation=interpretation
        )
    
    def _interpret_context(
        self,
        market_return: float,
        sector_return: Optional[float],
        peer_return: Optional[float]
    ) -> str:
        """Generate interpretation of market/sector/peer context."""
        interpretations = []
        
        # Market interpretation
        if market_return < -2:
            interpretations.append("Market was down significantly")
        elif market_return < -0.5:
            interpretations.append("Market was down slightly")
        elif market_return > 2:
            interpretations.append("Market was up significantly")
        elif market_return > 0.5:
            interpretations.append("Market was up slightly")
        else:
            interpretations.append("Market was relatively flat")
        
        # Sector interpretation
        if sector_return is not None:
            if sector_return < -2:
                interpretations.append("sector was down significantly")
            elif sector_return < -0.5:
                interpretations.append("sector was down slightly")
            elif sector_return > 0.5:
                interpretations.append("sector was up")
            else:
                interpretations.append("sector was flat")
        
        # Peer interpretation
        if peer_return is not None:
            if peer_return < -2:
                interpretations.append("peers were also down significantly")
            elif peer_return < -0.5:
                interpretations.append("peers were down slightly")
            elif peer_return > 0.5:
                interpretations.append("peers were up")
            else:
                interpretations.append("peers were flat")
        
        # Determine if move is company-specific
        if market_return > -1 and (sector_return is None or sector_return > -1):
            interpretations.append("suggesting this is mostly company-specific")
        elif market_return < -3 or (sector_return and sector_return < -3):
            interpretations.append("suggesting broad market/sector pressure")
        
        return "; ".join(interpretations) + "."
    
    def classify_move_type(
        self,
        stock_return: float,
        market_return: float,
        sector_return: Optional[float],
        peer_return: Optional[float]
    ) -> str:
        """
        Classify if the move is company-specific, sector-wide, or market-wide.
        
        Returns one of: "company_specific", "sector_wide", "market_wide", "mixed"
        """
        # If market is down a lot, likely market-wide
        if market_return < -3 and abs(stock_return - market_return) < 5:
            return "market_wide"
        
        # If sector is down similarly, likely sector-wide
        if sector_return and sector_return < -3 and abs(stock_return - sector_return) < 5:
            return "sector_wide"
        
        # If peers are down similarly, likely sector/peer issue
        if peer_return and peer_return < -3 and abs(stock_return - peer_return) < 5:
            return "sector_wide"
        
        # If market/sector/peers are mostly flat but stock is down, company-specific
        if market_return > -2 and (sector_return is None or sector_return > -2):
            return "company_specific"
        
        # Mixed if some factors present
        return "mixed"
