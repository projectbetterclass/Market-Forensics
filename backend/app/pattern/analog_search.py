"""Pattern analog search with outcome dispersion analysis."""

import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
from app.models.schemas import PatternAnalog, ChartDataPoint
from app.retrieval.prices import PriceClient
from app.cache.swr_cache import SWRCache
from app.config import settings


class PatternAnalogEngine:
    """Searches for historical pattern analogs with outcome dispersion."""
    
    def __init__(self):
        self.price_client = PriceClient()
        self._cache = SWRCache(refresh_interval_seconds=settings.pattern_cache_refresh_seconds)
    
    async def find_analogs(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        max_analogs: int = 10
    ) -> List[PatternAnalog]:
        """
        Find historical pattern analogs for a given price movement.
        
        Args:
            ticker: Stock ticker
            start_date: Start of target pattern
            end_date: End of target pattern
            max_analogs: Maximum number of analogs to return
        
        Returns:
            List of PatternAnalog objects with outcome dispersion
        """
        cache_key = f"pattern:{ticker}:{start_date.isoformat()}:{end_date.isoformat()}"
        return await self._cache.get_or_fetch(
            cache_key,
            self._find_analogs_uncached,
            ticker,
            start_date,
            end_date,
            max_analogs
        )
    
    async def _find_analogs_uncached(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        max_analogs: int
    ) -> List[PatternAnalog]:
        """Find pattern analogs (uncached)."""
        # Get target pattern
        target_prices = await self.price_client.get_price_data(ticker, start_date, end_date)
        if not target_prices:
            return []
        
        # Normalize target pattern to returns
        target_pattern = self._normalize_pattern(target_prices)
        if target_pattern is None or len(target_pattern) < 5:
            return []
        
        # Search historical data for similar patterns
        # For now, we'll search the same ticker's history
        # In production, could also search peer tickers and indices
        
        # Get long history for the ticker
        try:
            historical_data = await self.price_client.get_chart_data_range(ticker, "max", "1d")
        except:
            return []
        
        if len(historical_data) < 100:
            return []
        
        # Convert to price array
        historical_prices = [point.value for point in historical_data]
        historical_dates = [datetime.fromisoformat(point.time) for point in historical_data]
        
        # Sliding window search
        pattern_length = len(target_pattern)
        analogs = []
        
        for i in range(len(historical_prices) - pattern_length - 252):  # Leave room for 1-year forward
            window_prices = historical_prices[i:i + pattern_length]
            window_pattern = self._normalize_window(window_prices)
            
            if window_pattern is None:
                continue
            
            # Calculate similarity
            similarity = self._calculate_similarity(target_pattern, window_pattern)
            
            if similarity > 0.7:  # Threshold for "similar"
                window_start = historical_dates[i]
                window_end = historical_dates[i + pattern_length - 1]
                
                # Skip if overlaps with target period (too close)
                if abs((window_start - start_date).days) < 90:
                    continue
                
                # Calculate outcome dispersion
                outcomes = await self._calculate_outcomes(
                    historical_prices,
                    historical_dates,
                    i + pattern_length - 1
                )
                
                analog = PatternAnalog(
                    analog_id=f"{ticker}_{window_start.strftime('%Y%m%d')}",
                    ticker=ticker,
                    start_date=window_start,
                    end_date=window_end,
                    similarity_score=similarity,
                    pattern_description=f"Similar {pattern_length}-day pattern from {window_start.strftime('%Y-%m-%d')}",
                    outcomes=outcomes,
                    sentiment_at_time=None,  # TODO: Add GDELT sentiment for that period
                    narrative_tags=[]  # TODO: Extract narrative tags from news
                )
                
                analogs.append(analog)
        
        # Sort by similarity and return top N
        analogs.sort(key=lambda a: a.similarity_score, reverse=True)
        return analogs[:max_analogs]
    
    def _normalize_pattern(self, price_data: Dict[str, Any]) -> Optional[np.ndarray]:
        """Normalize price data to returns."""
        # This is a placeholder - actual implementation would extract OHLC array
        # For now, return None to indicate not yet implemented
        return None
    
    def _normalize_window(self, prices: List[float]) -> Optional[np.ndarray]:
        """Normalize a price window to returns."""
        if len(prices) < 2:
            return None
        
        try:
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] == 0:
                    return None
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
            
            return np.array(returns)
        except:
            return None
    
    def _calculate_similarity(self, pattern1: np.ndarray, pattern2: np.ndarray) -> float:
        """Calculate cosine similarity between two patterns."""
        try:
            sim = cosine_similarity([pattern1], [pattern2])[0][0]
            return float(sim)
        except:
            return 0.0
    
    async def _calculate_outcomes(
        self,
        historical_prices: List[float],
        historical_dates: List[datetime],
        pattern_end_idx: int
    ) -> Dict[str, Any]:
        """
        Calculate outcome dispersion at multiple horizons.
        
        Horizons: 1w, 1m, 3m, 6m, 12m
        
        Returns:
            {
                "1w": {"return_pct": X, "percentile": Y},
                "1m": {"return_pct": X, "percentile": Y},
                ...
            }
        """
        outcomes = {}
        
        horizons = {
            "1w": 5,
            "1m": 21,
            "3m": 63,
            "6m": 126,
            "12m": 252
        }
        
        for horizon_name, horizon_days in horizons.items():
            end_idx = pattern_end_idx + horizon_days
            if end_idx < len(historical_prices):
                start_price = historical_prices[pattern_end_idx]
                end_price = historical_prices[end_idx]
                
                if start_price > 0:
                    return_pct = ((end_price - start_price) / start_price) * 100
                    
                    outcomes[horizon_name] = {
                        "return_pct": round(return_pct, 2),
                        "percentile": None,  # TODO: Calculate percentile vs all analogs
                        "as_of": historical_dates[end_idx].isoformat()
                    }
            else:
                outcomes[horizon_name] = {
                    "return_pct": None,
                    "percentile": None,
                    "as_of": None,
                    "note": "Insufficient forward data"
                }
        
        return outcomes
