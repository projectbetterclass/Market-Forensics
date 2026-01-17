"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# SYSTEM JSON OUTPUT CONTRACT SCHEMAS
# ============================================================================

class PriceTruth(BaseModel):
    """Verified price behavior from authoritative source (STEP 1)."""
    start_price: float
    end_price: float
    drawdown_pct: float = Field(description="Percentage change from start to end")
    volume_spike: Optional[float] = Field(None, description="Volume vs average (1.0 = normal)")
    splits: List[str] = Field(default_factory=list, description="Detected stock splits")
    dividends: List[str] = Field(default_factory=list, description="Detected dividends")
    data_source: str = "Yahoo Finance"
    verified: bool = True


class MarketStateVector(BaseModel):
    """
    Tier-1 Market State Vector at event time (STEP 2).
    
    Represents the state of key market indicators at the time of the event.
    Used for historical state matching.
    """
    # Valuation indicators
    cape_ratio: Optional[float] = None
    cape_percentile: Optional[float] = Field(None, description="CAPE percentile vs history (0-100)")
    buffett_indicator: Optional[float] = None
    buffett_percentile: Optional[float] = Field(None, description="Buffett Indicator percentile (0-100)")
    
    # Volatility
    vix_level: Optional[float] = None
    vix_regime: Literal["low", "normal", "high", "unknown"] = "unknown"
    vix_vs_60d_avg: Optional[float] = Field(None, description="VIX relative to 60-day average")
    
    # Trend
    sp500_above_50ma: Optional[bool] = None
    sp500_above_200ma: Optional[bool] = None
    trend_regime: Literal["uptrend", "downtrend", "sideways", "unknown"] = "unknown"
    
    # Breadth
    breadth_value: Optional[float] = None
    breadth_regime: Literal["strong", "neutral", "weak", "unknown"] = "unknown"
    
    # Leadership
    leadership_concentration: Optional[float] = Field(None, description="% of returns from top stocks")
    leadership_regime: Literal["broad", "moderate", "narrow", "unknown"] = "unknown"
    
    # Sector rotation
    xly_xlp_ratio: Optional[float] = Field(None, description="Consumer discretionary vs staples ratio")
    sector_rotation_regime: Literal["risk_on", "neutral", "risk_off", "unknown"] = "unknown"
    
    # Definitions (for transparency)
    indicator_definitions: Dict[str, str] = Field(default_factory=lambda: {
        "cape_ratio": "Cyclically Adjusted PE ratio (Shiller PE) - price to 10-year inflation-adjusted earnings",
        "buffett_indicator": "Total US stock market capitalization divided by GDP",
        "vix": "CBOE Volatility Index - measures expected 30-day S&P 500 volatility",
        "breadth": "Market breadth - proportion of advancing vs declining stocks",
        "leadership_concentration": "Percentage of market returns driven by top stocks",
        "xly_xlp_ratio": "Consumer Discretionary (XLY) vs Consumer Staples (XLP) - risk appetite proxy"
    })


class OutcomeDistribution(BaseModel):
    """Forward outcome distribution for a time horizon."""
    horizon: str = Field(description="Time horizon (e.g., '3m', '6m', '12m')")
    mean_return_pct: float
    median_return_pct: float
    percentile_10: float
    percentile_25: float
    percentile_75: float
    percentile_90: float
    max_drawdown_mean: Optional[float] = None
    positive_outcome_pct: float = Field(description="Percentage of cases with positive return")
    sample_size: int


class TickerPatternMatch(BaseModel):
    """
    A ticker-specific price-shape pattern match.
    
    Represents a past time period where the same ticker showed similar price movement.
    """
    start_date: datetime
    end_date: datetime
    similarity_score: float = Field(ge=0.0, le=1.0, description="How similar the price pattern was")
    outcomes: Dict[str, Any] = Field(default_factory=dict, description="Forward returns from match end")
    reasoning_events: List[str] = Field(default_factory=list, description="What caused the movement then")


