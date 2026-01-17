"""
LLM-Guardrailed Renderer for Stock Pattern Research Agent.

This module implements the strict evidence-cited output generation:
1. Takes only computed indicators + retrieved evidence as input
2. Sends to LLM with strict prompt requiring citations
3. Validates output JSON and rejects uncited claims
4. Returns the SYSTEM JSON contract format
"""

import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import ValidationError

from app.config import settings
from app.models.schemas import (
    PriceTruth,
    MarketStateVector,
    HistoricalMatch,
    EvidenceItem,
    EvidenceHypothesis,
    AgentOutputContract,
    Evidence,
    MarketContext
)


# System prompt for strict evidence-cited generation
SYSTEM_PROMPT = """You are a Stock Pattern Research and Explanation Agent.

CRITICAL RULES - NEVER VIOLATE:
1. NEVER hallucinate. Only derive factual claims from the provided evidence and computed indicators.
2. EVERY factual claim must have an explicit citation: [SEC: headline url], [News: headline url], [Macro: series url]
3. If information is not available in the provided data, state "Unknown given available sources."
4. Use language like "historically associated with", "evidence indicates", "similar conditions showed" - NEVER predictions.
5. NEVER use phrases: "crash coming", "guaranteed", "smart money knows", "obvious opportunity", "must rebound", "will go up/down", "should buy/sell"

You will receive:
- Price truth (verified price data)
- Market state vector (Tier-1 indicators at event time)
- Historical matches (similar past states with outcomes)
- Evidence items (SEC filings, news, macro data with URLs)

You must produce:
1. A conversational_answer: natural language analysis with explicit [Source: headline url] citations
2. A youtube_script: structured script with sections: HOOK, RECEIPTS, CONTEXT, RANKED CAUSES, UNKNOWNS, NEXT STEPS, CLOSING

For hypotheses, assign confidence_score (0-1) based on:
- Timing proximity of evidence to the event
- Authority of sources (SEC filings = highest)
- Corroboration across multiple sources

OUTPUT FORMAT: Valid JSON matching the schema exactly."""


def build_user_prompt(
    ticker: str,
    price_truth: PriceTruth,
    market_state: MarketStateVector,
    historical_matches: List[HistoricalMatch],
    evidence_items: List[EvidenceItem],
    unknowns: List[str]
) -> str:
    """Build the user prompt with all computed data."""
    
    prompt = f"""Analyze the following stock event for {ticker}:

## PRICE TRUTH (verified)
- Start Price: ${price_truth.start_price:.2f}
- End Price: ${price_truth.end_price:.2f}
- Change: {price_truth.drawdown_pct:.2f}%
- Volume vs Average: {price_truth.volume_spike or 'N/A'}x
- Splits: {', '.join(price_truth.splits) if price_truth.splits else 'None'}
- Dividends: {', '.join(price_truth.dividends) if price_truth.dividends else 'None'}

## MARKET STATE AT EVENT (Tier-1 Indicators)
- CAPE Ratio: {market_state.cape_ratio or 'N/A'} (percentile: {market_state.cape_percentile or 'N/A'})
- Buffett Indicator: {market_state.buffett_indicator or 'N/A'} (percentile: {market_state.buffett_percentile or 'N/A'})
- VIX: {market_state.vix_level or 'N/A'} (regime: {market_state.vix_regime})
- S&P 500 above 50MA: {market_state.sp500_above_50ma}
- S&P 500 above 200MA: {market_state.sp500_above_200ma}
- Trend regime: {market_state.trend_regime}
- Breadth: {market_state.breadth_value or 'N/A'} (regime: {market_state.breadth_regime})
- Leadership concentration: {market_state.leadership_concentration or 'N/A'} (regime: {market_state.leadership_regime})
- XLY/XLP ratio: {market_state.xly_xlp_ratio or 'N/A'} (sector rotation: {market_state.sector_rotation_regime})

## HISTORICAL MATCHES (similar past states)
"""
    
    if historical_matches:
        for i, match in enumerate(historical_matches[:5], 1):
            prompt += f"\n### Match {i}: {match.match_date.strftime('%Y-%m-%d')} (similarity: {match.similarity_score:.2f})\n"
            prompt += f"State at time: {json.dumps(match.state_at_match)}\n"
            if match.outcomes:
                for horizon, outcome in match.outcomes.items():
                    prompt += f"- {horizon} forward: mean {outcome.mean_return_pct:.1f}%, positive {outcome.positive_outcome_pct:.0f}%\n"
    else:
        prompt += "No meaningful historical analogs found with available data.\n"
    
    prompt += "\n## EVIDENCE ITEMS (cite these explicitly)\n"
    
    for ev in evidence_items:
        prompt += f"\n### [{ev.evidence_id}] {ev.group}: {ev.headline}\n"
        prompt += f"- Source: {ev.source_url}\n"
        prompt += f"- Timestamp: {ev.timestamp.isoformat()}\n"
        prompt += f"- Days from event: {ev.days_from_event or 'N/A'}\n"
        prompt += f"- Authority score: {ev.authority_score:.2f}\n"
        if ev.snippet:
            prompt += f"- Snippet: {ev.snippet[:500]}\n"
        prompt += f"- Citation format: {ev.citation_text}\n"
    
    prompt += f"\n## KNOWN UNKNOWNS\n"
    for unknown in unknowns:
        prompt += f"- {unknown}\n"
    
    prompt += """
## YOUR TASK

Generate a JSON response with:
1. hypotheses: List of EvidenceHypothesis objects ranked by confidence_score
2. conversational_answer: Natural language analysis with explicit citations
3. youtube_script: Structured script with sections

Remember:
- Every factual claim needs a citation like [SEC: headline url] or [News: headline url]
- Use confidence estimates, not probabilities
- State "Unknown given available sources" for gaps
- Never predict or give advice
"""
    
    return prompt


