"""VIX volatility index retrieval client."""

import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from app.config import settings
from app.cache.swr_cache import SWRCache


class VixClient:
    """Client for retrieving VIX data from Yahoo Finance."""
    
    def __init__(self):
        self._cache = SWRCache(refresh_interval_seconds=300)  # 5 min cache
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://finance.yahoo.com/",
            "Origin": "https://finance.yahoo.com"
        }
    
    async def get_vix_data(self) -> Dict[str, Any]:
        """
        Get current VIX data with regime classification.
        
        Returns:
            {
                "value": float,
                "regime": "Compressed" | "Normal" | "Elevated",
                "interpretation": str,
                "as_of": datetime
            }
        """
        cache_key = "vix:current"
        return await self._cache.get_or_fetch(cache_key, self._fetch_vix_uncached)
    
    async def _fetch_vix_uncached(self) -> Dict[str, Any]:
        """Fetch VIX data from Yahoo Finance."""
        url = f"{settings.yahoo_finance_base_url}/v8/finance/chart/^VIX"
        params = {"range": "5d", "interval": "1d"}
        
        try:
            async with httpx.AsyncClient(timeout=settings.http_timeout, headers=self._headers) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    return self._default_vix_response()
                
                data = response.json()
                result = data["chart"]["result"][0]
                
                # Get latest close
                quotes = result["indicators"]["quote"][0]
                closes = [c for c in quotes["close"] if c is not None]
                
                if not closes:
                    return self._default_vix_response()
                
                current_vix = closes[-1]
                
                # Classify regime
                regime = self._classify_vix_regime(current_vix)
                interpretation = self._get_vix_interpretation(regime, current_vix)
                
                return {
                    "value": round(current_vix, 2),
                    "regime": regime,
                    "interpretation": interpretation,
                    "as_of": datetime.now(timezone.utc)
                }
        
        except Exception as e:
            print(f"VIX fetch error: {e}")
            return self._default_vix_response()
    
    def _classify_vix_regime(self, vix_value: float) -> str:
        """
        Classify VIX into regime categories.
        
        Historical context:
        - < 12: Very compressed (historically rare, often precedes volatility)
        - 12-20: Normal range
        - 20-30: Elevated (heightened concern)
        - > 30: High fear (crisis levels)
        """
        if vix_value < 12:
            return "Compressed"
        elif vix_value < 20:
            return "Normal"
        else:
            return "Elevated"
    
    def _get_vix_interpretation(self, regime: str, value: float) -> str:
        """Generate regime-appropriate interpretation."""
        if regime == "Compressed":
            return (
                f"VIX at {value:.1f} is historically low. "
                "Very low volatility has historically preceded periods of instability. "
                "This is a contextual signal, not a timing indicator."
            )
        elif regime == "Normal":
            return (
                f"VIX at {value:.1f} is within normal historical range. "
                "Market volatility expectations are moderate."
            )
        else:  # Elevated
            return (
                f"VIX at {value:.1f} indicates elevated volatility expectations. "
                "High volatility reflects fear already present in markets."
            )
    
    def _default_vix_response(self) -> Dict[str, Any]:
        """Default response when VIX data is unavailable."""
        return {
            "value": None,
            "regime": "Unknown",
            "interpretation": "VIX data not available",
            "as_of": datetime.now(timezone.utc)
        }
