"""Event normalization and validation."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.retrieval.prices import PriceClient


class EventNormalizer:
    """Validates and normalizes stock drop events."""
    
    def __init__(self):
        self.price_client = PriceClient()
    
    async def validate_and_normalize(
        self,
        ticker: str,
        drop_percent: Optional[float],
        time_window_hours: int
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a stock drop event and normalize the data.
        
        Args:
            ticker: Stock ticker symbol
            drop_percent: Expected drop % (optional, will be calculated if None)
            time_window_hours: Lookback window in hours
        
        Returns:
            Normalized event data or None if invalid
        """
        # Calculate time window
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_window_hours)
        
        # Get price data
        price_data = await self.price_client.get_price_data(ticker, start_time, end_time)
        
        if not price_data:
            return None
        
        # Validate drop occurred
        actual_drop = price_data["drop_percent"]
        
        # If user specified a drop %, check if actual drop is significant
        if drop_percent and abs(actual_drop) < abs(drop_percent) * 0.5:
            # Actual drop is less than 50% of expected, might be wrong window
            return None
        
        # Check for splits/dividends (simplified - using pattern matching)
        is_likely_split = self._check_for_split(actual_drop)
        
        return {
            "ticker": ticker,
            "start_time": start_time,
            "end_time": end_time,
            "start_price": price_data["start_price"],
            "end_price": price_data["end_price"],
            "drop_percent": actual_drop,
            "volume_vs_average": price_data["volume_vs_average"],
            "session_type": price_data["session_type"],
            "is_likely_split": is_likely_split
        }
    
    def _check_for_split(self, drop_percent: float) -> bool:
        """
        Check if the drop might be due to a stock split.
        
        Common splits: 2:1 (-50%), 3:1 (-66.67%), 4:1 (-75%)
        """
        split_ratios = [-50.0, -66.67, -75.0, -80.0]
        tolerance = 2.0  # % tolerance
        
        for ratio in split_ratios:
            if abs(drop_percent - ratio) < tolerance:
                return True
        
        return False
