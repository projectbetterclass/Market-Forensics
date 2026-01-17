/**
 * API client for Stock Drop Agent backend
 */

export interface Evidence {
  timestamp: string;
  source_type: string;
  source_url: string;
  headline: string;
  snippet?: string;
  authority_score: number;
  group: string;
  relevance_score: number;
  why_this_matters?: string;
  what_it_explains?: string;
}

export interface Hypothesis {
  rank: number;
  title: string;
  probability: number;
  confidence: "high" | "medium" | "low";
  explanation: string;
  evidence: Evidence[];
  mechanism: string;
  confirmation_check: string;
}

export interface MarketContext {
  market_index: string;
  market_return_pct: number;
  sector_name?: string;
  sector_return_pct?: number;
  peer_median_return_pct?: number;
  interpretation: string;
}

export interface TimelineEvent {
  timestamp: string;
  description: string;
  evidence: Evidence;
  price_impact?: string;
}

export interface MarketRegime {
  stage: 1 | 2 | 3 | 4;
  stage_name: string;
  description: string;
  volatility_regime: "low" | "medium" | "high";
}

export interface ValuationContext {
  cape_ratio?: number;
  cape_percentile?: number;
  buffett_indicator?: number;
  buffett_percentile?: number;
  breadth_reading?: number;
  breadth_interpretation?: string;
  context_statement: string;
}

export interface CrowdBehavior {
  retail_inflow_proxy?: string;
  options_activity_proxy?: string;
  leadership_narrowing?: string;
  speculative_outperformance?: string;
  interpretation: string;
}

export interface SectorRotation {
  sector_performances: Array<{
    sector: string;
    etf: string;
    return_pct: number;
  }>;
  leadership_concentration_warning?: string;
  interpretation: string;
}

export interface PatternAnalog {
  analog_id: string;
  ticker: string;
  start_date: string;
  end_date: string;
  similarity_score: number;
  pattern_description: string;
  outcomes: Record<string, any>;
  sentiment_at_time?: string;
  narrative_tags: string[];
}

export interface AnalysisResponse {
  ticker: string;
  drop_percent: number;
  start_time: string;
  end_time: string;
  start_price: number;
  end_price: number;
  volume_vs_average: number;
  session_type: string;
  market_context: MarketContext;
  move_type: string;
  hypotheses: Hypothesis[];
  timeline: TimelineEvent[];
  unknowns: string[];
  next_steps: string[];
  analysis_timestamp: string;
  data_sources: string[];
  disclaimer: string;
}

export interface ScriptSection {
  section_name: string;
  content: string;
  duration_hint?: string;
}

export interface ScriptResponse {
  title: string;
  sections: ScriptSection[];
  citations: Evidence[];
  total_duration_hint: string;
}

// ============================================================================
// SYSTEM JSON CONTRACT TYPES (new agent output)
// ============================================================================

export interface PriceTruth {
  start_price: number;
  end_price: number;
  drawdown_pct: number;
  volume_spike?: number;
  splits: string[];
  dividends: string[];
  data_source: string;
  verified: boolean;
}

export interface MarketStateVector {
  cape_ratio?: number;
  cape_percentile?: number;
  buffett_indicator?: number;
  buffett_percentile?: number;
  vix_level?: number;
  vix_regime: "low" | "normal" | "high" | "unknown";
  vix_vs_60d_avg?: number;
  sp500_above_50ma?: boolean;
  sp500_above_200ma?: boolean;
  trend_regime: "uptrend" | "downtrend" | "sideways" | "unknown";
  breadth_value?: number;
  breadth_regime: "strong" | "neutral" | "weak" | "unknown";
  leadership_concentration?: number;
  leadership_regime: "broad" | "moderate" | "narrow" | "unknown";
  xly_xlp_ratio?: number;
  sector_rotation_regime: "risk_on" | "neutral" | "risk_off" | "unknown";
  indicator_definitions: Record<string, string>;
}

export interface OutcomeDistribution {
  horizon: string;
  mean_return_pct: number;
  median_return_pct: number;
  percentile_10: number;
  percentile_25: number;
  percentile_75: number;
  percentile_90: number;
  max_drawdown_mean?: number;
  positive_outcome_pct: number;
  sample_size: number;
}

export interface HistoricalMatch {
  match_date: string;
  similarity_score: number;
  state_at_match: Record<string, any>;
  outcomes: Record<string, OutcomeDistribution>;
  market_regime_at_time?: string;
  notable_events: string[];
  outcome_warning: string;
}

