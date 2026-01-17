'use client';

import { PatternAnalog } from '@/lib/api';

interface PatternAnalogsProps {
  analogs: PatternAnalog[];
}

export default function PatternAnalogs({ analogs }: PatternAnalogsProps) {
  if (!analogs || analogs.length === 0) {
    return (
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">Historical Pattern Analogs</h2>
        <p className="text-slate-400">No similar historical patterns found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg p-4">
        <p className="text-sm text-yellow-200">
          ⚠️ <strong>Pattern ≠ Outcome:</strong> Similar patterns have led to varied outcomes in the past. Historical patterns do not predict future results.
        </p>
      </div>

      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">Historical Pattern Analogs</h2>
        
        <div className="space-y-4">
          {analogs.map((analog, idx) => (
            <div key={idx} className="border border-slate-700 rounded-lg p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-lg font-semibold text-slate-100">{analog.pattern_description}</h3>
                  <p className="text-sm text-slate-400">
                    {new Date(analog.start_date).toLocaleDateString()} - {new Date(analog.end_date).toLocaleDateString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-slate-400">Similarity</p>
                  <p className="text-xl font-bold text-blue-400">{(analog.similarity_score * 100).toFixed(0)}%</p>
                </div>
              </div>

              {/* Outcome Dispersion */}
              <div className="mt-4">
                <p className="text-sm font-semibold text-slate-300 mb-2">Forward Returns:</p>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                  {Object.entries(analog.outcomes).map(([horizon, outcome]: [string, any]) => (
                    <div key={horizon} className="p-2 bg-slate-900/50 rounded text-center">
                      <p className="text-xs text-slate-400">{horizon}</p>
                      {outcome.return_pct !== null ? (
                        <p className={`text-sm font-semibold ${outcome.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {outcome.return_pct >= 0 ? '+' : ''}{outcome.return_pct}%
                        </p>
                      ) : (
                        <p className="text-xs text-slate-500">{outcome.note || 'N/A'}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Sentiment/Narrative */}
              {analog.sentiment_at_time && (
                <div className="mt-3 p-2 bg-slate-900/50 rounded">
                  <p className="text-xs text-slate-400">How people felt then:</p>
                  <p className="text-sm text-slate-300">{analog.sentiment_at_time}</p>
                </div>
              )}
              
              {analog.narrative_tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {analog.narrative_tags.map((tag, tagIdx) => (
                    <span key={tagIdx} className="text-xs px-2 py-1 bg-blue-900/30 text-blue-300 rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
