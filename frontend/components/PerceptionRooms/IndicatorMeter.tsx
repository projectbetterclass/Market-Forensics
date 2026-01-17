'use client';

import PerceptionBar from './PerceptionBar';

interface IndicatorMeterProps {
  title: string;
  value: number | null | undefined;
  displayValue?: string;
  percentile?: number | null;
  label: string;
  gradient: 'valuation' | 'mood' | 'engine';
  min?: number;
  max?: number;
  referenceTicks?: Array<{ value: number; label: string }>;
  badge?: string;
  badgeColor?: string;
}

/**
 * Complete indicator display: title, value, perception bar, and interpretation label.
 */
export default function IndicatorMeter({
  title,
  value,
  displayValue,
  percentile,
  label,
  gradient,
  min,
  max,
  referenceTicks,
  badge,
  badgeColor
}: IndicatorMeterProps) {
  // Format display value if not provided
  const formattedValue = displayValue || (
    value !== null && value !== undefined
      ? typeof value === 'number'
        ? value.toFixed(1)
        : String(value)
      : 'N/A'
  );

  return (
    <div className="space-y-2">
      {/* Header: Title + Value + Badge */}
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h4 className="text-xs font-medium text-slate-400">{title}</h4>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span className="text-lg font-bold text-slate-100">{formattedValue}</span>
            {percentile !== null && percentile !== undefined && (
              <span className="text-xs text-slate-500">
                {percentile.toFixed(0)}th %ile
              </span>
            )}
          </div>
        </div>
        {badge && (
          <span className={`text-xs px-2 py-0.5 rounded font-medium ${badgeColor || 'bg-slate-700 text-slate-300'}`}>
            {badge}
          </span>
        )}
      </div>

      {/* Perception Bar */}
      <PerceptionBar
        value={value}
        percentile={percentile}
        min={min}
        max={max}
        gradient={gradient}
        referenceTicks={referenceTicks}
      />

      {/* Label / Interpretation */}
      <p className="text-xs text-slate-400 leading-relaxed">{label}</p>
    </div>
  );
}
