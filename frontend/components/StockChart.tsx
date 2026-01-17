'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, IChartApi, ISeriesApi, UTCTimestamp, LineStyle, ColorType } from 'lightweight-charts';

interface StockChartProps {
  ticker: string;
  data: Array<{
    time: string;
    value: number;
  }>;
  onPointsSelected: (startDate: Date, endDate: Date) => void;
  onRangeChange?: (range: string) => void;
}

// Store time/price values (not pixel coords) so we can recalculate on pan/zoom
interface SelectionPoint {
  date: Date;
  price: number;
  time: UTCTimestamp; // Store the UTC timestamp for coordinate conversion
}

interface SelectionStats {
  priceChange: number;
  percentChange: number;
  bars: number;
}

interface SelectionBoxState {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  stats: SelectionStats;
  isPositive: boolean;
}

export default function StockChart({ ticker, data, onPointsSelected, onRangeChange }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const lineSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  
  const [selectedPoints, setSelectedPoints] = useState<SelectionPoint[]>([]);
  const [selectedRange, setSelectedRange] = useState<string>('max');
  const [hoverPoint, setHoverPoint] = useState<SelectionPoint | null>(null);
  const [selectionBox, setSelectionBox] = useState<SelectionBoxState | null>(null);
  
  // Counter to trigger re-render when chart view changes
  const [viewUpdateCounter, setViewUpdateCounter] = useState(0);

  // Calculate selection statistics
  const calculateStats = useCallback((point1: SelectionPoint, point2: SelectionPoint): SelectionStats => {
    const [start, end] = [point1, point2].sort((a, b) => a.date.getTime() - b.date.getTime());
    const priceChange = end.price - start.price;
    const percentChange = ((end.price - start.price) / start.price) * 100;
    
    // Count bars between the two dates
    const startTime = start.date.getTime();
    const endTime = end.date.getTime();
    const bars = data.filter(d => {
      const t = new Date(d.time).getTime();
      return t >= startTime && t <= endTime;
    }).length;

    return { priceChange, percentChange, bars };
  }, [data]);

  // Convert time/price to pixel coordinates using the chart's current view
  const getPixelCoordinates = useCallback((point: SelectionPoint): { x: number; y: number } | null => {
    if (!chartRef.current || !lineSeriesRef.current) return null;
    
    const timeScale = chartRef.current.timeScale();
    const x = timeScale.timeToCoordinate(point.time);
    const y = lineSeriesRef.current.priceToCoordinate(point.price);
    
    if (x === null || y === null) return null;
    return { x, y };
  }, []);

  // Update selection box - recalculates pixel positions from time/price
  useEffect(() => {
    const hasFirstPoint = selectedPoints.length >= 1;
    const hasSecondPoint = selectedPoints.length === 2;
    
    if (hasFirstPoint && chartRef.current && lineSeriesRef.current) {
      const p1 = selectedPoints[0];
      const p2 = hasSecondPoint ? selectedPoints[1] : hoverPoint;
      
      // Get pixel coordinates for first point
      const coords1 = getPixelCoordinates(p1);
      if (!coords1) {
        setSelectionBox(null);
        return;
      }
      
      if (!p2) {
        // Show initial state with just first point
        setSelectionBox({
          x1: coords1.x,
          y1: coords1.y,
          x2: coords1.x,
          y2: coords1.y,
          stats: { priceChange: 0, percentChange: 0, bars: 0 },
          isPositive: true,
        });
        return;
      }
      
      // Get pixel coordinates for second point
      const coords2 = getPixelCoordinates(p2);
      if (!coords2) {
        setSelectionBox(null);
        return;
      }
      
      const stats = calculateStats(p1, p2);
      const isPositive = stats.percentChange >= 0;
      
      setSelectionBox({
        x1: coords1.x,
        y1: coords1.y,
        x2: coords2.x,
        y2: coords2.y,
        stats,
        isPositive,
      });
    } else {
      setSelectionBox(null);
    }
  }, [selectedPoints, hoverPoint, calculateStats, getPixelCoordinates, viewUpdateCounter]);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { type: ColorType.Solid, color: '#0f172a' },
        textColor: '#cbd5e1',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
      },
      rightPriceScale: {
        borderColor: '#334155',
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#6366f1',
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: '#6366f1',
        },
        horzLine: {
          color: '#6366f1',
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: '#6366f1',
        },
      },
    });

    chartRef.current = chart;

    const lineSeries = chart.addLineSeries({
      color: '#eab308',
      lineWidth: 2,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 6,
      crosshairMarkerBorderColor: '#ffffff',
      crosshairMarkerBackgroundColor: '#eab308',
    });

    lineSeriesRef.current = lineSeries;

    const chartData = data.map(d => ({
      time: (new Date(d.time).getTime() / 1000) as UTCTimestamp,
      value: d.value,
    }));

    lineSeries.setData(chartData);
    chart.timeScale().fitContent();

    // Subscribe to visible time range changes to update selection overlay positions
    chart.timeScale().subscribeVisibleTimeRangeChange(() => {
      // Trigger re-render of selection box with updated coordinates
      setViewUpdateCounter(c => c + 1);
    });

    // Track crosshair movement for dynamic selection preview
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.point) {
        return;
      }
      
      // Don't update hover if selection is complete (2 points selected)
      setSelectedPoints(currentPoints => {
        if (currentPoints.length >= 2) {
          // Selection is locked, don't update hover
          return currentPoints;
        }
        
        const hoverDate = new Date((param.time as number) * 1000);
        const seriesData = param.seriesData.get(lineSeries);
        const price = seriesData && 'value' in seriesData ? seriesData.value : 0;
        
        setHoverPoint({
          date: hoverDate,
          price: price as number,
          time: param.time as UTCTimestamp,
        });
        
        return currentPoints;
      });
    });

    chart.subscribeClick((param) => {
      if (!param.time || !param.point) return;

      const clickedDate = new Date((param.time as number) * 1000);
      
      // Get price at this point
      const seriesData = param.seriesData.get(lineSeries);
      const price = seriesData && 'value' in seriesData ? seriesData.value : 0;
      
      const newPoint: SelectionPoint = {
        date: clickedDate,
        price: price as number,
        time: param.time as UTCTimestamp,
      };
      
      setSelectedPoints(prev => {
        // If already have 2 points, ignore the click (selection is locked)
        if (prev.length >= 2) {
          return prev;
        }
        
        const newPoints = [...prev, newPoint];
        
        if (newPoints.length === 2) {
          const [start, end] = newPoints
            .map(p => p.date)
            .sort((a, b) => a.getTime() - b.getTime());
          
          // Clear hover point when selection is complete
          setHoverPoint(null);
          
          // Delay the callback slightly so the selection box renders first
          setTimeout(() => {
            onPointsSelected(start, end);
          }, 1500);
          
          return newPoints;
        }
        
        return newPoints;
      });
    });

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
        // Reset selection on resize since coordinates change
        setSelectedPoints([]);
        setHoverPoint(null);
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, onPointsSelected]);

  const handleRangeSelect = (range: string) => {
    setSelectedRange(range);
    setSelectedPoints([]);
    setHoverPoint(null);
    if (onRangeChange) {
      onRangeChange(range);
    }
  };

  const resetSelection = () => {
    setSelectedPoints([]);
    setSelectionBox(null);
    setHoverPoint(null);
  };

  return (
    <div className="space-y-4">
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-lg p-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-200 mb-1">
              {ticker} - Historical Price
            </h3>
            <p className="text-sm text-slate-400">
              {selectedPoints.length === 0 && 'Click on the chart to select the START of the period'}
              {selectedPoints.length === 1 && 'Now click to select the END of the period'}
              {selectedPoints.length === 2 && 'Selection complete — click "Reset Selection" to choose new points'}
            </p>
          </div>
          
          <div className="flex gap-2">
            {['1y', '5y', '10y', 'max'].map(range => (
              <button
                key={range}
                onClick={() => handleRangeSelect(range)}
                className={`px-3 py-1 rounded transition-colors ${
                  selectedRange === range
                    ? 'bg-blue-500 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {range.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        
        {selectedPoints.length >= 1 && (
          <div className="mt-3 flex items-center gap-4">
            <span className="text-sm text-blue-400">
              ✓ Start: {selectedPoints[0].date.toLocaleDateString()} @ ${selectedPoints[0].price.toFixed(2)}
            </span>
            {selectedPoints.length === 2 && (
              <span className="text-sm text-purple-400">
                ✓ End: {selectedPoints[1].date.toLocaleDateString()} @ ${selectedPoints[1].price.toFixed(2)}
              </span>
            )}
          </div>
        )}
        
        {selectedPoints.length > 0 && (
          <button
            onClick={resetSelection}
            className="mt-3 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors text-sm"
          >
            Reset Selection
          </button>
        )}
      </div>

      {/* Chart Container with Selection Overlay */}
      <div className="relative" style={{ zIndex: 1 }}>
        <div 
          ref={chartContainerRef} 
          className="bg-slate-950 rounded-lg border border-slate-700 [&_a]:hidden [&_a]:!hidden"
          style={{ cursor: selectedPoints.length >= 2 ? 'not-allowed' : 'crosshair' }}
        />
        {/* Hide TradingView watermark */}
        <style jsx global>{`
          .tv-lightweight-charts a,
          [class*="chart"] a[href*="tradingview"],
          a[target="_blank"][href*="tradingview"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
          }
        `}</style>
        
        {/* Selection Box Overlay */}
        {selectionBox && (
          <>
            {/* Selection Rectangle - color based on positive/negative */}
            <div
              className={`absolute pointer-events-none border-2 ${
                selectionBox.isPositive ? 'border-green-500' : 'border-red-500'
              }`}
              style={{
                left: Math.min(selectionBox.x1, selectionBox.x2),
                top: Math.min(selectionBox.y1, selectionBox.y2),
                width: Math.max(Math.abs(selectionBox.x2 - selectionBox.x1), 2),
                height: Math.max(Math.abs(selectionBox.y2 - selectionBox.y1), 50),
                background: selectionBox.isPositive 
                  ? 'rgba(34, 197, 94, 0.15)' 
                  : 'rgba(239, 68, 68, 0.15)',
                borderStyle: 'dashed',
                zIndex: 100,
              }}
            />
            
            {/* Stats Tooltip - background color based on positive/negative */}
            <div
              className={`absolute pointer-events-none rounded-lg px-4 py-3 shadow-xl border ${
                selectionBox.isPositive 
                  ? 'bg-green-900/95 border-green-600' 
                  : 'bg-red-900/95 border-red-600'
              }`}
              style={{
                right: 20,
                top: 20,
                minWidth: '180px',
                zIndex: 200,
              }}
            >
              <div className="flex flex-col gap-1 text-sm font-mono">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-slate-300 text-xs">Change:</span>
                  <span className={`font-bold ${selectionBox.isPositive ? 'text-green-300' : 'text-red-300'}`}>
                    {selectionBox.stats.priceChange >= 0 ? '+' : ''}${selectionBox.stats.priceChange.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-slate-300 text-xs">Percent:</span>
                  <span className={`font-bold text-lg ${selectionBox.isPositive ? 'text-green-300' : 'text-red-300'}`}>
                    {selectionBox.stats.percentChange >= 0 ? '+' : ''}{selectionBox.stats.percentChange.toFixed(2)}%
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4 border-t border-slate-600 pt-1 mt-1">
                  <span className="text-slate-400 text-xs">Bars:</span>
                  <span className="text-slate-300">{selectionBox.stats.bars}</span>
                </div>
              </div>
              {selectedPoints.length < 2 ? (
                <div className="text-xs text-slate-400 mt-2 text-center italic">
                  Click to confirm end point
                </div>
              ) : (
                <div className="text-xs text-green-400 mt-2 text-center font-semibold">
                  ✓ Selection locked
                </div>
              )}
            </div>

            {/* Start point vertical line */}
            <div
              className="absolute pointer-events-none w-0.5"
              style={{
                left: selectionBox.x1,
                top: 0,
                height: '100%',
                background: selectionBox.isPositive ? '#22c55e' : '#ef4444',
                opacity: 0.8,
                zIndex: 50,
              }}
            />
            
            {/* End point / hover vertical line */}
            {(selectedPoints.length === 2 || hoverPoint) && (
              <div
                className="absolute pointer-events-none w-0.5"
                style={{
                  left: selectionBox.x2,
                  top: 0,
                  height: '100%',
                  background: selectionBox.isPositive ? '#22c55e' : '#ef4444',
                  opacity: selectedPoints.length === 2 ? 0.8 : 0.5,
                  zIndex: 50,
                }}
              />
            )}
          </>
        )}

      </div>

      <div className="flex items-center justify-center gap-6 text-sm text-slate-400">
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-yellow-500"></div>
          <span>Price History</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-green-500 border-dashed bg-green-500/20"></div>
          <span>Gain</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-red-500 border-dashed bg-red-500/20"></div>
          <span>Loss</span>
        </div>
      </div>
      
      <div className="text-center text-sm text-slate-500">
        Showing {data.length.toLocaleString()} data points • Range: {selectedRange.toUpperCase()}
      </div>
    </div>
  );
}
