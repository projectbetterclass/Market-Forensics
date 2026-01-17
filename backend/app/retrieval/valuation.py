"""Valuation data providers (CAPE, Buffett Indicator, breadth)."""

import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from io import StringIO
import re

from app.cache.swr_cache import SWRCache
from app.config import settings


class ValuationProvider:
    """Provider for valuation stress indicators."""
    
    # Historical CAPE averages for percentile calculation
    CAPE_HISTORY = {
        "mean": 17.0,
        "median": 16.0,
        "percentile_80": 24.0,
        "percentile_90": 28.0,
        "percentile_95": 32.0,
    }
    
    # Historical Buffett Indicator levels
    BUFFETT_HISTORY = {
        "mean": 85.0,
        "median": 80.0,
        "fair_max": 100.0,
        "stretched_max": 140.0,
    }
    
    def __init__(self):
        self._cache = SWRCache(refresh_interval_seconds=settings.valuation_cache_refresh_seconds)
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*"
        }
    
    async def get_cape_ratio(self) -> Optional[Dict[str, Any]]:
        """
        Get current CAPE ratio from multpl.com or estimate from data.
        
        Returns:
            {
                "value": float,
                "percentile": float,
                "as_of": datetime
            }
        """
        cache_key = "valuation:cape"
        return await self._cache.get_or_fetch(cache_key, self._fetch_cape_uncached)
    
    async def _fetch_cape_uncached(self) -> Optional[Dict[str, Any]]:
        """Fetch CAPE data from public sources."""
        try:
            # Try multpl.com (scrape current CAPE)
            async with httpx.AsyncClient(timeout=15, headers=self._headers) as client:
                response = await client.get("https://www.multpl.com/shiller-pe")
                
                if response.status_code == 200:
                    html = response.text
                    
                    # Extract CAPE value from page
                    # Looking for pattern like "Current Shiller PE Ratio is 35.12"
                    match = re.search(r'Current Shiller PE Ratio[^\d]*(\d+\.?\d*)', html)
                    if match:
                        cape_value = float(match.group(1))
                        percentile = self._calculate_cape_percentile(cape_value)
                        
                        return {
                            "value": cape_value,
                            "percentile": percentile,
                            "as_of": datetime.now(timezone.utc)
                        }
                    
                    # Alternative pattern
                    match = re.search(r'<div id="current"[^>]*>(\d+\.?\d*)', html)
                    if match:
                        cape_value = float(match.group(1))
                        percentile = self._calculate_cape_percentile(cape_value)
                        
                        return {
                            "value": cape_value,
                            "percentile": percentile,
                            "as_of": datetime.now(timezone.utc)
                        }
        except Exception as e:
            print(f"CAPE fetch error from multpl.com: {e}")
        
        # Fallback: Try Yahoo Finance for S&P 500 PE as a proxy
        try:
            async with httpx.AsyncClient(timeout=15, headers=self._headers) as client:
                # Get S&P 500 summary info which sometimes includes PE
                response = await client.get(
                    "https://query1.finance.yahoo.com/v10/finance/quoteSummary/%5EGSPC",
                    params={"modules": "summaryDetail,defaultKeyStatistics"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("quoteSummary", {}).get("result", [])
                    if result:
                        # Try to get trailing PE
                        summary = result[0].get("summaryDetail", {})
                        pe = summary.get("trailingPE", {}).get("raw")
                        
                        if pe:
                            # Convert PE to approximate CAPE (PE is typically lower than CAPE)
                            # Historical ratio is roughly CAPE ≈ PE * 1.3-1.5
                            cape_estimate = pe * 1.4
                            percentile = self._calculate_cape_percentile(cape_estimate)
                            
                            return {
                                "value": round(cape_estimate, 2),
                                "percentile": percentile,
                                "as_of": datetime.now(timezone.utc),
                                "note": "Estimated from trailing PE"
                            }
        except Exception as e:
            print(f"CAPE fallback error: {e}")
        
        return None
    
    def _calculate_cape_percentile(self, cape_value: float) -> float:
        """Calculate historical percentile for a CAPE value."""
        # Simplified percentile based on historical distribution
        if cape_value <= 10:
            return 5.0
        elif cape_value <= 12:
            return 15.0
        elif cape_value <= 15:
            return 30.0
        elif cape_value <= 17:
            return 50.0
        elif cape_value <= 20:
            return 65.0
        elif cape_value <= 24:
            return 80.0
        elif cape_value <= 28:
            return 90.0
        elif cape_value <= 32:
            return 95.0
        else:
            return 98.0
    
    async def get_buffett_indicator(self) -> Optional[Dict[str, Any]]:
        """
        Get Buffett Indicator (Market Cap / GDP).
        
        Returns:
            {
                "value": float (as percentage),
                "percentile": float,
                "zone": str,
                "as_of": datetime
            }
        """
        cache_key = "valuation:buffett"
        return await self._cache.get_or_fetch(cache_key, self._fetch_buffett_uncached)
    
    async def _fetch_buffett_uncached(self) -> Optional[Dict[str, Any]]:
        """Fetch Buffett Indicator from market cap and GDP estimates."""
        
        # Method 1: Estimate from total US stock market ETFs
        try:
            async with httpx.AsyncClient(timeout=15, headers=self._headers) as client:
                # Get VTI (Vanguard Total Stock Market) as a proxy for total market cap
                # VTI tracks ~4000 stocks representing nearly 100% of US market
                vti_response = await client.get(
                    f"{settings.yahoo_finance_base_url}/v8/finance/chart/VTI",
                    params={"range": "1d", "interval": "1d"}
                )
                
                if vti_response.status_code == 200:
                    data = vti_response.json()
                    result = data.get("chart", {}).get("result", [])
                    if result:
                        closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
                        if closes and closes[-1]:
                            vti_price = closes[-1]
                            
                            # VTI shares outstanding ~ 1.3 billion (approx)
                            # VTI price * shares = market cap of VTI
                            # VTI holds about $400B AUM, representing ~$50 trillion market
                            # So rough conversion: VTI price * 200 ≈ total market cap in billions
                            
                            # More accurate: Use known relationship
                            # As of late 2024/early 2025, VTI ~$280 corresponds to ~$50T market cap
                            # US GDP ~$28-29 trillion
                            # Buffett Indicator = 50/28 * 100 ≈ 180%
                            
                            # Linear scaling from VTI price
                            # VTI $280 → $50T market cap → Buffett ~180%
                            market_cap_trillion = (vti_price / 280) * 50
                            gdp_trillion = 28.5  # US GDP 2025 estimate
                            
                            buffett_value = (market_cap_trillion / gdp_trillion) * 100
                            
                            # Clamp to reasonable range
                            buffett_value = max(50, min(250, buffett_value))
                            
                            percentile = self._calculate_buffett_percentile(buffett_value)
                            zone = self._get_buffett_zone(buffett_value)
                            
                            return {
                                "value": round(buffett_value, 1),
                                "percentile": percentile,
                                "zone": zone,
                                "as_of": datetime.now(timezone.utc),
                                "note": "Estimated from VTI/GDP"
                            }
        except Exception as e:
            print(f"Buffett VTI method error: {e}")
        
        # Method 2: Use SPY market cap as proxy
        try:
            async with httpx.AsyncClient(timeout=15, headers=self._headers) as client:
                spy_response = await client.get(
                    f"{settings.yahoo_finance_base_url}/v8/finance/chart/SPY",
                    params={"range": "1d", "interval": "1d"}
                )
                
                if spy_response.status_code == 200:
                    data = spy_response.json()
                    result = data.get("chart", {}).get("result", [])
                    if result:
                        closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
                        if closes and closes[-1]:
                            spy_price = closes[-1]
                            
                            # S&P 500 represents ~80% of US market cap
                            # SPY ~$580 corresponds to S&P 500 ~$45T, total market ~$55T
                            market_cap_trillion = (spy_price / 580) * 55
                            gdp_trillion = 28.5
                            
                            buffett_value = (market_cap_trillion / gdp_trillion) * 100
                            buffett_value = max(50, min(250, buffett_value))
                            
                            percentile = self._calculate_buffett_percentile(buffett_value)
                            zone = self._get_buffett_zone(buffett_value)
                            
                            return {
                                "value": round(buffett_value, 1),
                                "percentile": percentile,
                                "zone": zone,
                                "as_of": datetime.now(timezone.utc),
                                "note": "Estimated from SPY/GDP"
                            }
        except Exception as e:
            print(f"Buffett SPY method error: {e}")
        
        return None
    
    def _calculate_buffett_percentile(self, buffett_value: float) -> float:
        """Calculate historical percentile for Buffett Indicator."""
        if buffett_value <= 60:
            return 10.0
        elif buffett_value <= 75:
            return 25.0
        elif buffett_value <= 85:
            return 40.0
        elif buffett_value <= 100:
            return 55.0
        elif buffett_value <= 120:
            return 75.0
        elif buffett_value <= 140:
            return 85.0
        elif buffett_value <= 160:
            return 92.0
        elif buffett_value <= 180:
            return 96.0
        else:
            return 99.0
    
    def _get_buffett_zone(self, buffett_value: float) -> str:
        """Get Buffett Indicator zone label."""
        if buffett_value <= 100:
            return "Fair"
        elif buffett_value <= 140:
            return "Stretched"
        else:
            return "Extreme"
    
    async def get_breadth_reading(self) -> Optional[Dict[str, Any]]:
        """
        Get market breadth reading using RSP vs SPY divergence.
        
        Returns:
            {
                "value": float,
                "interpretation": str,
                "as_of": datetime
            }
        """
        cache_key = "valuation:breadth"
        return await self._cache.get_or_fetch(cache_key, self._fetch_breadth_uncached)
    
    async def _fetch_breadth_uncached(self) -> Optional[Dict[str, Any]]:
        """Fetch breadth data using ETF comparison."""
        try:
            async with httpx.AsyncClient(timeout=15, headers=self._headers) as client:
                # Get SPY and RSP 30-day returns
                spy_response = await client.get(
                    f"{settings.yahoo_finance_base_url}/v8/finance/chart/SPY",
                    params={"range": "1mo", "interval": "1d"}
                )
                rsp_response = await client.get(
                    f"{settings.yahoo_finance_base_url}/v8/finance/chart/RSP",
                    params={"range": "1mo", "interval": "1d"}
                )
                
                if spy_response.status_code == 200 and rsp_response.status_code == 200:
                    spy_data = spy_response.json()
                    rsp_data = rsp_response.json()
                    
                    spy_closes = spy_data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                    rsp_closes = rsp_data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                    
                    # Get first and last non-null values
                    spy_start = next(c for c in spy_closes if c is not None)
                    spy_end = next(c for c in reversed(spy_closes) if c is not None)
                    rsp_start = next(c for c in rsp_closes if c is not None)
                    rsp_end = next(c for c in reversed(rsp_closes) if c is not None)
                    
                    spy_return = ((spy_end - spy_start) / spy_start) * 100
                    rsp_return = ((rsp_end - rsp_start) / rsp_start) * 100
                    
                    divergence = rsp_return - spy_return
                    
                    if divergence > 2:
                        interpretation = "Broad participation: equal-weight outperforming. Historically associated with healthier market conditions."
                    elif divergence < -2:
                        interpretation = "Narrow participation: cap-weight outperforming. A smaller number of large stocks are driving gains."
                    else:
                        interpretation = "Moderate breadth: no significant divergence."
                    
                    return {
                        "value": round(divergence, 2),
                        "interpretation": interpretation,
                        "as_of": datetime.now(timezone.utc)
                    }
        except Exception as e:
            print(f"Breadth fetch error: {e}")
        
        return None
