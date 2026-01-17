"""GDELT news retrieval client."""

import httpx
from datetime import datetime, timezone
from typing import List, Optional, Set
from app.models.schemas import Evidence
from app.config import settings


class NewsClient:
    """Client for GDELT news API."""
    
    def __init__(self):
        self._headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
    
    async def search_news(
        self,
        ticker: str,
        company_name: Optional[str],
        start_time: datetime,
        end_time: datetime,
        max_results: int = 50
    ) -> List[Evidence]:
        """
        Search for news articles using GDELT.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name (optional, helps improve results)
            start_time: Start of search window
            end_time: End of search window
            max_results: Maximum number of results to return
        """
        evidence_list = []
        
        # Build search query
        query = ticker
        if company_name:
            query = f"{company_name} OR {ticker}"
        
        # GDELT API doc mode endpoint
        url = f"{settings.gdelt_base_url}/doc/doc"
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": max_results,
            "format": "json",
            "startdatetime": start_time.strftime("%Y%m%d%H%M%S"),
            "enddatetime": end_time.strftime("%Y%m%d%H%M%S")
        }
        
        try:
            async with httpx.AsyncClient(timeout=settings.http_timeout, headers=self._headers) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    return evidence_list
                
                data = response.json()
                articles = data.get("articles", [])
                
                # Deduplicate by URL
                seen_urls: Set[str] = set()
                
                for article in articles:
                    url_str = article.get("url", "")
                    if url_str in seen_urls or not url_str:
                        continue
                    seen_urls.add(url_str)
                    
                    # Parse date
                    date_str = article.get("seendate", "")
                    try:
                        article_time = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                    except:
                        article_time = start_time
                    
                    # Classify source type and authority
                    domain = article.get("domain", "")
                    authority_score = self._calculate_authority(domain)
                    
                    evidence = Evidence(
                        timestamp=article_time,
                        source_type="news",
                        source_url=url_str,
                        headline=article.get("title", "Unknown headline"),
                        snippet=article.get("description", ""),
                        authority_score=authority_score,
                        group="News"
                    )
                    
                    evidence_list.append(evidence)
        
        except Exception as e:
            print(f"GDELT search error: {e}")
        
        return evidence_list
    
    def _calculate_authority(self, domain: str) -> float:
        """Calculate authority score based on domain."""
        domain_lower = domain.lower()
        
        # Tier 1: Premium financial news
        if any(d in domain_lower for d in ["wsj.com", "ft.com", "bloomberg.com", "reuters.com"]):
            return 0.90
        
        # Tier 2: Major news outlets
        if any(d in domain_lower for d in ["nytimes.com", "washingtonpost.com", "cnbc.com", "marketwatch.com"]):
            return 0.80
        
        # Tier 3: General business news
        if any(d in domain_lower for d in ["forbes.com", "fortune.com", "barrons.com", "thestreet.com"]):
            return 0.70
        
        # Tier 4: Tech/industry publications
        if any(d in domain_lower for d in ["techcrunch.com", "theverge.com", "arstechnica.com"]):
            return 0.65
        
        # Default: unknown source
        return 0.50
