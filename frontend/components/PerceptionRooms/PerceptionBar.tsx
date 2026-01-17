'use client';

interface PerceptionBarProps {
  value: number | null | undefined;
  percentile?: number | null;
  min?: number;
  max?: number;
  gradient: 'valuation' | 'mood' | 'engine';
  referenceTicks?: Array<{ value: number; label: string }>;
  clamp?: boolean;
}

/**
 * Data-driven perception bar with percentile positioning.
 * Supports three gradient types matching the room themes.
 */
export default function PerceptionBar({
  value,
  percentile,
  min = 0,
  max = 100,
  gradient,
  referenceTicks = [],
  clamp = true
}: PerceptionBarProps) {
  // If no value, show empty bar
  if (value === null || value === undefined) {
    return (
      <div className="w-full h-2 bg-slate-700 rounded-full relative">
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs text-slate-500">N/A</span>
        </div>
      </div>
    );
  }

  // Calculate position: prefer percentile if available, otherwise scale value to range
  let position: number;
  if (percentile !== null && percentile !== undefined) {
    position = Math.max(0, Math.min(100, percentile));
  } else {
    // Map value to 0-100 based on min/max
    const range = max - min;
    const normalized = (value - min) / range;
    position = Math.max(0, Math.min(100, normalized * 100));
  }

  // Apply clamping visually if value is outside range
  const isOutOfRange = clamp && (value < min || value > max);

  // Gradient class based on room type
  const gradientClass = {
    valuation: 'bg-gradient-to-r from-green-600 via-yellow-500 to-red-600',
    mood: 'bg-gradient-to-r from-blue-500 via-green-500 via-yellow-500 to-red-600',
    engine: 'bg-gradient-to-r from-red-600 via-slate-500 to-green-600'
  }[gradient];

  return (
    <div className="space-y-1">
      {/* Bar */}
      <div className={`w-full h-3 rounded-full relative ${gradientClass}`}>
        {/* Current value marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 transition-all duration-300"
          style={{ left: `${position}%` }}
        >
          <div className={`w-1 h-5 ${isOutOfRange ? 'bg-yellow-400 animate-pulse' : 'bg-white'} rounded-full shadow-lg`} />
        </div>

        {/* Reference ticks (optional) */}
        {referenceTicks.map((tick, idx) => {
          const tickRange = max - min;
          const tickPos = ((tick.value - min) / tickRange) * 100;
          if (tickPos < 0 || tickPos > 100) return null;
          
          return (
            <div
              key={idx}
              className="absolute top-0 h-full w-px bg-slate-900/30"
              style={{ left: `${tickPos}%` }}
              title={tick.label}
            />
          );
        })}
      </div>

      {/* Reference labels */}
      {referenceTicks.length > 0 && (
        <div className="relative w-full h-4 text-[10px] text-slate-500">
          {referenceTicks.map((tick, idx) => {
            const tickRange = max - min;
            const tickPos = ((tick.value - min) / tickRange) * 100;
            if (tickPos < 0 || tickPos > 100) return null;

            return (
              <div
                key={idx}
                className="absolute -translate-x-1/2"
                style={{ left: `${tickPos}%` }}
              >
                {tick.label}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
