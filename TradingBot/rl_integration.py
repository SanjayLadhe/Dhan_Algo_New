"""
RL Integration
==============
Bridge functions between the RL agent and existing entry/exit logic.
These functions are called from ce_entry_logic.py, pe_entry_logic.py, and exit_logic.py.

All functions are safe to call regardless of RL_ENABLED state - they gracefully
fall through to rule-based behavior when RL is disabled or unavailable.
"""

import datetime
from rl_config import (
    RL_ENABLED, RL_ENTRY_FILTER_ENABLED, RL_EXIT_FILTER_ENABLED,
    RL_CONFIDENCE_THRESHOLD, RL_FALLBACK_TO_RULES, RL_LOG_DECISIONS,
    ACTION_SKIP, ACTION_TAKE, ACTION_TAKE_REDUCED,
    ACTION_HOLD, ACTION_EXIT, ACTION_TIGHTEN
)

# Lazy-loaded singletons
_entry_agent = None
_exit_agent = None
_data_logger = None
_initialized = False

ACTION_NAMES_ENTRY = {ACTION_SKIP: 'SKIP', ACTION_TAKE: 'TAKE', ACTION_TAKE_REDUCED: 'TAKE_REDUCED'}
ACTION_NAMES_EXIT = {ACTION_HOLD: 'HOLD', ACTION_EXIT: 'EXIT', ACTION_TIGHTEN: 'TIGHTEN'}


def _ensure_initialized():
    """Lazy-initialize the RL components."""
    global _entry_agent, _exit_agent, _data_logger, _initialized

    if _initialized:
        return

    _initialized = True

    try:
        # Always initialize the data logger (for data collection even when RL is off)
        from rl_data_logger import TradeDataLogger
        _data_logger = TradeDataLogger()
        print("[RL Integration] Data logger initialized")
    except Exception as e:
        print(f"[RL Integration] Warning: Could not initialize data logger: {e}")

    if RL_ENABLED:
        try:
            from rl_agent import RLEntryAgent, RLExitAgent
            if RL_ENTRY_FILTER_ENABLED:
                _entry_agent = RLEntryAgent()
                print(f"[RL Integration] Entry agent: {'READY' if _entry_agent.is_available() else 'FALLBACK MODE'}")
            if RL_EXIT_FILTER_ENABLED:
                _exit_agent = RLExitAgent()
                print(f"[RL Integration] Exit agent: {'READY' if _exit_agent.is_available() else 'FALLBACK MODE'}")
        except ImportError as e:
            print(f"[RL Integration] Warning: stable-baselines3 not installed. RL disabled. ({e})")
        except Exception as e:
            print(f"[RL Integration] Warning: Could not initialize RL agents: {e}")


def filter_entry_signal(chart, option_chart, spread_info, symbol, signal_type):
    """
    Filter an entry signal through the RL agent.

    Called from execute_ce_entry() / execute_pe_entry() after all rule-based
    conditions pass and bid-ask spread is acceptable.

    Args:
        chart: DataFrame with underlying stock indicators
        option_chart: DataFrame with option indicators
        spread_info: dict with bid-ask spread data, or float spread_pct
        symbol: Stock symbol (e.g., 'KOTAKBANK')
        signal_type: 'CE' or 'PE'

    Returns:
        tuple: (should_enter: bool, lot_multiplier: float, reason: str)
            - should_enter: True to proceed with entry, False to skip
            - lot_multiplier: 1.0 for normal, 0.5 for reduced
            - reason: Human-readable reason for the decision
    """
    try:
        _ensure_initialized()

        # Build observation
        from rl_state_builder import build_entry_observation
        spread_pct = _extract_spread_pct(spread_info)
        observation = build_entry_observation(chart, option_chart, spread_pct, datetime.datetime.now())

        # Log observation (always, for data collection)
        if _data_logger and observation is not None:
            rl_action = -1
            rl_confidence = 0.0

            if RL_ENABLED and RL_ENTRY_FILTER_ENABLED and _entry_agent and _entry_agent.is_available():
                # Get RL decision
                rl_action, rl_confidence = _entry_agent.should_enter(observation)

                _data_logger.log_entry_observation(symbol, observation, signal_type, rl_action, rl_confidence)

                _log_decision('ENTRY', symbol, signal_type,
                              ACTION_NAMES_ENTRY.get(rl_action, '?'), rl_confidence)

                # Apply confidence threshold
                if rl_confidence < RL_CONFIDENCE_THRESHOLD:
                    print(f"[RL] Entry confidence {rl_confidence:.2f} < threshold {RL_CONFIDENCE_THRESHOLD}. Using rules.")
                    return True, 1.0, "rl_low_confidence"

                # Apply RL decision
                if rl_action == ACTION_SKIP:
                    # Log skip for counterfactual learning
                    opt_close = 0
                    if option_chart is not None and not option_chart.empty:
                        opt_close = float(option_chart.iloc[-1].get('close', 0))
                    _data_logger.log_skip_observation(symbol, observation, signal_type, opt_close)
                    return False, 0.0, f"rl_skip (confidence={rl_confidence:.2f})"

                elif rl_action == ACTION_TAKE_REDUCED:
                    return True, 0.5, f"rl_take_reduced (confidence={rl_confidence:.2f})"

                else:  # ACTION_TAKE
                    return True, 1.0, f"rl_take (confidence={rl_confidence:.2f})"

            else:
                # RL not active - just log the observation for future training
                _data_logger.log_entry_observation(symbol, observation, signal_type, -1, 0.0)
                return True, 1.0, "rl_disabled"

        return True, 1.0, "rl_no_logger"

    except Exception as e:
        print(f"[RL Integration] Entry filter error (falling back to rules): {e}")
        return True, 1.0, f"rl_error: {e}"


