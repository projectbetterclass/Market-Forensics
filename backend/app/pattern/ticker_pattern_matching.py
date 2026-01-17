"""Ticker-specific price-shape pattern matching engine."""

import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from scipy.interpolate import interp1d
from app.retrieval.prices import PriceClient
from app.models.schemas import ChartDataPoint


class TickerPatternMatcher:
    """Match price-shape patterns for a specific ticker using normalized shape comparison."""
    
    def __init__(self):
        self.price_client = PriceClient()
    
    async def find_similar_patterns(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        top_k: int = 5,
        min_separation_days: int = 30,
        target_points: int = 60,
        window_size_tolerance: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Find historical patterns that match the selected price movement.
        
        Uses fixed-length normalization so we can compare shapes fairly
        even when selections vary in duration.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start of selected range
            end_date: End of selected range
            interval: Data interval (1d, 1wk, 1mo)
            top_k: Number of top matches to return
            min_separation_days: Minimum days between selected range and match windows
            target_points: Normalize all windows to this many points for comparison
            window_size_tolerance: Allow candidate windows within this % of selected size
        
        Returns:
            List of pattern matches with similarity scores and outcomes
        """
        # Get full price history
        historical_data = await self._get_historical_data(ticker, interval)
        
        if not historical_data or len(historical_data) < 20:
            print(f"Insufficient historical data for {ticker}: {len(historical_data) if historical_data else 0} bars")
            return []
        
        # Extract selected window data
        selected_window = self._extract_window(historical_data, start_date, end_date)
        
        if not selected_window or len(selected_window) < 2:
            return []
        
        selected_size = len(selected_window)
        
        # Compute normalized cumulative return curve for selected window
        selected_cum_returns = self._compute_cumulative_returns(selected_window)
        selected_normalized = self._normalize_to_fixed_length(selected_cum_returns, target_points)
        
        if selected_normalized is None or len(selected_normalized) < 2:
            print(f"Could not normalize selected window")
            return []
        
        # Calculate total move magnitude for selected window
        selected_total_return = ((selected_window[-1].value - selected_window[0].value) / selected_window[0].value) * 100
        
        # Define candidate window size range (±tolerance)
        min_window_size = int(selected_size * (1 - window_size_tolerance))
        max_window_size = int(selected_size * (1 + window_size_tolerance))
        min_window_size = max(5, min_window_size)  # At least 5 bars
        
        # Slide across history to find similar windows
        matches = []
        
        for window_size in range(min_window_size, max_window_size + 1):
            for i in range(len(historical_data) - window_size + 1):
                candidate_window = historical_data[i:i + window_size]
                
                # Skip if this overlaps with selected period or is too close
                candidate_start = datetime.fromisoformat(candidate_window[0].time.replace('Z', '+00:00'))
                candidate_end = datetime.fromisoformat(candidate_window[-1].time.replace('Z', '+00:00'))
                
                # Check if too close to selected range
                if self._is_too_close(candidate_start, candidate_end, start_date, end_date, min_separation_days):
                    continue
                
                # Compute normalized cumulative returns for candidate
                candidate_cum_returns = self._compute_cumulative_returns(candidate_window)
                candidate_normalized = self._normalize_to_fixed_length(candidate_cum_returns, target_points)
                
                if candidate_normalized is None or len(candidate_normalized) < 2:
                    continue
                
                # Compute similarity
                similarity_score = self._compute_similarity(
                    selected_normalized, 
                    candidate_normalized,
                    selected_total_return,
                    ((candidate_window[-1].value - candidate_window[0].value) / candidate_window[0].value) * 100
                )
                
                if similarity_score > 0.5:  # Threshold for meaningful similarity
                    # Compute forward outcomes from this match
                    outcomes = await self._compute_forward_outcomes(
                        historical_data, 
                        i + window_size - 1,
                        interval
                    )
                    
                    matches.append({
                        "start_date": candidate_start.isoformat(),
                        "end_date": candidate_end.isoformat(),
                        "similarity_score": similarity_score,
                        "window_data": candidate_window,
                        "outcomes": outcomes,
                        "window_size": window_size
                    })
        
        # Sort by similarity and return top K
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        return matches[:top_k]
    
    async def _get_historical_data(self, ticker: str, interval: str) -> List[ChartDataPoint]:
        """Get historical price data for pattern matching."""
        try:
            # For pattern matching, we need enough history but at the requested interval
            # Use "10y" to get sufficient history without being too sparse
            # Note: Yahoo Finance "max" often returns monthly data, which is too coarse
            range_param = "10y" if interval == "1d" else "max"
            data = await self.price_client.get_chart_data_range(ticker, range_param, interval)
            return data
        except Exception as e:
            print(f"Error fetching historical data for {ticker}: {e}")
            return []
    
    def _extract_window(
        self, 
        data: List[ChartDataPoint], 
        start_date: datetime, 
        end_date: datetime
    ) -> List[ChartDataPoint]:
        """Extract data points within the specified date range."""
        window = []
        
        # Ensure start_date and end_date are timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        # Convert to date-only for comparison (ignore time component)
        start_date_only = start_date.date()
        end_date_only = end_date.date()
        
        for point in data:
            # Parse time from point (handle both formats)
            time_str = point.time.replace('Z', '+00:00')
            if 'T' not in time_str:
                time_str = time_str + 'T00:00:00+00:00'
            
            try:
                point_time = datetime.fromisoformat(time_str)
                if point_time.tzinfo is None:
                    point_time = point_time.replace(tzinfo=timezone.utc)
                
                point_date = point_time.date()
                
                if start_date_only <= point_date <= end_date_only:
                    window.append(point)
            except Exception as e:
                # Skip invalid dates
                continue
        
        return window
    
    def _compute_cumulative_returns(self, data: List[ChartDataPoint]) -> np.ndarray:
        """
        Compute cumulative log returns from price data.
        
        This creates a curve representing the shape of the price movement.
        """
        if len(data) < 2:
            return np.array([])
        
        prices = np.array([p.value for p in data])
        log_prices = np.log(prices)
        log_prices = log_prices - log_prices[0]  # Start at 0
        
        return log_prices
    
    def _normalize_to_fixed_length(
        self, 
        cumulative_returns: np.ndarray, 
        target_length: int
    ) -> Optional[np.ndarray]:
        """
        Resample cumulative return curve to fixed length using interpolation.
        
        This allows comparing windows of different durations on the same scale.
        """
        if len(cumulative_returns) < 2:
            return None
        
        try:
            # Create interpolation function
            x_original = np.linspace(0, 1, len(cumulative_returns))
            x_target = np.linspace(0, 1, target_length)
            
            # Linear interpolation
            interp_func = interp1d(x_original, cumulative_returns, kind='linear')
            normalized = interp_func(x_target)
            
            return normalized
        except Exception as e:
            print(f"Error normalizing curve: {e}")
            return None
    
    def _compute_similarity(
        self, 
        curve1: np.ndarray, 
        curve2: np.ndarray,
        total_return1: float,
        total_return2: float
    ) -> float:
        """
        Compute similarity between two normalized cumulative return curves.
        
        Uses hybrid score:
        - Shape correlation (primary)
        - Magnitude similarity (penalty for very different total moves)
        """
        if len(curve1) == 0 or len(curve2) == 0 or len(curve1) != len(curve2):
            return 0.0
        
        try:
            # 1. Shape correlation
            correlation = np.corrcoef(curve1, curve2)[0, 1]
            
            if np.isnan(correlation):
                return 0.0
            
            # Convert to 0-1 scale (correlation is -1 to 1)
            # We want positive correlation for similar shapes
            shape_score = (correlation + 1) / 2
            
            # 2. Magnitude similarity
            # Penalize if total returns differ significantly
            magnitude_diff = abs(total_return1 - total_return2)
            
            # Sigmoid penalty: if diff > 20%, reduce score
            magnitude_penalty = 1.0 / (1.0 + (magnitude_diff / 20.0) ** 2)
            
            # 3. Combined score (weighted: 70% shape, 30% magnitude)
            combined_score = 0.7 * shape_score + 0.3 * magnitude_penalty
            
            return float(combined_score)
        
        except Exception as e:
            print(f"Error computing similarity: {e}")
            return 0.0
    
    def _is_too_close(
        self,
        cand_start: datetime,
        cand_end: datetime,
        sel_start: datetime,
        sel_end: datetime,
        min_days: int
    ) -> bool:
        """Check if candidate window is too close to selected range."""
        separation = timedelta(days=min_days)
        
        # Check if candidate overlaps or is within min_days of selected range
        if cand_end >= sel_start - separation and cand_start <= sel_end + separation:
            return True
        
        return False
    
    async def _compute_forward_outcomes(
        self,
        full_data: List[ChartDataPoint],
        end_idx: int,
        interval: str
    ) -> Dict[str, Any]:
        """
        Compute forward returns from the match window end.
        
        Args:
            full_data: Complete historical data
            end_idx: Index of the match window end
            interval: Data interval
        
        Returns:
            Dict with forward returns for different horizons
        """
        outcomes = {}
        
        # Define horizons based on interval
        if interval == "1d":
            horizons = {"1mo": 21, "3mo": 63, "6mo": 126}
        elif interval == "1wk":
            horizons = {"1mo": 4, "3mo": 13, "6mo": 26}
        else:  # 1mo
            horizons = {"1mo": 1, "3mo": 3, "6mo": 6}
        
        end_price = full_data[end_idx].value
        
        for horizon_name, bars_ahead in horizons.items():
            future_idx = end_idx + bars_ahead
            
            if future_idx < len(full_data):
                future_price = full_data[future_idx].value
                forward_return = ((future_price - end_price) / end_price) * 100
                
                # Also compute max drawdown in forward period
                forward_prices = [full_data[j].value for j in range(end_idx + 1, min(future_idx + 1, len(full_data)))]
                if forward_prices:
                    max_price = max(forward_prices)
                    min_price = min(forward_prices)
                    max_dd = ((min_price - end_price) / end_price) * 100 if min_price < end_price else 0.0
                else:
                    max_dd = 0.0
                
                outcomes[horizon_name] = {
                    "mean_return_pct": round(forward_return, 2),
                    "positive_outcome_pct": 100.0 if forward_return >= 0 else 0.0,
                    "max_drawdown": round(max_dd, 2)
                }
            else:
                # Not enough future data
                outcomes[horizon_name] = {
                    "mean_return_pct": None,
                    "positive_outcome_pct": None,
                    "max_drawdown": None
                }
        
        return outcomes
