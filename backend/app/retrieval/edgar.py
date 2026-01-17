"""SEC EDGAR filing retrieval client."""

import httpx
from datetime import datetime, timezone
from typing import List
from app.models.schemas import Evidence
from app.config import settings


class EdgarClient:
    """Client for SEC EDGAR filings."""
    
    def __init__(self):
        self._headers = {
            "User-Agent": "Stock Analysis App admin@example.com",
            "Accept": "application/json"
        }
    
    async def search_filings(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        form_types: List[str] = None
    ) -> List[Evidence]:
        """
        Search for SEC filings in a date range.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start of search window
            end_date: End of search window
            form_types: List of form types to search for (default: 8-K, 10-Q, 10-K, S-3, S-1)
        """
        if form_types is None:
            form_types = ["8-K", "10-Q", "10-K", "S-3", "S-1"]
        
        # Note: EDGAR API requires CIK, not ticker
        # For this implementation, we'll use a simplified approach
        # In production, map ticker → CIK first
        
        evidence_list = []
        
        # Placeholder: In real implementation, query EDGAR RSS feed or API
        # For now, return empty list (user will need to add EDGAR API integration)
        # Example EDGAR API endpoint: https://data.sec.gov/submissions/CIK##########.json
        
        # TODO: Implement actual EDGAR search
        # This requires: ticker→CIK mapping + submissions query + date filtering
        
        return evidence_list
