'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';

const AsyncSelect = dynamic(() => import('react-select/async'), { ssr: false });

interface TickerSearchProps {
  onSelect: (ticker: string) => void;
}

const popularTickers = [
  { value: 'AAPL', label: 'AAPL - Apple Inc.' },
  { value: 'MSFT', label: 'MSFT - Microsoft Corporation' },
  { value: 'GOOGL', label: 'GOOGL - Alphabet Inc.' },
  { value: 'AMZN', label: 'AMZN - Amazon.com Inc.' },
  { value: 'TSLA', label: 'TSLA - Tesla Inc.' },
  { value: 'META', label: 'META - Meta Platforms Inc.' },
  { value: 'NVDA', label: 'NVDA - NVIDIA Corporation' },
  { value: 'JPM', label: 'JPM - JPMorgan Chase & Co.' },
  { value: 'V', label: 'V - Visa Inc.' },
  { value: 'WMT', label: 'WMT - Walmart Inc.' },
  { value: 'SPY', label: 'SPY - SPDR S&P 500 ETF Trust (ETF)' },
  { value: 'QQQ', label: 'QQQ - Invesco QQQ Trust (ETF)' },
];

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function TickerSearch({ onSelect }: TickerSearchProps) {
  const [selectedOption, setSelectedOption] = useState<any>(null);

  const loadOptions = async (inputValue: string) => {
    if (!inputValue || inputValue.length < 1) {
      return popularTickers;
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/symbols/search?q=${encodeURIComponent(inputValue)}&limit=20`
      );
      
      if (!response.ok) {
        console.error('Failed to fetch symbols');
        return popularTickers;
      }

      const results = await response.json();
      return results;
    } catch (error) {
      console.error('Error searching symbols:', error);
      return popularTickers;
    }
  };

  const handleChange = (option: any) => {
    setSelectedOption(option);
    if (option) {
      onSelect(option.value);
    }
  };

  return (
    <div className="w-full max-w-md">
      <AsyncSelect
        value={selectedOption}
        onChange={handleChange}
        loadOptions={loadOptions}
        defaultOptions={popularTickers}
        placeholder="Search ticker or company..."
        className="react-select-container"
        classNamePrefix="react-select"
        cacheOptions
        styles={{
          control: (base) => ({
            ...base,
            backgroundColor: '#1e293b',
            borderColor: '#475569',
            '&:hover': {
              borderColor: '#64748b'
            }
          }),
          menu: (base) => ({
            ...base,
            backgroundColor: '#1e293b',
            border: '1px solid #475569'
          }),
          option: (base, state) => ({
            ...base,
            backgroundColor: state.isFocused ? '#334155' : '#1e293b',
            color: '#cbd5e1',
            '&:active': {
              backgroundColor: '#475569'
            }
          }),
          singleValue: (base) => ({
            ...base,
            color: '#cbd5e1'
          }),
          input: (base) => ({
            ...base,
            color: '#cbd5e1'
          }),
          placeholder: (base) => ({
            ...base,
            color: '#94a3b8'
          }),
          loadingMessage: (base) => ({
            ...base,
            color: '#94a3b8'
          }),
          noOptionsMessage: (base) => ({
            ...base,
            color: '#94a3b8'
          })
        }}
      />
    </div>
  );
}
