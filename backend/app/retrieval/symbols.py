"""
Symbol universe loader for US stocks and ETFs.

Downloads and caches symbol data from Alpha Vantage daily.
"""

import httpx
import json
import csv
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional
from app.config import settings
import asyncio


class SymbolUniverse:
    """Manages US stock and ETF symbol universe."""
    
    def __init__(self):
        self.symbols: List[Dict[str, any]] = []
        self.last_updated: Optional[datetime] = None
        self.cache_file = Path("app/data/symbols_cache.json")
        self.fallback_file = Path("app/data/symbols_fallback.json")
        self.cache_file.parent.mkdir(exist_ok=True)
        self._lock = asyncio.Lock()
    
    async def get_symbols(self, force_refresh: bool = False) -> List[Dict[str, any]]:
        """
        Get all symbols, refreshing if cache is stale.
        
        Returns:
            List of symbol dicts with: symbol, display_symbol, name, exchange, is_etf
        """
        async with self._lock:
            # Check if we need to refresh
            needs_refresh = (
                force_refresh or
                not self.symbols or
                not self.last_updated or
                datetime.now(timezone.utc) - self.last_updated > timedelta(hours=24)
            )
            
            if needs_refresh:
                # Try to download fresh data
                try:
                    print("Downloading fresh symbol data from NASDAQ Trader...")
                    await self._download_and_parse()
                    if len(self.symbols) > 0:
                        self._save_cache()
                        print(f"Symbol universe loaded: {len(self.symbols)} symbols")
                    else:
                        print("Download returned 0 symbols, falling back...")
                        # Fall back to cached data if available
                        self._load_cache()
                        # If still no symbols, load fallback
                        if not self.symbols:
                            self._load_fallback()
                except Exception as e:
                    print(f"Error downloading symbols: {e}")
                    # Fall back to cached data if available
                    if not self.symbols:
                        self._load_cache()
                    # If still no symbols, load fallback
                    if not self.symbols:
                        self._load_fallback()
            elif not self.symbols:
                # Load from cache if not in memory
                self._load_cache()
                # If still no symbols, load fallback
                if not self.symbols:
                    self._load_fallback()
            
            return self.symbols
    
    async def _download_and_parse(self):
        """Download Alpha Vantage LISTING_STATUS and parse symbols."""
        # Try Alpha Vantage first (comprehensive list)
        symbols = await self._download_from_alphavantage()
        
        # Fallback to NASDAQ Trader if Alpha Vantage fails
        if len(symbols) == 0:
            print("Alpha Vantage failed, trying NASDAQ Trader...")
            symbols = await self._download_from_nasdaq_trader()
        
        if len(symbols) > 0:
            self.symbols = symbols
            self.last_updated = datetime.now(timezone.utc)
            print(f"Successfully loaded {len(symbols)} symbols")
        else:
            print("No symbols downloaded from any source")
    
    async def _download_from_alphavantage(self) -> List[Dict[str, any]]:
        """Download symbols from Alpha Vantage LISTING_STATUS."""
        api_key = settings.alphavantage_api_key
        
        if not api_key or api_key == "demo":
            print("Alpha Vantage API key not configured (using 'demo' or empty)")
            return []
        
        url = f"https://www.alphavantage.co/query?function=LISTING_STATUS&state=active&apikey={api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Parse CSV response
                csv_text = response.text
                reader = csv.DictReader(io.StringIO(csv_text))
                
                symbols = []
                for row in reader:
                    symbol = row.get('symbol', '').strip()
                    name = row.get('name', '').strip()
                    exchange = row.get('exchange', '').strip()
                    asset_type = row.get('assetType', '').strip()
                    
                    if not symbol or not name:
                        continue
                    
                    # Convert to Yahoo Finance format (replace . with -)
                    yahoo_symbol = symbol.replace('.', '-')
                    
                    # Determine if ETF
                    is_etf = asset_type.upper() == 'ETF'
                    
                    symbols.append({
                        'symbol': yahoo_symbol,
                        'display_symbol': symbol,
                        'name': name,
                        'exchange': exchange,
                        'is_etf': is_etf
                    })
                
                print(f"Downloaded {len(symbols)} symbols from Alpha Vantage")
                return symbols
                
        except Exception as e:
            print(f"Error fetching from Alpha Vantage: {e}")
            return []
    
    async def _download_from_nasdaq_trader(self) -> List[Dict[str, any]]:
        """Download symbols from NASDAQ Trader (fallback)."""
        nasdaq_listed_url = "https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
        other_listed_url = "https://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
        
        symbols = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Download NASDAQ-listed symbols
            try:
                nasdaq_response = await client.get(nasdaq_listed_url)
                nasdaq_response.raise_for_status()
                nasdaq_symbols = self._parse_nasdaq_listed(nasdaq_response.text)
                symbols.extend(nasdaq_symbols)
                print(f"Downloaded {len(nasdaq_symbols)} NASDAQ symbols")
            except Exception as e:
                print(f"Error fetching NASDAQ listed: {e}")
            
            # Download other-listed symbols (NYSE, AMEX, etc.)
            try:
                other_response = await client.get(other_listed_url)
                other_response.raise_for_status()
                other_symbols = self._parse_other_listed(other_response.text)
                symbols.extend(other_symbols)
                print(f"Downloaded {len(other_symbols)} other exchange symbols")
            except Exception as e:
                print(f"Error fetching other listed: {e}")
        
        return symbols
    
    def _parse_nasdaq_listed(self, content: str) -> List[Dict[str, any]]:
        """Parse nasdaqlisted.txt file."""
        symbols = []
        lines = content.strip().split('\n')
        
        # Skip header and footer
        for line in lines[1:-1]:
            parts = line.split('|')
            if len(parts) < 4:
                continue
            
            symbol = parts[0].strip()
            name = parts[1].strip()
            etf = parts[4].strip() == 'Y' if len(parts) > 4 else False
            test_issue = parts[5].strip() == 'Y' if len(parts) > 5 else False
            
            # Skip test issues
            if test_issue or not symbol or not name:
                continue
            
            # Convert to Yahoo Finance format (replace . with -)
            yahoo_symbol = symbol.replace('.', '-')
            
            symbols.append({
                'symbol': yahoo_symbol,
                'display_symbol': symbol,
                'name': name,
                'exchange': 'NASDAQ',
                'is_etf': etf
            })
        
        return symbols
    
    def _parse_other_listed(self, content: str) -> List[Dict[str, any]]:
        """Parse otherlisted.txt file (NYSE, AMEX, ARCA, etc.)."""
        symbols = []
        lines = content.strip().split('\n')
        
        # Skip header and footer
        for line in lines[1:-1]:
            parts = line.split('|')
            if len(parts) < 4:
                continue
            
            symbol = parts[0].strip()
            name = parts[1].strip()
            exchange = parts[2].strip()
            etf = parts[4].strip() == 'Y' if len(parts) > 4 else False
            test_issue = parts[5].strip() == 'Y' if len(parts) > 5 else False
            
            # Skip test issues
            if test_issue or not symbol or not name:
                continue
            
            # Convert to Yahoo Finance format
            yahoo_symbol = symbol.replace('.', '-').replace('$', '-P')
            
            symbols.append({
                'symbol': yahoo_symbol,
                'display_symbol': symbol,
                'name': name,
                'exchange': exchange,
                'is_etf': etf
            })
        
        return symbols
    
    def _save_cache(self):
        """Save symbols to disk cache."""
        try:
            cache_data = {
                'symbols': self.symbols,
                'last_updated': self.last_updated.isoformat() if self.last_updated else None
            }
            self.cache_file.write_text(json.dumps(cache_data, indent=2))
        except Exception as e:
            print(f"Error saving symbol cache: {e}")
    
    def _load_cache(self):
        """Load symbols from disk cache."""
        try:
            if self.cache_file.exists():
                cache_data = json.loads(self.cache_file.read_text())
                self.symbols = cache_data.get('symbols', [])
                last_updated_str = cache_data.get('last_updated')
                if last_updated_str:
                    self.last_updated = datetime.fromisoformat(last_updated_str)
                print(f"Loaded {len(self.symbols)} symbols from cache")
        except Exception as e:
            print(f"Error loading symbol cache: {e}")
            self.symbols = []
            self.last_updated = None
    
    def _load_fallback(self):
        """Load symbols from bundled fallback file."""
        try:
            if self.fallback_file.exists():
                fallback_data = json.loads(self.fallback_file.read_text())
                self.symbols = fallback_data.get('symbols', [])
                last_updated_str = fallback_data.get('last_updated')
                if last_updated_str:
                    self.last_updated = datetime.fromisoformat(last_updated_str)
                print(f"Loaded {len(self.symbols)} symbols from fallback (bundled snapshot)")
        except Exception as e:
            print(f"Error loading fallback symbols: {e}")
            self.symbols = []
            self.last_updated = None
    
    async def search(self, query: str, limit: int = 20) -> List[Dict[str, any]]:
        """
        Search symbols by symbol or name.
        
        Args:
            query: Search query (symbol or company name)
            limit: Maximum number of results
        
        Returns:
            List of matching symbols sorted by relevance
        """
        if not query:
            return []
        
        symbols = await self.get_symbols()
        query_upper = query.upper()
        query_lower = query.lower()
        
        matches = []
        
        for sym in symbols:
            score = 0
            
            # Exact symbol match (highest priority)
            if sym['symbol'].upper() == query_upper:
                score = 1000
            # Symbol prefix match
            elif sym['symbol'].upper().startswith(query_upper):
                score = 500
            # Symbol contains query
            elif query_upper in sym['symbol'].upper():
                score = 100
            # Name starts with query
            elif sym['name'].lower().startswith(query_lower):
                score = 50
            # Name contains query
            elif query_lower in sym['name'].lower():
                score = 10
            
            if score > 0:
                matches.append({
                    'score': score,
                    'data': sym
                })
        
        # Sort by score (descending) and return top results
        matches.sort(key=lambda x: x['score'], reverse=True)
        return [m['data'] for m in matches[:limit]]


# Global singleton instance
_symbol_universe: Optional[SymbolUniverse] = None


def get_symbol_universe() -> SymbolUniverse:
    """Get the global symbol universe instance."""
    global _symbol_universe
    if _symbol_universe is None:
        _symbol_universe = SymbolUniverse()
    return _symbol_universe
