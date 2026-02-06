"""
RL State Builder
================
Builds observation vectors from chart data and position state for the RL agent.
Uses indicators already computed by compute_indicators() in single_trade_focus_bot.py.
"""

import numpy as np
import datetime


def build_entry_observation(chart, option_chart, spread_pct, current_time):
    """
    Build the 19-feature observation vector for entry decisions.

    Args:
        chart: DataFrame with underlying stock indicators (from compute_indicators)
        option_chart: DataFrame with option indicators (from process_ce/pe_option_data)
        spread_pct: Bid-ask spread as fraction of mid price (e.g., 0.005 for 0.5%)
        current_time: datetime object for current market time

    Returns:
        np.ndarray: 19-dimensional observation vector, or None if data insufficient
    """
    try:
        if chart is None or chart.empty or len(chart) < 2:
            return None
        if option_chart is None or option_chart.empty or len(option_chart) < 2:
            return None

        last = chart.iloc[-1]
        prev = chart.iloc[-2]

        opt_last = option_chart.iloc[-1]

        obs = np.zeros(19, dtype=np.float32)

        # --- Underlying stock features (0-11) ---
        # 1. RSI normalized to [0, 1]
        obs[0] = _safe_val(last.get('rsi', 50)) / 100.0

        # 2. RSI - MA_RSI momentum, normalized
        rsi_val = _safe_val(last.get('rsi', 50))
        ma_rsi_val = _safe_val(last.get('ma_rsi', 50))
        obs[1] = (rsi_val - ma_rsi_val) / 50.0

        # 3. RSI cross above MA_RSI (binary)
        prev_rsi = _safe_val(prev.get('rsi', 50))
        prev_ma_rsi = _safe_val(prev.get('ma_rsi', 50))
        obs[2] = 1.0 if (rsi_val > ma_rsi_val and prev_rsi <= prev_ma_rsi) else 0.0

        # 4. Close vs VWAP %
        close = _safe_val(last.get('close', 0))
        vwap = _safe_val(last.get('vwap', close))
        obs[3] = (close - vwap) / max(vwap, 1e-6)

        # 5. Close vs Long_Stop %
        long_stop = _safe_val(last.get('Long_Stop', close))
        obs[4] = (close - long_stop) / max(close, 1e-6)

        # 6. Close vs Fractal_High %
        fractal_high = _safe_val(last.get('fractal_high', close))
        obs[5] = (close - fractal_high) / max(close, 1e-6)

        # 7. Close vs Fractal_Low %
        fractal_low = _safe_val(last.get('fractal_low', close))
        obs[6] = (close - fractal_low) / max(close, 1e-6)

        # 8. ADX normalized to [0, 1]
        obs[7] = _safe_val(last.get('adx', 25)) / 100.0

        # 9. ADX rising (binary)
        prev_adx = _safe_val(prev.get('adx', 25))
        curr_adx = _safe_val(last.get('adx', 25))
        obs[8] = 1.0 if curr_adx > prev_adx else 0.0

        # 10. +DI minus -DI, normalized
        plus_di = _safe_val(last.get('plus_di', 25))
        minus_di = _safe_val(last.get('minus_di', 25))
        obs[9] = (plus_di - minus_di) / 50.0

        # 11. ATR as % of price (volatility measure)
        atr = _safe_val(last.get('ATR', 0))
        obs[10] = atr / max(close, 1e-6)

        # 12. Trend direction from ATR indicator (-1 or 1)
        position = _safe_val(last.get('Position', 1))
        obs[11] = 1.0 if position > 0 else -1.0

        # --- Option features (12-16) ---
        opt_close = _safe_val(opt_last.get('close', 0))

        # 13. Option RSI
        obs[12] = _safe_val(opt_last.get('rsi', 50)) / 100.0

        # 14. Option Close vs VWAP %
        opt_vwap = _safe_val(opt_last.get('vwap', opt_close))
        obs[13] = (opt_close - opt_vwap) / max(opt_vwap, 1e-6)

        # 15. Option Close vs Long_Stop %
        opt_long_stop = _safe_val(opt_last.get('Long_Stop', opt_close))
        obs[14] = (opt_close - opt_long_stop) / max(opt_close, 1e-6)

        # 16. Option ADX
        obs[15] = _safe_val(opt_last.get('adx', 25)) / 100.0

        # 17. Option +DI minus -DI
        opt_plus_di = _safe_val(opt_last.get('plus_di', 25))
        opt_minus_di = _safe_val(opt_last.get('minus_di', 25))
        obs[16] = (opt_plus_di - opt_minus_di) / 50.0

        # --- Market context (17-18) ---
        # 18. Bid-Ask spread %
        obs[17] = np.clip(_safe_val(spread_pct, 0.01), 0.0, 0.1)

        # 19. Time of day (market progress 0=open, 1=close)
        obs[18] = _time_to_market_progress(current_time)

        return validate_observation(obs)

    except Exception as e:
        print(f"[RL] Error building entry observation: {e}")
        return None


