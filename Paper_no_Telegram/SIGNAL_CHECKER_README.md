# Signal Checker Utility

## Overview

The `check_latest_signals.py` script is a utility tool that scans stocks in your watchlist for fresh entry signals based on the same indicators and conditions used by the main trading bot.

## Features

- Scans multiple stocks simultaneously
- Checks for both CE (Call) and PE (Put) entry signals
- Uses real-time market data from Dhan API
- Calculates all required indicators:
  - RSI (Relative Strength Index)
  - VWAP (Volume Weighted Average Price)
  - ATR Trailing Stop
  - Fractal Chaos Bands
  - Moving Averages
  - Parabolic SAR
- Provides detailed condition breakdown
- Saves results to JSON for later analysis

## Usage

### Basic Usage

```bash
python check_latest_signals.py
```

### Interactive Mode

When you run the script, it will:

1. Ask for stocks to scan (or use default watchlist)
2. Initialize the API connection
3. Scan each stock for signals
4. Display a comprehensive summary
5. Save results to a JSON file

### Example Output

```
================================================================================
SCANNING WATCHLIST FOR LATEST SIGNALS
================================================================================
Time: 2025-10-23 14:30:00
Stocks to scan: 10
================================================================================

[1/10] Checking RELIANCE...
    No signals

[2/10] Checking TATASTEEL...
    CE SIGNAL

[3/10] Checking INFY...
    No signals

================================================================================
SIGNAL SUMMARY
================================================================================

Total stocks scanned: 10
CE signals found: 2
PE signals found: 1
Errors: 0

--------------------------------------------------------------------------------
CALL ENTRY (CE) SIGNALS:
--------------------------------------------------------------------------------

  TATASTEEL
    Close: 145.50
    RSI: 62.34
    VWAP: 144.20
    ATR: 2.15
    Timestamp: 2025-10-23 14:30:00
    Conditions met: rsi_gt_50, rsi_crossabove, close_gt_longstop, close_gt_fractal_high, close_gt_vwap
```

## Entry Conditions

### CE (Call Entry) Conditions

All of the following must be true:

1. **RSI > 50** - Bullish momentum
2. **RSI crosses above MA(RSI)** - Trend confirmation
3. **Close > Long Stop (ATR)** - Price above trailing stop
4. **Close > Fractal High** - Breaking resistance
5. **Close > VWAP** - Price above average
6. **No existing position** - Position check
7. **Order limit OK** - Less than 5 active orders

### PE (Put Entry) Conditions

All of the following must be true:

1. **RSI < 60** - Bearish momentum
2. **RSI crosses below MA(RSI)** - Trend confirmation
3. **Close < Long Stop (ATR)** - Price below trailing stop
4. **Close < Fractal Low** - Breaking support
5. **Close < VWAP** - Price below average
6. **No existing position** - Position check
7. **Order limit OK** - Less than 5 active orders

## Configuration

### Watchlist

Modify the `DEFAULT_WATCHLIST` in the script:

```python
DEFAULT_WATCHLIST = [
    "RELIANCE", "TATASTEEL", "INFY", "SBIN", "HDFCBANK",
    "ICICIBANK", "TCS", "WIPRO", "LT", "AXISBANK"
]
```

### Credentials

Update your Dhan API credentials:

```python
CLIENT_CODE = "your_client_code"
TOKEN_ID = "your_token_id"
```

## Output Files

The script generates:

1. **Console Output** - Real-time progress and summary
2. **JSON File** - Detailed results with timestamp
   - Format: `signal_check_YYYYMMDD_HHMMSS.json`
   - Contains all indicator values and condition results

## Requirements

- Python 3.7+
- Dhan API credentials
- Required packages:
  - dhanhq
  - pandas
  - numpy
  - talib
  - pandas_ta

## Indicators Explained

### RSI (Relative Strength Index)
- Measures momentum on a scale of 0-100
- > 50 indicates bullish momentum
- < 50 indicates bearish momentum

### VWAP (Volume Weighted Average Price)
- Average price weighted by volume
- Price above VWAP = bullish
- Price below VWAP = bearish

### ATR Trailing Stop
- Dynamic stop loss based on volatility
- Adapts to market conditions
- Used for position sizing and risk management

### Fractal Chaos Bands
- Support/resistance levels based on price patterns
- Fractal High = resistance level
- Fractal Low = support level

### MA(RSI)
- Moving average of RSI
- Smooths RSI to identify trends
- Crossovers indicate momentum shifts

## Tips

1. **Market Hours** - Run during market hours (9:15 AM - 3:30 PM IST) for fresh signals
2. **Frequency** - Check every 3-5 minutes for new signals
3. **Multiple Timeframes** - Script uses 3-minute candles (optimal for intraday)
4. **Confirmation** - Always verify signals with price action before trading
5. **Risk Management** - Use the ATR values for position sizing

## Troubleshooting

### "No data received"
- Check if market is open
- Verify stock symbol is correct
- Ensure API credentials are valid

### "Import Error"
- Install missing packages: `pip install -r requirements.txt`
- Verify Python version is 3.7+

### "API Error"
- Check internet connection
- Verify Dhan API token is not expired
- Ensure you have active Dhan account

## Integration with Main Bot

This utility uses the exact same logic as the main trading bot (`Dhan_Tradehull_V3.py`). Signals found here would trigger actual trades in the main bot when running in live mode.

## Disclaimer

This tool is for analysis and educational purposes. Always verify signals independently before making trading decisions. Past performance does not guarantee future results.
