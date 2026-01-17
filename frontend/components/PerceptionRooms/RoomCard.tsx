'use client';

import { ReactNode } from 'react';

interface RoomCardProps {
  title: string;
  theme: 'price' | 'mood' | 'engine';
  children: ReactNode;
}

/**
 * Container card for grouping related indicators into perceptual "rooms".
 */
export default function RoomCard({ title, theme, children }: RoomCardProps) {
  // Theme-specific accent colors
  const accentClass = {
    price: 'border-l-red-500',
    mood: 'border-l-blue-500',
    engine: 'border-l-green-500'
  }[theme];

  const titleGradient = {
    price: 'from-red-500/10 to-transparent',
    mood: 'from-blue-500/10 to-transparent',
    engine: 'from-green-500/10 to-transparent'
  }[theme];

  return (
    <div className={`bg-slate-900/50 border border-slate-700 ${accentClass} border-l-4 rounded-lg overflow-hidden`}>
      {/* Room Header */}
      <div className={`bg-gradient-to-r ${titleGradient} px-4 py-2 border-b border-slate-700/50`}>
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
          {title}
        </h3>
      </div>

      {/* Room Content */}
      <div className="p-4 space-y-3">
        {children}
      </div>
    </div>
  );
}