def build_exit_observation(option_chart, orderbook_entry, current_price, current_time):
    """
    Build the 23-feature observation vector for exit decisions.
    Uses option chart data + 4 position-specific features.

    Args:
        option_chart: DataFrame with option indicators (3-min resampled with indicators)
        orderbook_entry: dict with position data (entry_price, sl, tsl, qty, entry_time, etc.)
        current_price: Current option LTP
        current_time: datetime object for current market time

    Returns:
        np.ndarray: 23-dimensional observation vector, or None if data insufficient
    """
    try:
        if option_chart is None or option_chart.empty or len(option_chart) < 2:
            return None

        last = option_chart.iloc[-1]
        prev = option_chart.iloc[-2]

        obs = np.zeros(23, dtype=np.float32)

        opt_close = _safe_val(last.get('close', 0))

        # --- Option technical features (0-11) mirroring entry obs structure ---
        # Use option data for all indicator slots
        obs[0] = _safe_val(last.get('rsi', 50)) / 100.0

        rsi_val = _safe_val(last.get('rsi', 50))
        ma_rsi_val = _safe_val(last.get('ma_rsi', 50))
        obs[1] = (rsi_val - ma_rsi_val) / 50.0

        prev_rsi = _safe_val(prev.get('rsi', 50))
        prev_ma_rsi = _safe_val(prev.get('ma_rsi', 50))
        obs[2] = 1.0 if (rsi_val > ma_rsi_val and prev_rsi <= prev_ma_rsi) else 0.0

        opt_vwap = _safe_val(last.get('vwap', opt_close))
        obs[3] = (opt_close - opt_vwap) / max(opt_vwap, 1e-6)

        opt_long_stop = _safe_val(last.get('Long_Stop', opt_close))
        obs[4] = (opt_close - opt_long_stop) / max(opt_close, 1e-6)

        opt_fractal_high = _safe_val(last.get('fractal_high', opt_close))
        obs[5] = (opt_close - opt_fractal_high) / max(opt_close, 1e-6)

        opt_fractal_low = _safe_val(last.get('fractal_low', opt_close))
        obs[6] = (opt_close - opt_fractal_low) / max(opt_close, 1e-6)

        obs[7] = _safe_val(last.get('adx', 25)) / 100.0

        prev_adx = _safe_val(prev.get('adx', 25))
        curr_adx = _safe_val(last.get('adx', 25))
        obs[8] = 1.0 if curr_adx > prev_adx else 0.0

        plus_di = _safe_val(last.get('plus_di', 25))
        minus_di = _safe_val(last.get('minus_di', 25))
        obs[9] = (plus_di - minus_di) / 50.0

        atr = _safe_val(last.get('ATR', 0))
        obs[10] = atr / max(opt_close, 1e-6)

        position = _safe_val(last.get('Position', 1))
        obs[11] = 1.0 if position > 0 else -1.0

        # Repeat key option features (12-16)
        obs[12] = obs[0]   # Option RSI (same as slot 0 for exit)
        obs[13] = obs[3]   # Option vs VWAP
        obs[14] = obs[4]   # Option vs Long_Stop
        obs[15] = obs[7]   # Option ADX
        obs[16] = obs[9]   # Option +DI - -DI

        # Spread placeholder (not always available during exit monitoring)
        obs[17] = 0.01

        # Time of day
        obs[18] = _time_to_market_progress(current_time)

        # --- Position-specific features (19-22) ---
        entry_price = _safe_val(orderbook_entry.get('entry_price', 0))
        sl = _safe_val(orderbook_entry.get('tsl') or orderbook_entry.get('sl', 0))
        current_price = _safe_val(current_price, 0)

        # 20. Current P&L %
        if entry_price > 0:
            obs[19] = (current_price - entry_price) / entry_price
        else:
            obs[19] = 0.0

        # 21. Time held as fraction of max (120 min)
        obs[20] = _get_time_held_fraction(orderbook_entry, current_time)

        # 22. Distance to SL %
        if entry_price > 0 and sl > 0:
            obs[21] = (current_price - sl) / entry_price
        else:
            obs[21] = 0.0

        # 23. Distance to target %
        risk = entry_price - sl if (entry_price > 0 and sl > 0) else 0
        target = entry_price + (risk * 3) if risk > 0 else entry_price * 1.15
        if entry_price > 0:
            obs[22] = (target - current_price) / entry_price
        else:
            obs[22] = 0.0

        return validate_observation(obs)

    except Exception as e:
        print(f"[RL] Error building exit observation: {e}")
        return None


