import pandas as pd
import numpy as np


def fractal_chaos_bands(df, window=2):
    """
    Calculates the Fractal Chaos Bands for a given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame with 'High' and 'Low' columns.
        window (int): The number of periods to look back and forward for fractal identification.
                      The standard is 2, creating a 5-bar pattern.

    Returns:
        pd.DataFrame: The original DataFrame with 'fractal_high' and 'fractal_low' columns added.
    """
    # Make a copy to avoid modifying the original DataFrame
    df_copy = df.copy()

    # --- Fractal High Calculation ---
    # A high is a fractal high if it is higher than the 'window' number of highs before and after it.
    highs = df_copy['high']
    df_copy['is_fractal_high'] = (
            (highs > highs.shift(1)) & (highs > highs.shift(2)) &
            (highs > highs.shift(-1)) & (highs > highs.shift(-2))
    )

    # Extract the high values where a fractal high is identified
    fractal_high_values = np.where(df_copy['is_fractal_high'], df_copy['high'], np.nan)

    # Create a forward-filled series of the fractal highs
    # A fractal is only confirmed after 'window' bars, so we shift the result
    ffilled_highs = pd.Series(fractal_high_values, index=df_copy.index).ffill().shift(window)
    df_copy['fractal_high'] = ffilled_highs

    # --- Fractal Low Calculation ---
    # A low is a fractal low if it is lower than the 'window' number of lows before and after it.
    lows = df_copy['low']
    df_copy['is_fractal_low'] = (
            (lows < lows.shift(1)) & (lows < lows.shift(2)) &
            (lows < lows.shift(-1)) & (lows < lows.shift(-2))
    )

    # Extract the low values where a fractal low is identified
    fractal_low_values = np.where(df_copy['is_fractal_low'], df_copy['low'], np.nan)

    # Create a forward-filled series of the fractal lows
    # A fractal is only confirmed after 'window' bars, so we shift the result
    ffilled_lows = pd.Series(fractal_low_values, index=df_copy.index).ffill().shift(window)
    df_copy['fractal_low'] = ffilled_lows

    # Clean up intermediate columns
    df_copy.drop(['is_fractal_high', 'is_fractal_low'], axis=1, inplace=True)

    return df_copy


def get_fcb_signals(df):
    """
    Generates trading signals based on Fractal Chaos Bands crossovers.

    Args:
        df (pd.DataFrame): DataFrame with 'Close', 'fractal_high', and 'fractal_low' columns.

    Returns:
        pd.DataFrame: The DataFrame with a 'signal' column added.
                      -  1: Buy signal (Close crosses above Fractal High)
                      - -1: Sell signal (Close crosses below Fractal Low)
                      -  0: No signal
    """
    df_copy = df.copy()

    # Initialize signal column
    df_copy['signal'] = 0

    # Get previous close and band values
    prev_close = df_copy['close'].shift(1)
    prev_fractal_high = df_copy['fractal_high'].shift(1)
    prev_fractal_low = df_copy['fractal_low'].shift(1)

    # --- Generate Buy Signals ---
    # A buy signal occurs when the close price crosses above the fractal high band.
    buy_condition = (df_copy['close'] > df_copy['fractal_high']) & (prev_close <= prev_fractal_high)
    df_copy.loc[buy_condition, 'signal'] = "BUY"

    # --- Generate Sell Signals ---
    # A sell signal occurs when the close price crosses below the fractal low band.
    sell_condition = (df_copy['close'] < df_copy['fractal_low']) & (prev_close >= prev_fractal_low)
    df_copy.loc[sell_condition, 'signal'] = "SELL"

    return df_copy


if __name__ == '__main__':
    # Sample 5-minute data for CDSL JUL 1760 CE
    data_5min = [
        {"datetime": "2025-07-04 09:15:00", "open": 84.15, "high": 84.2, "low": 71.6, "close": 80.75},
        {"datetime": "2025-07-04 09:20:00", "open": 80.75, "high": 84.6, "low": 76, "close": 78.8},
        {"datetime": "2025-07-04 09:25:00", "open": 78.8, "high": 80.8, "low": 77.95, "close": 79.65},
        {"datetime": "2025-07-04 09:30:00", "open": 79.65, "high": 81.15, "low": 75, "close": 75.45},
        {"datetime": "2025-07-04 09:35:00", "open": 75, "high": 75, "low": 71, "close": 74},
        {"datetime": "2025-07-04 09:40:00", "open": 74, "high": 80, "low": 73.75, "close": 80},
        {"datetime": "2025-07-04 09:45:00", "open": 80, "high": 82, "low": 78.75, "close": 78.75},
        {"datetime": "2025-07-04 09:50:00", "open": 78.75, "high": 78.75, "low": 76.65, "close": 78},
        {"datetime": "2025-07-04 09:55:00", "open": 78, "high": 80.25, "low": 78, "close": 80.25},
        {"datetime": "2025-07-04 10:00:00", "open": 79.05, "high": 82.2, "low": 78.75, "close": 80.25},
        {"datetime": "2025-07-04 10:05:00", "open": 80.25, "high": 80.25, "low": 78.2, "close": 79.85},
        {"datetime": "2025-07-04 10:10:00", "open": 79.85, "high": 82, "low": 79.6, "close": 79.6},
        {"datetime": "2025-07-04 10:15:00", "open": 79.6, "high": 79.95, "low": 79.6, "close": 79.95},
        # ... (rest of the data can be included here)
    ]

    # Create a pandas DataFrame from the sample data
    df = pd.DataFrame(data_5min)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)

    # 1. Calculate the Fractal Chaos Bands
    df_with_bands = fractal_chaos_bands(df)

    # 2. Generate signals based on the bands
    df_with_signals = get_fcb_signals(df_with_bands)

    # Display the results
    pd.set_option('display.max_rows', None)  # Show all rows
    print("Fractal Chaos Bands and Signals:")
    print(df_with_signals[['high', 'low', 'close', 'fractal_high', 'fractal_low', 'signal']])

    # You can now use df_with_signals['signal'] in your trading logic.
    # For example, to get only the rows with a signal:
    print("\nRows with Trading Signals:")
    print(df_with_signals[df_with_signals['signal'] != 0])