class HistoricalMatch(BaseModel):
    """
    A historical state match (STEP 3).
    
    Represents a past time period where the market state vector was similar.
    Includes forward outcomes for context (not prediction).
    """
    match_date: datetime
    similarity_score: float = Field(ge=0.0, le=1.0, description="How similar the state was (1.0 = identical)")
    
    # State at match time
    state_at_match: Dict[str, Any] = Field(description="Key indicator values at match time")
    
    # Forward outcomes (historical facts, not predictions)
    outcomes: Dict[str, OutcomeDistribution] = Field(
        description="Forward returns from this date (3m, 6m, 12m)"
    )
    
    # Context
    market_regime_at_time: Optional[str] = None
    notable_events: List[str] = Field(default_factory=list)
    
    # Guardrail reminder
    outcome_warning: str = "Historical outcomes varied. Similar patterns have led to different results."


class EvidenceHypothesis(BaseModel):
    """
    A hypothesis with confidence estimate (not probability) and strict citations.
    """
    hypothesis_id: str
    title: str
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence estimate based on evidence quality")
    confidence_label: Literal["high", "medium", "low"]
    explanation: str = Field(description="Must cite evidence explicitly")
    
    # Attached evidence (strict citation requirement)
    evidence_ids: List[str] = Field(description="IDs of evidence items supporting this hypothesis")
    
    # Scoring breakdown
    timing_proximity_score: float = Field(ge=0.0, le=1.0)
    authority_score: float = Field(ge=0.0, le=1.0)
    corroboration_score: float = Field(ge=0.0, le=1.0)
    
    # Non-hallucination requirement
    is_speculative: bool = Field(False, description="True if hypothesis extends beyond direct evidence")
    speculation_disclosure: Optional[str] = None


class EvidenceItem(BaseModel):
    """
    Evidence item with strict citation requirements.
    Extended from base Evidence with additional fields for contract compliance.
    """
    evidence_id: str
    timestamp: datetime
    source_type: Literal["sec_filing", "news", "macro", "corporate_action", "indicator"]
    source_url: str
    headline: str
    snippet: Optional[str] = None
    authority_score: float = Field(ge=0.0, le=1.0)
    
    # Citation format
    citation_text: str = Field(description="Formatted citation: [Type: headline url]")
    
    # Grouping for UX
    group: Literal["SEC", "News", "Macro", "CorporateActions", "Indicator", "Other"] = "Other"
    
    # Timing proximity to event
    days_from_event: Optional[float] = None


class ForensicReportHeader(BaseModel):
    """Header for the forensic report."""
    company_name: str
    ticker: str
    analysis_window: str
    principle: str = "Prepare, don't predict. Understand context before conclusions."


class ForensicHypothesis(BaseModel):
    """A ranked hypothesis in the forensic report (max 3)."""
    title: str
    estimated_probability: str  # e.g., "~40%", "Low (~20%)", "Moderate"
    confidence_level: Literal["Low", "Medium", "High"]
    mechanism: str
    evidence_types: List[str]  # e.g., ["SEC Filings", "News Articles", "Market Data"]


class ForensicReport(BaseModel):
    """
    Institutional forensic report for price movement analysis.
    Follows strict structure: neutral, clear, explicit about uncertainty.
    """
    # 1. Header
    header: ForensicReportHeader
    
    # 2. Executive Summary (One-Glance)
    executive_summary_bullets: List[str] = Field(
        description="3-5 bullet points: primary driver, trigger presence, confidence"
    )
    
    # 3. Market Context (ALWAYS FIRST)
    market_context_assessment: str = Field(
        description="Whether move coincided with broad market/sector pressure"
    )
    
    # 4. Primary Trigger Assessment
    primary_trigger_assessment: str = Field(
        description="Explicit statement of verified earnings/guidance/regulatory/corporate action, or 'None identified'"
    )
    
    # 5. Ranked Explanatory Hypotheses (max 3)
    ranked_hypotheses: List[ForensicHypothesis] = Field(
        default_factory=list,
        description="Max 3 hypotheses ranked by plausibility"
    )
    
    # 6. Timeline Summary (Condensed)
    timeline_summary: str = Field(
        description="Whether information preceded price or commentary followed"
    )
    
    # 7. What This Was NOT (mandatory)
    what_this_was_not: List[str] = Field(
        description="Events checked but not found, common misconceptions avoided"
    )
    
    # 8. Unknowns & Limitations
    unknowns_and_limitations: List[str] = Field(
        description="What public data cannot reveal, where uncertainty remains"
    )
    
    # 9. Practical Interpretation (Non-Advice)
    practical_interpretation: Dict[str, List[str]] = Field(
        description="Keys: 'emotional_errors_to_avoid', 'what_to_monitor_next'"
    )
    
    # 10. Final Takeaway
    final_takeaway: str = Field(
        description="Single sentence: context over narratives, evidence over headlines"
    )


