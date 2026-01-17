'use client';

import { useState } from 'react';
import { CuratedEvidenceSummary, CuratedSourceGroup, CuratedSource } from '@/lib/api';

interface CuratedEvidencePanelProps {
  curatedEvidence: CuratedEvidenceSummary;
}

export default function CuratedEvidencePanel({ curatedEvidence }: CuratedEvidencePanelProps) {
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  const toggleGroup = (category: string) => {
    setExpandedGroups(prev => ({ ...prev, [category]: !prev[category] }));
  };

  const getCategoryIcon = (category: string): string => {
    switch (category) {
      case 'Primary':
        return '📄';
      case 'CorporateOperational':
        return '🏢';
      case 'MacroSystemic':
        return '🌍';
      case 'Narrative':
        return '💬';
      default:
        return '📰';
    }
  };

  const getCategoryColor = (category: string): string => {
    switch (category) {
      case 'Primary':
        return 'border-green-700 bg-green-900/20';
      case 'CorporateOperational':
        return 'border-blue-700 bg-blue-900/20';
      case 'MacroSystemic':
        return 'border-purple-700 bg-purple-900/20';
      case 'Narrative':
        return 'border-yellow-700 bg-yellow-900/20';
      default:
        return 'border-slate-700 bg-slate-900/20';
    }
  };

  const getWeightBadgeColor = (weight: number): string => {
    if (weight >= 0.8) return 'bg-green-600 text-white';
    if (weight >= 0.6) return 'bg-blue-600 text-white';
    if (weight >= 0.4) return 'bg-yellow-600 text-white';
    return 'bg-gray-600 text-white';
  };

  const renderSource = (source: CuratedSource, index: number) => (
    <div key={index} className="py-3 border-b border-slate-700 last:border-0">
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-400 hover:text-blue-300 hover:underline font-medium"
          >
            {source.headline}
          </a>
          <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
            <span>{source.relative_time_label}</span>
            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${getWeightBadgeColor(source.final_weight)}`}>
              {(source.final_weight * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  if (!curatedEvidence.groups || curatedEvidence.groups.length === 0) {
    return (
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
        <h3 className="text-xl font-semibold text-slate-100 mb-3">Sources & Evidence</h3>
        <p className="text-slate-400 text-sm">No evidence sources found for this analysis window.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
      <div className="mb-4">
        <h3 className="text-xl font-semibold text-slate-100 mb-2">Sources & Evidence</h3>
        <p className="text-xs text-slate-400">
          {curatedEvidence.total_sources_validated} sources validated
          {curatedEvidence.total_sources_collapsed > 0 && `, ${curatedEvidence.total_sources_collapsed} duplicates collapsed`}
        </p>
      </div>

      {/* Narrative-only disclaimer */}
      {curatedEvidence.disclaimer_if_narrative_only && (
        <div className="mb-4 p-3 bg-yellow-900/30 border border-yellow-700 rounded text-sm text-yellow-200">
          {curatedEvidence.disclaimer_if_narrative_only}
        </div>
      )}

      {/* Category groups */}
      <div className="space-y-4">
        {curatedEvidence.groups.map((group: CuratedSourceGroup) => (
          <div
            key={group.category}
            className={`border rounded-lg overflow-hidden ${getCategoryColor(group.category)}`}
          >
            {/* Group header */}
            <div className="p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg">{getCategoryIcon(group.category)}</span>
                <h4 className="font-semibold text-slate-100 text-sm">
                  {group.category_label}
                </h4>
                <span className="text-xs text-slate-400">
                  ({group.top_sources.length + group.remaining_count})
                </span>
              </div>
              {group.remaining_count > 0 && (
                <button
                  onClick={() => toggleGroup(group.category)}
                  className="text-xs text-blue-400 hover:text-blue-300"
                >
                  {expandedGroups[group.category] ? 'Show less' : `Show ${group.remaining_count} more`}
                </button>
              )}
            </div>

            {/* Sources */}
            <div className="px-3 pb-3">
              {/* Top 3 sources */}
              {group.top_sources.map((source, idx) => renderSource(source, idx))}

              {/* Additional sources (collapsed by default) */}
              {expandedGroups[group.category] &&
                group.all_sources
                  .slice(3)
                  .map((source, idx) => renderSource(source, idx + 3))}
            </div>
          </div>
        ))}
      </div>

      {/* Footer note */}
      <div className="mt-4 pt-4 border-t border-slate-700 text-xs text-slate-500">
        <p>
          <strong>Quality over quantity:</strong> Sources are filtered, deduplicated, and ranked by
          authority, relevance, and timing. The percentage badge shows the confidence score.
        </p>
      </div>
    </div>
  );
}
