'use client';

import type { TimelineEvent } from '@/lib/api';

interface TimelineProps {
  events: TimelineEvent[];
}

export default function Timeline({ events }: TimelineProps) {
  if (events.length === 0) {
    return <p className="text-slate-400">No timeline events found.</p>;
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-600"></div>

      {/* Events */}
      <div className="space-y-6">
        {events.map((event, idx) => (
          <div key={idx} className="relative pl-12">
            {/* Dot */}
            <div className="absolute left-2.5 top-1 w-3 h-3 rounded-full bg-blue-500 border-2 border-slate-900"></div>

            {/* Content */}
            <div className="bg-slate-700/30 rounded-lg p-4">
              <div className="flex justify-between items-start mb-2">
                <p className="text-sm text-slate-400">
                  {new Date(event.timestamp).toLocaleString()}
                </p>
                {event.price_impact && (
                  <span className="text-xs px-2 py-1 bg-red-500/20 text-red-300 rounded">
                    {event.price_impact}
                  </span>
                )}
              </div>
              <p className="text-slate-200 font-medium mb-2">{event.description}</p>
              <div className="flex items-center gap-2 text-sm">
                <span className="px-2 py-0.5 bg-slate-600 text-slate-300 rounded text-xs">
                  {event.evidence.source_type.replace('_', ' ')}
                </span>
                {event.evidence.source_url && (
                  <a
                    href={event.evidence.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:underline text-xs"
                  >
                    View source →
                  </a>
                )}
              </div>
              {event.evidence.snippet && (
                <p className="text-slate-400 text-sm mt-2 italic">"{event.evidence.snippet}"</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
