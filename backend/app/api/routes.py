"""API routes for stock drop analysis."""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta, timezone
from typing import List

from app.models.schemas import (
    AnalysisRequest,
    AnalysisFullResponse,
    DateRangeRequest,
    ChartDataPoint,
    ValuationContext,
    Tier1Dashboard,
    PriceTruth,
    MarketStateVector,
    EvidenceItem,
    AgentOutputContract,
    ForensicReport,
    ForensicReportHeader,
    ForensicHypothesis,
    CuratedSource,
    CuratedSourceGroup,
    CuratedEvidenceSummary
)
from app.agent.normalizer import EventNormalizer
from app.agent.market_context import MarketContextAnalyzer
from app.agent.hypothesis import HypothesisGenerator
from app.agent.renderer import ResponseRenderer
from app.agent.llm_renderer import LLMRenderer, create_llm_renderer
from app.retrieval.prices import PriceClient
from app.retrieval.edgar import EdgarClient
from app.retrieval.news import NewsClient
from app.retrieval.macro import MacroClient
from app.retrieval.valuation import ValuationProvider
from app.retrieval.symbols import get_symbol_universe
from app.context.regime import RegimeAnalyzer
from app.context.crowd import CrowdAnalyzer
from app.context.rotation import RotationAnalyzer
from app.context.tier1 import Tier1DashboardService
from app.pattern.analog_search import PatternAnalogEngine
from app.pattern.state_matching import create_state_matcher, find_historical_matches
from app.pattern.ticker_pattern_matching import TickerPatternMatcher
from app.evidence.curator import EvidenceCurator
from app.data.state_db.builder import get_state_db_builder, rebuild_state_db

router = APIRouter()


def _get_company_name_for_ticker(ticker: str) -> str:
    """
    Get company name for a ticker from the symbol universe.
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Company name if found, otherwise None
    """
    try:
        symbol_universe = get_symbol_universe()
        # Search the cached symbols
        for symbol in symbol_universe.symbols:
            if symbol.get('symbol', '').upper() == ticker.upper():
                return symbol.get('name')
        return None
    except Exception as e:
        print(f"Error getting company name for {ticker}: {e}")
        return None


async def _fetch_pattern_reasoning(
    ticker: str,
    start_date: str,
    end_date: str,
    news_client: NewsClient,
    macro_client: MacroClient
) -> List[str]:
    """
    Fetch concise reasoning bullets for why a pattern occurred.
    
    Looks for major events around the window and summarizes them.
    Expands the search window by ±7 days to catch catalysts near the pattern.
    """
    reasoning_bullets = []
    
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        
        # Expand search window by ±7 days to catch events just before/after the pattern
        search_start = start_dt - timedelta(days=7)
        search_end = end_dt + timedelta(days=7)
        
        # Get company name to improve news search results
        company_name = _get_company_name_for_ticker(ticker)
        
        # Fetch news for this period (limit to top 3-5 most relevant)
        news_articles = await news_client.search_news(
            ticker=ticker,
            company_name=company_name,
            start_time=search_start,
            end_time=search_end,
            max_results=20
        )
        
        # Get top news by authority score
        top_news = sorted(news_articles, key=lambda x: x.authority_score, reverse=True)[:3]
        
        for article in top_news:
            reasoning_bullets.append(f"{article.headline}")
        
        # Check for major macro events
        macro_context = await macro_client.get_macro_context(search_start, search_end)
        
        for event in macro_context[:2]:  # Top 2 macro events
            reasoning_bullets.append(f"Macro: {event.headline}")
        
        # If no events found, add a generic note
        if len(reasoning_bullets) == 0:
            date_str = start_dt.strftime("%B %Y")
            reasoning_bullets.append(f"Market movement in {date_str} - specific catalysts not available in current data sources")
        
    except Exception as e:
        print(f"Error fetching pattern reasoning: {e}")
        reasoning_bullets = ["Historical price movement - specific catalysts not available"]
    
    # Return max 5 bullets
    return reasoning_bullets[:5]


