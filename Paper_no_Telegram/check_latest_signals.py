#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Latest Signal Checker
=====================

This script checks for fresh/latest signals from indicators for the trading bot.
It analyzes real-time market data and identifies CE/PE entry opportunities.

Usage:
    python check_latest_signals.py
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import traceback
from collections import defaultdict

# Import required modules
try:
    from Dhan_Tradehull_V3 import Tradehull
    import talib
    import pandas_ta as pta
    from VWAP import calculate_vwap_daily
    from ATRTrailingStop import ATRTrailingStopIndicator
    import Fractal_Chaos_Bands
    from ce_entry_logic import check_ce_entry_conditions
    from pe_entry_logic import check_pe_entry_conditions
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Import Error: {e}")
    print("Please ensure all required modules are available.")
    sys.exit(1)


# ==========================================
# CONFIGURATION
# ==========================================

# Default watchlist - modify as needed
DEFAULT_WATCHLIST = [
    "RELIANCE", "TATASTEEL", "INFY", "SBIN", "HDFCBANK",
    "ICICIBANK", "TCS", "WIPRO", "LT", "AXISBANK"
]

# Credentials (replace with your own)
CLIENT_CODE = "1106090196"
TOKEN_ID = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzYwMDcwNDg1LCJpYXQiOjE3NTk5ODQwODUsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.XKcfhAj9zzhYe-48SzIqYdyMETwJyRrxnfI-M9X0gtzV3EenqWOvq_8jFfK9WhPguZvmacGhFba8HD7nsRFPeQ"


# ==========================================
# INDICATOR CALCULATION
# ==========================================

def calculate_all_indicators(chart_data):
    """
    Calculate all required indicators for entry logic

    Args:
        chart_data: DataFrame with OHLCV data

    Returns:
        DataFrame with all indicators added
    """
    try:
        df = chart_data.copy()

        # 1. VWAP
        df['vwap'] = calculate_vwap_daily(
            df['high'], df['low'], df['close'],
            df['volume'], df['timestamp']
        )

        # 2. RSI
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)

        # 3. MA of RSI
        df['ma_rsi'] = talib.SMA(df['rsi'], timeperiod=20)

        # 4. Moving Average
        df['ma'] = pta.sma(df['close'], length=12)

        # 5. PSAR (Parabolic SAR)
        para = pta.psar(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            step=0.05,
            max_step=0.2
        )
        df['PSARl_0.02_0.2'] = para['PSARl_0.02_0.2']
        df['PSARs_0.02_0.2'] = para['PSARs_0.02_0.2']
        df['PSARaf_0.02_0.2'] = para['PSARaf_0.02_0.2']
        df['PSARr_0.02_0.2'] = para['PSARr_0.02_0.2']

        # 6. ATR Trailing Stop
        atr_strategy = ATRTrailingStopIndicator(period=21, multiplier=1.0)
        result_df = atr_strategy.compute_indicator(df)
        df['TR'] = result_df['TR']
        df['ATR'] = result_df['ATR']
        df['Long_Stop'] = result_df['Long_Stop']
        df['Short_Stop'] = result_df['Short_Stop']
        df['Stop_Loss'] = result_df['Stop_Loss']
        df['Position'] = result_df['Position']
        df['Stop_Distance'] = result_df['Stop_Distance']

        # 7. Fractal Chaos Bands
        df_with_bands = Fractal_Chaos_Bands.fractal_chaos_bands(df)
        df_with_signals = Fractal_Chaos_Bands.get_fcb_signals(df_with_bands)
        df['fractal_high'] = df_with_signals['fractal_high']
        df['fractal_low'] = df_with_signals['fractal_low']
        df['signal'] = df_with_signals['signal']

        return df

    except Exception as e:
        print(f"Error calculating indicators: {e}")
        traceback.print_exc()
        return None


# ==========================================
# SIGNAL CHECKING
# ==========================================

