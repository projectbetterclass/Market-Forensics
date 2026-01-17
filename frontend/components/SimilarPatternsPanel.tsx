'use client';

import { useState } from 'react';
import { TickerPatternMatch } from '@/lib/api';
import HistoricalMiniChart from './HistoricalMiniChart';

interface SimilarPatternsPanelProps {
  matches: TickerPatternMatch[];
  ticker: string;
}

export default function SimilarPatternsPanel({ matches, ticker }: SimilarPatternsPanelProps) {
  const [expandedMatches, setExpandedMatches] = useState<Record<number, boolean>>({
    0: true // Expand first match by default
  });

  const toggleMatchExpanded = (idx: number) => {
    setExpandedMatches(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  if (matches.length === 0) return null;

  return (
    <div className="h-fit">
      <h3 className="text-base font-semibold text-slate-100 mb-1">
        Similar Patterns
      </h3>
      <p className="text-xs text-slate-400 mb-3">
        When {ticker} showed similar behavior and what caused it
      </p>
      
      <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto pr-1">
        {matches.slice(0, 5).map((match, idx) => {
          const isExpanded = expandedMatches[idx] || false;
          
          return (
            <div key={idx} className="bg-slate-900/50 rounded-lg border border-slate-700 overflow-hidden">
              {/* Header */}
              <button
                onClick={() => toggleMatchExpanded(idx)}
                className="w-full p-3 flex items-center justify-between text-left hover:bg-slate-800/50 transition-colors"
              >
                <div>
                  <div className="text-sm font-semibold text-slate-200">
                    {new Date(match.start_date).toLocaleDateString('en-US', { 
                      month: 'short', 
                      year: 'numeric' 
                    })}
                  </div>
                  <div className="text-xs text-blue-400 mt-0.5">
                    {(match.similarity_score * 100).toFixed(0)}% similar
                  </div>
                </div>
                <span className={`text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
                  ▼
                </span>
              </button>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="border-t border-slate-700">
                  {/* Mini Chart */}
                  <div className="p-2 bg-slate-900/30">
                    <HistoricalMiniChart 
                      startDate={match.start_date}
                      endDate={match.end_date}
                      ticker={ticker}
                    />
                  </div>

                  {/* What Caused This */}
                  {match.reasoning_events && match.reasoning_events.length > 0 && (
                    <div className="px-3 py-2 border-t border-slate-700">
                      <h4 className="text-xs font-semibold text-amber-400 mb-2">
                        Why it moved:
                      </h4>
                      <ul className="space-y-1.5">
                        {match.reasoning_events.map((event, evIdx) => (
                          <li key={evIdx} className="text-xs text-slate-300 flex items-start gap-1.5">
                            <span className="text-amber-500 mt-0.5 flex-shrink-0">•</span>
                            <span className="leading-tight">{event}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Outcome Summary */}
                  <div className="px-3 py-2 border-t border-slate-700">
                    <h4 className="text-xs font-semibold text-slate-400 mb-1.5">
                      What happened next:
                    </h4>
                    <div className="space-y-1">
                      {Object.entries(match.outcomes).slice(0, 2).map(([horizon, outcome]) => (
                        <div key={horizon} className="flex justify-between text-xs">
                          <span className="text-slate-500">{horizon}:</span>
                          <span className={`font-semibold ${outcome.mean_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {outcome.mean_return_pct >= 0 ? '+' : ''}{outcome.mean_return_pct.toFixed(1)}%
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="text-[10px] text-slate-600 mt-1 italic">
                      Click for full details below ↓
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
