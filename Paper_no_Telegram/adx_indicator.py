"""
ADX (Average Directional Index) Indicator Module
=================================================

This module provides functions to calculate and check ADX conditions for directional movement.

ADX Components:
- ADX: Average Directional Index (measures trend strength)
- +DI: Positive Directional Indicator (upward movement)
- -DI: Negative Directional Indicator (downward movement)

Trading Logic:
1. For CE (Call) Entry:
   - Stock ADX rising and > 23
   - +DI crossed above -DI (bullish crossover)

2. For PE (Put) Entry:
   - Stock ADX rising and > 23 (stock falling)
   - -DI crossed above +DI (bearish crossover for stock)
   - BUT for PE option itself: ADX rising > 23 and +DI > -DI (PE option is rising)
"""

import pandas as pd
import talib


def calculate_adx_indicators(chart, period=14):
    """
    Calculate ADX, +DI, and -DI indicators for a given chart.

    Args:
        chart: DataFrame with 'high', 'low', 'close' columns
        period: ADX period (default 14)

    Returns:
        DataFrame: Chart with added columns 'adx', 'plus_di', 'minus_di'
    """
    try:
        if chart is None or chart.empty:
            return None

        # Calculate ADX, +DI, -DI using TA-Lib
        chart['adx'] = talib.ADX(chart['high'], chart['low'], chart['close'], timeperiod=period)
        chart['plus_di'] = talib.PLUS_DI(chart['high'], chart['low'], chart['close'], timeperiod=period)
        chart['minus_di'] = talib.MINUS_DI(chart['high'], chart['low'], chart['close'], timeperiod=period)

        return chart

    except Exception as e:
        print(f"❌ Error calculating ADX indicators: {e}")
        import traceback
        traceback.print_exc()
        return None


def is_adx_rising(chart, lookback=2):
    """
    Check if ADX is rising (comparing current vs previous candles).

    Args:
        chart: DataFrame with 'adx' column
        lookback: Number of periods to check (default 2)

    Returns:
        bool: True if ADX is rising
    """
    try:
        if 'adx' not in chart.columns or len(chart) < lookback + 1:
            return False

        # Get last N+1 ADX values
        recent_adx = chart['adx'].iloc[-(lookback+1):].values

        # Check if each value is greater than the previous
        for i in range(1, len(recent_adx)):
            if pd.isna(recent_adx[i]) or pd.isna(recent_adx[i-1]):
                return False
            if recent_adx[i] <= recent_adx[i-1]:
                return False

        return True

    except Exception as e:
        print(f"❌ Error checking if ADX is rising: {e}")
        return False


def check_plus_di_crossover(chart):
    """
    Check if +DI has crossed above -DI (bullish crossover).

    Args:
        chart: DataFrame with 'plus_di' and 'minus_di' columns

    Returns:
        bool: True if +DI crossed above -DI on the current or previous candle
    """
    try:
        if len(chart) < 2:
            return False

        current = chart.iloc[-1]
        previous = chart.iloc[-2]

        # Current candle: +DI > -DI
        current_bullish = current['plus_di'] > current['minus_di']

        # Previous candle: +DI was below or equal to -DI
        previous_bearish = previous['plus_di'] <= previous['minus_di']

        # Crossover occurred if previous was bearish and current is bullish
        crossover = previous_bearish and current_bullish

        # Also accept if +DI is already above -DI
        already_above = current_bullish and previous['plus_di'] > previous['minus_di']

        return crossover or already_above

    except Exception as e:
        print(f"❌ Error checking +DI crossover: {e}")
        return False


def check_minus_di_crossover(chart):
    """
    Check if -DI has crossed above +DI (bearish crossover).

    Args:
        chart: DataFrame with 'plus_di' and 'minus_di' columns

    Returns:
        bool: True if -DI crossed above +DI on the current or previous candle
    """
    try:
        if len(chart) < 2:
            return False

        current = chart.iloc[-1]
        previous = chart.iloc[-2]

        # Current candle: -DI > +DI
        current_bearish = current['minus_di'] > current['plus_di']

        # Previous candle: -DI was below or equal to +DI
        previous_bullish = previous['minus_di'] <= previous['plus_di']

        # Crossover occurred if previous was bullish and current is bearish
        crossover = previous_bullish and current_bearish

        # Also accept if -DI is already above +DI
        already_above = current_bearish and previous['minus_di'] > previous['plus_di']

        return crossover or already_above

    except Exception as e:
        print(f"❌ Error checking -DI crossover: {e}")
        return False