def check_signals_for_stock(tsl, stock, orderbook):
    """
    Check for CE and PE signals for a specific stock

    Args:
        tsl: Tradehull instance
        stock: Stock symbol
        orderbook: Order tracking dictionary

    Returns:
        dict with signal information
    """
    try:
        # Fetch historical data
        chart = tsl.get_historical_data(
            tradingsymbol=stock,
            exchange='NFO',
            timeframe='1'  # 1-minute candles
        )

        if chart is None or chart.empty:
            return {'stock': stock, 'error': 'No data received'}

        # Resample to 3-minute timeframe
        chart_3min = tsl.resample_timeframe(chart, timeframe='3T')

        if chart_3min is None or chart_3min.empty:
            return {'stock': stock, 'error': 'Resampling failed'}

        # Calculate indicators
        chart_with_indicators = calculate_all_indicators(chart_3min)

        if chart_with_indicators is None:
            return {'stock': stock, 'error': 'Indicator calculation failed'}

        # Get latest values
        last = chart_with_indicators.iloc[-1]
        cc = chart_with_indicators.iloc[-2]

        # Initialize result
        result = {
            'stock': stock,
            'timestamp': str(last['timestamp']),
            'close': float(last['close']),
            'volume': int(last['volume']),
            'indicators': {
                'rsi': float(cc['rsi']),
                'ma_rsi': float(cc['ma_rsi']),
                'long_stop': float(cc['Long_Stop']),
                'fractal_high': float(cc['fractal_high']),
                'fractal_low': float(cc['fractal_low']),
                'vwap': float(last['vwap']),
                'atr': float(cc['ATR'])
            },
            'ce_signal': False,
            'pe_signal': False,
            'ce_conditions': {},
            'pe_conditions': {}
        }

        # Check CE conditions
        try:
            ce_met = check_ce_entry_conditions(
                chart_with_indicators, stock, orderbook, 0
            )
            result['ce_signal'] = ce_met

            # Get detailed conditions
            cc_close = float(cc['close'])
            long_stop = float(cc['Long_Stop'])
            fractal_high = float(cc['fractal_high'])
            vwap = float(last['vwap'])
            Crossabove = pta.above(chart_with_indicators['rsi'], chart_with_indicators['ma_rsi'])

            result['ce_conditions'] = {
                'rsi_gt_50': bool(cc['rsi'] > 50),
                'rsi_crossabove': bool(Crossabove.iloc[-2]),
                'close_gt_longstop': bool(cc_close > long_stop),
                'close_gt_fractal_high': bool(cc_close > fractal_high),
                'close_gt_vwap': bool(cc_close > vwap)
            }
        except Exception as e:
            result['ce_error'] = str(e)

        # Check PE conditions
        try:
            pe_met = check_pe_entry_conditions(
                chart_with_indicators, stock, orderbook, 0
            )
            result['pe_signal'] = pe_met

            # Get detailed conditions
            cc_close = float(cc['close'])
            long_stop = float(cc['Long_Stop'])
            fractal_low = float(cc['fractal_low'])
            vwap = float(last['vwap'])
            Crossbelow = pta.below(chart_with_indicators['rsi'], chart_with_indicators['ma_rsi'])

            result['pe_conditions'] = {
                'rsi_lt_60': bool(cc['rsi'] < 60),
                'rsi_crossbelow': bool(Crossbelow.iloc[-2]),
                'close_lt_longstop': bool(cc_close < long_stop),
                'close_lt_fractal_low': bool(cc_close < fractal_low),
                'close_lt_vwap': bool(cc_close < vwap)
            }
        except Exception as e:
            result['pe_error'] = str(e)

        return result

    except Exception as e:
        return {
            'stock': stock,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def scan_watchlist(tsl, watchlist):
    """
    Scan entire watchlist for signals

    Args:
        tsl: Tradehull instance
        watchlist: List of stock symbols

    Returns:
        dict with all results
    """
    print(f"\n{'=' * 80}")
    print(f"SCANNING WATCHLIST FOR LATEST SIGNALS")
    print(f"{'=' * 80}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Stocks to scan: {len(watchlist)}")
    print(f"{'=' * 80}\n")

    results = []
    orderbook = defaultdict(lambda: {'traded': None})

    for i, stock in enumerate(watchlist, 1):
        print(f"\n[{i}/{len(watchlist)}] Checking {stock}...")

        result = check_signals_for_stock(tsl, stock, orderbook)
        results.append(result)

        # Show quick status
        if 'error' in result:
            print(f"    Error: {result['error']}")
        else:
            status = []
            if result.get('ce_signal'):
                status.append('CE SIGNAL')
            if result.get('pe_signal'):
                status.append('PE SIGNAL')

            if status:
                print(f"    {' + '.join(status)}")
            else:
                print(f"    No signals")

    return results


# ==========================================
# DISPLAY FUNCTIONS
# ==========================================

def print_signal_summary(results):
    """
    Print a summary of all signals found
    """
    print(f"\n{'=' * 80}")
    print(f"SIGNAL SUMMARY")
    print(f"{'=' * 80}\n")

    ce_signals = [r for r in results if r.get('ce_signal')]
    pe_signals = [r for r in results if r.get('pe_signal')]
    errors = [r for r in results if 'error' in r]

    print(f"Total stocks scanned: {len(results)}")
    print(f"CE signals found: {len(ce_signals)}")
    print(f"PE signals found: {len(pe_signals)}")
    print(f"Errors: {len(errors)}")

    # Display CE signals
    if ce_signals:
        print(f"\n{'-' * 80}")
        print(f"CALL ENTRY (CE) SIGNALS:")
        print(f"{'-' * 80}")

        for r in ce_signals:
            print(f"\n  {r['stock']}")
            print(f"    Close: {r['close']:.2f}")
            print(f"    RSI: {r['indicators']['rsi']:.2f}")
            print(f"    VWAP: {r['indicators']['vwap']:.2f}")
            print(f"    ATR: {r['indicators']['atr']:.2f}")
            print(f"    Timestamp: {r['timestamp']}")

            # Show which conditions are met
            conditions = r.get('ce_conditions', {})
            met_conditions = [k for k, v in conditions.items() if v]
            if met_conditions:
                print(f"    Conditions met: {', '.join(met_conditions)}")

    # Display PE signals
    if pe_signals:
        print(f"\n{'-' * 80}")
        print(f"PUT ENTRY (PE) SIGNALS:")
        print(f"{'-' * 80}")

        for r in pe_signals:
            print(f"\n  {r['stock']}")
            print(f"    Close: {r['close']:.2f}")
            print(f"    RSI: {r['indicators']['rsi']:.2f}")
            print(f"    VWAP: {r['indicators']['vwap']:.2f}")
            print(f"    ATR: {r['indicators']['atr']:.2f}")
            print(f"    Timestamp: {r['timestamp']}")

            # Show which conditions are met
            conditions = r.get('pe_conditions', {})
            met_conditions = [k for k, v in conditions.items() if v]
            if met_conditions:
                print(f"    Conditions met: {', '.join(met_conditions)}")

    # Display errors if any
    if errors:
        print(f"\n{'-' * 80}")
        print(f"ERRORS:")
        print(f"{'-' * 80}")
        for r in errors:
            print(f"  {r['stock']}: {r['error']}")

    if not ce_signals and not pe_signals:
        print(f"\n  No signals found in current market conditions.")

    print(f"\n{'=' * 80}\n")


def save_results(results, filename=None):
    """
    Save results to JSON file
    """
    if filename is None:
        filename = f"signal_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to: {filename}")
        return filename
    except Exception as e:
        print(f"Error saving results: {e}")
        return None


# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    """
    Main function
    """
    print(f"\n{'=' * 80}")
    print(f"LATEST SIGNAL CHECKER")
    print(f"{'=' * 80}")
    print(f"\nThis tool scans stocks for fresh CE/PE entry signals")
    print(f"based on the indicator conditions configured in the bot.\n")

    # Get watchlist
    print("Enter stock symbols to scan (comma-separated)")
    print(f"Press Enter to use default watchlist: {', '.join(DEFAULT_WATCHLIST[:5])}...")
    user_input = input("\nStocks: ").strip()

    if user_input:
        watchlist = [s.strip().upper() for s in user_input.split(',')]
    else:
        watchlist = DEFAULT_WATCHLIST

    # Initialize Tradehull
    print("\nInitializing API...")
    try:
        tsl = Tradehull(CLIENT_CODE, TOKEN_ID)
        print("API initialized successfully")
    except Exception as e:
        print(f"Error initializing API: {e}")
        print("\nPlease check:")
        print("1. Your credentials are correct")
        print("2. You have internet connection")
        print("3. All required modules are installed")
        return

    # Scan watchlist
    try:
        results = scan_watchlist(tsl, watchlist)

        # Print summary
        print_signal_summary(results)

        # Save results
        save_results(results)

        print(f"Scan completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")
    except Exception as e:
        print(f"\nError during scan: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
