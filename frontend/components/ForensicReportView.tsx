'use client';

import { ForensicReport } from '@/lib/api';

interface ForensicReportViewProps {
  report: ForensicReport;
}

export default function ForensicReportView({ report }: ForensicReportViewProps) {
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6 space-y-6">
      {/* Header */}
      <div className="border-b border-slate-700 pb-4">
        <h2 className="text-2xl font-bold text-slate-100 mb-1">
          {report.header.company_name} ({report.header.ticker})
        </h2>
        <p className="text-sm text-slate-400">{report.header.analysis_window}</p>
        <p className="text-xs text-blue-400 italic mt-2">{report.header.principle}</p>
      </div>

      {/* Executive Summary */}
      <div>
        <h3 className="text-lg font-semibold text-slate-100 mb-3">Executive Summary</h3>
        <ul className="space-y-2">
          {report.executive_summary_bullets.map((bullet, idx) => (
            <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
              <span className="text-blue-500 mt-1">•</span>
              <span>{bullet}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Market Context */}
      <div className="bg-slate-900/50 border border-slate-700 rounded p-4">
        <h3 className="text-base font-semibold text-slate-100 mb-2">Market Context</h3>
        <p className="text-sm text-slate-300">{report.market_context_assessment}</p>
      </div>

      {/* Primary Trigger Assessment */}
      <div className="bg-slate-900/50 border border-slate-700 rounded p-4">
        <h3 className="text-base font-semibold text-slate-100 mb-2">Primary Trigger Assessment</h3>
        <p className="text-sm text-slate-300">{report.primary_trigger_assessment}</p>
      </div>

      {/* Ranked Hypotheses */}
      {report.ranked_hypotheses.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Ranked Explanatory Hypotheses</h3>
          <div className="space-y-4">
            {report.ranked_hypotheses.map((hyp, idx) => (
              <div key={idx} className="bg-slate-900/50 border border-slate-700 rounded p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                    {idx + 1}
                  </div>
                  <div className="flex-1">
                    <h4 className="text-base font-semibold text-slate-100">{hyp.title}</h4>
                    <div className="flex items-center gap-4 mt-2 text-xs">
                      <span className="text-slate-400">
                        Probability: <span className="text-blue-400 font-semibold">{hyp.estimated_probability}</span>
                      </span>
                      <span className="text-slate-400">
                        Confidence: <span className={`font-semibold ${
                          hyp.confidence_level === 'High' ? 'text-green-400' :
                          hyp.confidence_level === 'Medium' ? 'text-yellow-400' : 'text-orange-400'
                        }`}>{hyp.confidence_level}</span>
                      </span>
                    </div>
                    <p className="text-sm text-slate-300 mt-3">{hyp.mechanism}</p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {hyp.evidence_types.map((type, tidx) => (
                        <span key={tidx} className="text-xs px-2 py-0.5 bg-slate-700 rounded text-slate-300">
                          {type}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timeline Summary */}
      <div className="bg-slate-900/50 border border-slate-700 rounded p-4">
        <h3 className="text-base font-semibold text-slate-100 mb-2">Timeline Summary</h3>
        <p className="text-sm text-slate-300">{report.timeline_summary}</p>
      </div>

      {/* What This Was NOT */}
      <div className="bg-slate-900/50 border border-slate-700 rounded p-4">
        <h3 className="text-base font-semibold text-slate-100 mb-3">What This Was NOT</h3>
        <ul className="space-y-1">
          {report.what_this_was_not.map((item, idx) => (
            <li key={idx} className="text-sm text-slate-400 flex items-start gap-2">
              <span className="text-slate-600 mt-1">✗</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Unknowns & Limitations */}
      <div className="bg-slate-900/50 border border-slate-700 rounded p-4">
        <h3 className="text-base font-semibold text-slate-100 mb-3">Unknowns & Limitations</h3>
        <ul className="space-y-2">
          {report.unknowns_and_limitations.map((unknown, idx) => (
            <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
              <span className="text-yellow-500 mt-1">⚠</span>
              <span>{unknown}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Practical Interpretation */}
      <div className="bg-slate-900/50 border border-slate-700 rounded p-4">
        <h3 className="text-base font-semibold text-slate-100 mb-3">Practical Interpretation</h3>
        <div className="space-y-3">
          <div>
            <p className="text-xs font-semibold text-slate-400 mb-1">Emotional Errors to Avoid:</p>
            <ul className="space-y-1">
              {report.practical_interpretation.emotional_errors_to_avoid.map((error, idx) => (
                <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                  <span className="text-red-400 mt-0.5">→</span>
                  <span>{error}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 mb-1">What to Monitor Next:</p>
            <ul className="space-y-1">
              {report.practical_interpretation.what_to_monitor_next.map((item, idx) => (
                <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                  <span className="text-blue-400 mt-0.5">→</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Final Takeaway */}
      <div className="bg-blue-900/20 border border-blue-700 rounded p-4">
        <h3 className="text-base font-semibold text-blue-200 mb-2">Final Takeaway</h3>
        <p className="text-sm text-blue-100">{report.final_takeaway}</p>
      </div>
    </div>
  );
}
