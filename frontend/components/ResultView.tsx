'use client';

import { useState } from 'react';
import { AnalysisFullResponse, Evidence } from '@/lib/api';
import ForensicReportView from './ForensicReportView';
import CuratedEvidencePanel from './CuratedEvidencePanel';

interface ResultViewProps {
  result: AnalysisFullResponse;
  ticker: string;
}

export default function ResultView({ result, ticker }: ResultViewProps) {
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [showAllEvidence, setShowAllEvidence] = useState<Record<string, boolean>>({});
  const [timelineExpanded, setTimelineExpanded] = useState<boolean>(false);

  const { chat_answer, agent_contract } = result;

  const toggleShowAll = (hypothesisIdx: number) => {
    setShowAllEvidence(prev => ({ ...prev, [hypothesisIdx]: !prev[hypothesisIdx] }));
  };

  const groupEvidence = (evidence: Evidence[]) => {
    const grouped: Record<string, Evidence[]> = {};
    for (const ev of evidence) {
      const group = ev.group || 'Other';
      if (!grouped[group]) grouped[group] = [];
      grouped[group].push(ev);
    }
    return grouped;
  };

  return (
    <div className="space-y-6">
      {/* Disclaimer Banner */}
      <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4">
        <p className="text-sm text-blue-200">
          <strong>Prepare, Don't Predict:</strong> {agent_contract?.disclaimer || chat_answer.disclaimer}
        </p>
      </div>

      {/* Summary */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">
          {chat_answer.ticker}: {Math.abs(chat_answer.drop_percent).toFixed(2)}% {chat_answer.drop_percent > 0 ? 'gain' : 'drop'}
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-slate-400">Period</p>
            <p className="text-slate-200">
              {new Date(chat_answer.start_time).toLocaleDateString()} - {new Date(chat_answer.end_time).toLocaleDateString()}
            </p>
          </div>
          <div>
            <p className="text-slate-400">Price Change</p>
            <p className="text-slate-200">${chat_answer.start_price.toFixed(2)} → ${chat_answer.end_price.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-slate-400">Volume vs Avg</p>
            <p className="text-slate-200">{chat_answer.volume_vs_average.toFixed(2)}x</p>
          </div>
          <div>
            <p className="text-slate-400">Move Type</p>
            <p className="text-slate-200 capitalize">{chat_answer.move_type.replace('_', ' ')}</p>
          </div>
        </div>
      </div>

      {/* Market Context */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
        <h3 className="text-xl font-semibold text-slate-100 mb-3">Market Context</h3>
        <p className="text-slate-300">{chat_answer.market_context.interpretation}</p>
        <div className="mt-4 text-sm text-slate-400">
          <p>{chat_answer.market_context.market_index}: {chat_answer.market_context.market_return_pct.toFixed(2)}%</p>
        </div>
      </div>

      {/* Forensic Report (replaces Ranked Causes) */}
      {agent_contract?.forensic_report && (
        <ForensicReportView report={agent_contract.forensic_report} />
      )}

      {/* Curated Evidence (replaces timeline source links) */}
      {agent_contract?.curated_evidence && (
        <CuratedEvidencePanel curatedEvidence={agent_contract.curated_evidence} />
      )}

      {/* Timeline - Collapsible (source links removed) */}
      {chat_answer.timeline.length > 0 && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg overflow-hidden">
          <button
            onClick={() => setTimelineExpanded(!timelineExpanded)}
            className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-700/30 transition-colors"
          >
            <h3 className="text-xl font-semibold text-slate-100">
              Timeline ({chat_answer.timeline.length} events)
            </h3>
            <span className={`text-slate-400 transition-transform ${timelineExpanded ? 'rotate-180' : ''}`}>
              ▼
            </span>
          </button>
          
          {timelineExpanded && (
            <div className="p-6 pt-0 space-y-3 border-t border-slate-700">
              {chat_answer.timeline.map((event, idx) => (
                <div key={idx} className="flex gap-3">
                  <div className="text-xs text-slate-400 w-32 flex-shrink-0">
                    {new Date(event.timestamp).toLocaleString()}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-slate-300">{event.description}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Unknowns */}
      {chat_answer.unknowns.length > 0 && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
          <h3 className="text-xl font-semibold text-slate-100 mb-4">Unknowns & Limitations</h3>
          <ul className="space-y-2">
            {chat_answer.unknowns.map((unknown, idx) => (
              <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                <span className="text-yellow-500 mt-1">⚠️</span>
                <span>{unknown}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Next Steps */}
      {chat_answer.next_steps.length > 0 && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
          <h3 className="text-xl font-semibold text-slate-100 mb-4">Monitoring Steps (Not Advice)</h3>
          <ul className="space-y-2">
            {chat_answer.next_steps.map((step, idx) => (
              <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                <span className="text-blue-500 mt-1">→</span>
                <span>{step}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Data Sources */}
      {agent_contract && agent_contract.data_sources_used.length > 0 && (
        <div className="text-center text-sm text-slate-500">
          Data sources: {agent_contract.data_sources_used.join(', ')}
        </div>
      )}
    </div>
  );
}