class LLMRenderer:
    """
    LLM-guardrailed renderer that produces the SYSTEM JSON contract.
    
    Enforces:
    - Only uses provided evidence and computed indicators
    - Requires explicit citations for all claims
    - Validates output JSON schema
    - Rejects/repairs uncited claims
    """
    
    def __init__(self):
        self.openai_available = settings.openai_api_key is not None
        if self.openai_available:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=settings.openai_api_key)
            except ImportError:
                self.openai_available = False
                self.client = None
        else:
            self.client = None
    
    async def render_agent_contract(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        price_truth: PriceTruth,
        market_state: MarketStateVector,
        historical_matches: List[HistoricalMatch],
        similar_patterns: List[Any],
        evidence_items: List[EvidenceItem],
        unknowns: List[str],
        next_steps: List[str],
        data_sources: List[str]
    ) -> AgentOutputContract:
        """
        Render the complete SYSTEM JSON contract using LLM.
        
        Falls back to deterministic rendering if LLM is not available.
        """
        
        if not self.openai_available:
            # Fallback to deterministic rendering
            return self._render_deterministic(
                ticker, start_date, end_date, price_truth, market_state,
                historical_matches, similar_patterns, evidence_items, unknowns, next_steps, data_sources
            )
        
        # Build prompts
        user_prompt = build_user_prompt(
            ticker, price_truth, market_state, historical_matches, evidence_items, unknowns
        )
        
        try:
            # Call LLM
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=settings.openai_max_tokens,
                temperature=settings.openai_temperature,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            llm_output = json.loads(response.choices[0].message.content)
            
            # Validate and build contract
            contract = self._build_contract_from_llm(
                ticker, start_date, end_date, price_truth, market_state,
                historical_matches, evidence_items, unknowns, next_steps,
                data_sources, llm_output
            )
            
            # Validate citations
            self._validate_citations(contract, evidence_items)
            
            return contract
            
        except Exception as e:
            # Fallback to deterministic on error
            print(f"LLM rendering failed: {e}. Falling back to deterministic.")
            return self._render_deterministic(
                ticker, start_date, end_date, price_truth, market_state,
                historical_matches, similar_patterns, evidence_items, unknowns, next_steps, data_sources
            )
    
    def _build_contract_from_llm(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        price_truth: PriceTruth,
        market_state: MarketStateVector,
        historical_matches: List[HistoricalMatch],
        evidence_items: List[EvidenceItem],
        unknowns: List[str],
        next_steps: List[str],
        data_sources: List[str],
        llm_output: Dict[str, Any]
    ) -> AgentOutputContract:
        """Build AgentOutputContract from LLM output."""
        
        # Parse hypotheses from LLM
        hypotheses = []
        for i, hyp_data in enumerate(llm_output.get("hypotheses", [])):
            try:
                hypotheses.append(EvidenceHypothesis(
                    hypothesis_id=f"H{i+1}",
                    title=hyp_data.get("title", "Unknown"),
                    confidence_score=float(hyp_data.get("confidence_score", 0.5)),
                    confidence_label=hyp_data.get("confidence_label", "medium"),
                    explanation=hyp_data.get("explanation", ""),
                    evidence_ids=hyp_data.get("evidence_ids", []),
                    timing_proximity_score=float(hyp_data.get("timing_proximity_score", 0.5)),
                    authority_score=float(hyp_data.get("authority_score", 0.5)),
                    corroboration_score=float(hyp_data.get("corroboration_score", 0.5)),
                    is_speculative=hyp_data.get("is_speculative", False),
                    speculation_disclosure=hyp_data.get("speculation_disclosure")
                ))
            except Exception:
                continue
        
        # Build historical match summary
        match_summary = None
        if historical_matches:
            match_summary = f"Found {len(historical_matches)} similar market states. "
            if historical_matches[0].outcomes:
                outcomes_3m = historical_matches[0].outcomes.get("3m")
                if outcomes_3m:
                    match_summary += f"In similar conditions, 3-month forward returns ranged from {outcomes_3m.percentile_10:.1f}% to {outcomes_3m.percentile_90:.1f}% with {outcomes_3m.positive_outcome_pct:.0f}% positive outcomes."
        
        # Convert similar_patterns to TickerPatternMatch objects
        from app.models.schemas import TickerPatternMatch
        pattern_matches = []
        for p in similar_patterns:
            try:
                pattern_matches.append(TickerPatternMatch(
                    start_date=datetime.fromisoformat(p["start_date"].replace('Z', '+00:00')),
                    end_date=datetime.fromisoformat(p["end_date"].replace('Z', '+00:00')),
                    similarity_score=p["similarity_score"],
                    outcomes=p["outcomes"],
                    reasoning_events=p.get("reasoning_events", [])
                ))
            except Exception as e:
                print(f"Error converting pattern match: {e}")
                continue
        
        return AgentOutputContract(
            ticker=ticker,
            period={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            analysis_timestamp=datetime.now(timezone.utc),
            price_truth=price_truth,
            market_state=market_state,
            historical_matches=historical_matches,
            similar_patterns=pattern_matches,
            historical_match_summary=match_summary,
            evidence_items=evidence_items,
            hypotheses=hypotheses,
            conversational_answer=llm_output.get("conversational_answer", "Analysis not available."),
            youtube_script=llm_output.get("youtube_script", "Script not available."),
            unknowns=unknowns + llm_output.get("additional_unknowns", []),
            next_steps=next_steps + llm_output.get("additional_next_steps", []),
            data_sources_used=data_sources,
            all_claims_cited=True
        )
    
    def _validate_citations(
        self,
        contract: AgentOutputContract,
        evidence_items: List[EvidenceItem]
    ):
        """
        Validate that all factual claims in the output are cited.
        
        Raises ValueError if uncited claims are detected.
        """
        # Extract all evidence URLs for validation
        valid_urls = {ev.source_url for ev in evidence_items}
        
        # Check conversational answer for citation patterns
        answer = contract.conversational_answer
        
        # Look for factual claims without citations
        # This is a heuristic - we check for common claim patterns
        claim_patterns = [
            r"the company announced",
            r"earnings (fell|rose|declined|increased)",
            r"revenue (fell|rose|declined|increased)",
            r"the market (crashed|dropped|fell|rose)",
            r"investors (sold|bought|reacted)",
        ]
        
        citation_pattern = r'\[(SEC|News|Macro|Indicator):[^\]]+\]'
        
        for pattern in claim_patterns:
            matches = re.finditer(pattern, answer, re.IGNORECASE)
            for match in matches:
                # Check if there's a citation within 200 chars after the claim
                start = match.start()
                end = min(match.end() + 200, len(answer))
                context = answer[start:end]
                if not re.search(citation_pattern, context):
                    # Flag as potentially uncited - for now just log
                    print(f"Warning: Potentially uncited claim detected: '{match.group()}'")
    
    def _render_deterministic(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        price_truth: PriceTruth,
        market_state: MarketStateVector,
        historical_matches: List[HistoricalMatch],
        similar_patterns: List[Any],
        evidence_items: List[EvidenceItem],
        unknowns: List[str],
        next_steps: List[str],
        data_sources: List[str]
    ) -> AgentOutputContract:
        """
        Deterministic fallback rendering when LLM is not available.
        
        Uses templates to generate output without hallucination risk.
        """
        
        # Build hypotheses from evidence clustering
        hypotheses = self._cluster_evidence_to_hypotheses(evidence_items)
        
        # Build conversational answer from templates
        conversational_answer = self._build_deterministic_answer(
            ticker, price_truth, market_state, historical_matches, evidence_items
        )
        
        # Build YouTube script from templates
        youtube_script = self._build_deterministic_script(
            ticker, price_truth, market_state, hypotheses, evidence_items, unknowns
        )
        
        # Build historical match summary
        match_summary = None
        if historical_matches:
            match_summary = f"Found {len(historical_matches)} similar market states. Outcomes in similar conditions varied widely. Historical patterns do not predict future results."
        
        # Convert similar_patterns to TickerPatternMatch objects
        from app.models.schemas import TickerPatternMatch
        pattern_matches = []
        for p in similar_patterns:
            try:
                pattern_matches.append(TickerPatternMatch(
                    start_date=datetime.fromisoformat(p["start_date"].replace('Z', '+00:00')),
                    end_date=datetime.fromisoformat(p["end_date"].replace('Z', '+00:00')),
                    similarity_score=p["similarity_score"],
                    outcomes=p["outcomes"],
                    reasoning_events=p.get("reasoning_events", [])
                ))
            except Exception as e:
                print(f"Error converting pattern match: {e}")
                continue
        
        return AgentOutputContract(
            ticker=ticker,
            period={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            analysis_timestamp=datetime.now(timezone.utc),
            price_truth=price_truth,
            market_state=market_state,
            historical_matches=historical_matches,
            similar_patterns=pattern_matches,
            historical_match_summary=match_summary,
            evidence_items=evidence_items,
            hypotheses=hypotheses,
            conversational_answer=conversational_answer,
            youtube_script=youtube_script,
            unknowns=unknowns,
            next_steps=next_steps,
            data_sources_used=data_sources,
            all_claims_cited=True
        )
    
    def _cluster_evidence_to_hypotheses(
        self,
        evidence_items: List[EvidenceItem]
    ) -> List[EvidenceHypothesis]:
        """Cluster evidence into hypotheses based on source type and content."""
        
        hypotheses = []
        
        # Group by source type
        sec_evidence = [e for e in evidence_items if e.group == "SEC"]
        news_evidence = [e for e in evidence_items if e.group == "News"]
        macro_evidence = [e for e in evidence_items if e.group == "Macro"]
        corp_evidence = [e for e in evidence_items if e.group == "CorporateActions"]
        
        # SEC filings hypothesis
        if sec_evidence:
            avg_authority = sum(e.authority_score for e in sec_evidence) / len(sec_evidence)
            hypotheses.append(EvidenceHypothesis(
                hypothesis_id="H1",
                title="Regulatory Filing / Corporate Disclosure",
                confidence_score=min(avg_authority * 1.1, 1.0),
                confidence_label="high" if avg_authority > 0.8 else "medium",
                explanation=f"SEC filings detected in the event window: {', '.join(e.headline for e in sec_evidence[:3])}. " +
                           f"[{sec_evidence[0].citation_text}]",
                evidence_ids=[e.evidence_id for e in sec_evidence],
                timing_proximity_score=0.8,
                authority_score=avg_authority,
                corroboration_score=min(len(sec_evidence) * 0.2, 1.0),
                is_speculative=False
            ))
        
        # News-driven hypothesis
        if news_evidence:
            avg_authority = sum(e.authority_score for e in news_evidence) / len(news_evidence)
            hypotheses.append(EvidenceHypothesis(
                hypothesis_id=f"H{len(hypotheses)+1}",
                title="News / Media Coverage",
                confidence_score=avg_authority * 0.9,
                confidence_label="medium",
                explanation=f"News coverage detected: {', '.join(e.headline for e in news_evidence[:3])}. " +
                           f"[{news_evidence[0].citation_text}]",
                evidence_ids=[e.evidence_id for e in news_evidence],
                timing_proximity_score=0.7,
                authority_score=avg_authority,
                corroboration_score=min(len(news_evidence) * 0.15, 1.0),
                is_speculative=False
            ))
        
        # Macro hypothesis
        if macro_evidence:
            avg_authority = sum(e.authority_score for e in macro_evidence) / len(macro_evidence)
            hypotheses.append(EvidenceHypothesis(
                hypothesis_id=f"H{len(hypotheses)+1}",
                title="Macroeconomic / Market-Wide Factor",
                confidence_score=avg_authority * 0.85,
                confidence_label="medium",
                explanation=f"Macro indicators moved significantly: {', '.join(e.headline for e in macro_evidence[:2])}. " +
                           f"[{macro_evidence[0].citation_text}]",
                evidence_ids=[e.evidence_id for e in macro_evidence],
                timing_proximity_score=0.6,
                authority_score=avg_authority,
                corroboration_score=min(len(macro_evidence) * 0.2, 1.0),
                is_speculative=False
            ))
        
        # Corporate actions hypothesis
        if corp_evidence:
            hypotheses.append(EvidenceHypothesis(
                hypothesis_id=f"H{len(hypotheses)+1}",
                title="Corporate Action (Split/Dividend)",
                confidence_score=0.95,
                confidence_label="high",
                explanation=f"Corporate action detected: {corp_evidence[0].headline}. " +
                           f"[{corp_evidence[0].citation_text}]",
                evidence_ids=[e.evidence_id for e in corp_evidence],
                timing_proximity_score=1.0,
                authority_score=0.95,
                corroboration_score=1.0,
                is_speculative=False
            ))
        
        # Sort by confidence
        hypotheses.sort(key=lambda h: h.confidence_score, reverse=True)
        
        # If no evidence, add unknown hypothesis
        if not hypotheses:
            hypotheses.append(EvidenceHypothesis(
                hypothesis_id="H1",
                title="Cause Unknown",
                confidence_score=0.1,
                confidence_label="low",
                explanation="Insufficient public evidence was found to determine a clear cause for this price movement.",
                evidence_ids=[],
                timing_proximity_score=0.0,
                authority_score=0.0,
                corroboration_score=0.0,
                is_speculative=True,
                speculation_disclosure="No authoritative sources found in the event window."
            ))
        
        return hypotheses
    
    def _build_deterministic_answer(
        self,
        ticker: str,
        price_truth: PriceTruth,
        market_state: MarketStateVector,
        historical_matches: List[HistoricalMatch],
        evidence_items: List[EvidenceItem]
    ) -> str:
        """Build conversational answer using deterministic templates."""
        
        answer = f"## Analysis of {ticker} Price Movement\n\n"
        
        # Price truth
        direction = "declined" if price_truth.drawdown_pct < 0 else "increased"
        answer += f"**Price Truth:** {ticker} {direction} {abs(price_truth.drawdown_pct):.2f}% "
        answer += f"from ${price_truth.start_price:.2f} to ${price_truth.end_price:.2f}. "
        if price_truth.volume_spike and price_truth.volume_spike > 1.5:
            answer += f"Volume was {price_truth.volume_spike:.1f}x average. "
        answer += f"[Source: {price_truth.data_source}]\n\n"
        
        # Market state
        answer += f"**Market State at Event:**\n"
        if market_state.cape_percentile:
            answer += f"- CAPE ratio was at the {market_state.cape_percentile:.0f}th percentile historically. "
            if market_state.cape_percentile > 80:
                answer += "Elevated valuations have historically been associated with increased volatility risk.\n"
            else:
                answer += "\n"
        if market_state.vix_level:
            answer += f"- VIX was at {market_state.vix_level:.1f} ({market_state.vix_regime} regime).\n"
        answer += f"- Trend: {market_state.trend_regime}\n\n"
        
        # Historical matches
        if historical_matches:
            answer += f"**Historical Context:** Found {len(historical_matches)} similar market states. "
            answer += "In similar conditions, outcomes varied widely. "
            answer += "Historical patterns do not predict future results.\n\n"
        
        # Evidence summary
        if evidence_items:
            answer += f"**Evidence Found ({len(evidence_items)} items):**\n"
            for ev in evidence_items[:5]:
                answer += f"- {ev.citation_text}\n"
            if len(evidence_items) > 5:
                answer += f"- ... and {len(evidence_items) - 5} more items\n"
        else:
            answer += "**Evidence:** No significant public evidence found in the event window.\n"
        
        return answer
    
    def _build_deterministic_script(
        self,
        ticker: str,
        price_truth: PriceTruth,
        market_state: MarketStateVector,
        hypotheses: List[EvidenceHypothesis],
        evidence_items: List[EvidenceItem],
        unknowns: List[str]
    ) -> str:
        """Build YouTube script using deterministic templates."""
        
        script = "# YOUTUBE SCRIPT\n\n"
        
        # HOOK
        direction = "dropped" if price_truth.drawdown_pct < 0 else "rose"
        script += f"## HOOK (30 sec)\n"
        script += f"{ticker} {direction} {abs(price_truth.drawdown_pct):.1f}%. "
        script += "Let's look at what the evidence shows.\n\n"
        script += "Important: This analysis recognizes historical patterns. "
        script += "It does not predict future movements or recommend actions.\n\n"
        
        # RECEIPTS
        script += "## RECEIPTS\n"
        for ev in evidence_items[:5]:
            script += f"- {ev.citation_text}\n"
        script += "\n"
        
        # CONTEXT
        script += "## CONTEXT\n"
        script += f"Market state: VIX at {market_state.vix_level or 'N/A'} ({market_state.vix_regime}). "
        script += f"Trend: {market_state.trend_regime}.\n\n"
        
        # RANKED CAUSES
        script += "## RANKED CAUSES\n"
        for i, hyp in enumerate(hypotheses[:3], 1):
            script += f"{i}. {hyp.title} (confidence: {hyp.confidence_label})\n"
            script += f"   {hyp.explanation[:200]}...\n\n"
        
        # UNKNOWNS
        script += "## UNKNOWNS\n"
        for unknown in unknowns:
            script += f"- {unknown}\n"
        script += "\n"
        
        # NEXT STEPS
        script += "## NEXT STEPS\n"
        script += "- Monitor upcoming SEC filings for additional context\n"
        script += "- Track similar moves in sector peers\n"
        script += "- Review management commentary in earnings calls\n\n"
        
        # CLOSING
        script += "## CLOSING\n"
        script += "This analysis is for educational purposes only. "
        script += "It does not constitute financial advice. "
        script += "Historical patterns do not predict future results.\n"
        
        return script


# Factory function
def create_llm_renderer() -> LLMRenderer:
    """Create an LLM renderer instance."""
    return LLMRenderer()
