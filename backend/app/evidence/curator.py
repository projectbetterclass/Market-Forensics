"""Market Evidence Curator - validate, dedupe, classify, score, and group sources."""

from datetime import datetime, timezone
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
import re
from app.models.schemas import Evidence


class EvidenceCurator:
    """
    Curator that filters, deduplicates, classifies, and scores evidence sources.
    
    Philosophy: Quality > Quantity. Reduce noise, not amplify it.
    """
    
    # Patterns that indicate generic/listicle content (to filter out)
    GENERIC_PATTERNS = [
        r'\btop\s+\d+\s+stocks?\b',
        r'\bbest\s+stocks?\s+to\s+buy\b',
        r'\bstocks?\s+to\s+watch\b',
        r'\bpicks?\s+of\s+the\s+(day|week|month)\b',
        r'\bportfolio\s+update\b',
        r'\bwatchlist\b',
    ]
    
    def __init__(self):
        self.generic_regex = re.compile('|'.join(self.GENERIC_PATTERNS), re.IGNORECASE)
    
    def curate_evidence(
        self,
        evidence_list: List[Evidence],
        ticker: str,
        company_name: Optional[str],
        start_time: datetime,
        end_time: datetime,
        evidence_window_start: datetime,
        evidence_window_end: datetime
    ) -> Dict[str, any]:
        """
        Curate evidence according to strict quality standards.
        
        Returns a dictionary with:
        - groups: Dict[category, list of sources]
        - disclaimer_if_narrative_only: str or None
        - total_validated: int
        - total_collapsed: int
        """
        # Step 1: Validate
        validated = self._validate_evidence(
            evidence_list,
            ticker,
            company_name,
            evidence_window_start,
            evidence_window_end
        )
        
        # Step 2: Deduplicate by URL
        deduped = self._deduplicate_by_url(validated)
        
        # Step 3: Collapse syndication
        collapsed, collapse_count = self._collapse_syndication(deduped)
        
        # Step 4: Classify
        classified = self._classify_evidence(collapsed, ticker, company_name)
        
        # Step 5: Score
        scored = self._score_evidence(classified, start_time, end_time, ticker, company_name)
        
        # Step 6: Group by category and rank
        groups = self._group_and_rank(scored)
        
        # Step 7: Check if narrative-only
        disclaimer = self._check_narrative_only(groups)
        
        return {
            'groups': groups,
            'disclaimer_if_narrative_only': disclaimer,
            'total_validated': len(validated),
            'total_collapsed': collapse_count
        }
    
    def _validate_evidence(
        self,
        evidence_list: List[Evidence],
        ticker: str,
        company_name: Optional[str],
        window_start: datetime,
        window_end: datetime
    ) -> List[Evidence]:
        """
        Validate evidence: drop items outside window, drop generics.
        """
        validated = []
        
        for ev in evidence_list:
            # Check time window
            if ev.timestamp < window_start or ev.timestamp > window_end:
                continue
            
            # Check for generic/listicle patterns
            if self.generic_regex.search(ev.headline):
                continue
            
            # Verify it references the company (loose check for now)
            headline_lower = ev.headline.lower()
            ticker_lower = ticker.lower()
            company_lower = company_name.lower() if company_name else ""
            
            # Accept if ticker or company name is in headline, or if it's SEC/macro
            if (ticker_lower in headline_lower or 
                (company_lower and company_lower in headline_lower) or
                ev.source_type in ["sec_filing", "macro", "corporate_action"]):
                validated.append(ev)
        
        return validated
    
    def _deduplicate_by_url(self, evidence_list: List[Evidence]) -> List[Evidence]:
        """Remove duplicate URLs."""
        seen_urls: Set[str] = set()
        deduped = []
        
        for ev in evidence_list:
            url_normalized = ev.source_url.lower().strip()
            if url_normalized not in seen_urls:
                seen_urls.add(url_normalized)
                deduped.append(ev)
        
        return deduped
    
    def _collapse_syndication(
        self,
        evidence_list: List[Evidence]
    ) -> Tuple[List[Evidence], int]:
        """
        Collapse syndicated articles (same headline) into one entry.
        Keep earliest + highest authority.
        """
        # Group by normalized headline
        headline_groups: Dict[str, List[Evidence]] = defaultdict(list)
        
        for ev in evidence_list:
            # Normalize: lowercase, remove extra spaces, remove punctuation at end
            normalized = ev.headline.lower().strip().rstrip('.,!?;:')
            headline_groups[normalized].append(ev)
        
        collapsed = []
        collapse_count = 0
        
        for normalized_headline, group in headline_groups.items():
            if len(group) == 1:
                collapsed.append(group[0])
            else:
                # Multiple articles with same headline - keep best one
                # Sort by: authority desc, then timestamp asc (earliest)
                group_sorted = sorted(
                    group,
                    key=lambda e: (-e.authority_score, e.timestamp)
                )
                best = group_sorted[0]
                
                # Annotate that we collapsed others
                # We'll store this info in a new field (will add to schema if needed)
                # For now, just track the count
                collapse_count += len(group) - 1
                collapsed.append(best)
        
        return collapsed, collapse_count
    
    def _classify_evidence(
        self,
        evidence_list: List[Evidence],
        ticker: str,
        company_name: Optional[str]
    ) -> List[Tuple[Evidence, str]]:
        """
        Classify each evidence item into exactly one category:
        - Primary: SEC filings, earnings, official statements
        - CorporateOperational: Product, legal, executive, operational
        - MacroSystemic: Interest rates, policy, market-wide indicators
        - Narrative: Commentary, analyst opinions, general news
        """
        classified = []
        
        for ev in evidence_list:
            category = self._determine_category(ev)
            classified.append((ev, category))
        
        return classified
    
    def _determine_category(self, ev: Evidence) -> str:
        """Determine the evidence category."""
        headline_lower = ev.headline.lower()
        
        # Primary: SEC filings, earnings, corporate actions
        if ev.source_type in ["sec_filing", "corporate_action", "earnings"]:
            return "Primary"
        
        # Check keywords for Primary
        primary_keywords = [
            "earnings", "files", "announces", "filing", "sec", "8-k", "10-k", "10-q",
            "dividend", "split", "merger", "acquisition announced"
        ]
        if any(kw in headline_lower for kw in primary_keywords):
            return "Primary"
        
        # MacroSystemic
        if ev.source_type == "macro":
            return "MacroSystemic"
        
        macro_keywords = [
            "fed ", "federal reserve", "interest rate", "gdp", "inflation",
            "unemployment", "policy", "regulation", "treasury", "market selloff",
            "market crash", "recession"
        ]
        if any(kw in headline_lower for kw in macro_keywords):
            return "MacroSystemic"
        
        # CorporateOperational
        operational_keywords = [
            "product", "recall", "lawsuit", "investigation", "fraud", "fine",
            "ceo", "executive", "resign", "layoff", "restructuring", "plant",
            "factory", "supply chain", "customer", "contract", "patent"
        ]
        if any(kw in headline_lower for kw in operational_keywords):
            return "CorporateOperational"
        
        # Narrative (analyst commentary, opinions)
        narrative_keywords = [
            "analyst", "rating", "upgrade", "downgrade", "target", "opinion",
            "commentary", "outlook", "expects", "predicts", "believes", "says",
            "could", "may", "might", "should"
        ]
        if any(kw in headline_lower for kw in narrative_keywords):
            return "Narrative"
        
        # Default to Narrative
        return "Narrative"
    
    def _score_evidence(
        self,
        classified_list: List[Tuple[Evidence, str]],
        start_time: datetime,
        end_time: datetime,
        ticker: str,
        company_name: Optional[str]
    ) -> List[Tuple[Evidence, str, Dict[str, float]]]:
        """
        Score each evidence item:
        - authority_score (already exists)
        - relevance_score (headline match quality)
        - timing_score (proximity to event, penalty for after-the-fact)
        - final_weight = min(authority, relevance, timing)
        """
        scored = []
        
        for ev, category in classified_list:
            scores = {
                'authority': ev.authority_score,
                'relevance': self._compute_relevance(ev, ticker, company_name),
                'timing': self._compute_timing(ev, start_time, end_time)
            }
            scores['final_weight'] = min(scores['authority'], scores['relevance'], scores['timing'])
            
            scored.append((ev, category, scores))
        
        return scored
    
    def _compute_relevance(
        self,
        ev: Evidence,
        ticker: str,
        company_name: Optional[str]
    ) -> float:
        """
        Compute relevance score based on headline content.
        1.0 = highly relevant
        0.0 = not relevant
        """
        headline_lower = ev.headline.lower()
        ticker_lower = ticker.lower()
        company_lower = company_name.lower() if company_name else ""
        
        score = 0.5  # Base score
        
        # Boost if ticker is prominently mentioned
        if ticker_lower in headline_lower:
            # Check if it's in first half of headline (more prominent)
            headline_mid = len(headline_lower) // 2
            ticker_pos = headline_lower.find(ticker_lower)
            if ticker_pos < headline_mid:
                score += 0.3
            else:
                score += 0.2
        
        # Boost if company name is mentioned
        if company_lower and company_lower in headline_lower:
            score += 0.2
        
        # Penalize if it's clearly about multiple companies
        if headline_lower.count(" and ") > 1 or headline_lower.count(", ") > 2:
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _compute_timing(
        self,
        ev: Evidence,
        start_time: datetime,
        end_time: datetime
    ) -> float:
        """
        Compute timing score.
        Best: 0-24h before start_time
        Decay over 7 days
        Penalty for articles published after start_time (likely commentary)
        """
        time_diff = (ev.timestamp - start_time).total_seconds() / 3600  # hours
        
        # Published before the move
        if time_diff <= 0:
            abs_hours = abs(time_diff)
            if abs_hours <= 24:
                return 1.0  # Perfect timing
            elif abs_hours <= 48:
                return 0.9
            elif abs_hours <= 72:
                return 0.8
            else:
                # Decay over 7 days
                days = abs_hours / 24
                if days <= 7:
                    return max(0.4, 1.0 - (days / 7) * 0.6)
                else:
                    return 0.4
        
        # Published after the move started (likely commentary)
        else:
            # Very high authority sources get less penalty
            if ev.authority_score >= 0.85:
                # Could be breaking news or official statement
                if time_diff <= 6:  # Within 6 hours
                    return 0.8
                else:
                    return 0.6
            else:
                # Narrative commentary after the fact
                if time_diff <= 12:
                    return 0.5
                else:
                    return 0.3
    
    def _group_and_rank(
        self,
        scored_list: List[Tuple[Evidence, str, Dict[str, float]]]
    ) -> Dict[str, List[Dict]]:
        """
        Group by category and rank by final_weight.
        """
        groups: Dict[str, List[Dict]] = defaultdict(list)
        
        for ev, category, scores in scored_list:
            source_entry = {
                'headline': ev.headline,
                'url': ev.source_url,
                'timestamp': ev.timestamp,
                'category': category,
                'authority': scores['authority'],
                'relevance': scores['relevance'],
                'timing': scores['timing'],
                'final_weight': scores['final_weight']
            }
            groups[category].append(source_entry)
        
        # Sort each group by final_weight descending
        for category in groups:
            groups[category].sort(key=lambda x: x['final_weight'], reverse=True)
        
        return dict(groups)
    
    def _check_narrative_only(self, groups: Dict[str, List[Dict]]) -> Optional[str]:
        """
        Check if only Narrative sources exist.
        Return mandatory disclaimer if true.
        """
        has_primary = 'Primary' in groups and len(groups['Primary']) > 0
        has_operational = 'CorporateOperational' in groups and len(groups['CorporateOperational']) > 0
        has_macro = 'MacroSystemic' in groups and len(groups['MacroSystemic']) > 0
        has_narrative = 'Narrative' in groups and len(groups['Narrative']) > 0
        
        if has_narrative and not (has_primary or has_operational or has_macro):
            return (
                "⚠️ No primary or macro evidence was found. "
                "The following links reflect market commentary rather than confirmed causes."
            )
        
        return None
