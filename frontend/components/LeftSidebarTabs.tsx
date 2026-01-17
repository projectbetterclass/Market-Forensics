'use client';

import { useState } from 'react';
import { MarketStateVector, TickerPatternMatch } from '@/lib/api';
import MarketStatePanel from './MarketStatePanel';
import SimilarPatternsPanel from './SimilarPatternsPanel';

interface LeftSidebarTabsProps {
  marketState?: MarketStateVector;
  ticker: string;
  startDate?: string;
  endDate?: string;
  similarPatterns?: TickerPatternMatch[];
}

export default function LeftSidebarTabs({
  marketState,
  ticker,
  startDate,
  endDate,
  similarPatterns = []
}: LeftSidebarTabsProps) {
  const [activeTab, setActiveTab] = useState<'patterns' | 'market'>('patterns');

  return (
    <div className="w-80 flex flex-col h-fit sticky top-4">
      {/* Tab Headers */}
      <div className="flex bg-slate-800/50 border border-slate-700 rounded-t-lg overflow-hidden">
        <button
          onClick={() => setActiveTab('patterns')}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'patterns'
              ? 'bg-slate-700 text-slate-100'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
          }`}
        >
          Similar Patterns
          {similarPatterns.length > 0 && (
            <span className="ml-2 text-xs bg-blue-600 text-white px-1.5 py-0.5 rounded">
              {similarPatterns.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('market')}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'market'
              ? 'bg-slate-700 text-slate-100'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
          }`}
        >
          Market State
        </button>
      </div>

      {/* Tab Content */}
      <div className="bg-slate-800/50 border-l border-r border-b border-slate-700 rounded-b-lg">
        {activeTab === 'patterns' && similarPatterns.length > 0 && (
          <div className="p-4">
            <SimilarPatternsPanel matches={similarPatterns} ticker={ticker} />
          </div>
        )}
        
        {activeTab === 'patterns' && similarPatterns.length === 0 && (
          <div className="p-8 text-center text-slate-400 text-sm">
            <p className="mb-2">No similar patterns found yet.</p>
            <p className="text-xs text-slate-500">
              Select a date range on the chart to find similar price movements.
            </p>
          </div>
        )}
        
        {activeTab === 'market' && marketState && startDate && endDate && (
          <div className="p-4">
            <MarketStatePanel
              marketState={marketState}
              ticker={ticker}
              startDate={startDate}
              endDate={endDate}
            />
          </div>
        )}
        
        {activeTab === 'market' && (!marketState || !startDate || !endDate) && (
          <div className="p-8 text-center text-slate-400 text-sm">
            <p>Market state data not available yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}
