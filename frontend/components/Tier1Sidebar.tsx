'use client';

import { useState, useEffect } from 'react';
import { api, Tier1Dashboard } from '@/lib/api';
import RoomCard from './PerceptionRooms/RoomCard';
import IndicatorMeter from './PerceptionRooms/IndicatorMeter';

interface Tier1SidebarProps {
  market?: string;
}

export default function Tier1Sidebar({ market = "^GSPC" }: Tier1SidebarProps) {
  const [dashboard, setDashboard] = useState<Tier1Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    loadDashboard();
    // Refresh every 10 minutes
    const interval = setInterval(loadDashboard, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, [market]);

  const loadDashboard = async () => {
    try {
      const data = await api.getTier1Dashboard(market);
      setDashboard(data);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Failed to load indicators');
    } finally {
      setLoading(false);
    }
  };

  // Mobile toggle
  const toggleCollapse = () => setCollapsed(!collapsed);

  if (loading) {
    return (
      <div className="bg-slate-800 border-l border-slate-700 p-4 w-96">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-700 rounded w-3/4"></div>
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-16 bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="bg-slate-800 border-l border-slate-700 p-4 w-96">
        <h2 className="text-lg font-bold text-slate-100 mb-4">Market Context</h2>
        <p className="text-sm text-red-400">{error || 'Unable to load indicators'}</p>
      </div>
    );
  }

  // Badge color helpers
  const getVixBadgeColor = (regime: string) => {
    switch (regime) {
      case 'Compressed': return 'bg-green-600 text-white';
      case 'Normal': return 'bg-blue-600 text-white';
      case 'Elevated': return 'bg-red-600 text-white';
      default: return 'bg-slate-600 text-white';
    }
  };

  const getBuffettBadgeColor = (zone: string) => {
    switch (zone) {
      case 'Fair': return 'bg-green-600 text-white';
      case 'Stretched': return 'bg-yellow-600 text-white';
      case 'Extreme': return 'bg-red-600 text-white';
      default: return 'bg-slate-600 text-white';
    }
  };

  const getLeadershipBadgeColor = (label: string) => {
    switch (label) {
      case 'Broad': return 'bg-green-600 text-white';
      case 'Moderate': return 'bg-yellow-600 text-white';
      case 'Narrow': return 'bg-red-600 text-white';
      default: return 'bg-slate-600 text-white';
    }
  };

  const getTrendBadgeColor = (health: string) => {
    switch (health) {
      case 'Strong': return 'bg-green-600 text-white';
      case 'Moderate': return 'bg-blue-600 text-white';
      case 'Weak': return 'bg-red-600 text-white';
      default: return 'bg-slate-600 text-white';
    }
  };

  return (
    <>
      {/* Mobile toggle button */}
      <button
        onClick={toggleCollapse}
        className="lg:hidden fixed bottom-4 right-4 z-50 bg-blue-600 text-white p-3 rounded-full shadow-lg"
      >
        {collapsed ? '📊' : '✕'}
      </button>

      {/* Sidebar */}
      <div className={`bg-slate-800 border-l border-slate-700 w-96 overflow-y-auto transition-transform ${
        collapsed ? 'hidden lg:block' : 'block'
      } fixed lg:static right-0 top-0 h-full z-40 lg:z-auto`}>
        <div className="p-4 space-y-4">
          {/* Header */}
          <div className="border-b border-slate-700 pb-3">
            <h2 className="text-lg font-bold text-slate-100">Market Context</h2>
            <p className="text-xs text-slate-400 mt-1">
              {dashboard.market_proxy_used} • {new Date(dashboard.as_of).toLocaleTimeString()}
            </p>
          </div>

          {/* Cycle Stage - Meta indicator at top */}
          <CycleStageCard stage={dashboard.cycle_stage} />

          {/* Room A: The Price Tag (Valuation) */}
          <RoomCard title="The Price Tag — Valuation" theme="price">
            {/* CAPE */}
            <IndicatorMeter
              title="CAPE Ratio"
              value={dashboard.cape.value}
              displayValue={dashboard.cape.value?.toFixed(1)}
              percentile={dashboard.cape.percentile}
              label={dashboard.cape.interpretation}
              gradient="valuation"
              referenceTicks={[
                { value: 17, label: 'Avg' },
                { value: 30, label: 'Warning' }
              ]}
              min={5}
              max={45}
            />

            {/* Buffett */}
            <IndicatorMeter
              title="Buffett Indicator"
              value={dashboard.buffett.value}
              displayValue={dashboard.buffett.value ? `${dashboard.buffett.value.toFixed(0)}%` : undefined}
              percentile={dashboard.buffett.percentile}
              label={dashboard.buffett.interpretation}
              gradient="valuation"
              badge={dashboard.buffett.zone}
              badgeColor={getBuffettBadgeColor(dashboard.buffett.zone)}
              referenceTicks={[
                { value: 100, label: 'Fair' },
                { value: 150, label: 'Stretched' }
              ]}
              min={75}
              max={220}
            />
          </RoomCard>

          {/* Room B: The Mood (Sentiment) */}
          <RoomCard title="The Mood — Sentiment" theme="mood">
            {/* VIX */}
            <IndicatorMeter
              title="VIX Index"
              value={dashboard.vix.value}
              displayValue={dashboard.vix.value?.toFixed(1)}
              label={dashboard.vix.interpretation}
              gradient="mood"
              badge={dashboard.vix.regime}
              badgeColor={getVixBadgeColor(dashboard.vix.regime)}
              referenceTicks={[
                { value: 20, label: 'Normal' },
                { value: 30, label: 'Fear' },
                { value: 50, label: 'Panic' }
              ]}
              min={10}
              max={60}
            />
            {dashboard.vix.insight && (
              <p className="text-xs text-blue-400 italic mt-2">{dashboard.vix.insight}</p>
            )}
          </RoomCard>

          {/* Room C: The Engine (Internal Health) */}
          <RoomCard title="The Engine — Internal Health" theme="engine">
            {/* Breadth */}
            <IndicatorMeter
              title="Market Breadth"
              value={dashboard.breadth.value}
              displayValue={dashboard.breadth.value ? `${dashboard.breadth.value.toFixed(1)}%` : undefined}
              label={dashboard.breadth.interpretation}
              gradient="engine"
              referenceTicks={[{ value: 0, label: 'Neutral' }]}
              min={-5}
              max={5}
            />

            {/* Sector Rotation */}
            <IndicatorMeter
              title="Sector Rotation (XLY/XLP)"
              value={dashboard.sector_rotation.xly_xlp_ratio}
              displayValue={dashboard.sector_rotation.xly_xlp_ratio ? `${dashboard.sector_rotation.xly_xlp_ratio.toFixed(1)}%` : undefined}
              label={dashboard.sector_rotation.interpretation}
              gradient="engine"
              referenceTicks={[{ value: 0, label: 'Neutral' }]}
              min={-5}
              max={5}
            />

            {/* Top Sectors (compact list) */}
            {dashboard.sector_rotation.top_sectors.length > 0 && (
              <div className="p-3 bg-slate-800/50 rounded border border-slate-700/50">
                <h4 className="text-xs font-medium text-slate-400 mb-2">Top Sectors</h4>
                <div className="space-y-1">
                  {dashboard.sector_rotation.top_sectors.slice(0, 3).map((sector, idx) => (
                    <div key={idx} className="flex justify-between text-xs">
                      <span className="text-slate-300">{sector.sector}</span>
                      <span className={sector.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {sector.return_pct >= 0 ? '+' : ''}{sector.return_pct}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Secondary: Trend Health */}
            <div className="p-3 bg-slate-800/50 rounded border border-slate-700/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-400">Trend Health</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${getTrendBadgeColor(dashboard.moving_averages.trend_health)}`}>
                  {dashboard.moving_averages.trend_health}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                <div>
                  <span className="text-slate-500">50D: </span>
                  <span className={
                    dashboard.moving_averages.price_vs_50 === 'Above' ? 'text-green-400' :
                    dashboard.moving_averages.price_vs_50 === 'Below' ? 'text-red-400' : 'text-slate-300'
                  }>
                    {dashboard.moving_averages.price_vs_50}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">200D: </span>
                  <span className={
                    dashboard.moving_averages.price_vs_200 === 'Above' ? 'text-green-400' :
                    dashboard.moving_averages.price_vs_200 === 'Below' ? 'text-red-400' : 'text-slate-300'
                  }>
                    {dashboard.moving_averages.price_vs_200}
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-400">{dashboard.moving_averages.interpretation}</p>
            </div>

            {/* Secondary: Leadership */}
            <div className="p-3 bg-slate-800/50 rounded border border-slate-700/50">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-400">Leadership</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${getLeadershipBadgeColor(dashboard.leadership.leadership_label)}`}>
                  {dashboard.leadership.leadership_label}
                </span>
              </div>
              {dashboard.leadership.value !== null && dashboard.leadership.value !== undefined && (
                <p className="text-lg font-bold text-slate-100 mb-1">{dashboard.leadership.value.toFixed(1)}%</p>
              )}
              <p className="text-xs text-slate-400">{dashboard.leadership.interpretation}</p>
            </div>
          </RoomCard>

          {/* Disclaimer */}
          <div className="text-xs text-slate-500 border-t border-slate-700 pt-3">
            {dashboard.disclaimer}
          </div>
        </div>
      </div>
    </>
  );
}

// Cycle Stage Card
function CycleStageCard({ stage }: { stage: Tier1Dashboard['cycle_stage'] }) {
  const stageMeta: Record<
    number,
    {
      label: string;
      meaning: string;
      accentGradientFrom: string;
      accentSolid: string;
      icon: 'base' | 'up' | 'flatTop' | 'down';
    }
  > = {
    1: {
      label: 'Accumulation',
      meaning: 'Smart money buying after a decline.',
      accentGradientFrom: 'from-teal-500/25',
      accentSolid: 'bg-teal-500',
      icon: 'base'
    },
    2: {
      label: 'Expansion',
      meaning: 'Sustained uptrend with broad participation.',
      accentGradientFrom: 'from-green-600/25',
      accentSolid: 'bg-green-600',
      icon: 'up'
    },
    3: {
      label: 'Distribution',
      meaning: 'Risk building near highs; smart money sells into strength.',
      accentGradientFrom: 'from-amber-500/25',
      accentSolid: 'bg-amber-500',
      icon: 'flatTop'
    },
    4: {
      label: 'Contraction',
      meaning: 'Downtrend and risk-off; fear and volatility spike.',
      accentGradientFrom: 'from-red-600/25',
      accentSolid: 'bg-red-600',
      icon: 'down'
    }
  };

  const s = stageMeta[stage.stage];

  const stageOrder = [
    stageMeta[1],
    stageMeta[2],
    stageMeta[3],
    stageMeta[4]
  ];

  const getSegmentColor = (segmentStage: 1 | 2 | 3 | 4) => {
    const active = segmentStage <= stage.stage;
    const solid =
      segmentStage === 1 ? 'bg-teal-500' :
      segmentStage === 2 ? 'bg-green-600' :
      segmentStage === 3 ? 'bg-amber-500' :
      'bg-red-600';
    return active ? solid : 'bg-slate-700';
  };

  const StageIcon = ({ type, active }: { type: 'base' | 'up' | 'flatTop' | 'down'; active: boolean }) => {
    const stroke = active ? 'stroke-slate-100' : 'stroke-slate-500';
    const fill = active ? 'fill-slate-100' : 'fill-slate-500';

    if (type === 'up') {
      return (
        <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" aria-hidden="true">
          <path className={stroke} strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" d="M4 16l6-6 4 4 6-8" />
        </svg>
      );
    }
    if (type === 'down') {
      return (
        <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" aria-hidden="true">
          <path className={stroke} strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" d="M4 8l6 6 4-4 6 8" />
        </svg>
      );
    }
    if (type === 'flatTop') {
      return (
        <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" aria-hidden="true">
          <path className={stroke} strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" d="M4 16l6-6h10" />
          <path className={stroke} strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" d="M10 10v6" />
        </svg>
      );
    }
    // base / flat line
    return (
      <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" aria-hidden="true">
        <path className={stroke} strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" d="M4 14h16" />
        <circle className={fill} cx="8" cy="14" r="1.5" />
      </svg>
    );
  };

  return (
    <div className="bg-slate-900/50 rounded-lg overflow-hidden border border-slate-700">
      {/* Subtle gradient accent at top */}
      <div className={`h-1 bg-gradient-to-r ${s.accentGradientFrom} to-transparent`} />
      
      <div className="p-4 text-center space-y-3">
        {/* Stage name (clear label) */}
        <div className="flex items-center justify-center gap-2">
          <div className={`w-2 h-2 rounded-full ${s.accentSolid}`} />
          <h3 className="text-base font-semibold text-slate-100">{s.label}</h3>
          <div className={`w-2 h-2 rounded-full ${s.accentSolid}`} />
        </div>
        
        {/* Subtitle */}
        <p className="text-xs text-slate-400 uppercase tracking-wide">Market Cycle Stage</p>

        {/* Progress cue */}
        <div className="space-y-2">
          <div className="text-xs text-slate-400">
            Stage <span className="font-semibold text-slate-200">{stage.stage}</span> of <span className="text-slate-300">4</span>
          </div>

          {/* 4-stage bar */}
          <div className="grid grid-cols-4 gap-1">
            <div className={`h-2 rounded ${getSegmentColor(1)}`} />
            <div className={`h-2 rounded ${getSegmentColor(2)}`} />
            <div className={`h-2 rounded ${getSegmentColor(3)}`} />
            <div className={`h-2 rounded ${getSegmentColor(4)}`} />
          </div>

          {/* Stage labels */}
          <div className="grid grid-cols-4 gap-2 pt-1">
            {stageOrder.map((meta, idx) => {
              const stageNum = (idx + 1) as 1 | 2 | 3 | 4;
              const isActive = stageNum === stage.stage;
              return (
                <div key={meta.label} className="flex flex-col items-center gap-1">
                  <StageIcon type={meta.icon} active={isActive} />
                  <span className={`text-[10px] leading-tight ${isActive ? 'text-slate-200' : 'text-slate-500'}`}>
                    {meta.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* One-line meaning (high clarity) */}
        <p className="text-xs text-slate-200">
          {s.meaning}
        </p>

        {/* Keep backend model label (subtle), so it’s not lost */}
        <p className="text-[10px] text-slate-500">
          Model label: {stage.stage_name}
        </p>
        
        {/* Description */}
        <p className="text-xs text-slate-300 leading-relaxed">{stage.description}</p>
        
        {/* Contributing factors (centered) */}
        {stage.contributing_factors.length > 0 && (
          <div className="flex flex-wrap gap-1 justify-center pt-1">
            {stage.contributing_factors.map((factor, idx) => (
              <span key={idx} className="text-xs px-2 py-0.5 bg-slate-700 rounded text-slate-300">
                {factor}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