class CuratedSource(BaseModel):
    """A curated evidence source with scoring metadata."""
    headline: str
    url: str
    timestamp: datetime
    category: Literal["Primary", "CorporateOperational", "MacroSystemic", "Narrative"]
    relative_time_label: str = Field(description="e.g., '2 hours before', '1 day after'")
    authority_score: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    timing_score: float = Field(ge=0.0, le=1.0)
    final_weight: float = Field(ge=0.0, le=1.0, description="min(authority, relevance, timing)")


class CuratedSourceGroup(BaseModel):
    """A group of curated sources by category."""
    category: Literal["Primary", "CorporateOperational", "MacroSystemic", "Narrative"]
    category_label: str = Field(description="Human-readable label")
    top_sources: List[CuratedSource] = Field(description="Top 3 sources by weight")
    remaining_count: int = Field(description="Count of additional sources not shown by default")
    all_sources: List[CuratedSource] = Field(default_factory=list, description="All sources in this group")


class CuratedEvidenceSummary(BaseModel):
    """Summary of curated evidence with grouped sources."""
    groups: List[CuratedSourceGroup] = Field(default_factory=list)
    disclaimer_if_narrative_only: Optional[str] = Field(
        None,
        description="Mandatory disclaimer if only Narrative sources exist"
    )
    total_sources_validated: int = Field(default=0)
    total_sources_collapsed: int = Field(default=0, description="Count of syndicated duplicates collapsed")


class AgentOutputContract(BaseModel):
    """
    Complete SYSTEM JSON Output Contract.
    
    This is the strict output format that the agent must produce.
    All factual claims must be backed by evidence or computed indicators.
    """
    # Metadata
    ticker: str
    period: Dict[str, str] = Field(description="{'start_date': ..., 'end_date': ...}")
    analysis_timestamp: datetime
    
    # STEP 1: Price Truth
    price_truth: PriceTruth
    
    # STEP 2: Market State at Event
    market_state: MarketStateVector
    
    # STEP 3a: Historical Matches (market state based)
    historical_matches: List[HistoricalMatch] = Field(
        default_factory=list,
        description="Similar historical states with outcomes"
    )
    historical_match_summary: Optional[str] = Field(
        None,
        description="Statistical summary of matched outcomes"
    )
    
    # STEP 3b: Similar Patterns (ticker price-shape based)
    similar_patterns: List[TickerPatternMatch] = Field(
        default_factory=list,
        description="Similar price patterns from same ticker's history"
    )
    
    # STEP 4: Evidence (all retrieved items)
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    
    # STEP 5: Hypotheses (ranked by confidence)
    hypotheses: List[EvidenceHypothesis] = Field(default_factory=list)
    
    # STEP 6: Conversational Answer
    conversational_answer: str = Field(
        description="Natural language analysis with explicit citations"
    )
    
    # STEP 7: YouTube Script
    youtube_script: str = Field(
        description="Structured script with HOOK, RECEIPTS, CONTEXT, RANKED CAUSES, UNKNOWNS, NEXT STEPS, CLOSING"
    )
    
    # Known gaps
    unknowns: List[str] = Field(
        default_factory=list,
        description="What cannot be resolved with available sources"
    )
    
    # Follow-up suggestions (not advice)
    next_steps: List[str] = Field(default_factory=list)
    
    # Data source attestation
    data_sources_used: List[str] = Field(default_factory=list)
    
    # Guardrails
    disclaimer: str = (
        "This analysis is provided for educational and informational purposes only. "
        "It does not constitute financial advice, investment recommendations, or predictions. "
        "All claims are backed by cited evidence or computed from public data. "
        "Historical patterns do not predict future results."
    )
    
    # Validation flag
    all_claims_cited: bool = Field(
        True,
        description="Attestation that all factual claims have explicit citations"
    )
    
    # Forensic Report (institutional structure)
    forensic_report: Optional[ForensicReport] = Field(
        None,
        description="Structured forensic report for institutional presentation"
    )
    
    # Curated Evidence (quality-filtered sources)
    curated_evidence: Optional[CuratedEvidenceSummary] = Field(
        None,
        description="Curated and grouped evidence sources with quality scoring"
    )


