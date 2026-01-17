'use client';

import { MarketStateVector } from '@/lib/api';
import RoomCard from './PerceptionRooms/RoomCard';
import IndicatorMeter from './PerceptionRooms/IndicatorMeter';

interface MarketStatePanelProps {
  marketState: MarketStateVector;
  ticker: string;
  startDate: string;
  endDate: string;
}

export default function MarketStatePanel({ marketState, ticker, startDate, endDate }: MarketStatePanelProps) {
  // Badge color helpers
  const getVixBadgeColor = (regime: string) => {
    switch (regime) {
      case 'low': return 'bg-green-600 text-white';
      case 'normal': return 'bg-blue-600 text-white';
      case 'high': return 'bg-red-600 text-white';
      default: return 'bg-slate-600 text-white';
    }
  };

  const getTrendBadgeColor = (regime: string) => {
    switch (regime) {
      case 'uptrend': return 'bg-green-600 text-white';
      case 'downtrend': return 'bg-red-600 text-white';
      case 'sideways': return 'bg-yellow-600 text-white';
      default: return 'bg-slate-600 text-white';
    }
  };

  const getBreadthBadgeColor = (regime: string) => {
    switch (regime) {
      case 'strong': return 'bg-green-600 text-white';
      case 'weak': return 'bg-red-600 text-white';
      default: return 'bg-slate-600 text-white';
    }
  };

  const getLeadershipBadgeColor = (regime: string) => {
    switch (regime) {
      case 'broad': return 'bg-green-600 text-white';
      case 'narrow': return 'bg-red-600 text-white';
      default: return 'bg-slate-600 text-white';
    }
  };

  const getRotationBadgeColor = (regime: string) => {
    switch (regime) {
      case 'risk_on': return 'bg-green-600 text-white';
      case 'risk_off': return 'bg-red-600 text-white';
      default: return 'bg-slate-600 text-white';
    }
  };

  return (
    <div className="space-y-4 w-full">
      {/* Header */}
      <div className="text-center">
        <h3 className="text-sm font-semibold text-slate-200 mb-1">Market State at Event</h3>
        <p className="text-xs text-slate-500">
          {new Date(startDate).toLocaleDateString()} - {new Date(endDate).toLocaleDateString()}
        </p>
      </div>

      {/* Room A: The Price Tag (Valuation) */}
      <RoomCard title="The Price Tag — Valuation" theme="price">
        {/* CAPE */}
        {marketState.cape_ratio !== undefined && marketState.cape_ratio !== null && (
          <IndicatorMeter
            title="CAPE Ratio"
            value={marketState.cape_ratio}
            displayValue={marketState.cape_ratio.toFixed(1)}
            percentile={marketState.cape_percentile}
            label={
              marketState.cape_percentile && marketState.cape_percentile > 80
                ? `Market at ${marketState.cape_percentile.toFixed(0)}th percentile — elevated historical pricing.`
                : `Historical valuation context.`
            }
            gradient="valuation"
            referenceTicks={[
              { value: 17, label: 'Avg' },
              { value: 30, label: 'Warning' }
            ]}
            min={5}
            max={45}
          />
        )}

        {/* Buffett Indicator */}
        {marketState.buffett_indicator !== undefined && marketState.buffett_indicator !== null && (
          <IndicatorMeter
            title="Buffett Indicator"
            value={marketState.buffett_indicator}
            displayValue={`${marketState.buffett_indicator.toFixed(0)}%`}
            percentile={marketState.buffett_percentile}
            label={
              marketState.buffett_percentile && marketState.buffett_percentile > 80
                ? `${marketState.buffett_percentile.toFixed(0)}th percentile — disconnect from economy.`
                : `Market cap vs GDP context.`
            }
            gradient="valuation"
            referenceTicks={[
              { value: 100, label: 'Fair' },
              { value: 150, label: 'Stretched' }
            ]}
            min={75}
            max={220}
          />
        )}
      </RoomCard>

      {/* Room B: The Mood (Sentiment) */}
      <RoomCard title="The Mood — Sentiment" theme="mood">
        {/* VIX */}
        {marketState.vix_level !== undefined && marketState.vix_level !== null && (
          <IndicatorMeter
            title="VIX Index"
            value={marketState.vix_level}
            displayValue={marketState.vix_level.toFixed(1)}
            label={
              marketState.vix_regime === 'low'
                ? 'Investors are calm — complacency risk.'
                : marketState.vix_regime === 'high'
                ? 'Elevated fear in the market.'
                : 'Normal volatility regime.'
            }
            gradient="mood"
            badge={marketState.vix_regime}
            badgeColor={getVixBadgeColor(marketState.vix_regime)}
            referenceTicks={[
              { value: 20, label: 'Normal' },
              { value: 30, label: 'Fear' },
              { value: 50, label: 'Panic' }
            ]}
            min={10}
            max={60}
          />
        )}
      </RoomCard>

      {/* Room C: The Engine (Internal Health) */}
      <RoomCard title="The Engine — Internal Health" theme="engine">
        {/* Breadth */}
        {marketState.breadth_value !== undefined && marketState.breadth_value !== null && (
          <IndicatorMeter
            title="Market Breadth"
            value={marketState.breadth_value}
            displayValue={`${marketState.breadth_value.toFixed(1)}%`}
            label={
              marketState.breadth_regime === 'strong'
                ? 'The team is participating equally — healthy breadth.'
                : marketState.breadth_regime === 'weak'
                ? 'Narrow participation — concentration risk.'
                : 'Participation quality context.'
            }
            gradient="engine"
            badge={marketState.breadth_regime}
            badgeColor={getBreadthBadgeColor(marketState.breadth_regime)}
            referenceTicks={[{ value: 0, label: 'Neutral' }]}
            min={-5}
            max={5}
          />
        )}

        {/* Sector Rotation */}
        {marketState.xly_xlp_ratio !== undefined && marketState.xly_xlp_ratio !== null && (
          <IndicatorMeter
            title="Sector Rotation (XLY/XLP)"
            value={marketState.xly_xlp_ratio}
            displayValue={marketState.xly_xlp_ratio.toFixed(2)}
            label={
              marketState.sector_rotation_regime === 'risk_on'
                ? 'Risk-on posture — attacking.'
                : marketState.sector_rotation_regime === 'risk_off'
                ? 'Risk-off posture — defending.'
                : 'Balanced posture between safety and growth.'
            }
            gradient="engine"
            badge={marketState.sector_rotation_regime?.replace('_', ' ')}
            badgeColor={getRotationBadgeColor(marketState.sector_rotation_regime)}
            referenceTicks={[{ value: 1, label: 'Neutral' }]}
            min={0.85}
            max={1.15}
          />
        )}

        {/* Secondary: Trend Health */}
        {marketState.trend_regime && marketState.trend_regime !== 'unknown' && (
          <div className="p-3 bg-slate-800/50 rounded border border-slate-700/50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-400">Trend Health</span>
              <span className={`text-xs font-medium px-2 py-0.5 rounded capitalize ${getTrendBadgeColor(marketState.trend_regime)}`}>
                {marketState.trend_regime}
              </span>
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">vs 50MA:</span>
                <span className={marketState.sp500_above_50ma ? 'text-green-400' : 'text-red-400'}>
                  {marketState.sp500_above_50ma ? '▲ Above' : '▼ Below'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">vs 200MA:</span>
                <span className={marketState.sp500_above_200ma ? 'text-green-400' : 'text-red-400'}>
                  {marketState.sp500_above_200ma ? '▲ Above' : '▼ Below'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Secondary: Leadership */}
        {marketState.leadership_regime && marketState.leadership_regime !== 'unknown' && (
          <div className="p-3 bg-slate-800/50 rounded border border-slate-700/50">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">Leadership</span>
              <span className={`text-xs font-medium px-2 py-0.5 rounded capitalize ${getLeadershipBadgeColor(marketState.leadership_regime)}`}>
                {marketState.leadership_regime}
              </span>
            </div>
            {marketState.leadership_regime === 'narrow' && (
              <p className="text-xs text-yellow-500 mt-1">Concentration risk present</p>
            )}
          </div>
        )}
      </RoomCard>

      <div className="text-xs text-slate-600 text-center pt-2 border-t border-slate-700">
        Context only — not predictive
      </div>
    </div>
  );
}
