"""Yahoo Finance price data client with SWR caching."""

import httpx
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from app.models.schemas import ChartDataPoint, Evidence
from app.cache.swr_cache import SWRCache
from app.config import settings


class PriceClient:
    """Client for retrieving stock price data from Yahoo Finance."""
    
    def __init__(self):
        self._chart_cache = SWRCache(refresh_interval_seconds=settings.chart_cache_refresh_seconds)
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://finance.yahoo.com/",
            "Origin": "https://finance.yahoo.com"
        }
    
    async def get_chart_data_range(
        self,
        ticker: str,
        range_param: str = "max",
        interval: str = "1d"
    ) -> List[ChartDataPoint]:
        """
        Get chart data with SWR caching.
        
        Args:
            ticker: Stock ticker symbol
            range_param: Time range (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1d, 1wk, 1mo)
        """
        cache_key = f"chart:{ticker}:{range_param}:{interval}"
        return await self._chart_cache.get_or_fetch(
            cache_key,
            self._fetch_chart_data_uncached,
            ticker,
            range_param,
            interval
        )
    
    async def _fetch_chart_data_uncached(
        self,
        ticker: str,
        range_param: str,
        interval: str
    ) -> List[ChartDataPoint]:
        """Fetch chart data from Yahoo Finance (no cache)."""
        url = f"{settings.yahoo_finance_base_url}/v8/finance/chart/{ticker}"
        params = {"range": range_param, "interval": interval}
        
        async with httpx.AsyncClient(timeout=settings.http_timeout, headers=self._headers) as client:
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                raise ValueError(f"Yahoo Finance returned status {response.status_code}")
            
            data = response.json()
            
            if "chart" not in data or "result" not in data["chart"]:
                raise ValueError("Invalid response format from Yahoo Finance")
            
            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            quotes = result["indicators"]["quote"][0]
            closes = quotes["close"]
            
            chart_data = []
            for ts, close in zip(timestamps, closes):
                if close is not None:
                    chart_data.append(ChartDataPoint(
                        time=datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                        value=close
                    ))
            
            return chart_data
    
    async def get_price_data(
        self,
        ticker: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Get OHLCV data for a specific time window."""
        period1 = int(start_time.timestamp())
        period2 = int(end_time.timestamp())
        
        url = f"{settings.yahoo_finance_base_url}/v8/finance/chart/{ticker}"
        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d"
        }
        
        async with httpx.AsyncClient(timeout=settings.http_timeout, headers=self._headers) as client:
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            result = data["chart"]["result"][0]
            
            timestamps = result["timestamp"]
            quotes = result["indicators"]["quote"][0]
            
            if not timestamps or not quotes["close"]:
                return None
            
            start_price = next((c for c in quotes["close"] if c is not None), None)
            end_price = next((c for c in reversed(quotes["close"]) if c is not None), None)
            
            if start_price is None or end_price is None:
                return None
            
            drop_percent = ((end_price - start_price) / start_price) * 100
            
            volumes = [v for v in quotes["volume"] if v is not None]
            avg_volume = sum(volumes) / len(volumes) if volumes else 0
            volume_vs_average = (volumes[-1] / avg_volume) if avg_volume > 0 else 1.0
            
            return {
                "start_price": start_price,
                "end_price": end_price,
                "drop_percent": drop_percent,
                "volume_vs_average": volume_vs_average,
                "session_type": "regular"
            }
    
    async def get_corporate_actions(
        self,
        ticker: str,
        start_time: datetime,
        end_time: datetime
    ) -> tuple[List[Evidence], List[Evidence]]:
        """Get stock splits and dividends."""
        period1 = int(start_time.timestamp())
        period2 = int(end_time.timestamp())
        
        url = f"{settings.yahoo_finance_base_url}/v8/finance/chart/{ticker}"
        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "splits,dividends"
        }
        
        splits = []
        dividends = []
        
        async with httpx.AsyncClient(timeout=settings.http_timeout, headers=self._headers) as client:
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                return splits, dividends
            
            data = response.json()
            result = data["chart"]["result"][0]
            
            if "events" in result:
                events = result["events"]
                
                if "splits" in events:
                    for ts, split_data in events["splits"].items():
                        split_date = datetime.fromtimestamp(int(ts), tz=timezone.utc)
                        splits.append(Evidence(
                            timestamp=split_date,
                            source_type="corporate_action",
                            source_url=f"https://finance.yahoo.com/quote/{ticker}/history",
                            headline=f"Stock Split: {split_data.get('numerator', '?')}:{split_data.get('denominator', '?')}",
                            snippet=f"Split ratio: {split_data.get('splitRatio', 'N/A')}",
                            authority_score=0.95,
                            group="CorporateActions"
                        ))
                
                if "dividends" in events:
                    for ts, div_data in events["dividends"].items():
                        div_date = datetime.fromtimestamp(int(ts), tz=timezone.utc)
                        dividends.append(Evidence(
                            timestamp=div_date,
                            source_type="corporate_action",
                            source_url=f"https://finance.yahoo.com/quote/{ticker}/history",
                            headline=f"Dividend: ${div_data.get('amount', 0):.2f}",
                            authority_score=0.95,
                            group="CorporateActions"
                        ))
        
        return splits, dividends
    
    async def get_market_index_data(
        self,
        index_ticker: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[float]:
        """Get market index return for a period."""
        price_data = await self.get_price_data(index_ticker, start_time, end_time)
        return price_data["drop_percent"] if price_data else None
    
    async def get_peer_returns(
        self,
        peer_tickers: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> List[float]:
        """Get returns for a list of peer tickers."""
        returns = []
        for ticker in peer_tickers:
            price_data = await self.get_price_data(ticker, start_time, end_time)
            if price_data:
                returns.append(price_data["drop_percent"])
        return returns

    async def get_chart_data_by_dates(
        self,
        ticker: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1d"
    ) -> List[ChartDataPoint]:
        """
        Get chart data for a specific date range.
        
        Args:
            ticker: Stock ticker symbol
            start_time: Start date/time
            end_time: End date/time
            interval: Data interval (1d, 1wk, 1mo)
        
        Returns:
            List of ChartDataPoint objects (empty list if data not available)
        """
        period1 = int(start_time.timestamp())
        period2 = int(end_time.timestamp())
        
        url = f"{settings.yahoo_finance_base_url}/v8/finance/chart/{ticker}"
        params = {
            "period1": period1,
            "period2": period2,
            "interval": interval
        }
        
        try:
            async with httpx.AsyncClient(timeout=settings.http_timeout, headers=self._headers) as client:
                response = await client.get(url, params=params)
                
                # Handle 400 errors (e.g., date before ticker existed)
                if response.status_code == 400:
                    print(f"Warning: No data available for {ticker} in period {start_time.date()} to {end_time.date()}")
                    return []
                
                if response.status_code == 404:
                    print(f"Warning: Ticker {ticker} not found")
                    return []
                
                if response.status_code != 200:
                    print(f"Warning: Yahoo Finance returned status {response.status_code} for {ticker}")
                    return []
                
                data = response.json()
                
                # Handle error in response
                if "chart" in data and "error" in data["chart"] and data["chart"]["error"]:
                    error = data["chart"]["error"]
                    print(f"Warning: Yahoo Finance error for {ticker}: {error.get('description', 'Unknown error')}")
                    return []
                
                if "chart" not in data or "result" not in data["chart"]:
                    print(f"Warning: Invalid response format from Yahoo Finance for {ticker}")
                    return []
                
                result = data["chart"]["result"][0] if data["chart"]["result"] else {}
                timestamps = result.get("timestamp", [])
                quotes = result.get("indicators", {}).get("quote", [{}])[0]
                closes = quotes.get("close", [])
                
                chart_data = []
                for ts, close in zip(timestamps, closes):
                    if close is not None:
                        chart_data.append(ChartDataPoint(
                            time=datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                            value=close
                        ))
                
                return chart_data
        except Exception as e:
            print(f"Error fetching chart data for {ticker}: {str(e)}")
            return []