# ============================================================================
# ORIGINAL SCHEMAS (kept for backward compatibility)
# ============================================================================

class Evidence(BaseModel):
    """Evidence object with strict citation requirements."""
    timestamp: datetime
    source_type: Literal["sec_filing", "news", "macro", "corporate_action", "social", "earnings"]
    source_url: str
    headline: str
    snippet: Optional[str] = None
    authority_score: float = Field(ge=0.0, le=1.0)
    # New fields for evidence UX
    group: Literal["SEC", "News", "Macro", "CorporateActions", "Other"] = "Other"
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    why_this_matters: Optional[str] = None
    what_it_explains: Optional[str] = None


class Hypothesis(BaseModel):
    """A ranked hypothesis with explicit probability."""
    rank: int
    title: str
    probability: float = Field(ge=0.0, le=1.0, description="Explicit probability [0,1]")
    confidence: Literal["high", "medium", "low"]
    explanation: str
    evidence: List[Evidence]
    mechanism: str
    confirmation_check: str


class MarketContext(BaseModel):
    """Market, sector, and peer context."""
    market_index: str
    market_return_pct: float
    sector_name: Optional[str] = None
    sector_return_pct: Optional[float] = None
    peer_median_return_pct: Optional[float] = None
    interpretation: str


class TimelineEvent(BaseModel):
    """Timeline event tied to evidence."""
    timestamp: datetime
    description: str
    evidence: Evidence
    price_impact: Optional[str] = None


class MarketRegime(BaseModel):
    """Market regime context (Stage 1-4)."""
    stage: Literal[1, 2, 3, 4]
    stage_name: str
    description: str
    volatility_regime: Literal["low", "medium", "high"]


class ValuationContext(BaseModel):
    """Valuation stress indicators with percentiles."""
    cape_ratio: Optional[float] = None
    cape_percentile: Optional[float] = None
    buffett_indicator: Optional[float] = None
    buffett_percentile: Optional[float] = None
    breadth_reading: Optional[float] = None
    breadth_interpretation: Optional[str] = None
    context_statement: str


class CrowdBehavior(BaseModel):
    """Crowd behavior indicators."""
    retail_inflow_proxy: Optional[str] = None
    options_activity_proxy: Optional[str] = None
    leadership_narrowing: Optional[str] = None
    speculative_outperformance: Optional[str] = None
    interpretation: str


class SectorRotation(BaseModel):
    """Sector and leadership rotation context."""
    sector_performances: List[dict]
    leadership_concentration_warning: Optional[str] = None
    interpretation: str


class PatternAnalog(BaseModel):
    """A historical pattern analog with outcome dispersion."""
    analog_id: str
    ticker: str
    start_date: datetime
    end_date: datetime
    similarity_score: float
    pattern_description: str
    outcomes: dict  # {horizon: {percentiles, distribution}}
    sentiment_at_time: Optional[str] = None
    narrative_tags: List[str] = []


class AnalysisResponse(BaseModel):
    """Main analysis response (chat answer)."""
    ticker: str
    drop_percent: float
    start_time: datetime
    end_time: datetime
    start_price: float
    end_price: float
    volume_vs_average: float
    session_type: str
    market_context: MarketContext
    move_type: str
    hypotheses: List[Hypothesis]
    timeline: List[TimelineEvent]
    unknowns: List[str]
    next_steps: List[str]
    analysis_timestamp: datetime
    data_sources: List[str]
    disclaimer: str


class ScriptSection(BaseModel):
    """YouTube-style script section."""
    section_name: str
    content: str
    duration_hint: Optional[str] = None


class ScriptResponse(BaseModel):
    """YouTube-style script response."""
    title: str
    sections: List[ScriptSection]
    citations: List[Evidence]
    total_duration_hint: str


