'use client';

import { useState, useEffect } from 'react';
import { api, ChartDataPoint, AnalysisFullResponse } from '@/lib/api';
import TickerSearch from '@/components/TickerSearch';
import StockChart from '@/components/StockChart';
import ResultView from '@/components/ResultView';
import ContextPanels from '@/components/ContextPanels';
import PatternAnalogs from '@/components/PatternAnalogs';
import Tier1Sidebar from '@/components/Tier1Sidebar';
import LeftSidebarTabs from '@/components/LeftSidebarTabs';

export default function Home() {
  const [ticker, setTicker] = useState<string>('');
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [selectedRange, setSelectedRange] = useState<string>('max');
  const [loading, setLoading] = useState<boolean>(false);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [result, setResult] = useState<AnalysisFullResponse | null>(null);
  const [showOnboarding, setShowOnboarding] = useState<boolean>(true);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');

  // Check backend health on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await api.healthCheck();
        setBackendStatus('connected');
      } catch (err) {
        console.error('Backend health check failed:', err);
        setBackendStatus('disconnected');
      }
    };
    checkBackend();
  }, []);

  const handleTickerSelect = async (selectedTicker: string) => {
    setTicker(selectedTicker);
    setError('');
    setResult(null);
    await loadChartData(selectedTicker, selectedRange);
  };

  const loadChartData = async (ticker: string, range: string) => {
    setLoading(true);
    setError('');
    
    try {
      const data = await api.getChartData(ticker, range, '1d');
      setChartData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load chart data');
      setChartData([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRangeChange = (range: string) => {
    setSelectedRange(range);
    if (ticker) {
      loadChartData(ticker, range);
    }
  };

  const handlePointsSelected = async (startDate: Date, endDate: Date) => {
    if (!ticker) return;
    
    setAnalyzing(true);
    setError('');
    
    try {
      const analysisResult = await api.analyzeByDateRange({
        ticker,
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString()
      });
      
      setResult(analysisResult);
      
      // Scroll to results
      setTimeout(() => {
        document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze stock drop');
      setResult(null);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 py-6 px-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-slate-100 mb-2">
            Market Forensics
          </h1>
          <p className="text-slate-400">
            Prepare, don't predict. Recognize patterns. Understand context.
          </p>
        </div>
      </header>

      {/* Backend Status Banner */}
      {backendStatus === 'disconnected' && (
        <div className="bg-red-900/30 border-b border-red-700 px-4 py-3">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 text-red-400 text-xl mt-0.5">⚠️</div>
              <div className="flex-1">
                <p className="font-semibold text-red-200 mb-1">Backend Disconnected</p>
                <p className="text-red-300 text-sm mb-2">
                  The backend server is not running on port 8000. Start it to use the application.
                </p>
                <div className="bg-slate-900/50 rounded p-3 font-mono text-xs text-slate-300">
                  <div className="text-slate-400 mb-1"># In PowerShell, navigate to the backend folder:</div>
                  <div className="text-green-400">cd backend</div>
                  <div className="text-green-400">.\venv\Scripts\Activate.ps1</div>
                  <div className="text-green-400">python -m app.main</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {backendStatus === 'connected' && (
        <div className="bg-green-900/20 border-b border-green-700/30 px-4 py-2">
          <div className="max-w-7xl mx-auto">
            <div className="flex items-center gap-2 text-green-400 text-sm">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span>Backend Connected</span>
            </div>
          </div>
        </div>
      )}

      {/* Onboarding Modal */}
      {showOnboarding && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-8 max-w-2xl">
            <h2 className="text-2xl font-bold text-slate-100 mb-4">Welcome</h2>
            <div className="space-y-4 text-slate-300">
              <p>
                <strong className="text-blue-400">This tool helps you recognize historical patterns, risk regimes, and behavioral signals.</strong>
              </p>
              <p>
                It does <strong>not</strong> predict market direction or recommend actions.
              </p>
              <p className="text-sm text-slate-400 bg-slate-900/50 p-3 rounded border border-slate-700">
                💡 <strong>Important:</strong> Most investors don't lose their wealth during crashes - they lose it in the months before, due to overconfidence, leverage, and poor timing. This tool helps you recognize risk, not chase returns.
              </p>
            </div>
            <button
              onClick={() => setShowOnboarding(false)}
              className="mt-6 w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg transition-colors"
            >
              I Understand
            </button>
          </div>
        </div>
      )}

      {/* Three-Column Layout: Left Sidebar + Main Content + Tier-1 Sidebar */}
      <div className="max-w-screen-2xl mx-auto">
        <div className="flex gap-4">
          {/* Main Content Area */}
          <main className="flex-1 py-8 px-4 space-y-8">
          {/* Search */}
          <div className="flex justify-center lg:justify-start">
            <TickerSearch onSelect={handleTickerSelect} />
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
              <p className="mt-4 text-slate-400">Loading chart data...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
              <p className="text-red-200">{error}</p>
            </div>
          )}

          {/* Chart with left sidebar */}
          {!loading && chartData.length > 0 && (
            <div className="flex gap-4">
              {/* Left Sidebar - Always visible on desktop */}
              <div className="hidden lg:block flex-shrink-0">
                <LeftSidebarTabs
                  marketState={result?.agent_contract?.market_state}
                  ticker={ticker}
                  startDate={result?.agent_contract?.period.start_date}
                  endDate={result?.agent_contract?.period.end_date}
                  similarPatterns={result?.agent_contract?.similar_patterns || []}
                />
              </div>
              
              {/* Chart */}
              <div className="flex-1 min-w-0">
                <StockChart
                  ticker={ticker}
                  data={chartData}
                  onPointsSelected={handlePointsSelected}
                  onRangeChange={handleRangeChange}
                />
              </div>
            </div>
          )}

          {/* Analyzing State */}
          {analyzing && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
              <p className="mt-4 text-slate-400">Analyzing price movement...</p>
              <p className="text-sm text-slate-500 mt-2">Retrieving evidence from SEC, news, macro sources</p>
            </div>
          )}

          {/* Results */}
          {result && (
            <div id="results" className="space-y-8">
              <ResultView result={result} ticker={ticker} />
              
              {/* Context Panels (only keep Sector Rotation) */}
              <ContextPanels rotation={result.rotation} />
              
              {/* Pattern Analogs */}
              {result.pattern_analogs && result.pattern_analogs.length > 0 && (
                <PatternAnalogs analogs={result.pattern_analogs} />
              )}
            </div>
          )}

          {/* Empty State */}
          {!loading && !analyzing && !result && ticker === '' && !error && (
            <div className="text-center py-16">
              <p className="text-slate-400 text-lg">
                Select a ticker to get started
              </p>
            </div>
          )}

          {/* Footer */}
          <footer className="border-t border-slate-700 py-6 mt-16">
            <div className="text-center text-slate-400 text-sm">
              <p>
                This analysis is provided for educational and informational purposes only. It does not constitute financial advice.
              </p>
              <p className="mt-2">
                Data sources: Yahoo Finance, SEC EDGAR, GDELT, FRED
              </p>
            </div>
          </footer>
          </main>

          {/* Tier-1 Sidebar (always visible on desktop, collapsible on mobile) */}
          <aside className="hidden lg:block flex-shrink-0">
            <Tier1Sidebar market="^GSPC" />
          </aside>
        </div>
      </div>

      {/* Mobile Tier-1 Sidebar (renders its own toggle button) */}
      <div className="lg:hidden">
        <Tier1Sidebar market="^GSPC" />
      </div>
    </div>
  );
}