def _generate_forensic_report(
    ticker: str,
    start_time: datetime,
    end_time: datetime,
    price_data: dict,
    market_context: dict,
    hypotheses: list,
    timeline: list,
    unknowns: list,
    next_steps: list
) -> ForensicReport:
    """
    Generate institutional forensic report from existing analysis data.
    Follows strict structure: neutral, clear, explicit about uncertainty.
    """
    # Get company name
    company_name = _get_company_name_for_ticker(ticker) or ticker
    
    # 1. Header
    header = ForensicReportHeader(
        company_name=company_name,
        ticker=ticker,
        analysis_window=f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}"
    )
    
    # 2. Executive Summary
    drop_pct = price_data.get("drop_percent", 0)
    market_return = market_context.get("market_return_pct", 0)
    
    exec_bullets = []
    
    # Primary driver
    if abs(market_return) > abs(drop_pct) * 0.7:
        exec_bullets.append(f"Primary driver: Broad market movement ({market_return:+.1f}%)")
    else:
        exec_bullets.append(f"Primary driver: Company-specific factors (market: {market_return:+.1f}%)")
    
    # Trigger presence
    has_sec_filing = any(ev.source_type == "sec_filing" for h in hypotheses for ev in h.evidence)
    has_earnings = any(ev.source_type == "earnings" for h in hypotheses for ev in h.evidence)
    if has_sec_filing or has_earnings:
        exec_bullets.append("Confirmed trigger: SEC filing or earnings event present")
    else:
        exec_bullets.append("No confirmed company-specific trigger identified")
    
    # Overall confidence
    high_conf = sum(1 for h in hypotheses if h.confidence == "high")
    if high_conf >= 2:
        exec_bullets.append("Overall confidence: High")
    elif high_conf >= 1:
        exec_bullets.append("Overall confidence: Medium")
    else:
        exec_bullets.append("Overall confidence: Low — limited verifiable evidence")
    
    # 3. Market Context Assessment
    market_assessment = (
        f"The {market_context.get('market_index', 'S&P 500')} moved {market_return:+.2f}% during this period. "
    )
    if abs(market_return) > 2.0:
        market_assessment += "This represents material broad market pressure. "
    if abs(market_return) > abs(drop_pct) * 0.5:
        market_assessment += "Market-wide factors likely contributed significantly to the price movement."
    else:
        market_assessment += "The move appears primarily company-specific rather than market-driven."
    
    # 4. Primary Trigger Assessment
    if has_earnings:
        trigger_assessment = "A verified earnings event was identified during this period."
    elif has_sec_filing:
        trigger_assessment = "SEC filings were detected during this period."
    else:
        trigger_assessment = "No confirmed company-specific trigger was identified in available public sources."
    
    # 5. Ranked Hypotheses (max 3)
    ranked_hyps = []
    for h in hypotheses[:3]:  # Max 3
        prob_str = f"~{int(h.probability * 100)}%"
        evidence_types = list(set(ev.group for ev in h.evidence))
        ranked_hyps.append(ForensicHypothesis(
            title=h.title,
            estimated_probability=prob_str,
            confidence_level=h.confidence.capitalize(),
            mechanism=h.mechanism,
            evidence_types=evidence_types
        ))
    
    # 6. Timeline Summary
    if timeline and len(timeline) > 0:
        first_event = min(ev.timestamp for ev in timeline)
        if first_event < start_time:
            timeline_summary = "Information preceded price movement — suggests causal relationship."
        else:
            timeline_summary = "Most commentary followed price movement — suggests post-hoc rationalization."
    else:
        timeline_summary = "Insufficient temporal evidence to determine information flow vs price action."
    
    # 7. What This Was NOT
    what_not = [
        "No stock split detected",
        "No dividend announcement during period",
        "No major M&A activity identified"
    ]
    if not has_sec_filing:
        what_not.append("No material SEC filings found")
    
    # 8. Unknowns & Limitations
    unknowns_list = unknowns if unknowns else [
        "Internal company decisions not reflected in public filings",
        "Private investor actions and motivations",
        "Intraday order flow and positioning"
    ]
    
    # 9. Practical Interpretation
    practical = {
        "emotional_errors_to_avoid": [
            "Assuming headlines explain causality without temporal evidence",
            "Confusing narrative volume with explanatory power",
            "Reacting to price movement without understanding context"
        ],
        "what_to_monitor_next": next_steps if next_steps else [
            "Watch for follow-on SEC filings or guidance updates",
            "Monitor whether sector peers exhibit similar patterns",
            "Track whether market conditions stabilize or deteriorate"
        ]
    }
    
    # 10. Final Takeaway
    if abs(market_return) > abs(drop_pct) * 0.7:
        final_takeaway = "This move is best explained by broad market pressure rather than company-specific deterioration."
    elif ranked_hyps and ranked_hyps[0].confidence_level == "High":
        final_takeaway = f"Evidence suggests {ranked_hyps[0].title.lower()} as the primary explanation."
    else:
        final_takeaway = "Multiple factors likely contributed; no single explanation reaches high confidence with available evidence."
    
    return ForensicReport(
        header=header,
        executive_summary_bullets=exec_bullets,
        market_context_assessment=market_assessment,
        primary_trigger_assessment=trigger_assessment,
        ranked_hypotheses=ranked_hyps,
        timeline_summary=timeline_summary,
        what_this_was_not=what_not,
        unknowns_and_limitations=unknowns_list,
        practical_interpretation=practical,
        final_takeaway=final_takeaway
    )