class AnalysisFullResponse(BaseModel):
    """Complete analysis with chat and script formats."""
    chat_answer: AnalysisResponse
    script: ScriptResponse
    # New context panels
    regime: Optional[MarketRegime] = None
    valuation: Optional[ValuationContext] = None
    crowd: Optional[CrowdBehavior] = None
    rotation: Optional[SectorRotation] = None
    pattern_analogs: Optional[List[PatternAnalog]] = None
    
    # NEW: SYSTEM JSON Contract (full agent output)
    agent_contract: Optional[AgentOutputContract] = Field(
        None,
        description="Full SYSTEM JSON output contract with strict evidence citations"
    )


class ChartDataPoint(BaseModel):
    """Chart data point."""
    time: str
    value: float


class DateRangeRequest(BaseModel):
    """Request to analyze a specific date range."""
    ticker: str
    start_date: str
    end_date: str


class AnalysisRequest(BaseModel):
    """Legacy analysis request (for backward compatibility)."""
    ticker: str
    drop_percent: Optional[float] = None
    time_window_hours: int = 24


# ============================================================================
# TIER-1 DASHBOARD SCHEMAS
# ============================================================================

class CapeIndicator(BaseModel):
    """CAPE (Shiller PE) indicator."""
    value: Optional[float] = None
    percentile: Optional[float] = None
    interpretation: str = "Data not available"
    data_source: str = "Shiller Dataset"


class BuffettIndicator(BaseModel):
    """Buffett Indicator (Market Cap / GDP)."""
    value: Optional[float] = None
    percentile: Optional[float] = None
    zone: Literal["Fair", "Stretched", "Extreme", "Unknown"] = "Unknown"
    interpretation: str = "Data not available"
    data_source: str = "FRED / Wilshire"


class BreadthIndicator(BaseModel):
    """Market Breadth indicator."""
    metric_name: str = "Equal-weight vs Cap-weight Divergence"
    value: Optional[float] = None
    interpretation: str = "Data not available"
    methodology: str = "Proxy-based measurement"
    data_source: str = "Yahoo Finance ETFs"


class LeadershipIndicator(BaseModel):
    """Leadership Concentration indicator."""
    metric_name: str = "Cap-weight vs Equal-weight Divergence"
    value: Optional[float] = None
    leadership_label: Literal["Broad", "Moderate", "Narrow", "Unknown"] = "Unknown"
    interpretation: str = "Data not available"
    methodology: str = "SPY vs RSP relative strength"
    data_source: str = "Yahoo Finance ETFs"


class SectorRotationTier1(BaseModel):
    """Sector Rotation for Tier-1 dashboard."""
    xly_xlp_ratio: Optional[float] = None
    ratio_interpretation: str = "Data not available"
    defensive_strength: Optional[str] = None
    top_sectors: List[dict] = []
    interpretation: str = "Data not available"


class VixIndicator(BaseModel):
    """VIX Volatility indicator."""
    value: Optional[float] = None
    regime: Literal["Compressed", "Normal", "Elevated", "Unknown"] = "Unknown"
    interpretation: str = "Data not available"
    insight: str = "Very low volatility has historically preceded instability; high volatility reflects fear already present."
    data_source: str = "Yahoo Finance ^VIX"


class MovingAveragesIndicator(BaseModel):
    """50-day and 200-day Moving Average indicators."""
    current_price: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None
    price_vs_50: Literal["Above", "Below", "At", "Unknown"] = "Unknown"
    price_vs_200: Literal["Above", "Below", "At", "Unknown"] = "Unknown"
    slope_50: Literal["Rising", "Flattening", "Falling", "Unknown"] = "Unknown"
    slope_200: Literal["Rising", "Flattening", "Falling", "Unknown"] = "Unknown"
    trend_health: str = "Data not available"
    interpretation: str = "Data not available"


class CycleStage(BaseModel):
    """Market Cycle Stage (1-4) - meta indicator."""
    stage: Literal[1, 2, 3, 4]
    stage_name: str
    description: str
    contributing_factors: List[str] = []
    interpretation: str


class Tier1Dashboard(BaseModel):
    """Complete Tier-1 dashboard response."""
    as_of: datetime
    market_proxy_used: str
    cape: CapeIndicator
    buffett: BuffettIndicator
    breadth: BreadthIndicator
    leadership: LeadershipIndicator
    sector_rotation: SectorRotationTier1
    vix: VixIndicator
    moving_averages: MovingAveragesIndicator
    cycle_stage: CycleStage
    disclaimer: str = "These indicators provide historical context and regime awareness. They do not predict market direction or recommend actions."