export interface TickerPatternMatch {
  start_date: string;
  end_date: string;
  similarity_score: number;
  outcomes: Record<string, any>;
  reasoning_events: string[];
}

export interface EvidenceHypothesis {
  hypothesis_id: string;
  title: string;
  confidence_score: number;
  confidence_label: "high" | "medium" | "low";
  explanation: string;
  evidence_ids: string[];
  timing_proximity_score: number;
  authority_score: number;
  corroboration_score: number;
  is_speculative: boolean;
  speculation_disclosure?: string;
}

export interface EvidenceItem {
  evidence_id: string;
  timestamp: string;
  source_type: string;
  source_url: string;
  headline: string;
  snippet?: string;
  authority_score: number;
  citation_text: string;
  group: string;
  days_from_event?: number;
}

export interface ForensicReportHeader {
  company_name: string;
  ticker: string;
  analysis_window: string;
  principle: string;
}

export interface ForensicHypothesis {
  title: string;
  estimated_probability: string;
  confidence_level: "Low" | "Medium" | "High";
  mechanism: string;
  evidence_types: string[];
}

export interface ForensicReport {
  header: ForensicReportHeader;
  executive_summary_bullets: string[];
  market_context_assessment: string;
  primary_trigger_assessment: string;
  ranked_hypotheses: ForensicHypothesis[];
  timeline_summary: string;
  what_this_was_not: string[];
  unknowns_and_limitations: string[];
  practical_interpretation: {
    emotional_errors_to_avoid: string[];
    what_to_monitor_next: string[];
  };
  final_takeaway: string;
}

export interface CuratedSource {
  headline: string;
  url: string;
  timestamp: string;
  category: "Primary" | "CorporateOperational" | "MacroSystemic" | "Narrative";
  relative_time_label: string;
  authority_score: number;
  relevance_score: number;
  timing_score: number;
  final_weight: number;
}

export interface CuratedSourceGroup {
  category: "Primary" | "CorporateOperational" | "MacroSystemic" | "Narrative";
  category_label: string;
  top_sources: CuratedSource[];
  remaining_count: number;
  all_sources: CuratedSource[];
}

export interface CuratedEvidenceSummary {
  groups: CuratedSourceGroup[];
  disclaimer_if_narrative_only?: string;
  total_sources_validated: number;
  total_sources_collapsed: number;
}

export interface AgentOutputContract {
  ticker: string;
  period: { start_date: string; end_date: string };
  analysis_timestamp: string;
  price_truth: PriceTruth;
  market_state: MarketStateVector;
  historical_matches: HistoricalMatch[];
  similar_patterns: TickerPatternMatch[];
  historical_match_summary?: string;
  evidence_items: EvidenceItem[];
  hypotheses: EvidenceHypothesis[];
  conversational_answer: string;
  youtube_script: string;
  unknowns: string[];
  next_steps: string[];
  data_sources_used: string[];
  disclaimer: string;
  all_claims_cited: boolean;
  forensic_report?: ForensicReport;
  curated_evidence?: CuratedEvidenceSummary;
}

export interface AnalysisFullResponse {
  chat_answer: AnalysisResponse;
  script: ScriptResponse;
  regime?: MarketRegime;
  valuation?: ValuationContext;
  crowd?: CrowdBehavior;
  rotation?: SectorRotation;
  pattern_analogs?: PatternAnalog[];
  // NEW: SYSTEM JSON Contract
  agent_contract?: AgentOutputContract;
}

export interface ChartDataPoint {
  time: string;
  value: number;
}

export interface DateRangeRequest {
  ticker: string;
  start_date: string;
  end_date: string;
}

// ============================================================================
// TIER-1 DASHBOARD TYPES
// ============================================================================

export interface CapeIndicator {
  value?: number;
  percentile?: number;
  interpretation: string;
  data_source: string;
}

export interface BuffettIndicator {
  value?: number;
  percentile?: number;
  zone: "Fair" | "Stretched" | "Extreme" | "Unknown";
  interpretation: string;
  data_source: string;
}

export interface BreadthIndicator {
  metric_name: string;
  value?: number;
  interpretation: string;
  methodology: string;
  data_source: string;
}

export interface LeadershipIndicator {
  metric_name: string;
  value?: number;
  leadership_label: "Broad" | "Moderate" | "Narrow" | "Unknown";
  interpretation: string;
  methodology: string;
  data_source: string;
}

export interface SectorRotationTier1 {
  xly_xlp_ratio?: number;
  ratio_interpretation: string;
  defensive_strength?: string;
  top_sectors: Array<{ sector: string; etf: string; return_pct: number }>;
  interpretation: string;
}

