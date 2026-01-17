"""Sector rotation analysis."""

from datetime import datetime, timedelta
from typing import List
from app.models.schemas import SectorRotation
from app.retrieval.prices import PriceClient


class RotationAnalyzer:
    """Analyzes sector rotation and leadership."""
    
    def __init__(self):
        self.price_client = PriceClient()
        
        # Sector ETFs
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
    
    async def get_rotation_context(
        self,
        lookback_days: int = 30
    ) -> SectorRotation:
        """
        Analyze sector rotation over a lookback period.
        
        Args:
            lookback_days: Number of days to look back
        
        Returns:
            SectorRotation object
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=lookback_days)
        
        # Get sector performance
        sector_performances = []
        
        for sector_name, etf_ticker in self.sector_etfs.items():
            try:
                price_data = await self.price_client.get_price_data(
                    etf_ticker,
                    start_time,
                    end_time
                )
                
                if price_data:
                    sector_performances.append({
                        "sector": sector_name,
                        "etf": etf_ticker,
                        "return_pct": price_data["drop_percent"]
                    })
            except:
                continue
        
        # Sort by performance
        sector_performances.sort(key=lambda x: x["return_pct"], reverse=True)
        
        # Interpret rotation
        interpretation = self._interpret_rotation(sector_performances)
        
        # Leadership concentration warning
        concentration_warning = None
        if len(sector_performances) >= 3:
            top_3_avg = sum(s["return_pct"] for s in sector_performances[:3]) / 3
            bottom_3_avg = sum(s["return_pct"] for s in sector_performances[-3:]) / 3
            spread = top_3_avg - bottom_3_avg
            
            if spread > 10:
                concentration_warning = (
                    f"Leadership appears concentrated: top 3 sectors outperformed bottom 3 by {spread:.1f}%. "
                    "Historically, high concentration has been associated with increased volatility risk."
                )
        
        return SectorRotation(
            sector_performances=sector_performances,
            leadership_concentration_warning=concentration_warning,
            interpretation=interpretation
        )
    
    def _interpret_rotation(self, sector_performances: List[dict]) -> str:
        """Interpret sector rotation patterns."""
        if not sector_performances:
            return "Insufficient data to determine sector rotation patterns."
        
        # Check if defensives (Utilities, Staples, Healthcare) are outperforming
        defensives = ["Utilities", "Consumer Staples", "Healthcare"]
        cyclicals = ["Energy", "Materials", "Industrials"]
        
        defensive_returns = [s["return_pct"] for s in sector_performances if s["sector"] in defensives]
        cyclical_returns = [s["return_pct"] for s in sector_performances if s["sector"] in cyclicals]
        
        if defensive_returns and cyclical_returns:
            avg_defensive = sum(defensive_returns) / len(defensive_returns)
            avg_cyclical = sum(cyclical_returns) / len(cyclical_returns)
            
            if avg_defensive > avg_cyclical + 3:
                return "Defensive sectors are outperforming cyclicals, historically associated with risk-off sentiment."
            elif avg_cyclical > avg_defensive + 3:
                return "Cyclical sectors are outperforming defensives, historically associated with risk-on sentiment."
        
        return "Sector rotation shows mixed patterns with no clear defensive or cyclical leadership."
