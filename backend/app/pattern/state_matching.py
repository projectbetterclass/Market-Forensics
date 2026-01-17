"""
State Vector Similarity Matching Engine.

This module implements historical state matching using the Tier-1 state database.
It computes similarity scores between the current market state and historical states,
and returns matches with their forward outcome distributions.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

import numpy as np

from app.models.schemas import (
    MarketStateVector,
    HistoricalMatch,
    OutcomeDistribution
)
from app.data.state_db.builder import get_state_db_builder, STATE_DB_FILE


class StateMatchingEngine:
    """
    Matches current market state against historical states.
    
    Uses a weighted similarity metric across Tier-1 indicators.
    Returns top-N matches with forward outcome distributions.
    """
    
    # Similarity weights for each indicator
    WEIGHTS = {
        "vix_regime": 0.20,        # Volatility regime is critical
        "trend_regime": 0.20,       # Trend alignment matters
        "vix_level": 0.15,          # Exact VIX level
        "sp500_above_50ma": 0.10,
        "sp500_above_200ma": 0.10,
        "xly_xlp_ratio": 0.10,      # Risk appetite
        "sector_rotation_regime": 0.05,
        "cape_percentile": 0.05,    # Valuation (if available)
        "buffett_percentile": 0.05, # Valuation (if available)
    }
    
    def __init__(self):
        self.states = self._load_states()
    
    def _load_states(self) -> List[Dict[str, Any]]:
        """Load historical states from database."""
        if STATE_DB_FILE.exists():
            with open(STATE_DB_FILE, 'r') as f:
                return json.load(f)
        return []
    
    def _categorical_similarity(self, val1: str, val2: str) -> float:
        """Compare categorical values (regimes)."""
        if val1 == val2:
            return 1.0
        
        # Partial matches for related regimes
        regime_groups = {
            # VIX
            ("low", "normal"): 0.5,
            ("normal", "high"): 0.5,
            ("low", "high"): 0.0,
            # Trend
            ("uptrend", "sideways"): 0.5,
            ("sideways", "downtrend"): 0.5,
            ("uptrend", "downtrend"): 0.0,
            # Risk
            ("risk_on", "neutral"): 0.5,
            ("neutral", "risk_off"): 0.5,
            ("risk_on", "risk_off"): 0.0,
        }
        
        key = tuple(sorted([val1, val2]))
        return regime_groups.get(key, 0.25)
    
    def _numeric_similarity(
        self,
        val1: Optional[float],
        val2: Optional[float],
        max_diff: float = 10.0
    ) -> float:
        """Compare numeric values with tolerance."""
        if val1 is None or val2 is None:
            return 0.5  # Neutral if missing
        
        diff = abs(val1 - val2)
        if diff > max_diff:
            return 0.0
        return 1.0 - (diff / max_diff)
    
    def _boolean_similarity(
        self,
        val1: Optional[bool],
        val2: Optional[bool]
    ) -> float:
        """Compare boolean values."""
        if val1 is None or val2 is None:
            return 0.5
        return 1.0 if val1 == val2 else 0.0
    
    def compute_similarity(
        self,
        current_state: MarketStateVector,
        historical_state: Dict[str, Any]
    ) -> float:
        """
        Compute similarity score between current and historical state.
        
        Returns a score from 0.0 (completely different) to 1.0 (identical).
        """
        scores = {}
        
        # VIX regime
        scores["vix_regime"] = self._categorical_similarity(
            current_state.vix_regime,
            historical_state.get("vix_regime", "unknown")
        )
        
        # VIX level (within 5 points is similar)
        scores["vix_level"] = self._numeric_similarity(
            current_state.vix_level,
            historical_state.get("vix_level"),
            max_diff=10.0
        )
        
        # Trend regime
        scores["trend_regime"] = self._categorical_similarity(
            current_state.trend_regime,
            historical_state.get("trend_regime", "unknown")
        )
        
        # Moving average positions
        scores["sp500_above_50ma"] = self._boolean_similarity(
            current_state.sp500_above_50ma,
            historical_state.get("sp500_above_50ma")
        )
        scores["sp500_above_200ma"] = self._boolean_similarity(
            current_state.sp500_above_200ma,
            historical_state.get("sp500_above_200ma")
        )
        
        # XLY/XLP ratio (within 0.2 is similar)
        scores["xly_xlp_ratio"] = self._numeric_similarity(
            current_state.xly_xlp_ratio,
            historical_state.get("xly_xlp_ratio"),
            max_diff=0.5
        )
        
        # Sector rotation regime
        scores["sector_rotation_regime"] = self._categorical_similarity(
            current_state.sector_rotation_regime,
            historical_state.get("sector_rotation_regime", "unknown")
        )
        
        # Valuation (if available)
        scores["cape_percentile"] = self._numeric_similarity(
            current_state.cape_percentile,
            historical_state.get("cape_percentile"),
            max_diff=20.0
        )
        scores["buffett_percentile"] = self._numeric_similarity(
            current_state.buffett_percentile,
            historical_state.get("buffett_percentile"),
            max_diff=20.0
        )
        
        # Compute weighted average
        total_weight = 0.0
        weighted_score = 0.0
        for key, weight in self.WEIGHTS.items():
            if key in scores:
                weighted_score += scores[key] * weight
                total_weight += weight
        
        if total_weight > 0:
            return weighted_score / total_weight
        return 0.5
    
    def find_similar_states(
        self,
        current_state: MarketStateVector,
        top_n: int = 10,
        min_similarity: float = 0.5
    ) -> List[HistoricalMatch]:
        """
        Find historical states similar to the current state.
        
        Args:
            current_state: Current market state vector
            top_n: Maximum number of matches to return
            min_similarity: Minimum similarity threshold
        
        Returns:
            List of HistoricalMatch objects with outcomes
        """
        if not self.states:
            return []
        
        # Compute similarities
        matches = []
        for state in self.states:
            similarity = self.compute_similarity(current_state, state)
            if similarity >= min_similarity:
                matches.append((state, similarity))
        
        # Sort by similarity (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Take top N
        top_matches = matches[:top_n]
        
        # Convert to HistoricalMatch objects
        results = []
        for state, similarity in top_matches:
            # Build outcomes
            outcomes = {}
            state_outcomes = state.get("outcomes", {})
            
            for horizon in ["3m", "6m", "12m"]:
                if horizon in state_outcomes:
                    outcome_data = state_outcomes[horizon]
                    return_pct = outcome_data.get("return_pct")
                    
                    if return_pct is not None:
                        # For single-state outcomes, we create a simplified distribution
                        outcomes[horizon] = OutcomeDistribution(
                            horizon=horizon,
                            mean_return_pct=return_pct,
                            median_return_pct=return_pct,
                            percentile_10=return_pct * 0.7,  # Simplified estimate
                            percentile_25=return_pct * 0.85,
                            percentile_75=return_pct * 1.15,
                            percentile_90=return_pct * 1.3,
                            positive_outcome_pct=100.0 if return_pct > 0 else 0.0,
                            sample_size=1
                        )
            
            # Build state summary
            state_at_match = {
                "vix": state.get("vix_level"),
                "vix_regime": state.get("vix_regime"),
                "trend": state.get("trend_regime"),
                "above_50ma": state.get("sp500_above_50ma"),
                "above_200ma": state.get("sp500_above_200ma"),
                "xly_xlp_ratio": state.get("xly_xlp_ratio"),
                "sector_rotation": state.get("sector_rotation_regime")
            }
            
            results.append(HistoricalMatch(
                match_date=datetime.fromisoformat(state["date"]),
                similarity_score=similarity,
                state_at_match=state_at_match,
                outcomes=outcomes,
                market_regime_at_time=state.get("trend_regime"),
                notable_events=[],
                outcome_warning="Historical outcomes varied. Similar patterns have led to different results."
            ))
        
        return results
    
    def compute_aggregate_outcomes(
        self,
        matches: List[HistoricalMatch]
    ) -> Dict[str, OutcomeDistribution]:
        """
        Compute aggregate outcome distributions from multiple matches.
        
        This provides a statistical summary of what happened in similar past states.
        """
        if not matches:
            return {}
        
        aggregated = {}
        
        for horizon in ["3m", "6m", "12m"]:
            returns = []
            
            for match in matches:
                if horizon in match.outcomes:
                    outcome = match.outcomes[horizon]
                    if outcome.mean_return_pct is not None:
                        returns.append(outcome.mean_return_pct)
            
            if returns:
                returns_arr = np.array(returns)
                aggregated[horizon] = OutcomeDistribution(
                    horizon=horizon,
                    mean_return_pct=float(np.mean(returns_arr)),
                    median_return_pct=float(np.median(returns_arr)),
                    percentile_10=float(np.percentile(returns_arr, 10)),
                    percentile_25=float(np.percentile(returns_arr, 25)),
                    percentile_75=float(np.percentile(returns_arr, 75)),
                    percentile_90=float(np.percentile(returns_arr, 90)),
                    positive_outcome_pct=float(np.sum(returns_arr > 0) / len(returns_arr) * 100),
                    sample_size=len(returns)
                )
        
        return aggregated


# Factory function
def create_state_matcher() -> StateMatchingEngine:
    """Create a state matching engine instance."""
    return StateMatchingEngine()


async def find_historical_matches(
    current_state: MarketStateVector,
    top_n: int = 10
) -> List[HistoricalMatch]:
    """Find historical matches for the given state."""
    matcher = create_state_matcher()
    return matcher.find_similar_states(current_state, top_n=top_n)