export interface VixIndicator {
  value?: number;
  regime: "Compressed" | "Normal" | "Elevated" | "Unknown";
  interpretation: string;
  insight: string;
  data_source: string;
}

export interface MovingAveragesIndicator {
  current_price?: number;
  ma_50?: number;
  ma_200?: number;
  price_vs_50: "Above" | "Below" | "At" | "Unknown";
  price_vs_200: "Above" | "Below" | "At" | "Unknown";
  slope_50: "Rising" | "Flattening" | "Falling" | "Unknown";
  slope_200: "Rising" | "Flattening" | "Falling" | "Unknown";
  trend_health: string;
  interpretation: string;
}

export interface CycleStage {
  stage: 1 | 2 | 3 | 4;
  stage_name: string;
  description: string;
  contributing_factors: string[];
  interpretation: string;
}

export interface Tier1Dashboard {
  as_of: string;
  market_proxy_used: string;
  cape: CapeIndicator;
  buffett: BuffettIndicator;
  breadth: BreadthIndicator;
  leadership: LeadershipIndicator;
  sector_rotation: SectorRotationTier1;
  vix: VixIndicator;
  moving_averages: MovingAveragesIndicator;
  cycle_stage: CycleStage;
  disclaimer: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export class StockDropAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Wraps fetch() to provide actionable error messages for network failures.
   */
  private async fetchWithErrorHandling(url: string, options?: RequestInit): Promise<Response> {
    try {
      const response = await fetch(url, options);
      return response;
    } catch (err: any) {
      // Network error (backend unreachable, CORS, etc.)
      if (err.name === 'TypeError' || err.message.includes('fetch')) {
        throw new Error(
          `Backend unreachable at ${this.baseUrl}. ` +
          `Ensure the backend is running on port 8000.\n\n` +
          `To start the backend:\n` +
          `  1. Open PowerShell in the backend/ folder\n` +
          `  2. Run: .\\venv\\Scripts\\Activate.ps1\n` +
          `  3. Run: python -m app.main\n\n` +
          `Original error: ${err.message}`
        );
      }
      throw err;
    }
  }

  async getChartData(
    ticker: string,
    rangeOrStartDate: string = "max",
    intervalOrEndDate?: string,
    interval?: string
  ): Promise<ChartDataPoint[]> {
    // Check if using date range mode (dates look like YYYY-MM-DD)
    const isDateRange = rangeOrStartDate.match(/^\d{4}-\d{2}-\d{2}$/);
    
    let url: string;
    if (isDateRange && intervalOrEndDate) {
      // Date range mode: getChartData(ticker, startDate, endDate, interval?)
      const startDate = rangeOrStartDate;
      const endDate = intervalOrEndDate;
      const dataInterval = interval || "1d";
      url = `${this.baseUrl}/api/chart/${ticker}?start_date=${startDate}&end_date=${endDate}&interval=${dataInterval}`;
    } else {
      // Standard range mode: getChartData(ticker, range, interval)
      const range = rangeOrStartDate;
      const dataInterval = intervalOrEndDate || "1d";
      url = `${this.baseUrl}/api/chart/${ticker}?range=${range}&interval=${dataInterval}`;
    }
    
    const response = await this.fetchWithErrorHandling(url);
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to fetch chart data" }));
      throw new Error(error.detail || "Failed to fetch chart data");
    }

    return response.json();
  }

  async analyzeByDateRange(request: DateRangeRequest): Promise<AnalysisFullResponse> {
    const response = await this.fetchWithErrorHandling(`${this.baseUrl}/api/analyze-range`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to analyze stock drop" }));
      throw new Error(error.detail || "Failed to analyze stock drop");
    }

    return response.json();
  }

  async healthCheck(): Promise<{ status: string; service?: string }> {
    try {
      const response = await this.fetchWithErrorHandling(`${this.baseUrl}/health`);
      if (!response.ok) {
        throw new Error(`Health check returned status ${response.status}`);
      }
      return response.json();
    } catch (err: any) {
      // Re-throw with backend-specific context
      throw new Error(err.message || 'Backend health check failed');
    }
  }

  async getTier1Dashboard(market: string = "^GSPC"): Promise<Tier1Dashboard> {
    const response = await this.fetchWithErrorHandling(
      `${this.baseUrl}/api/tier1/dashboard?market=${encodeURIComponent(market)}`
    );
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Failed to fetch Tier-1 dashboard" }));
      throw new Error(error.detail || "Failed to fetch Tier-1 dashboard");
    }

    return response.json();
  }
}

export const api = new StockDropAPI();
