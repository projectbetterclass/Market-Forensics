'use client';

import { useState } from 'react';

interface AnalysisFormProps {
  onAnalyze: (ticker: string, dropPercent?: number, timeWindowHours?: number) => void;
  loading: boolean;
}

export default function AnalysisForm({ onAnalyze, loading }: AnalysisFormProps) {
  const [ticker, setTicker] = useState('');
  const [dropPercent, setDropPercent] = useState('');
  const [timeWindowHours, setTimeWindowHours] = useState('24');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) return;

    onAnalyze(
      ticker.toUpperCase(),
      dropPercent ? parseFloat(dropPercent) : undefined,
      timeWindowHours ? parseInt(timeWindowHours) : undefined
    );
  };

  return (
    <form onSubmit={handleSubmit} className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-8 shadow-2xl">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Ticker Input */}
        <div>
          <label htmlFor="ticker" className="block text-sm font-medium text-slate-300 mb-2">
            Ticker Symbol *
          </label>
          <input
            type="text"
            id="ticker"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="e.g., AAPL"
            className="w-full px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading}
            required
          />
        </div>

        {/* Drop Percent (Optional) */}
        <div>
          <label htmlFor="dropPercent" className="block text-sm font-medium text-slate-300 mb-2">
            Expected Drop % (Optional)
          </label>
          <input
            type="number"
            id="dropPercent"
            value={dropPercent}
            onChange={(e) => setDropPercent(e.target.value)}
            placeholder="e.g., 20"
            step="0.1"
            className="w-full px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading}
          />
        </div>

        {/* Time Window */}
        <div>
          <label htmlFor="timeWindow" className="block text-sm font-medium text-slate-300 mb-2">
            Time Window (Hours)
          </label>
          <select
            id="timeWindow"
            value={timeWindowHours}
            onChange={(e) => setTimeWindowHours(e.target.value)}
            className="w-full px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading}
          >
            <option value="6">6 hours</option>
            <option value="12">12 hours</option>
            <option value="24">24 hours</option>
            <option value="48">48 hours</option>
            <option value="72">72 hours</option>
            <option value="168">1 week</option>
          </select>
        </div>
      </div>

      {/* Submit Button */}
      <div className="mt-6">
        <button
          type="submit"
          disabled={loading || !ticker.trim()}
          className="w-full py-3 px-6 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg shadow-lg hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {loading ? 'Analyzing...' : 'Analyze Drop'}
        </button>
      </div>
    </form>
  );
}