def validate_observation(obs):
    """
    Validate and clean an observation vector.
    Replaces NaN/inf with 0, clips to reasonable range.

    Args:
        obs: np.ndarray observation vector

    Returns:
        np.ndarray: cleaned observation vector
    """
    if obs is None:
        return None

    # Replace NaN and inf
    obs = np.nan_to_num(obs, nan=0.0, posinf=1.0, neginf=-1.0)

    # Clip to reasonable range
    obs = np.clip(obs, -5.0, 5.0)

    return obs.astype(np.float32)


def _safe_val(value, default=0.0):
    """Safely extract a numeric value, handling None/NaN."""
    if value is None:
        return default
    try:
        val = float(value)
        if np.isnan(val) or np.isinf(val):
            return default
        return val
    except (ValueError, TypeError):
        return default


def _time_to_market_progress(current_time):
    """
    Convert current time to market progress [0, 1].
    Market: 9:15 AM to 3:15 PM (360 minutes).
    """
    try:
        if isinstance(current_time, datetime.datetime):
            t = current_time
        elif isinstance(current_time, datetime.time):
            t = datetime.datetime.combine(datetime.date.today(), current_time)
        else:
            return 0.5  # Default to mid-day

        market_open = t.replace(hour=9, minute=15, second=0, microsecond=0)
        minutes_since_open = (t - market_open).total_seconds() / 60.0
        progress = np.clip(minutes_since_open / 360.0, 0.0, 1.0)
        return float(progress)
    except Exception:
        return 0.5


def _get_time_held_fraction(orderbook_entry, current_time):
    """
    Calculate time held as fraction of max holding time (120 minutes).
    """
    try:
        entry_time_str = orderbook_entry.get('entry_time')
        if not entry_time_str:
            return 0.0

        if isinstance(current_time, datetime.datetime):
            current_dt = current_time
        else:
            current_dt = datetime.datetime.now()

        entry_time = datetime.datetime.strptime(entry_time_str, "%H:%M:%S").time()
        entry_dt = datetime.datetime.combine(current_dt.date(), entry_time)

        minutes_held = (current_dt - entry_dt).total_seconds() / 60.0
        return float(np.clip(minutes_held / 120.0, 0.0, 1.0))
    except Exception:
        return 0.0
