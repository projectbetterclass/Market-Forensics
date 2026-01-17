"""Response renderer with language guardrails."""

from datetime import datetime, timezone
from typing import List, Dict, Any
from app.models.schemas import (
    AnalysisResponse,
    ScriptResponse,
    ScriptSection,
    AnalysisFullResponse,
    Hypothesis,
    TimelineEvent,
    Evidence,
    MarketContext
)


class ResponseRenderer:
    """Renders analysis responses with strict language guardrails."""
    
    # Forbidden phrases (must never appear in output)
    FORBIDDEN_PHRASES = [
        "crash coming",
        "guaranteed",
        "smart money knows",
        "obvious opportunity",
        "must rebound",
        "will go up",
        "will go down",
        "should buy",
        "should sell",
        "recommend buying",
        "recommend selling",
        "top pick",
        "can't miss",
        "safe bet"
    ]
    
    # Allowed language patterns
    ALLOWED_PHRASES = [
        "historically",
        "associated with",
        "risk has increased",
        "outcomes varied",
        "similar conditions",
        "pattern suggests",
        "evidence indicates",
        "may be related to"
    ]
    
    def __init__(self):
        pass
    
    def render_full_response(
        self,
        ticker: str,
        event_data: Dict[str, Any],
        market_context: MarketContext,
        move_type: str,
        hypotheses: List[Hypothesis],
        timeline: List[TimelineEvent],
        regime: Any = None,
        valuation: Any = None,
        crowd: Any = None,
        rotation: Any = None,
        pattern_analogs: List[Any] = None
    ) -> AnalysisFullResponse:
        """
        Render complete analysis response with both chat and script formats.
        
        Args:
            ticker: Stock ticker
            event_data: Normalized event data
            market_context: Market/sector/peer context
            move_type: Classification of move (company_specific, sector_wide, etc.)
            hypotheses: Ranked hypotheses
            timeline: Timeline events
            regime: Market regime context (optional)
            valuation: Valuation context (optional)
            crowd: Crowd behavior (optional)
            rotation: Sector rotation (optional)
            pattern_analogs: Pattern analogs (optional)
        
        Returns:
            AnalysisFullResponse with chat and script
        """
        # Build unknowns and next steps
        unknowns = self._identify_unknowns(hypotheses, event_data)
        next_steps = self._generate_next_steps(hypotheses)
        
        # Build data sources list
        data_sources = self._list_data_sources(timeline)
        
        # Build chat answer
        chat_answer = AnalysisResponse(
            ticker=ticker,
            drop_percent=event_data["drop_percent"],
            start_time=event_data["start_time"],
            end_time=event_data["end_time"],
            start_price=event_data["start_price"],
            end_price=event_data["end_price"],
            volume_vs_average=event_data["volume_vs_average"],
            session_type=event_data["session_type"],
            market_context=market_context,
            move_type=move_type,
            hypotheses=hypotheses,
            timeline=timeline,
            unknowns=unknowns,
            next_steps=next_steps,
            analysis_timestamp=datetime.now(timezone.utc),
            data_sources=data_sources,
            disclaimer=self._get_disclaimer()
        )
        
        # Build script
        script = self._build_script(ticker, event_data, hypotheses, timeline, market_context)
        
        # Apply language guardrails
        self._apply_guardrails(chat_answer, script)
        
        return AnalysisFullResponse(
            chat_answer=chat_answer,
            script=script,
            regime=regime,
            valuation=valuation,
            crowd=crowd,
            rotation=rotation,
            pattern_analogs=pattern_analogs or []
        )
    
    def _build_script(
        self,
        ticker: str,
        event_data: Dict[str, Any],
        hypotheses: List[Hypothesis],
        timeline: List[TimelineEvent],
        market_context: MarketContext
    ) -> ScriptResponse:
        """Build YouTube-style script."""
        sections = []
        
        # Cold Open / Hook
        drop_pct = abs(event_data["drop_percent"])
        hook = f"{ticker} dropped {drop_pct:.1f}% recently. Let's examine what the evidence shows.\n\n"
        hook += "Important: This analysis recognizes historical patterns and presents evidence. "
        hook += "It does not predict future market movements or recommend actions."
        
        sections.append(ScriptSection(
            section_name="Cold Open",
            content=hook,
            duration_hint="30 sec"
        ))
        
        # The Receipts / Evidence
        receipts = "Here's what we found in public records:\n\n"
        for i, hyp in enumerate(hypotheses[:3], 1):
            receipts += f"{i}. {hyp.title} (probability: {hyp.probability:.0%}, confidence: {hyp.confidence})\n"
            receipts += f"   {hyp.explanation}\n\n"
        
        sections.append(ScriptSection(
            section_name="The Receipts",
            content=receipts,
            duration_hint="2 min"
        ))
        
        # Context / What Else Was Happening
        context = f"Market context: {market_context.interpretation}\n\n"
        context += f"Move classification: {event_data.get('move_type', 'mixed')}\n\n"
        context += "This context helps us understand whether the move was company-specific or part of broader market dynamics."
        
        sections.append(ScriptSection(
            section_name="Context",
            content=context,
            duration_hint="1 min"
        ))
        
        # What's Most Likely / Roundup
        if hypotheses:
            roundup = f"Based on the evidence, the most likely explanation is:\n\n"
            top_hyp = hypotheses[0]
            roundup += f"{top_hyp.title}\n\n"
            roundup += f"Probability: {top_hyp.probability:.0%}\n"
            roundup += f"Confidence: {top_hyp.confidence}\n\n"
            roundup += f"Mechanism: {top_hyp.mechanism}\n\n"
            roundup += "Remember: similar patterns have led to varied outcomes in the past. "
            roundup += "Historical analysis does not guarantee future results."
        else:
            roundup = "Insufficient public evidence was found to determine a clear cause."
        
        sections.append(ScriptSection(
            section_name="What's Most Likely",
            content=roundup,
            duration_hint="1 min"
        ))
        
        # Collect all citations
        all_evidence = []
        for hyp in hypotheses:
            all_evidence.extend(hyp.evidence)
        
        return ScriptResponse(
            title=f"{ticker} Drop Analysis: {drop_pct:.1f}%",
            sections=sections,
            citations=all_evidence,
            total_duration_hint="4-5 min"
        )
    
    def _identify_unknowns(
        self,
        hypotheses: List[Hypothesis],
        event_data: Dict[str, Any]
    ) -> List[str]:
        """Identify what's unknown or uncertain."""
        unknowns = []
        
        if not hypotheses or len(hypotheses) == 1 and hypotheses[0].confidence == "low":
            unknowns.append("Limited public information available for this time period")
        
        if event_data["volume_vs_average"] > 2.0:
            unknowns.append("Cause of elevated volume not fully explained by public sources")
        
        # Check if top hypothesis has low confidence
        if hypotheses and hypotheses[0].confidence == "low":
            unknowns.append("Top hypothesis has low confidence due to limited corroborating evidence")
        
        # Check for timing gaps
        if hypotheses and hypotheses[0].evidence:
            event_start = event_data["start_time"]
            closest_evidence = min(hypotheses[0].evidence, key=lambda e: abs((e.timestamp - event_start).total_seconds()))
            time_diff_hours = abs((closest_evidence.timestamp - event_start).total_seconds()) / 3600
            if time_diff_hours > 48:
                unknowns.append(f"Closest evidence is {time_diff_hours:.0f} hours from the price move")
        
        if not unknowns:
            unknowns.append("No major information gaps identified")
        
        return unknowns
    
    def _generate_next_steps(self, hypotheses: List[Hypothesis]) -> List[str]:
        """Generate next steps for monitoring (not advice)."""
        next_steps = []
        
        if hypotheses:
            top_hyp = hypotheses[0]
            next_steps.append(f"Monitor: {top_hyp.confirmation_check}")
        
        next_steps.append("Watch for regulatory filings (8-K, 10-Q) that may provide additional context")
        next_steps.append("Track similar moves in peer companies or sector ETFs for correlation")
        next_steps.append("Review management commentary in upcoming earnings calls")
        
        return next_steps
    
    def _list_data_sources(self, timeline: List[TimelineEvent]) -> List[str]:
        """List unique data sources used."""
        sources = set()
        for event in timeline:
            if event.evidence.source_type == "sec_filing":
                sources.add("SEC EDGAR")
            elif event.evidence.source_type == "news":
                sources.add("GDELT News")
            elif event.evidence.source_type == "macro":
                sources.add("FRED")
            elif event.evidence.source_type == "corporate_action":
                sources.add("Yahoo Finance Corporate Actions")
        
        if not sources:
            sources.add("Yahoo Finance")
        
        return sorted(list(sources))
    
    def _get_disclaimer(self) -> str:
        """Get standard disclaimer."""
        return (
            "This analysis is provided for educational and informational purposes only. "
            "It does not constitute financial advice, investment recommendations, or predictions of future market behavior. "
            "Past patterns and historical context do not guarantee future results. "
            "Always conduct your own research and consult with qualified professionals before making investment decisions."
        )
    
    def _apply_guardrails(
        self,
        chat_answer: AnalysisResponse,
        script: ScriptResponse
    ):
        """
        Apply language guardrails to ensure no forbidden phrases.
        
        Raises ValueError if forbidden phrases are detected.
        """
        # Check all text fields in chat_answer
        text_to_check = []
        
        # Hypotheses
        for hyp in chat_answer.hypotheses:
            text_to_check.append(hyp.title.lower())
            text_to_check.append(hyp.explanation.lower())
            text_to_check.append(hyp.mechanism.lower())
            text_to_check.append(hyp.confirmation_check.lower())
        
        # Script sections
        for section in script.sections:
            text_to_check.append(section.content.lower())
        
        # Check for forbidden phrases
        for text in text_to_check:
            for forbidden in self.FORBIDDEN_PHRASES:
                if forbidden in text:
                    raise ValueError(
                        f"Language guardrail violation: forbidden phrase '{forbidden}' detected. "
                        f"This tool provides historical context and pattern recognition, not predictions or advice."
                    )