def filter_exit_signal(option_chart_3min, orderbook_entry, current_price, symbol, exit_signal_type):
    """
    Filter an exit signal through the RL agent.

    Called from process_exit_conditions() when RSI/LongStop exit is triggered.
    NEVER called for hard exits (SL hit, target hit, time exit).

    Args:
        option_chart_3min: DataFrame with 3-min option data (with indicators)
        orderbook_entry: dict with position data
        current_price: Current option LTP
        symbol: Stock symbol
        exit_signal_type: e.g., 'rsi_below_ma_rsi', 'close_below_longstop'

    Returns:
        tuple: (should_exit: bool, sl_adjustment_pct: float, reason: str)
            - should_exit: True to proceed with exit, False to hold
            - sl_adjustment_pct: If TIGHTEN, move SL up by this % (e.g., 0.02 = 2%)
            - reason: Human-readable reason
    """
    try:
        _ensure_initialized()

        # Build observation
        from rl_state_builder import build_exit_observation
        observation = build_exit_observation(
            option_chart_3min, orderbook_entry, current_price, datetime.datetime.now()
        )

        if _data_logger and observation is not None:
            rl_action = -1
            rl_confidence = 0.0

            if RL_ENABLED and RL_EXIT_FILTER_ENABLED and _exit_agent and _exit_agent.is_available():
                rl_action, rl_confidence = _exit_agent.should_exit(observation)

                _data_logger.log_exit_observation(symbol, observation, exit_signal_type, rl_action, rl_confidence)

                _log_decision('EXIT', symbol, exit_signal_type,
                              ACTION_NAMES_EXIT.get(rl_action, '?'), rl_confidence)

                # Apply confidence threshold
                if rl_confidence < RL_CONFIDENCE_THRESHOLD:
                    print(f"[RL] Exit confidence {rl_confidence:.2f} < threshold. Using rules.")
                    return True, 0.0, "rl_low_confidence"

                if rl_action == ACTION_HOLD:
                    return False, 0.0, f"rl_hold (confidence={rl_confidence:.2f})"

                elif rl_action == ACTION_TIGHTEN:
                    return False, 0.02, f"rl_tighten (confidence={rl_confidence:.2f})"

                else:  # ACTION_EXIT
                    return True, 0.0, f"rl_exit (confidence={rl_confidence:.2f})"

            else:
                _data_logger.log_exit_observation(symbol, observation, exit_signal_type, -1, 0.0)
                return True, 0.0, "rl_disabled"

        return True, 0.0, "rl_no_logger"

    except Exception as e:
        print(f"[RL Integration] Exit filter error (falling back to rules): {e}")
        return True, 0.0, f"rl_error: {e}"


def log_trade_completion(symbol, orderbook_entry, exit_reason):
    """
    Log a completed trade for RL training data.
    Called from all exit handlers in exit_logic.py.

    Args:
        symbol: Stock symbol
        orderbook_entry: dict with trade data (must have entry_price, exit_price, pnl, etc.)
        exit_reason: e.g., 'Stop_Loss_Hit', 'Target_Reached', 'RSI_Below_MA_Exit', 'Time_Exit_Loss'
    """
    try:
        _ensure_initialized()
        if _data_logger:
            _data_logger.log_trade_completion(symbol, orderbook_entry, exit_reason)
    except Exception as e:
        print(f"[RL Integration] Trade logging error (non-critical): {e}")


def _extract_spread_pct(spread_info):
    """Extract bid-ask spread percentage from various input formats."""
    try:
        if isinstance(spread_info, (int, float)):
            return float(spread_info)
        if isinstance(spread_info, dict):
            bid = spread_info.get('bid', 0)
            ask = spread_info.get('ask', 0)
            if bid and ask and bid > 0:
                mid = (bid + ask) / 2
                return (ask - bid) / mid if mid > 0 else 0.01
            # Try spread directly
            spread = spread_info.get('spread', 0)
            ltp = spread_info.get('ltp', 0)
            if spread and ltp and ltp > 0:
                return spread / ltp
        return 0.01  # Default
    except Exception:
        return 0.01


def _log_decision(decision_type, symbol, signal_type, action_name, confidence):
    """Log RL decision for monitoring."""
    if not RL_LOG_DECISIONS:
        return
    try:
        msg = f"[RL {decision_type}] {symbol} | {signal_type} | Action: {action_name} | Confidence: {confidence:.2f}"
        print(msg)

        from rl_config import RL_LOG_FILE
        with open(RL_LOG_FILE, 'a') as f:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {msg}\n")
    except Exception:
        pass
