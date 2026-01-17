"""Tier-1 Dashboard orchestrator - computes all always-visible indicators."""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from app.models.schemas import (
    Tier1Dashboard,
    CapeIndicator,
    BuffettIndicator,
    BreadthIndicator,
    LeadershipIndicator,
    SectorRotationTier1,
    VixIndicator,
    MovingAveragesIndicator,
    CycleStage
)
from app.retrieval.prices import PriceClient
from app.retrieval.vix import VixClient
from app.retrieval.valuation import ValuationProvider
from app.cache.swr_cache import SWRCache
from app.config import settings


class Tier1DashboardService:
    """
    Service for computing all Tier-1 indicators.
    
    Anchored to S&P 500 (^GSPC), fallback to SPY.
    """
    
    def __init__(self):
        self.price_client = PriceClient()
        self.vix_client = VixClient()
        self.valuation_provider = ValuationProvider()
        self._cache = SWRCache(refresh_interval_seconds=600)  # 10 min cache
        
        # ETFs for proxy calculations
        self.market_proxy = "^GSPC"
        self.market_etf = "SPY"
        self.equal_weight_etf = "RSP"  # Invesco S&P 500 Equal Weight
        self.sector_etfs = {
            "XLY": "Consumer Discretionary",
            "XLP": "Consumer Staples",
            "XLK": "Technology",
            "XLF": "Financials",
            "XLV": "Healthcare",
            "XLE": "Energy",
            "XLI": "Industrials",
            "XLU": "Utilities"
        }
    
    async def get_dashboard(self, market: str = "^GSPC") -> Tier1Dashboard:
        """Get complete Tier-1 dashboard."""
        cache_key = f"tier1:dashboard:{market}"
        return await self._cache.get_or_fetch(cache_key, self._compute_dashboard, market)
    
    async def _compute_dashboard(self, market: str) -> Tier1Dashboard:
        """Compute all Tier-1 indicators."""
        market_proxy_used = market
        
        # Compute each indicator
        cape = await self._get_cape()
        buffett = await self._get_buffett()
        breadth = await self._get_breadth()
        leadership = await self._get_leadership()
        sector_rotation = await self._get_sector_rotation()
        vix = await self._get_vix()
        moving_averages = await self._get_moving_averages(market)
        
        # Compute cycle stage from other indicators
        cycle_stage = self._compute_cycle_stage(
            cape, buffett, breadth, leadership, vix, moving_averages
        )
        
        return Tier1Dashboard(
            as_of=datetime.now(timezone.utc),
            market_proxy_used=market_proxy_used,
            cape=cape,
            buffett=buffett,
            breadth=breadth,
            leadership=leadership,
            sector_rotation=sector_rotation,
            vix=vix,
            moving_averages=moving_averages,
            cycle_stage=cycle_stage,
            disclaimer="These indicators provide historical context and regime awareness. They do not predict market direction or recommend actions."
        )
    
    async def _get_cape(self) -> CapeIndicator:
        """Get CAPE ratio from valuation provider."""
        try:
            cape_data = await self.valuation_provider.get_cape_ratio()
            
            if cape_data and cape_data.get("value"):
                value = cape_data["value"]
                percentile = cape_data.get("percentile", 50)
                
                # Generate interpretation based on percentile
                if percentile >= 90:
                    interpretation = f"CAPE at {value:.1f} is in the top 10% historically. Elevated valuations have historically been associated with lower subsequent long-term returns and increased volatility risk."
                elif percentile >= 75:
                    interpretation = f"CAPE at {value:.1f} is elevated (top 25%). Historically associated with moderate headwinds for long-term returns."
                elif percentile >= 50:
                    interpretation = f"CAPE at {value:.1f} is near historical average. Valuations appear moderate by historical standards."
                else:
                    interpretation = f"CAPE at {value:.1f} is below average historically. Lower valuations have historically been associated with better long-term return prospects."
                
                return CapeIndicator(
                    value=value,
                    percentile=percentile,
                    interpretation=interpretation,
                    data_source=cape_data.get("note", "Shiller PE / multpl.com")
                )
        except Exception as e:
            print(f"CAPE indicator error: {e}")
        
        return CapeIndicator(
            value=None,
            percentile=None,
            interpretation="CAPE data temporarily unavailable. This metric measures price relative to 10-year average earnings.",
            data_source="Shiller Dataset"
        )
    
    async def _get_buffett(self) -> BuffettIndicator:
        """Get Buffett Indicator from valuation provider."""
        try:
            buffett_data = await self.valuation_provider.get_buffett_indicator()
            
            if buffett_data and buffett_data.get("value"):
                value = buffett_data["value"]
                percentile = buffett_data.get("percentile", 50)
                zone = buffett_data.get("zone", "Unknown")
                
                # Generate interpretation based on zone
                if zone == "Extreme":
                    interpretation = f"Buffett Indicator at {value:.0f}% is in extreme territory. Total market cap significantly exceeds GDP. Historically, this has been associated with elevated risk."
                elif zone == "Stretched":
                    interpretation = f"Buffett Indicator at {value:.0f}% is stretched above historical norms. Market cap exceeds GDP, suggesting above-average valuations."
                else:
                    interpretation = f"Buffett Indicator at {value:.0f}% is in fair value range. Market cap relative to GDP is within historical norms."
                
                return BuffettIndicator(
                    value=value,
                    percentile=percentile,
                    zone=zone,
                    interpretation=interpretation,
                    data_source=buffett_data.get("note", "Market Cap / GDP")
                )
        except Exception as e:
            print(f"Buffett indicator error: {e}")
        
        return BuffettIndicator(
            value=None,
            percentile=None,
            zone="Unknown",
            interpretation="Buffett Indicator temporarily unavailable. This metric compares total market capitalization to GDP.",
            data_source="Market Cap / GDP"
        )
    
    async def _get_breadth(self) -> BreadthIndicator:
        """
        Get market breadth using equal-weight vs cap-weight proxy.
        
        Methodology: Compare RSP (equal-weight S&P 500) vs SPY (cap-weight)
        relative performance over 30 days.
        
        If RSP outperforms: broad participation
        If SPY outperforms: narrow leadership
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=30)
            
            spy_return = await self.price_client.get_market_index_data(
                self.market_etf, start_time, end_time
            )
            rsp_return = await self.price_client.get_market_index_data(
                self.equal_weight_etf, start_time, end_time
            )
            
            if spy_return is not None and rsp_return is not None:
                divergence = rsp_return - spy_return
                
                if divergence > 2:
                    interpretation = "Broad market participation: equal-weight index outperforming. Historically associated with healthier market conditions."
                elif divergence < -2:
                    interpretation = "Narrow market participation: cap-weight index outperforming. A smaller number of large stocks are driving gains."
                else:
                    interpretation = "Moderate breadth: no significant divergence between equal-weight and cap-weight indices."
                
                return BreadthIndicator(
                    metric_name="Equal-weight vs Cap-weight Divergence (30d)",
                    value=round(divergence, 2),
                    interpretation=interpretation,
                    methodology="RSP (equal-weight S&P 500) minus SPY (cap-weight) 30-day return",
                    data_source="Yahoo Finance ETFs"
                )
        except Exception as e:
            print(f"Breadth calculation error: {e}")
        
        return BreadthIndicator(
            metric_name="Equal-weight vs Cap-weight Divergence",
            value=None,
            interpretation="Breadth data not available",
            methodology="RSP vs SPY relative strength",
            data_source="Yahoo Finance ETFs"
        )
    
    async def _get_leadership(self) -> LeadershipIndicator:
        """
        Get leadership concentration using cap-weight vs equal-weight divergence.
        
        Large divergence where SPY >> RSP indicates narrow leadership.
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=90)  # 3-month window
            
            spy_return = await self.price_client.get_market_index_data(
                self.market_etf, start_time, end_time
            )
            rsp_return = await self.price_client.get_market_index_data(
                self.equal_weight_etf, start_time, end_time
            )
            
            if spy_return is not None and rsp_return is not None:
                concentration = spy_return - rsp_return  # Positive = narrow leadership
                
                if concentration > 5:
                    label = "Narrow"
                    interpretation = "Market gains are concentrated in a small number of large stocks. Historically, high concentration has been associated with increased fragility."
                elif concentration > 2:
                    label = "Moderate"
                    interpretation = "Some concentration in large-cap leadership, but not extreme. Market participation is moderate."
                else:
                    label = "Broad"
                    interpretation = "Leadership is broadly distributed across market capitalization. This has historically been associated with more sustainable market advances."
                
                return LeadershipIndicator(
                    metric_name="Cap-weight vs Equal-weight Divergence (90d)",
                    value=round(concentration, 2),
                    leadership_label=label,
                    interpretation=interpretation,
                    methodology="SPY (cap-weight) minus RSP (equal-weight) 90-day return; positive indicates narrow leadership",
                    data_source="Yahoo Finance ETFs"
                )
        except Exception as e:
            print(f"Leadership calculation error: {e}")
        
        return LeadershipIndicator(
            metric_name="Leadership Concentration",
            value=None,
            leadership_label="Unknown",
            interpretation="Leadership data not available",
            methodology="SPY vs RSP relative strength",
            data_source="Yahoo Finance ETFs"
        )
    
    async def _get_sector_rotation(self) -> SectorRotationTier1:
        """Get sector rotation context with XLY/XLP ratio."""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=30)
            
            # Get XLY and XLP for ratio
            xly_return = await self.price_client.get_market_index_data("XLY", start_time, end_time)
            xlp_return = await self.price_client.get_market_index_data("XLP", start_time, end_time)
            
            # Get all sector performances
            sector_perfs = []
            for etf, sector_name in self.sector_etfs.items():
                ret = await self.price_client.get_market_index_data(etf, start_time, end_time)
                if ret is not None:
                    sector_perfs.append({
                        "sector": sector_name,
                        "etf": etf,
                        "return_pct": round(ret, 2)
                    })
            
            # Sort by performance
            sector_perfs.sort(key=lambda x: x["return_pct"], reverse=True)
            
            # Calculate XLY/XLP ratio interpretation
            if xly_return is not None and xlp_return is not None:
                ratio = xly_return - xlp_return
                
                if ratio > 3:
                    ratio_interpretation = "Discretionary outperforming Staples: historically associated with risk-on sentiment."
                elif ratio < -3:
                    ratio_interpretation = "Staples outperforming Discretionary: historically associated with defensive positioning."
                else:
                    ratio_interpretation = "Discretionary and Staples relatively balanced."
                
                # Check defensive strength
                defensive_etfs = ["XLP", "XLV", "XLU"]
                defensive_returns = [s["return_pct"] for s in sector_perfs if s["etf"] in defensive_etfs]
                if defensive_returns:
                    avg_defensive = sum(defensive_returns) / len(defensive_returns)
                    if avg_defensive > 2:
                        defensive_strength = "Defensive sectors showing relative strength"
                    elif avg_defensive < -2:
                        defensive_strength = "Defensive sectors underperforming"
                    else:
                        defensive_strength = "Defensive sectors neutral"
                else:
                    defensive_strength = None
                
                interpretation = f"Sector rotation context: {ratio_interpretation}"
                
                return SectorRotationTier1(
                    xly_xlp_ratio=round(ratio, 2),
                    ratio_interpretation=ratio_interpretation,
                    defensive_strength=defensive_strength,
                    top_sectors=sector_perfs[:3],
                    interpretation=interpretation
                )
        except Exception as e:
            print(f"Sector rotation error: {e}")
        
        return SectorRotationTier1(
            xly_xlp_ratio=None,
            ratio_interpretation="Data not available",
            defensive_strength=None,
            top_sectors=[],
            interpretation="Sector rotation data not available"
        )
    
    async def _get_vix(self) -> VixIndicator:
        """Get VIX indicator."""
        vix_data = await self.vix_client.get_vix_data()
        
        return VixIndicator(
            value=vix_data.get("value"),
            regime=vix_data.get("regime", "Unknown"),
            interpretation=vix_data.get("interpretation", "Data not available"),
            insight="Very low volatility has historically preceded instability; high volatility reflects fear already present.",
            data_source="Yahoo Finance ^VIX"
        )
    
    async def _get_moving_averages(self, market: str) -> MovingAveragesIndicator:
        """
        Compute 50-day and 200-day moving averages for market proxy.
        
        Shows trend health, not trading signals.
        """
        try:
            # Get 250 days of data to compute 200-day MA + slope
            chart_data = await self.price_client.get_chart_data_range(
                market, "1y", "1d"
            )
            
            if len(chart_data) < 200:
                # Fallback to SPY
                chart_data = await self.price_client.get_chart_data_range(
                    "SPY", "1y", "1d"
                )
            
            if len(chart_data) < 50:
                return self._default_ma_response()
            
            # Extract close prices
            closes = [p.value for p in chart_data]
            
            current_price = closes[-1]
            
            # Compute MAs
            ma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
            ma_200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None
            
            # Compute price vs MA
            price_vs_50 = "Unknown"
            price_vs_200 = "Unknown"
            
            if ma_50:
                diff_50 = (current_price - ma_50) / ma_50 * 100
                if diff_50 > 0.5:
                    price_vs_50 = "Above"
                elif diff_50 < -0.5:
                    price_vs_50 = "Below"
                else:
                    price_vs_50 = "At"
            
            if ma_200:
                diff_200 = (current_price - ma_200) / ma_200 * 100
                if diff_200 > 0.5:
                    price_vs_200 = "Above"
                elif diff_200 < -0.5:
                    price_vs_200 = "Below"
                else:
                    price_vs_200 = "At"
            
            # Compute slopes (comparing current MA vs MA from 20 days ago)
            slope_50 = "Unknown"
            slope_200 = "Unknown"
            
            if len(closes) >= 70:
                ma_50_prev = sum(closes[-70:-20]) / 50
                slope_50_pct = (ma_50 - ma_50_prev) / ma_50_prev * 100 if ma_50 else 0
                if slope_50_pct > 1:
                    slope_50 = "Rising"
                elif slope_50_pct < -1:
                    slope_50 = "Falling"
                else:
                    slope_50 = "Flattening"
            
            if len(closes) >= 220:
                ma_200_prev = sum(closes[-220:-20]) / 200
                slope_200_pct = (ma_200 - ma_200_prev) / ma_200_prev * 100 if ma_200 else 0
                if slope_200_pct > 1:
                    slope_200 = "Rising"
                elif slope_200_pct < -1:
                    slope_200 = "Falling"
                else:
                    slope_200 = "Flattening"
            
            # Generate trend health assessment
            trend_health = self._assess_trend_health(price_vs_50, price_vs_200, slope_50, slope_200)
            interpretation = self._get_ma_interpretation(price_vs_50, price_vs_200, slope_50, slope_200)
            
            return MovingAveragesIndicator(
                current_price=round(current_price, 2),
                ma_50=round(ma_50, 2) if ma_50 else None,
                ma_200=round(ma_200, 2) if ma_200 else None,
                price_vs_50=price_vs_50,
                price_vs_200=price_vs_200,
                slope_50=slope_50,
                slope_200=slope_200,
                trend_health=trend_health,
                interpretation=interpretation
            )
        
        except Exception as e:
            print(f"Moving averages error: {e}")
            return self._default_ma_response()
    
    def _assess_trend_health(
        self,
        price_vs_50: str,
        price_vs_200: str,
        slope_50: str,
        slope_200: str
    ) -> str:
        """Assess overall trend health."""
        score = 0
        
        if price_vs_50 == "Above":
            score += 1
        elif price_vs_50 == "Below":
            score -= 1
        
        if price_vs_200 == "Above":
            score += 1
        elif price_vs_200 == "Below":
            score -= 1
        
        if slope_50 == "Rising":
            score += 1
        elif slope_50 == "Falling":
            score -= 1
        
        if slope_200 == "Rising":
            score += 1
        elif slope_200 == "Falling":
            score -= 1
        
        if score >= 3:
            return "Strong"
        elif score >= 1:
            return "Moderate"
        elif score >= -1:
            return "Neutral"
        else:
            return "Weak"
    
    def _get_ma_interpretation(
        self,
        price_vs_50: str,
        price_vs_200: str,
        slope_50: str,
        slope_200: str
    ) -> str:
        """Generate MA interpretation without trading language."""
        parts = []
        
        if price_vs_200 == "Above":
            parts.append("Price is above the 200-day average, suggesting longer-term trend remains upward")
        elif price_vs_200 == "Below":
            parts.append("Price is below the 200-day average, suggesting longer-term trend pressure")
        
        if slope_50 == "Rising" and slope_200 == "Rising":
            parts.append("Both moving averages are rising, indicating positive momentum")
        elif slope_50 == "Falling" and slope_200 == "Falling":
            parts.append("Both moving averages are declining, indicating negative momentum")
        elif slope_50 == "Falling" and slope_200 == "Rising":
            parts.append("Short-term momentum weakening while longer-term trend remains intact")
        
        if not parts:
            return "Trend indicators show mixed signals"
        
        return ". ".join(parts) + "."
    
    def _default_ma_response(self) -> MovingAveragesIndicator:
        """Default MA response when data unavailable."""
        return MovingAveragesIndicator(
            current_price=None,
            ma_50=None,
            ma_200=None,
            price_vs_50="Unknown",
            price_vs_200="Unknown",
            slope_50="Unknown",
            slope_200="Unknown",
            trend_health="Data not available",
            interpretation="Moving average data not available"
        )
    
    def _compute_cycle_stage(
        self,
        cape: CapeIndicator,
        buffett: BuffettIndicator,
        breadth: BreadthIndicator,
        leadership: LeadershipIndicator,
        vix: VixIndicator,
        ma: MovingAveragesIndicator
    ) -> CycleStage:
        """
        Compute market cycle stage (1-4) from component indicators.
        
        Stage 1: Rational Growth - healthy valuations, broad participation, normal volatility
        Stage 2: Acceleration - rising valuations, momentum building, declining volatility
        Stage 3: Euphoria - stretched valuations, narrow leadership, compressed volatility
        Stage 4: Panic/Liquidation - falling prices, elevated volatility, weak trend
        """
        factors = []
        stage_score = 0  # Higher = later stage
        
        # VIX contribution
        if vix.regime == "Compressed":
            stage_score += 2  # Complacency indicator
            factors.append("Low volatility (historically a late-cycle signal)")
        elif vix.regime == "Elevated":
            stage_score += 3  # Crisis indicator
            factors.append("Elevated volatility (fear present)")
        else:
            stage_score += 1
        
        # Leadership contribution
        if leadership.leadership_label == "Narrow":
            stage_score += 2
            factors.append("Narrow leadership concentration")
        elif leadership.leadership_label == "Broad":
            stage_score -= 1
            factors.append("Broad market participation")
        
        # Trend health contribution
        if ma.trend_health == "Weak":
            stage_score += 2
            factors.append("Weak trend integrity")
        elif ma.trend_health == "Strong":
            stage_score -= 1
            factors.append("Strong trend integrity")
        
        # Breadth contribution
        if breadth.value is not None:
            if breadth.value < -3:
                stage_score += 1
                factors.append("Declining breadth")
            elif breadth.value > 3:
                stage_score -= 1
                factors.append("Improving breadth")
        
        # Map score to stage
        if stage_score <= 0:
            stage = 1
            stage_name = "Rational Growth"
            description = "Market conditions suggest rational growth phase with healthy participation and reasonable risk indicators."
        elif stage_score <= 2:
            stage = 2
            stage_name = "Acceleration"
            description = "Market showing acceleration with building momentum. Historically, this stage can persist for extended periods."
        elif stage_score <= 4:
            stage = 3
            stage_name = "Euphoria"
            description = "Indicators suggest late-cycle conditions with potential concentration and complacency. Historically associated with elevated risk of correction."
        else:
            stage = 4
            stage_name = "Panic / Liquidation"
            description = "Indicators show stress across multiple dimensions. High volatility and weak trend suggest fear-driven selling."
        
        interpretation = (
            f"Current conditions most closely resemble historical Stage {stage} ({stage_name}). "
            "This is a contextual assessment based on available indicators, not a prediction or timing signal."
        )
        
        return CycleStage(
            stage=stage,
            stage_name=stage_name,
            description=description,
            contributing_factors=factors,
            interpretation=interpretation
        )
