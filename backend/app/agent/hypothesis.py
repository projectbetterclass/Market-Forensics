"""Hypothesis generation and scoring."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
from app.models.schemas import Evidence, Hypothesis, TimelineEvent, MarketContext
from app.config import settings


class HypothesisGenerator:
    """Generates and scores hypotheses based on evidence."""
    
    def __init__(self):
        pass
    
    def generate_hypotheses(
        self,
        evidence_list: List[Evidence],
        event_data: Dict[str, Any],
        market_context: MarketContext
    ) -> List[Hypothesis]:
        """
        Generate and rank hypotheses from evidence.
        
        Args:
            evidence_list: All collected evidence
            event_data: Normalized event data
            market_context: Market/sector/peer context
        
        Returns:
            List of ranked hypotheses
        """
        if not evidence_list:
            return self._generate_unknowns_hypothesis(event_data, market_context)
        
        # Cluster evidence by type and theme
        evidence_clusters = self._cluster_evidence(evidence_list)
        
        # Generate hypotheses from clusters
        hypotheses = []
        
        for cluster_name, cluster_evidence in evidence_clusters.items():
            hyp = self._create_hypothesis_from_cluster(
                cluster_name,
                cluster_evidence,
                event_data,
                market_context
            )
            if hyp:
                hypotheses.append(hyp)
        
        # Score and rank hypotheses
        for i, hyp in enumerate(hypotheses):
            hyp.rank = i + 1
        
        # Sort by computed relevance
        scored_hyps = [
            (self._score_hypothesis(h, event_data), h)
            for h in hypotheses
        ]
        scored_hyps.sort(key=lambda x: x[0], reverse=True)
        
        # Re-rank
        ranked_hypotheses = []
        for rank, (score, hyp) in enumerate(scored_hyps, 1):
            hyp.rank = rank
            # Set probability based on score
            hyp.probability = min(0.95, max(0.10, score / 100.0))
            ranked_hypotheses.append(hyp)
        
        return ranked_hypotheses[:5]  # Top 5
    
    def _cluster_evidence(self, evidence_list: List[Evidence]) -> Dict[str, List[Evidence]]:
        """Cluster evidence by type and content."""
        clusters = defaultdict(list)
        
        for ev in evidence_list:
            # Group by source type
            if ev.source_type == "sec_filing":
                clusters["SEC Filing"].append(ev)
            elif ev.source_type == "news":
                # Simple keyword clustering for news
                headline_lower = ev.headline.lower()
                if any(word in headline_lower for word in ["earnings", "revenue", "profit", "loss"]):
                    clusters["Earnings/Financial Results"].append(ev)
                elif any(word in headline_lower for word in ["lawsuit", "investigation", "fraud", "fine"]):
                    clusters["Legal/Regulatory"].append(ev)
                elif any(word in headline_lower for word in ["layoff", "ceo", "executive", "resign"]):
                    clusters["Management/Personnel"].append(ev)
                elif any(word in headline_lower for word in ["product", "recall", "failure", "issue"]):
                    clusters["Product/Operations"].append(ev)
                else:
                    clusters["General News"].append(ev)
            elif ev.source_type == "macro":
                clusters["Macroeconomic"].append(ev)
            elif ev.source_type == "corporate_action":
                clusters["Corporate Actions"].append(ev)
            else:
                clusters["Other"].append(ev)
        
        return clusters
    
    def _create_hypothesis_from_cluster(
        self,
        cluster_name: str,
        cluster_evidence: List[Evidence],
        event_data: Dict[str, Any],
        market_context: MarketContext
    ) -> Optional[Hypothesis]:
        """Create a hypothesis from a cluster of evidence."""
        if not cluster_evidence:
            return None
        
        # Sort evidence by timestamp proximity to event
        event_start = event_data["start_time"]
        cluster_evidence.sort(key=lambda e: abs((e.timestamp - event_start).total_seconds()))
        
        # Build hypothesis
        title = cluster_name
        
        # Build explanation from evidence
        top_evidence = cluster_evidence[:3]
        explanation_parts = []
        for ev in top_evidence:
            explanation_parts.append(f"- {ev.headline}")
        explanation = "\n".join(explanation_parts)
        
        # Determine confidence based on evidence quality
        avg_authority = sum(e.authority_score for e in cluster_evidence) / len(cluster_evidence)
        if avg_authority > 0.8:
            confidence = "high"
        elif avg_authority > 0.6:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Build mechanism
        mechanism = f"Based on {len(cluster_evidence)} piece(s) of evidence from {cluster_name} sources."
        
        # Build confirmation check
        confirmation_check = f"Monitor for follow-up {cluster_name.lower()} developments."
        
        return Hypothesis(
            rank=0,  # Will be set later
            title=title,
            probability=0.5,  # Will be calculated during scoring
            confidence=confidence,
            explanation=explanation,
            evidence=cluster_evidence,
            mechanism=mechanism,
            confirmation_check=confirmation_check
        )
    
    def _score_hypothesis(
        self,
        hypothesis: Hypothesis,
        event_data: Dict[str, Any]
    ) -> float:
        """
        Score a hypothesis using multiple factors.
        
        Factors:
        - Timing: How close is the evidence to the event?
        - Authority: How authoritative are the sources?
        - Specificity: How specific is the evidence?
        - Magnitude: Does the evidence magnitude match the price move?
        - Corroboration: How many independent sources?
        """
        event_start = event_data["start_time"]
        
        # Timing score
        timing_scores = []
        for ev in hypothesis.evidence:
            time_diff_hours = abs((ev.timestamp - event_start).total_seconds()) / 3600
            # Closer = better, decay over 7 days
            timing_score = max(0, 100 * (1 - time_diff_hours / (7 * 24)))
            timing_scores.append(timing_score)
        avg_timing = sum(timing_scores) / len(timing_scores) if timing_scores else 0
        
        # Authority score
        avg_authority = sum(e.authority_score for e in hypothesis.evidence) / len(hypothesis.evidence)
        authority_score = avg_authority * 100
        
        # Specificity score (based on whether evidence has snippets and detail)
        specificity_scores = []
        for ev in hypothesis.evidence:
            if ev.snippet and len(ev.snippet) > 50:
                specificity_scores.append(100)
            elif ev.snippet:
                specificity_scores.append(70)
            else:
                specificity_scores.append(40)
        avg_specificity = sum(specificity_scores) / len(specificity_scores) if specificity_scores else 50
        
        # Magnitude score (placeholder - would require NLP)
        magnitude_score = 50  # Neutral default
        
        # Corroboration score
        num_sources = len(hypothesis.evidence)
        corroboration_score = min(100, num_sources * 20)  # Cap at 5 sources
        
        # Weighted total
        total_score = (
            settings.timing_weight * avg_timing +
            settings.authority_weight * authority_score +
            settings.specificity_weight * avg_specificity +
            settings.magnitude_weight * magnitude_score +
            settings.corroboration_weight * corroboration_score
        )
        
        return total_score
    
    def _generate_unknowns_hypothesis(
        self,
        event_data: Dict[str, Any],
        market_context: MarketContext
    ) -> List[Hypothesis]:
        """Generate a default hypothesis when no evidence is found."""
        return [
            Hypothesis(
                rank=1,
                title="Insufficient Public Information",
                probability=0.5,
                confidence="low",
                explanation="No significant public filings, news, or macroeconomic events were identified during the analysis window.",
                evidence=[],
                mechanism="The price move may be due to non-public factors, technical trading, or events not yet reported in public sources.",
                confirmation_check="Monitor for delayed disclosures or upcoming earnings reports."
            )
        ]
    
    def build_timeline(self, evidence_list: List[Evidence]) -> List[TimelineEvent]:
        """Build a chronological timeline from evidence."""
        # Sort evidence by timestamp
        sorted_evidence = sorted(evidence_list, key=lambda e: e.timestamp)
        
        timeline = []
        for ev in sorted_evidence:
            event = TimelineEvent(
                timestamp=ev.timestamp,
                description=ev.headline,
                evidence=ev,
                price_impact=None  # Could be calculated if we had tick data
            )
            timeline.append(event)
        
        return timeline
