'use client';

import { MarketRegime, ValuationContext, CrowdBehavior, SectorRotation } from '@/lib/api';

interface ContextPanelsProps {
  regime?: MarketRegime;
  valuation?: ValuationContext;
  crowd?: CrowdBehavior;
  rotation?: SectorRotation;
}

export default function ContextPanels({ regime, valuation, crowd, rotation }: ContextPanelsProps) {
  if (!regime && !valuation && !crowd && !rotation) {
    return null;
  }

  // If the user only wants Sector Rotation, avoid rendering the big "Market Context" header.
  const showOnlyRotation = !!rotation && !regime && !valuation && !crowd;

  return (
    <div className="space-y-6">
      {!showOnlyRotation && (
        <h2 className="text-2xl font-bold text-slate-100">Market Context</h2>
      )}

      {/* Market Regime */}
      {regime && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center text-white text-xl font-bold">
              {regime.stage}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-100">{regime.stage_name}</h3>
              <p className="text-sm text-slate-400">Volatility: {regime.volatility_regime}</p>
            </div>
          </div>
          <p className="text-slate-300">{regime.description}</p>
        </div>
      )}

      {/* Valuation Stress */}
      {valuation && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Valuation Stress Indicators</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            {valuation.cape_ratio && (
              <div className="p-3 bg-slate-900/50 rounded">
                <p className="text-xs text-slate-400">CAPE Ratio</p>
                <p className="text-xl font-bold text-slate-100">{valuation.cape_ratio.toFixed(2)}</p>
                {valuation.cape_percentile && (
                  <p className="text-xs text-slate-400">{valuation.cape_percentile.toFixed(0)}th percentile</p>
                )}
              </div>
            )}
            {valuation.buffett_indicator && (
              <div className="p-3 bg-slate-900/50 rounded">
                <p className="text-xs text-slate-400">Buffett Indicator</p>
                <p className="text-xl font-bold text-slate-100">{valuation.buffett_indicator.toFixed(2)}%</p>
                {valuation.buffett_percentile && (
                  <p className="text-xs text-slate-400">{valuation.buffett_percentile.toFixed(0)}th percentile</p>
                )}
              </div>
            )}
            {valuation.breadth_reading && (
              <div className="p-3 bg-slate-900/50 rounded">
                <p className="text-xs text-slate-400">Breadth</p>
                <p className="text-xl font-bold text-slate-100">{valuation.breadth_reading.toFixed(1)}%</p>
                {valuation.breadth_interpretation && (
                  <p className="text-xs text-slate-400">{valuation.breadth_interpretation}</p>
                )}
              </div>
            )}
          </div>
          <p className="text-sm text-slate-400 italic">{valuation.context_statement}</p>
        </div>
      )}

      {/* Crowd Behavior */}
      {crowd && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Crowd Behavior</h3>
          <div className="space-y-2 text-sm">
            {crowd.retail_inflow_proxy && (
              <p><span className="text-slate-400">Retail Inflow:</span> <span className="text-slate-300">{crowd.retail_inflow_proxy}</span></p>
            )}
            {crowd.options_activity_proxy && (
              <p><span className="text-slate-400">Options Activity:</span> <span className="text-slate-300">{crowd.options_activity_proxy}</span></p>
            )}
            {crowd.leadership_narrowing && (
              <p><span className="text-slate-400">Leadership:</span> <span className="text-slate-300">{crowd.leadership_narrowing}</span></p>
            )}
            {crowd.speculative_outperformance && (
              <p><span className="text-slate-400">Speculative Assets:</span> <span className="text-slate-300">{crowd.speculative_outperformance}</span></p>
            )}
          </div>
          <p className="text-sm text-slate-400 italic mt-4">{crowd.interpretation}</p>
        </div>
      )}

      {/* Sector Rotation */}
      {rotation && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Sector Rotation</h3>
          
          {rotation.leadership_concentration_warning && (
            <div className="mb-4 p-3 bg-yellow-900/20 border border-yellow-700 rounded">
              <p className="text-sm text-yellow-200">⚠️ {rotation.leadership_concentration_warning}</p>
            </div>
          )}
          
          <div className="space-y-2 mb-4">
            {rotation.sector_performances.slice(0, 5).map((sector, idx) => (
              <div key={idx} className="flex items-center justify-between text-sm">
                <span className="text-slate-300">{sector.sector}</span>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400 text-xs">{sector.etf}</span>
                  <span className={`font-semibold ${sector.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {sector.return_pct >= 0 ? '+' : ''}{sector.return_pct.toFixed(2)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
          
          <p className="text-sm text-slate-400 italic">{rotation.interpretation}</p>
        </div>
      )}
    </div>
  );
}
