'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, IChartApi, ISeriesApi, LineData, Time } from 'lightweight-charts';
import { api, ChartDataPoint } from '@/lib/api';

interface HistoricalMiniChartProps {
  startDate: string;
  endDate: string;
  ticker: string;
}

interface SelectionBox {
  left: number;
  width: number;
  priceChange: number;
}

export default function HistoricalMiniChart({ startDate, endDate, ticker }: HistoricalMiniChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const lineSeriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [selectionBox, setSelectionBox] = useState<SelectionBox | null>(null);

  // Calculate selection box position for exact start/end dates
  const updateSelectionBox = useCallback(() => {
    if (!chartRef.current || !lineSeriesRef.current || data.length === 0) return;

    const chart = chartRef.current;
    const timeScale = chart.timeScale();
    
    // Find indices for start and end dates
    const startIdx = data.findIndex(d => d.time >= startDate.split('T')[0]);
    const endIdx = data.findIndex(d => d.time >= endDate.split('T')[0]);
    
    if (startIdx < 0 || endIdx < 0) return;

    const startTime = data[startIdx].time as Time;
    const endTime = data[endIdx].time as Time;
    
    // Get pixel positions
    const startX = timeScale.timeToCoordinate(startTime);
    const endX = timeScale.timeToCoordinate(endTime);
    
    if (startX === null || endX === null) return;

    // Calculate price change within this exact window
    const startPrice = data[startIdx].value;
    const endPrice = data[endIdx].value;
    const change = ((endPrice - startPrice) / startPrice) * 100;

    setSelectionBox({
      left: Math.min(startX, endX),
      width: Math.abs(endX - startX),
      priceChange: change
    });
  }, [data, startDate, endDate]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Calculate date range: include buffer before/after for context
        const startDateObj = new Date(startDate);
        const endDateObj = new Date(endDate);
        const bufferStart = new Date(startDateObj);
        bufferStart.setMonth(bufferStart.getMonth() - 2);
        const bufferEnd = new Date(endDateObj);
        bufferEnd.setMonth(bufferEnd.getMonth() + 2);

        // Fetch chart data for this period
        const chartData = await api.getChartData(
          ticker,
          bufferStart.toISOString().split('T')[0],
          bufferEnd.toISOString().split('T')[0]
        );
        
        if (!chartData || chartData.length === 0) {
          throw new Error('No data available for this period');
        }
        
        setData(chartData);
      } catch (err: any) {
        console.error('HistoricalMiniChart error:', err);
        setError(err.message || 'Failed to load historical data');
      } finally {
        setLoading(false);
      }
    };

    if (ticker && startDate && endDate) {
      fetchData();
    }
  }, [startDate, endDate, ticker]);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    // Clean up previous chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      lineSeriesRef.current = null;
    }

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 160,
      layout: {
        background: { color: 'transparent' },
        textColor: '#94a3b8',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: 'rgba(51, 65, 85, 0.3)' },
        horzLines: { color: 'rgba(51, 65, 85, 0.3)' },
      },
      rightPriceScale: {
        borderColor: 'rgba(51, 65, 85, 0.5)',
        scaleMargins: { top: 0.15, bottom: 0.15 },
      },
      timeScale: {
        borderColor: 'rgba(51, 65, 85, 0.5)',
        timeVisible: false,
        tickMarkFormatter: (time: Time) => {
          const date = new Date(time as string);
          return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        },
      },
      crosshair: {
        vertLine: { visible: false },
        horzLine: { visible: false },
      },
      handleScroll: false,
      handleScale: false,
    });

    chartRef.current = chart;

    // Add area series
    const lineSeries = chart.addAreaSeries({
      lineColor: '#64748b',
      topColor: 'rgba(100, 116, 139, 0.2)',
      bottomColor: 'rgba(100, 116, 139, 0.02)',
      lineWidth: 2,
    });

    lineSeriesRef.current = lineSeries;

    // Convert data
    const chartData: LineData[] = data.map(d => ({
      time: d.time as Time,
      value: d.value,
    }));

    lineSeries.setData(chartData);

    // Fit content
    chart.timeScale().fitContent();

    // Update selection box after chart is ready
    setTimeout(updateSelectionBox, 100);

    // Update selection box on time scale changes
    chart.timeScale().subscribeVisibleTimeRangeChange(updateSelectionBox);

    // Cleanup
    return () => {
      chart.timeScale().unsubscribeVisibleTimeRangeChange(updateSelectionBox);
      chart.remove();
      chartRef.current = null;
      lineSeriesRef.current = null;
    };
  }, [data, updateSelectionBox]);

  if (loading) {
    return (
      <div className="h-[160px] flex items-center justify-center bg-slate-900/30 rounded">
        <div className="text-xs text-slate-500">Loading {ticker} chart...</div>
      </div>
    );
  }

  if (error || data.length === 0) {
    return (
      <div className="h-[160px] flex items-center justify-center bg-slate-900/30 rounded border border-slate-700">
        <div className="text-center">
          <div className="text-xs text-slate-500 mb-1">{error || `No historical data for ${ticker}`}</div>
          <div className="text-[10px] text-slate-600">
            {new Date(startDate).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
          </div>
        </div>
      </div>
    );
  }

  const isPositive = selectionBox ? selectionBox.priceChange >= 0 : true;

  return (
    <div className="relative">
      <div ref={chartContainerRef} className="w-full" />
      
      {/* Selection Box Overlay - Exact dates */}
      {selectionBox && (
        <>
          {/* Highlighted region box */}
          <div
            className={`absolute pointer-events-none border-2 ${
              isPositive ? 'border-green-500' : 'border-red-500'
            }`}
            style={{
              left: selectionBox.left,
              top: 0,
              width: Math.max(selectionBox.width, 4),
              height: '100%',
              background: isPositive
                ? 'rgba(34, 197, 94, 0.15)'
                : 'rgba(239, 68, 68, 0.15)',
              borderStyle: 'dashed',
              zIndex: 10,
            }}
          />
          
          {/* Left vertical line */}
          <div
            className={`absolute pointer-events-none w-0.5 ${
              isPositive ? 'bg-green-500' : 'bg-red-500'
            }`}
            style={{
              left: selectionBox.left,
              top: 0,
              height: '100%',
              zIndex: 11,
            }}
          />
          
          {/* Right vertical line */}
          <div
            className={`absolute pointer-events-none w-0.5 ${
              isPositive ? 'bg-green-500' : 'bg-red-500'
            }`}
            style={{
              left: selectionBox.left + selectionBox.width,
              top: 0,
              height: '100%',
              zIndex: 11,
            }}
          />
        </>
      )}
      
      {/* Labels */}
      <div className="absolute top-1 left-1 flex items-center gap-1 z-20">
        <span className="text-[10px] text-slate-400 bg-slate-900/90 px-1.5 py-0.5 rounded">
          {ticker}
        </span>
        {selectionBox && (
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
            selectionBox.priceChange >= 0 
              ? 'bg-green-900/90 text-green-400' 
              : 'bg-red-900/90 text-red-400'
          }`}>
            {selectionBox.priceChange >= 0 ? '+' : ''}{selectionBox.priceChange.toFixed(1)}%
          </span>
        )}
      </div>
      
      <div className="absolute bottom-1 right-1 text-[9px] text-slate-500 bg-slate-900/90 px-1 rounded z-20">
        {new Date(startDate).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
      </div>
    </div>
  );
}
