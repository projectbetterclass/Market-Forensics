"""
Historical Tier-1 State Database Builder.

This module builds a local database of Tier-1 indicator states over time
for the S&P 500, sampled monthly. Used for historical state matching.

Data sources (all free):
- Yahoo Finance: VIX, S&P 500 prices, moving averages, sector ETFs
- Shiller dataset: CAPE ratio (external CSV)
- FRED: GDP for Buffett indicator

The database stores:
- Date (monthly snapshots)
- Tier-1 indicator values at that date
- Forward returns (3m, 6m, 12m) from that date
- Max drawdown in forward periods
"""

import os
import json
import csv
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

import pandas as pd
import numpy as np


# Path to state database files
STATE_DB_DIR = Path(__file__).parent
STATE_DB_FILE = STATE_DB_DIR / "sp500_states.json"
METADATA_FILE = STATE_DB_DIR / "metadata.json"


class StateDBBuilder:
    """Builds and maintains the historical state database."""
    
    def __init__(self):
        self.states: List[Dict[str, Any]] = []
        self._load_existing()
    
    def _load_existing(self):
        """Load existing state database if available."""
        if STATE_DB_FILE.exists():
            with open(STATE_DB_FILE, 'r') as f:
                self.states = json.load(f)
    
    def save(self):
        """Save state database to disk."""
        with open(STATE_DB_FILE, 'w') as f:
            json.dump(self.states, f, indent=2, default=str)
        
        # Update metadata
        with open(METADATA_FILE, 'w') as f:
            json.dump({
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "num_states": len(self.states),
                "date_range": {
                    "start": self.states[0]["date"] if self.states else None,
                    "end": self.states[-1]["date"] if self.states else None
                },
                "version": "1.0"
            }, f, indent=2)
    
    async def build_from_yahoo(self, start_year: int = 2000, end_year: int = None):
        """
        Build state database from Yahoo Finance data.
        
        This fetches S&P 500 data and computes monthly state snapshots.
        Note: CAPE and Buffett Indicator require external data sources.
        """
        import httpx
        from app.config import settings
        
        if end_year is None:
            end_year = datetime.now().year
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        # Fetch S&P 500 historical data
        async with httpx.AsyncClient(timeout=60, headers=headers) as client:
            # Get max historical data
            url = f"{settings.yahoo_finance_base_url}/v8/finance/chart/^GSPC"
            params = {"range": "max", "interval": "1wk"}
            
            try:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    print(f"Failed to fetch S&P 500 data: {response.status_code}")
                    return
                
                data = response.json()
                result = data["chart"]["result"][0]
                timestamps = result["timestamp"]
                quotes = result["indicators"]["quote"][0]
                closes = quotes["close"]
                
                # Convert to DataFrame
                df = pd.DataFrame({
                    "date": [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in timestamps],
                    "close": closes
                })
                df = df.dropna()
                df = df.set_index("date")
                
                # Compute moving averages
                df["ma_50"] = df["close"].rolling(window=50, min_periods=1).mean()
                df["ma_200"] = df["close"].rolling(window=200, min_periods=1).mean()
                df["ma_50_slope"] = df["ma_50"].diff(5) / df["ma_50"].shift(5)
                df["ma_200_slope"] = df["ma_200"].diff(10) / df["ma_200"].shift(10)
                
            except Exception as e:
                print(f"Error fetching S&P 500 data: {e}")
                return
            
            # Fetch VIX data
            try:
                vix_url = f"{settings.yahoo_finance_base_url}/v8/finance/chart/^VIX"
                vix_response = await client.get(vix_url, params=params)
                
                if vix_response.status_code == 200:
                    vix_data = vix_response.json()
                    vix_result = vix_data["chart"]["result"][0]
                    vix_timestamps = vix_result["timestamp"]
                    vix_closes = vix_result["indicators"]["quote"][0]["close"]
                    
                    vix_df = pd.DataFrame({
                        "date": [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in vix_timestamps],
                        "vix": vix_closes
                    })
                    vix_df = vix_df.dropna()
                    vix_df = vix_df.set_index("date")
                    
                    # Merge VIX into main dataframe
                    df = df.join(vix_df, how="left")
                    df["vix"] = df["vix"].ffill()
                    df["vix_60d_avg"] = df["vix"].rolling(window=60, min_periods=1).mean()
                else:
                    df["vix"] = None
                    df["vix_60d_avg"] = None
            except Exception as e:
                print(f"Error fetching VIX data: {e}")
                df["vix"] = None
                df["vix_60d_avg"] = None
            
            # Fetch sector ETF data for XLY/XLP ratio
            try:
                xly_url = f"{settings.yahoo_finance_base_url}/v8/finance/chart/XLY"
                xlp_url = f"{settings.yahoo_finance_base_url}/v8/finance/chart/XLP"
                
                xly_response = await client.get(xly_url, params=params)
                xlp_response = await client.get(xlp_url, params=params)
                
                if xly_response.status_code == 200 and xlp_response.status_code == 200:
                    xly_data = xly_response.json()["chart"]["result"][0]
                    xlp_data = xlp_response.json()["chart"]["result"][0]
                    
                    xly_df = pd.DataFrame({
                        "date": [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in xly_data["timestamp"]],
                        "xly": xly_data["indicators"]["quote"][0]["close"]
                    }).dropna().set_index("date")
                    
                    xlp_df = pd.DataFrame({
                        "date": [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in xlp_data["timestamp"]],
                        "xlp": xlp_data["indicators"]["quote"][0]["close"]
                    }).dropna().set_index("date")
                    
                    df = df.join(xly_df, how="left")
                    df = df.join(xlp_df, how="left")
                    df["xly"] = df["xly"].ffill()
                    df["xlp"] = df["xlp"].ffill()
                    df["xly_xlp_ratio"] = df["xly"] / df["xlp"]
                else:
                    df["xly_xlp_ratio"] = None
            except Exception as e:
                print(f"Error fetching sector ETF data: {e}")
                df["xly_xlp_ratio"] = None
        
        # Sample monthly (last trading day of each month)
        df = df.resample("M").last()
        
        # Compute forward returns
        df["fwd_return_3m"] = df["close"].shift(-13) / df["close"] - 1  # ~3 months
        df["fwd_return_6m"] = df["close"].shift(-26) / df["close"] - 1  # ~6 months
        df["fwd_return_12m"] = df["close"].shift(-52) / df["close"] - 1  # ~12 months
        
        # Compute max drawdowns in forward periods
        # (simplified - uses close-to-close, not intraday)
        def max_drawdown(series):
            peak = series.cummax()
            drawdown = (series - peak) / peak
            return drawdown.min()
        
        # Build states
        self.states = []
        for date, row in df.iterrows():
            if pd.isna(row["close"]):
                continue
            
            # Determine regimes
            vix_regime = "unknown"
            if pd.notna(row.get("vix")):
                if row["vix"] < 15:
                    vix_regime = "low"
                elif row["vix"] < 25:
                    vix_regime = "normal"
                else:
                    vix_regime = "high"
            
            trend_regime = "unknown"
            if pd.notna(row.get("ma_200")):
                if row["close"] > row["ma_200"]:
                    trend_regime = "uptrend"
                else:
                    trend_regime = "downtrend"
            
            sector_rotation_regime = "unknown"
            if pd.notna(row.get("xly_xlp_ratio")):
                if row["xly_xlp_ratio"] > 1.1:
                    sector_rotation_regime = "risk_on"
                elif row["xly_xlp_ratio"] < 0.9:
                    sector_rotation_regime = "risk_off"
                else:
                    sector_rotation_regime = "neutral"
            
            state = {
                "date": date.isoformat(),
                "sp500_close": row["close"],
                
                # Tier-1 indicators
                "vix_level": row.get("vix") if pd.notna(row.get("vix")) else None,
                "vix_regime": vix_regime,
                "vix_vs_60d_avg": (row["vix"] / row["vix_60d_avg"]) if pd.notna(row.get("vix_60d_avg")) and row.get("vix_60d_avg") else None,
                
                "sp500_above_50ma": bool(row["close"] > row["ma_50"]) if pd.notna(row.get("ma_50")) else None,
                "sp500_above_200ma": bool(row["close"] > row["ma_200"]) if pd.notna(row.get("ma_200")) else None,
                "trend_regime": trend_regime,
                "ma_50_slope": row.get("ma_50_slope") if pd.notna(row.get("ma_50_slope")) else None,
                "ma_200_slope": row.get("ma_200_slope") if pd.notna(row.get("ma_200_slope")) else None,
                
                "xly_xlp_ratio": row.get("xly_xlp_ratio") if pd.notna(row.get("xly_xlp_ratio")) else None,
                "sector_rotation_regime": sector_rotation_regime,
                
                # Note: CAPE and Buffett require external data - set to None for now
                "cape_ratio": None,
                "cape_percentile": None,
                "buffett_indicator": None,
                "buffett_percentile": None,
                "breadth_value": None,
                "breadth_regime": "unknown",
                "leadership_concentration": None,
                "leadership_regime": "unknown",
                
                # Forward outcomes
                "outcomes": {
                    "3m": {
                        "return_pct": row["fwd_return_3m"] * 100 if pd.notna(row.get("fwd_return_3m")) else None
                    },
                    "6m": {
                        "return_pct": row["fwd_return_6m"] * 100 if pd.notna(row.get("fwd_return_6m")) else None
                    },
                    "12m": {
                        "return_pct": row["fwd_return_12m"] * 100 if pd.notna(row.get("fwd_return_12m")) else None
                    }
                }
            }
            
            self.states.append(state)
        
        # Save database
        self.save()
        print(f"Built state database with {len(self.states)} monthly snapshots")
    
    def get_states(self) -> List[Dict[str, Any]]:
        """Get all states."""
        return self.states
    
    def get_states_in_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get states within a date range."""
        result = []
        for state in self.states:
            state_date = datetime.fromisoformat(state["date"])
            if start_date <= state_date <= end_date:
                result.append(state)
        return result


# Singleton instance
_builder_instance: Optional[StateDBBuilder] = None


def get_state_db_builder() -> StateDBBuilder:
    """Get or create the state database builder instance."""
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = StateDBBuilder()
    return _builder_instance


async def rebuild_state_db():
    """Rebuild the entire state database."""
    builder = get_state_db_builder()
    await builder.build_from_yahoo()
    return builder.get_states()
