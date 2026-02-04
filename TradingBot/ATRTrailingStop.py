import pandas as pd
import numpy as np

class ATRTrailingStopIndicator:
    """
    ATR Trailing Stop Indicator (Signals Only)
    ------------------------------------------
    Provides:
    - True Range
    - ATR (Wilder's method)
    - Long/Short trailing stops
    - Trend direction
    - Entry/Exit signals (BUY/SELL)
    - Stop-loss level
    - Stop distance and risk %
    """

    def __init__(self, period: int = 21, multiplier: float = 2.0):
        self.period = period
        self.multiplier = multiplier

    def calculate_true_range(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        prev_close = close.shift(1)
        hl = high - low
        hc = abs(high - prev_close)
        lc = abs(low - prev_close)
        return pd.concat([hl, hc, lc], axis=1).max(axis=1)

    def calculate_atr_wilder(self, true_range: pd.Series) -> pd.Series:
        atr = pd.Series(index=true_range.index, dtype=float)
        if len(true_range) >= self.period:
            atr.iloc[self.period - 1] = true_range.iloc[:self.period].mean()
            for i in range(self.period, len(true_range)):
                atr.iloc[i] = ((atr.iloc[i - 1] * (self.period - 1)) + true_range.iloc[i]) / self.period
        return atr

    def compute_indicator(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate trailing stops, trend, signals, ATR, stop distance and risk %.
        Input DataFrame must have: ['high', 'low', 'close']
        """
        required = ['high', 'low', 'close']
        if not all(col in data.columns for col in required):
            raise ValueError(f"Data must contain columns: {required}")

        result = data.copy()
        tr = self.calculate_true_range(result['high'], result['low'], result['close'])
        atr = self.calculate_atr_wilder(tr)

        # Prepare series
        long_stop = pd.Series(index=result.index, dtype=float)
        short_stop = pd.Series(index=result.index, dtype=float)
        trend = pd.Series(index=result.index, dtype=int)
        signal = pd.Series(index=result.index, dtype=str)
        stop_loss = pd.Series(index=result.index, dtype=float)

        for i in range(self.period, len(result)):
            if pd.isna(atr.iloc[i]):
                continue

            close = result['close'].iloc[i]
            prev_close = result['close'].iloc[i - 1] if i > 0 else close
            atr_val = atr.iloc[i]
            basic_long_stop = close - atr_val * self.multiplier
            basic_short_stop = close + atr_val * self.multiplier

            if i == self.period:
                long_stop.iloc[i] = basic_long_stop
                short_stop.iloc[i] = basic_short_stop
                trend.iloc[i] = 1 if close > basic_long_stop else -1
            else:
                prev_long_stop = long_stop.iloc[i - 1]
                prev_short_stop = short_stop.iloc[i - 1]
                prev_trend = trend.iloc[i - 1]

                long_stop.iloc[i] = max(basic_long_stop, prev_long_stop) if prev_close >= prev_long_stop else basic_long_stop
                short_stop.iloc[i] = min(basic_short_stop, prev_short_stop) if prev_close <= prev_short_stop else basic_short_stop

                if prev_trend == 1 and close <= long_stop.iloc[i]:
                    trend.iloc[i] = -1
                    signal.iloc[i] = "SELL"
                    stop_loss.iloc[i] = short_stop.iloc[i]
                elif prev_trend == -1 and close >= short_stop.iloc[i]:
                    trend.iloc[i] = 1
                    signal.iloc[i] = "BUY"
                    stop_loss.iloc[i] = long_stop.iloc[i]
                else:
                    trend.iloc[i] = prev_trend
                    stop_loss.iloc[i] = long_stop.iloc[i] if prev_trend == 1 else short_stop.iloc[i]

        # Final result assignment
        result['TR'] = tr
        result['ATR'] = atr
        result['Long_Stop'] = long_stop
        result['Short_Stop'] = short_stop
        result['Trend'] = trend
        result['Signal'] = signal
        result['Stop_Loss']= stop_loss
        result['Position'] = trend.map({1: 'BUY', -1: 'SELL'})
        result['Stop_Distance'] = abs(result['close'] - result['Stop_Loss'])
        result['Risk_Percent'] = (result['Stop_Distance'] / result['close']) * 100
        # Shift signal-related outputs to the next candle
        #result['Signal'] = result['Signal'].shift(1)
        result['Stop_Loss'] = result['Stop_Loss'].shift(1)
        #result['Position'] = result['Position'].shift(1)
        result['Stop_Distance'] = result['Stop_Distance'].shift(1)
        result['Risk_Percent'] = result['Risk_Percent'].shift(1)

        return result