def check_adx_ce_condition(chart, adx_threshold=23, lookback=2):
    """
    Check ADX condition for CE (Call) entry:
    - ADX rising and > threshold
    - +DI crossed above -DI (bullish)

    Args:
        chart: DataFrame with ADX indicators
        adx_threshold: Minimum ADX value (default 23)
        lookback: Number of periods to check for rising ADX (default 2)

    Returns:
        tuple: (condition_met: bool, adx_value: float, plus_di: float, minus_di: float, details: str)
    """
    try:
        if chart is None or chart.empty or len(chart) < 2:
            return False, None, None, None, "Insufficient data"

        current = chart.iloc[-1]

        # Get values
        adx_value = current['adx']
        plus_di_value = current['plus_di']
        minus_di_value = current['minus_di']

        # Check if values are valid
        if pd.isna(adx_value) or pd.isna(plus_di_value) or pd.isna(minus_di_value):
            return False, None, None, None, "ADX/DI values are NaN"

        # Check ADX > threshold
        adx_above_threshold = adx_value > adx_threshold

        # Check ADX rising
        adx_rising = is_adx_rising(chart, lookback)

        # Check +DI crossover above -DI
        plus_di_crossover = check_plus_di_crossover(chart)

        # All conditions must be true
        condition_met = adx_above_threshold and adx_rising and plus_di_crossover

        # Build details string
        details = (
            f"ADX={adx_value:.2f} (>{adx_threshold}: {adx_above_threshold}), "
            f"ADX_Rising={adx_rising}, "
            f"+DI={plus_di_value:.2f} > -DI={minus_di_value:.2f}: {plus_di_crossover}"
        )

        return condition_met, adx_value, plus_di_value, minus_di_value, details

    except Exception as e:
        print(f"❌ Error checking ADX CE condition: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None, None, f"Error: {e}"


def check_adx_pe_stock_condition(chart, adx_threshold=23, lookback=2):
    """
    Check ADX condition for stock in PE (Put) scenario:
    - ADX rising and > threshold
    - -DI crossed above +DI (bearish - stock falling)

    Args:
        chart: DataFrame with ADX indicators
        adx_threshold: Minimum ADX value (default 23)
        lookback: Number of periods to check for rising ADX (default 2)

    Returns:
        tuple: (condition_met: bool, adx_value: float, plus_di: float, minus_di: float, details: str)
    """
    try:
        if chart is None or chart.empty or len(chart) < 2:
            return False, None, None, None, "Insufficient data"

        current = chart.iloc[-1]

        # Get values
        adx_value = current['adx']
        plus_di_value = current['plus_di']
        minus_di_value = current['minus_di']

        # Check if values are valid
        if pd.isna(adx_value) or pd.isna(plus_di_value) or pd.isna(minus_di_value):
            return False, None, None, None, "ADX/DI values are NaN"

        # Check ADX > threshold
        adx_above_threshold = adx_value > adx_threshold

        # Check ADX rising
        adx_rising = is_adx_rising(chart, lookback)

        # Check -DI crossover above +DI (bearish for stock)
        minus_di_crossover = check_minus_di_crossover(chart)

        # All conditions must be true
        condition_met = adx_above_threshold and adx_rising and minus_di_crossover

        # Build details string
        details = (
            f"ADX={adx_value:.2f} (>{adx_threshold}: {adx_above_threshold}), "
            f"ADX_Rising={adx_rising}, "
            f"-DI={minus_di_value:.2f} > +DI={plus_di_value:.2f}: {minus_di_crossover}"
        )

        return condition_met, adx_value, plus_di_value, minus_di_value, details

    except Exception as e:
        print(f"❌ Error checking ADX PE stock condition: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None, None, f"Error: {e}"


def check_adx_pe_option_condition(chart, adx_threshold=23, lookback=2):
    """
    Check ADX condition for PE option itself:
    - ADX rising and > threshold
    - +DI crossed above -DI (bullish - PE option is rising in value)

    Note: Even though stock is falling, the PE option value rises,
    so we check for bullish ADX on the PE option chart.

    Args:
        chart: DataFrame with ADX indicators for PE option
        adx_threshold: Minimum ADX value (default 23)
        lookback: Number of periods to check for rising ADX (default 2)

    Returns:
        tuple: (condition_met: bool, adx_value: float, plus_di: float, minus_di: float, details: str)
    """
    # For PE option, we check the same as CE - bullish ADX because PE option price is rising
    return check_adx_ce_condition(chart, adx_threshold, lookback)