async def _fetch_pattern_reasoning(
    ticker: str,
    start_date: str,
    end_date: str,
    news_client: NewsClient,
    macro_client: MacroClient
) -> List[str]:
    """
    Fetch concise reasoning bullets for why a pattern occurred.
    
    Looks for major events around the window and summarizes them.
    Expands the search window by ±7 days to catch catalysts near the pattern.
    """
    reasoning_bullets = []
    
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        
        # Expand search window by ±7 days to catch events just before/after the pattern
        search_start = start_dt - timedelta(days=7)
        search_end = end_dt + timedelta(days=7)
        
        # Get company name to improve news search results
        company_name = _get_company_name_for_ticker(ticker)
        
        # Fetch news for this period (limit to top 3-5 most relevant)
        news_articles = await news_client.search_news(
            ticker=ticker,
            company_name=company_name,
            start_time=search_start,
            end_time=search_end,
            max_results=20
        )
        
        # Get top news by authority score
        top_news = sorted(news_articles, key=lambda x: x.authority_score, reverse=True)[:3]
        
        for article in top_news:
            reasoning_bullets.append(f"{article.headline}")
        
        # Check for major macro events
        macro_context = await macro_client.get_macro_context(search_start, search_end)
        
        for event in macro_context[:2]:  # Top 2 macro events
            reasoning_bullets.append(f"Macro: {event.headline}")
        
        # If no events found, add a generic note
        if len(reasoning_bullets) == 0:
            date_str = start_dt.strftime("%B %Y")
            reasoning_bullets.append(f"Market movement in {date_str} - specific catalysts not available in current data sources")
        
    except Exception as e:
        print(f"Error fetching pattern reasoning: {e}")
        reasoning_bullets = ["Historical price movement - specific catalysts not available"]
    
    # Return max 5 bullets
    return reasoning_bullets[:5]


def _generate_forensic_report(
    ticker: str,
    start_time: datetime,
    end_time: datetime,
    price_data: dict,
    market_context: dict,
    hypotheses: list,
    timeline: list,
    unknowns: list,
    next_steps: list
) -> ForensicReport:
    """
    Generate institutional forensic report from existing analysis data.
    Follows strict structure: neutral, clear, explicit about uncertainty.
    """
    # Get company name
    company_name = _get_company_name_for_ticker(ticker) or ticker
    
    # 1. Header
    header = ForensicReportHeader(
        company_name=company_name,
        ticker=ticker,
        analysis_window=f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}"
    )
    
    # 2. Executive Summary
    drop_pct = price_data.get("drop_percent", 0)
    market_return = market_context.get("market_return_pct", 0)
    
    exec_bullets = []
    
    # Primary driver
    if abs(market_return) > abs(drop_pct) * 0.7:
        exec_bullets.append(f"Primary driver: Broad market movement ({market_return:+.1f}%)")
    else:
        exec_bullets.append(f"Primary driver: Company-specific factors (market: {market_return:+.1f}%)")
    
    # Trigger presence
    has_sec_filing = any(ev.source_type == "sec_filing" for h in hypotheses for ev in h.evidence)
    has_earnings = any(ev.source_type == "earnings" for h in hypotheses for ev in h.evidence)
    if has_sec_filing or has_earnings:
        exec_bullets.append("Confirmed trigger: SEC filing or earnings event present")
    else:
        exec_bullets.append("No confirmed company-specific trigger identified")
    
    # Overall confidence
    high_conf = sum(1 for h in hypotheses if h.confidence == "high")
    if high_conf >= 2:
        exec_bullets.append("Overall confidence: High")
    elif high_conf >= 1:
        exec_bullets.append("Overall confidence: Medium")
    else:
        exec_bullets.append("Overall confidence: Low — limited verifiable evidence")
    
    # 3. Market Context Assessment
    market_assessment = (
        f"The {market_context.get('market_index', 'S&P 500')} moved {market_return:+.2f}% during this period. "
    )
    if abs(market_return) > 2.0:
        market_assessment += "This represents material broad market pressure. "
    if abs(market_return) > abs(drop_pct) * 0.5:
        market_assessment += "Market-wide factors likely contributed significantly to the price movement."
    else:
        market_assessment += "The move appears primarily company-specific rather than market-driven."
    
    # 4. Primary Trigger Assessment
    if has_earnings:
        trigger_assessment = "A verified earnings event was identified during this period."
    elif has_sec_filing:
        trigger_assessment = "SEC filings were detected during this period."
    else:
        trigger_assessment = "No confirmed company-specific trigger was identified in available public sources."
    
    # 5. Ranked Hypotheses (max 3)
    ranked_hyps = []
    for h in hypotheses[:3]:  # Max 3
        prob_str = f"~{int(h.probability * 100)}%"
        evidence_types = list(set(ev.group for ev in h.evidence))
        ranked_hyps.append(ForensicHypothesis(
            title=h.title,
            estimated_probability=prob_str,
            confidence_level=h.confidence.capitalize(),
            mechanism=h.mechanism,
            evidence_types=evidence_types
        ))
    
    # 6. Timeline Summary
    if timeline and len(timeline) > 0:
        first_event = min(ev.timestamp for ev in timeline)
        if first_event < start_time:
            timeline_summary = "Information preceded price movement — suggests causal relationship."
        else:
            timeline_summary = "Most commentary followed price movement — suggests post-hoc rationalization."
    else:
        timeline_summary = "Insufficient temporal evidence to determine information flow vs price action."
    
    # 7. What This Was NOT
    what_not = [
        "No stock split detected",
        "No dividend announcement during period",
        "No major M&A activity identified"
    ]
    if not has_sec_filing:
        what_not.append("No material SEC filings found")
    
    # 8. Unknowns & Limitations
    unknowns_list = unknowns if unknowns else [
        "Internal company decisions not reflected in public filings",
        "Private investor actions and motivations",
        "Intraday order flow and positioning"
    ]
    
    # 9. Practical Interpretation
    practical = {
        "emotional_errors_to_avoid": [
            "Assuming headlines explain causality without temporal evidence",
            "Confusing narrative volume with explanatory power",
            "Reacting to price movement without understanding context"
        ],
        "what_to_monitor_next": next_steps if next_steps else [
            "Watch for follow-on SEC filings or guidance updates",
            "Monitor whether sector peers exhibit similar patterns",
            "Track whether market conditions stabilize or deteriorate"
        ]
    }
    
    # 10. Final Takeaway
    if abs(market_return) > abs(drop_pct) * 0.7:
        final_takeaway = "This move is best explained by broad market pressure rather than company-specific deterioration."
    elif ranked_hyps and ranked_hyps[0].confidence_level == "High":
        final_takeaway = f"Evidence suggests {ranked_hyps[0].title.lower()} as the primary explanation."
    else:
        final_takeaway = "Multiple factors likely contributed; no single explanation reaches high confidence with available evidence."
    
    return ForensicReport(
        header=header,
        executive_summary_bullets=exec_bullets,
        market_context_assessment=market_assessment,
        primary_trigger_assessment=trigger_assessment,
        ranked_hypotheses=ranked_hyps,
        timeline_summary=timeline_summary,
        what_this_was_not=what_not,
        unknowns_and_limitations=unknowns_list,
        practical_interpretation=practical,
        final_takeaway=final_takeaway
    )


@router.get("/chart/{ticker}", response_model=List[ChartDataPoint])
async def get_chart_data(
    ticker: str, 
    range: str = "max", 
    interval: str = "1d",
    start_date: str = None,
    end_date: str = None
):
    """
    Get chart data for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        range: Time range (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max) - ignored if dates provided
        interval: Data interval (1d, 1wk, 1mo)
        start_date: Optional start date (YYYY-MM-DD) for specific date range
        end_date: Optional end date (YYYY-MM-DD) for specific date range
    
    Returns:
        List of ChartDataPoint objects
    """
    try:
        price_client = PriceClient()
        
        # If specific dates provided, use period-based fetch
        if start_date and end_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            chart_data = await price_client.get_chart_data_by_dates(ticker, start_dt, end_dt, interval)
        else:
            chart_data = await price_client.get_chart_data_range(ticker, range, interval)
        
        return chart_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not fetch chart data for {ticker}: {str(e)}"
        )


@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics.
    
    Shows how many chart requests are cached and cache performance.
    """
    price_client = PriceClient()
    stats = price_client._chart_cache.get_stats()
    
    return {
        "chart_cache": stats,
        "description": "SWR cache: serves stale data instantly, refreshes in background after 60s"
    }


@router.post("/analyze-range", response_model=AnalysisFullResponse)
async def analyze_range(request: DateRangeRequest):
    """
    Analyze a stock price movement for a specific date range.
    
    This endpoint:
    1. Fetches price truth for the window
    2. Checks corporate actions (splits/dividends)
    3. Analyzes market/sector/peer context
    4. Retrieves evidence (SEC, news, macro)
    5. Generates and scores hypotheses
    6. Fetches regime, valuation, crowd, rotation context
    7. Finds pattern analogs with outcome dispersion
    8. Returns analysis with all context panels
    
    Args:
        request: DateRangeRequest with ticker, start_date, end_date
    
    Returns:
        AnalysisFullResponse with chat answer, script, and context panels
    """
    try:
        # Parse dates
        start_time = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
        
        # Ensure timezone-aware
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        
        # Initialize components
        price_client = PriceClient()
        market_analyzer = MarketContextAnalyzer()
        hypothesis_gen = HypothesisGenerator()
        renderer = ResponseRenderer()
        edgar_client = EdgarClient()
        news_client = NewsClient()
        macro_client = MacroClient()
        valuation_provider = ValuationProvider()
        regime_analyzer = RegimeAnalyzer()
        crowd_analyzer = CrowdAnalyzer()
        rotation_analyzer = RotationAnalyzer()
        pattern_engine = PatternAnalogEngine()
        
        # Step 1: Get price data (truth)
        price_data = await price_client.get_price_data(request.ticker, start_time, end_time)
        
        if not price_data:
            raise HTTPException(
                status_code=404,
                detail=f"Could not find price data for {request.ticker} in the selected range"
            )
        
        # Build event_data dict
        event_data = {
            "ticker": request.ticker,
            "start_time": start_time,
            "end_time": end_time,
            "start_price": price_data["start_price"],
            "end_price": price_data["end_price"],
            "drop_percent": price_data["drop_percent"],
            "volume_vs_average": price_data["volume_vs_average"],
            "session_type": price_data["session_type"]
        }
        
        # Step 2: Check corporate actions
        splits, dividends = await price_client.get_corporate_actions(request.ticker, start_time, end_time)
        
        evidence_list = []
        evidence_list.extend(splits)
        evidence_list.extend(dividends)
        
        # If there's a split and the drop matches split pattern, warn user
        if splits:
            drop_pct = price_data["drop_percent"]
            if abs(drop_pct + 50) < 2 or abs(drop_pct + 66.67) < 2 or abs(drop_pct + 75) < 2:
                raise HTTPException(
                    status_code=400,
                    detail=f"Price change matches a stock split pattern. Split detected: {splits[0].headline}. "
                           f"This is not a true price decline."
                )
        
        # Step 3: Analyze market context
        market_context = await market_analyzer.analyze_context(
            request.ticker,
            start_time,
            end_time,
            sector=None,  # TODO: Add sector lookup
            peers=None    # TODO: Add peer lookup
        )
        
        # Classify move type
        move_type = market_analyzer.classify_move_type(
            event_data["drop_percent"],
            market_context.market_return_pct,
            market_context.sector_return_pct,
            market_context.peer_median_return_pct
        )
        event_data["move_type"] = move_type
        
        # Step 4: Retrieve evidence (tight window: ±10 days)
        evidence_window_days = 10
        evidence_start = start_time - timedelta(days=evidence_window_days)
        evidence_end = end_time + timedelta(days=evidence_window_days)
        
        # Get SEC filings
        filings = await edgar_client.search_filings(request.ticker, evidence_start, evidence_end)
        evidence_list.extend(filings)
        
        # Get news
        news_items = await news_client.search_news(
            request.ticker,
            company_name=None,  # TODO: Add company name lookup
            start_time=evidence_start,
            end_time=evidence_end
        )
        evidence_list.extend(news_items)
        
        # Get macro context
        macro_items = await macro_client.get_macro_context(evidence_start, evidence_end)
        evidence_list.extend(macro_items)
        
        # Step 5: Generate hypotheses
        hypotheses = hypothesis_gen.generate_hypotheses(
            evidence_list,
            event_data,
            market_context
        )
        
        # Build timeline
        timeline = hypothesis_gen.build_timeline(evidence_list)
        
        # Step 6: Get context panels
        try:
            regime = await regime_analyzer.get_regime()
        except:
            regime = None
        
        try:
            # Get valuation context
            cape_data = await valuation_provider.get_cape_ratio()
            buffett_data = await valuation_provider.get_buffett_indicator()
            breadth_data = await valuation_provider.get_breadth_reading()
            
            # Build context statement
            context_parts = []
            if cape_data:
                context_parts.append(f"CAPE ratio is at {cape_data['percentile']:.0f}th percentile")
            if buffett_data:
                context_parts.append(f"Buffett Indicator is at {buffett_data['percentile']:.0f}th percentile")
            
            if context_parts:
                context_statement = "Valuation metrics: " + ", ".join(context_parts) + ". "
                context_statement += "Elevated percentiles have historically been associated with increased volatility risk."
            else:
                context_statement = "Valuation data not available from current free data sources."
            
            valuation = ValuationContext(
                cape_ratio=cape_data["value"] if cape_data else None,
                cape_percentile=cape_data["percentile"] if cape_data else None,
                buffett_indicator=buffett_data["value"] if buffett_data else None,
                buffett_percentile=buffett_data["percentile"] if buffett_data else None,
                breadth_reading=breadth_data["value"] if breadth_data else None,
                breadth_interpretation=breadth_data["interpretation"] if breadth_data else None,
                context_statement=context_statement
            )
        except:
            valuation = ValuationContext(
                context_statement="Valuation data not available from current free data sources."
            )
        
        try:
            crowd = await crowd_analyzer.get_crowd_behavior()
        except:
            crowd = None
        
        try:
            rotation = await rotation_analyzer.get_rotation_context()
        except:
            rotation = None
        
        # Step 7: Find pattern analogs
        try:
            pattern_analogs = await pattern_engine.find_analogs(
                request.ticker,
                start_time,
                end_time,
                max_analogs=10
            )
        except:
            pattern_analogs = []
        
        # Step 8: Render response (legacy format)
        response = renderer.render_full_response(
            ticker=request.ticker,
            event_data=event_data,
            market_context=market_context,
            move_type=move_type,
            hypotheses=hypotheses,
            timeline=timeline,
            regime=regime,
            valuation=valuation,
            crowd=crowd,
            rotation=rotation,
            pattern_analogs=pattern_analogs
        )
        
        # Step 9: Build SYSTEM JSON Contract (new format)
        try:
            # Build PriceTruth
            price_truth = PriceTruth(
                start_price=price_data["start_price"],
                end_price=price_data["end_price"],
                drawdown_pct=price_data["drop_percent"],
                volume_spike=price_data["volume_vs_average"],
                splits=[s.headline for s in splits],
                dividends=[d.headline for d in dividends]
            )
            
            # Build MarketStateVector from Tier-1 dashboard
            try:
                tier1_service = Tier1DashboardService()
                tier1_data = await tier1_service.get_dashboard("^GSPC")
                
                market_state = MarketStateVector(
                    cape_ratio=tier1_data.cape.value,
                    cape_percentile=tier1_data.cape.percentile,
                    buffett_indicator=tier1_data.buffett.value,
                    buffett_percentile=tier1_data.buffett.percentile,
                    vix_level=tier1_data.vix.value,
                    vix_regime=tier1_data.vix.regime.lower() if tier1_data.vix.regime != "Unknown" else "unknown",
                    sp500_above_50ma=tier1_data.moving_averages.price_vs_50 == "Above",
                    sp500_above_200ma=tier1_data.moving_averages.price_vs_200 == "Above",
                    trend_regime="uptrend" if tier1_data.moving_averages.price_vs_200 == "Above" else "downtrend",
                    breadth_value=tier1_data.breadth.value,
                    breadth_regime=tier1_data.breadth.interpretation.lower() if "strong" in tier1_data.breadth.interpretation.lower() else "neutral",
                    leadership_concentration=tier1_data.leadership.value,
                    leadership_regime=tier1_data.leadership.leadership_label.lower() if tier1_data.leadership.leadership_label != "Unknown" else "unknown",
                    xly_xlp_ratio=tier1_data.sector_rotation.xly_xlp_ratio,
                    sector_rotation_regime="risk_on" if tier1_data.sector_rotation.xly_xlp_ratio and tier1_data.sector_rotation.xly_xlp_ratio > 1.0 else "risk_off"
                )
            except Exception as e:
                # Fallback to empty market state
                market_state = MarketStateVector()
            
            # Convert Evidence to EvidenceItem format
            evidence_items = []
            for i, ev in enumerate(evidence_list):
                evidence_items.append(EvidenceItem(
                    evidence_id=f"E{i+1}",
                    timestamp=ev.timestamp,
                    source_type=ev.source_type,
                    source_url=ev.source_url,
                    headline=ev.headline,
                    snippet=ev.snippet,
                    authority_score=ev.authority_score,
                    citation_text=f"[{ev.group}: {ev.headline} {ev.source_url}]",
                    group=ev.group,
                    days_from_event=(ev.timestamp - start_time).days if ev.timestamp else None
                ))
            
            # Build unknowns and next_steps
            unknowns = response.chat_answer.unknowns
            next_steps = response.chat_answer.next_steps
            data_sources = response.chat_answer.data_sources
            
            # Find historical state matches
            try:
                historical_matches = await find_historical_matches(market_state, top_n=10)
            except Exception as e:
                print(f"Error finding historical matches: {e}")
                historical_matches = []
            
            # Find similar price patterns (ticker-specific)
            similar_patterns_data = []
            try:
                pattern_matcher = TickerPatternMatcher()
                similar_patterns_raw = await pattern_matcher.find_similar_patterns(
                    ticker=request.ticker,
                    start_date=start_time,
                    end_date=end_time,
                    interval="1d",
                    top_k=5
                )
                
                # Convert to schema and add reasoning
                for match in similar_patterns_raw:
                    # Fetch reasoning for this historical window
                    reasoning = await _fetch_pattern_reasoning(
                        request.ticker,
                        match["start_date"],
                        match["end_date"],
                        news_client,
                        macro_client
                    )
                    
                    similar_patterns_data.append({
                        "start_date": match["start_date"],
                        "end_date": match["end_date"],
                        "similarity_score": match["similarity_score"],
                        "outcomes": match["outcomes"],
                        "reasoning_events": reasoning
                    })
            except Exception as e:
                # Silently handle pattern matching errors (non-critical feature)
                similar_patterns_data = []
            
            # Render agent contract using LLM (or deterministic fallback)
            llm_renderer = create_llm_renderer()
            agent_contract = await llm_renderer.render_agent_contract(
                ticker=request.ticker,
                start_date=start_time,
                end_date=end_time,
                price_truth=price_truth,
                market_state=market_state,
                historical_matches=historical_matches,
                similar_patterns=similar_patterns_data,
                evidence_items=evidence_items,
                unknowns=unknowns,
                next_steps=next_steps,
                data_sources=data_sources
            )
            
            # Generate forensic report
            try:
                forensic_report = _generate_forensic_report(
                    ticker=request.ticker,
                    start_time=start_time,
                    end_time=end_time,
                    price_data=price_data,
                    market_context=market_context.__dict__,
                    hypotheses=hypotheses,
                    timeline=timeline,
                    unknowns=unknowns,
                    next_steps=next_steps
                )
                agent_contract.forensic_report = forensic_report
            except Exception as e:
                print(f"Error generating forensic report: {e}")
                agent_contract.forensic_report = None
            
            # Curate evidence
            try:
                curator = EvidenceCurator()
                company_name = _get_company_name_for_ticker(request.ticker)
                
                curation_result = curator.curate_evidence(
                    evidence_list=evidence_list,
                    ticker=request.ticker,
                    company_name=company_name,
                    start_time=start_time,
                    end_time=end_time,
                    evidence_window_start=evidence_start,
                    evidence_window_end=evidence_end
                )
                
                # Build curated groups
                groups = []
                category_labels = {
                    'Primary': 'Primary Sources',
                    'CorporateOperational': 'Corporate & Operational',
                    'MacroSystemic': 'Macro & Systemic',
                    'Narrative': 'Market Commentary'
                }
                
                for category, sources in curation_result['groups'].items():
                    if not sources:
                        continue
                    
                    # Build CuratedSource objects with relative time labels
                    curated_sources = []
                    for source in sources:
                        # Compute relative time label
                        time_diff = (source['timestamp'] - start_time).total_seconds()
                        hours = abs(time_diff) / 3600
                        
                        if time_diff < 0:
                            # Before the move
                            if hours < 1:
                                rel_time = f"{int(abs(time_diff) / 60)} min before"
                            elif hours < 24:
                                rel_time = f"{int(hours)} hr{'s' if int(hours) > 1 else ''} before"
                            else:
                                days = int(hours / 24)
                                rel_time = f"{days} day{'s' if days > 1 else ''} before"
                        else:
                            # After the move
                            if hours < 1:
                                rel_time = f"{int(time_diff / 60)} min after"
                            elif hours < 24:
                                rel_time = f"{int(hours)} hr{'s' if int(hours) > 1 else ''} after"
                            else:
                                days = int(hours / 24)
                                rel_time = f"{days} day{'s' if days > 1 else ''} after"
                        
                        curated_sources.append(CuratedSource(
                            headline=source['headline'],
                            url=source['url'],
                            timestamp=source['timestamp'],
                            category=category,
                            relative_time_label=rel_time,
                            authority_score=source['authority'],
                            relevance_score=source['relevance'],
                            timing_score=source['timing'],
                            final_weight=source['final_weight']
                        ))
                    
                    # Top 3 and remaining
                    top_3 = curated_sources[:3]
                    remaining = len(curated_sources) - 3 if len(curated_sources) > 3 else 0
                    
                    groups.append(CuratedSourceGroup(
                        category=category,
                        category_label=category_labels.get(category, category),
                        top_sources=top_3,
                        remaining_count=remaining,
                        all_sources=curated_sources
                    ))
                
                agent_contract.curated_evidence = CuratedEvidenceSummary(
                    groups=groups,
                    disclaimer_if_narrative_only=curation_result['disclaimer_if_narrative_only'],
                    total_sources_validated=curation_result['total_validated'],
                    total_sources_collapsed=curation_result['total_collapsed']
                )
                
            except Exception as e:
                print(f"Error curating evidence: {e}")
                import traceback
                traceback.print_exc()
                agent_contract.curated_evidence = None
            
            # Add to response
            response.agent_contract = agent_contract
            
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error building agent contract: {e}")
            response.agent_contract = None
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing stock drop: {str(e)}"
        )


@router.post("/analyze", response_model=AnalysisFullResponse)
async def analyze_stock_drop(request: AnalysisRequest):
    """
    Legacy analysis endpoint (for backward compatibility).
    
    Converts time window to date range and calls analyze_range.
    """
    # Calculate time window
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=request.time_window_hours)
    
    # Create DateRangeRequest
    range_request = DateRangeRequest(
        ticker=request.ticker,
        start_date=start_time.isoformat(),
        end_date=end_time.isoformat()
    )
    
    return await analyze_range(range_request)


@router.get("/context/regime")
async def get_regime():
    """Get current market regime (Stage 1-4)."""
    try:
        regime_analyzer = RegimeAnalyzer()
        regime = await regime_analyzer.get_regime()
        return regime
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching regime context: {str(e)}"
        )


@router.get("/context/valuation")
async def get_valuation():
    """Get valuation stress indicators (CAPE, Buffett, breadth)."""
    try:
        valuation_provider = ValuationProvider()
        
        cape_data = await valuation_provider.get_cape_ratio()
        buffett_data = await valuation_provider.get_buffett_indicator()
        breadth_data = await valuation_provider.get_breadth_reading()
        
        context_parts = []
        if cape_data:
            context_parts.append(f"CAPE ratio at {cape_data['percentile']:.0f}th percentile")
        if buffett_data:
            context_parts.append(f"Buffett Indicator at {buffett_data['percentile']:.0f}th percentile")
        
        if context_parts:
            context_statement = "Valuation metrics: " + ", ".join(context_parts) + ". "
            context_statement += "Elevated percentiles have historically been associated with increased volatility risk."
        else:
            context_statement = "Valuation data not available from current free data sources."
        
        return ValuationContext(
            cape_ratio=cape_data["value"] if cape_data else None,
            cape_percentile=cape_data["percentile"] if cape_data else None,
            buffett_indicator=buffett_data["value"] if buffett_data else None,
            buffett_percentile=buffett_data["percentile"] if buffett_data else None,
            breadth_reading=breadth_data["value"] if breadth_data else None,
            breadth_interpretation=breadth_data["interpretation"] if breadth_data else None,
            context_statement=context_statement
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching valuation context: {str(e)}"
        )


@router.get("/context/crowd")
async def get_crowd():
    """Get crowd behavior indicators."""
    try:
        crowd_analyzer = CrowdAnalyzer()
        crowd = await crowd_analyzer.get_crowd_behavior()
        return crowd
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching crowd context: {str(e)}"
        )


@router.get("/context/rotation")
async def get_rotation(lookback_days: int = 30):
    """Get sector rotation context."""
    try:
        rotation_analyzer = RotationAnalyzer()
        rotation = await rotation_analyzer.get_rotation_context(lookback_days)
        return rotation
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching rotation context: {str(e)}"
        )


@router.post("/pattern/analogs")
async def find_pattern_analogs(request: DateRangeRequest, max_analogs: int = 10):
    """Find historical pattern analogs with outcome dispersion."""
    try:
        start_time = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
        
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        
        pattern_engine = PatternAnalogEngine()
        analogs = await pattern_engine.find_analogs(
            request.ticker,
            start_time,
            end_time,
            max_analogs
        )
        
        return {"analogs": analogs, "pattern_not_outcome_warning": "Similar patterns have led to varied outcomes. Historical patterns do not predict future results."}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error finding pattern analogs: {str(e)}"
        )


# ============================================================================
# TIER-1 DASHBOARD ENDPOINT
# ============================================================================

@router.get("/tier1/dashboard", response_model=Tier1Dashboard)
async def get_tier1_dashboard(market: str = "^GSPC"):
    """
    Get the Tier-1 always-visible indicator dashboard.
    
    This endpoint returns all 8 Tier-1 indicators:
    - CAPE (Shiller PE) with percentile
    - Buffett Indicator with zone
    - Market Breadth (equal-weight vs cap-weight proxy)
    - Leadership Concentration
    - Sector Rotation (XLY/XLP ratio + defensives)
    - VIX regime (Compressed/Normal/Elevated)
    - Moving Averages (50D/200D trend health)
    - Market Cycle Stage (1-4 meta indicator)
    
    All indicators are contextual and regime-focused.
    No prediction or timing signals are provided.
    
    Args:
        market: Market proxy to use (default: ^GSPC, fallback: SPY)
    
    Returns:
        Tier1Dashboard with all indicators
    """
    try:
        tier1_service = Tier1DashboardService()
        dashboard = await tier1_service.get_dashboard(market)
        return dashboard
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching Tier-1 dashboard: {str(e)}"
        )


@router.get("/symbols/search")
async def search_symbols(q: str = "", limit: int = 20):
    """
    Search US stocks and ETFs by symbol or company name.
    
    Returns results formatted for react-select autocomplete.
    
    Args:
        q: Search query (symbol or company name)
        limit: Maximum number of results (default: 20)
    
    Returns:
        List of { value, label, meta } objects for react-select
    """
    try:
        symbol_universe = get_symbol_universe()
        matches = await symbol_universe.search(q, limit)
        
        # Format for react-select
        results = []
        for match in matches:
            # Format label with symbol and company name
            label = f"{match['display_symbol']} - {match['name']}"
            if match['is_etf']:
                label += " (ETF)"
            
            results.append({
                "value": match['symbol'],  # Yahoo-compatible symbol
                "label": label,
                "meta": {
                    "exchange": match['exchange'],
                    "is_etf": match['is_etf']
                }
            })
        
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching symbols: {str(e)}"
        )


# ============================================================================
# STATE DATABASE MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/state-db/rebuild")
async def rebuild_state_database():
    """
    Rebuild the historical state database.
    
    This fetches S&P 500 historical data and builds monthly state snapshots
    with Tier-1 indicators and forward outcomes.
    
    Note: This may take a minute to complete.
    """
    try:
        states = await rebuild_state_db()
        return {
            "status": "success",
            "message": f"Rebuilt state database with {len(states)} monthly snapshots",
            "num_states": len(states)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error rebuilding state database: {str(e)}"
        )


@router.get("/state-db/stats")
async def get_state_db_stats():
    """Get statistics about the historical state database."""
    try:
        builder = get_state_db_builder()
        states = builder.get_states()
        
        if not states:
            return {
                "status": "empty",
                "num_states": 0,
                "message": "State database is empty. Call POST /api/state-db/rebuild to populate."
            }
        
        return {
            "status": "ready",
            "num_states": len(states),
            "date_range": {
                "start": states[0]["date"] if states else None,
                "end": states[-1]["date"] if states else None
            },
            "indicators_available": [
                "vix_level", "vix_regime", "trend_regime",
                "sp500_above_50ma", "sp500_above_200ma",
                "xly_xlp_ratio", "sector_rotation_regime"
            ],
            "outcomes_available": ["3m", "6m", "12m"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting state database stats: {str(e)}"
        )


@router.post("/state-matching/find")
async def find_state_matches(state: MarketStateVector, top_n: int = 10):
    """
    Find historical states similar to the provided state vector.
    
    Args:
        state: Current market state vector
        top_n: Maximum number of matches to return
    
    Returns:
        List of historical matches with similarity scores and outcomes
    """
    try:
        matches = await find_historical_matches(state, top_n=top_n)
        
        # Compute aggregate outcomes
        matcher = create_state_matcher()
        aggregate_outcomes = matcher.compute_aggregate_outcomes(matches)
        
        return {
            "matches": [m.model_dump() for m in matches],
            "aggregate_outcomes": {k: v.model_dump() for k, v in aggregate_outcomes.items()},
            "warning": "Historical patterns do not predict future results. Outcomes in similar conditions varied widely."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error finding state matches: {str(e)}"
        )
