"""
RL Data Logger
==============
Logs trade observations and outcomes for offline RL training.
Appends to CSV files that accumulate over time.
"""

import os
import csv
import datetime
import numpy as np
from rl_config import (
    RL_DATA_DIR, RL_TRADE_LOG_PATH, RL_ENTRY_OBS_LOG_PATH,
    RL_EXIT_OBS_LOG_PATH, RL_SKIP_LOG_PATH, ENTRY_OBS_DIM, EXIT_OBS_DIM
)


class TradeDataLogger:
    """Logs trade observations and outcomes for RL training data collection."""

    def __init__(self):
        """Initialize logger and create data directories if needed."""
        os.makedirs(RL_DATA_DIR, exist_ok=True)
        self._ensure_csv_headers()

    def _ensure_csv_headers(self):
        """Create CSV files with headers if they don't exist."""
        # Entry observations CSV
        if not os.path.exists(RL_ENTRY_OBS_LOG_PATH):
            entry_header = (
                ['timestamp', 'symbol', 'signal_type', 'rl_action', 'rl_confidence']
                + [f'obs_{i}' for i in range(ENTRY_OBS_DIM)]
            )
            self._write_header(RL_ENTRY_OBS_LOG_PATH, entry_header)

        # Exit observations CSV
        if not os.path.exists(RL_EXIT_OBS_LOG_PATH):
            exit_header = (
                ['timestamp', 'symbol', 'exit_signal_type', 'rl_action', 'rl_confidence']
                + [f'obs_{i}' for i in range(EXIT_OBS_DIM)]
            )
            self._write_header(RL_EXIT_OBS_LOG_PATH, exit_header)

        # Trade log (outcomes) CSV
        if not os.path.exists(RL_TRADE_LOG_PATH):
            trade_header = [
                'timestamp', 'symbol', 'options_name', 'signal_type',
                'entry_time', 'exit_time', 'entry_price', 'exit_price',
                'qty', 'pnl', 'pnl_pct', 'exit_reason', 'sl', 'tsl', 'target'
            ]
            self._write_header(RL_TRADE_LOG_PATH, trade_header)

        # Skip observations CSV
        if not os.path.exists(RL_SKIP_LOG_PATH):
            skip_header = (
                ['timestamp', 'symbol', 'signal_type', 'hypothetical_entry_price']
                + [f'obs_{i}' for i in range(ENTRY_OBS_DIM)]
            )
            self._write_header(RL_SKIP_LOG_PATH, skip_header)

    def _write_header(self, filepath, header):
        """Write CSV header row."""
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)
        except Exception as e:
            print(f"[RL Logger] Error writing header to {filepath}: {e}")

    def log_entry_observation(self, symbol, observation, signal_type, rl_action=-1, rl_confidence=0.0):
        """
        Log the observation vector at an entry decision point.

        Args:
            symbol: Stock symbol (e.g., 'KOTAKBANK')
            observation: np.ndarray of shape (ENTRY_OBS_DIM,)
            signal_type: 'CE' or 'PE'
            rl_action: Action taken by RL agent (-1 if RL disabled)
            rl_confidence: Confidence of RL decision
        """
        try:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row = [timestamp, symbol, signal_type, rl_action, f'{rl_confidence:.4f}']
            if observation is not None:
                row.extend([f'{v:.6f}' for v in observation])
            else:
                row.extend(['0.0'] * ENTRY_OBS_DIM)

            self._append_row(RL_ENTRY_OBS_LOG_PATH, row)
        except Exception as e:
            print(f"[RL Logger] Error logging entry observation: {e}")

    def log_exit_observation(self, symbol, observation, exit_signal_type, rl_action=-1, rl_confidence=0.0):
        """
        Log the observation vector at an exit decision point.

        Args:
            symbol: Stock symbol
            observation: np.ndarray of shape (EXIT_OBS_DIM,)
            exit_signal_type: e.g., 'rsi_below_ma_rsi', 'close_below_longstop'
            rl_action: Action taken by RL agent (-1 if RL disabled)
            rl_confidence: Confidence of RL decision
        """
        try:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row = [timestamp, symbol, exit_signal_type, rl_action, f'{rl_confidence:.4f}']
            if observation is not None:
                row.extend([f'{v:.6f}' for v in observation])
            else:
                row.extend(['0.0'] * EXIT_OBS_DIM)

            self._append_row(RL_EXIT_OBS_LOG_PATH, row)
        except Exception as e:
            print(f"[RL Logger] Error logging exit observation: {e}")

    def log_trade_completion(self, symbol, orderbook_entry, exit_reason):
        """
        Log a completed trade outcome for training the reward function.

        Args:
            symbol: Stock symbol
            orderbook_entry: dict with trade data (entry_price, exit_price, qty, pnl, etc.)
            exit_reason: e.g., 'Stop_Loss_Hit', 'Target_Reached', 'RSI_Below_MA_Exit', 'Time_Exit_Loss'
        """
        try:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            entry_price = orderbook_entry.get('entry_price', 0)
            exit_price = orderbook_entry.get('exit_price', 0)
            qty = orderbook_entry.get('qty', 0)
            pnl = orderbook_entry.get('pnl', 0)
            sl = orderbook_entry.get('sl', 0)
            tsl = orderbook_entry.get('tsl', 0)

            # Calculate P&L percentage
            pnl_pct = 0.0
            if entry_price and entry_price > 0 and qty and qty > 0:
                pnl_pct = pnl / (entry_price * qty)

            # Calculate target (3:1 risk-reward)
            risk = entry_price - sl if (entry_price and sl and entry_price > sl > 0) else 0
            target = entry_price + (risk * 3) if risk > 0 else 0

            # Determine signal type from options_name
            options_name = orderbook_entry.get('options_name', '')
            signal_type = 'CE' if 'CALL' in str(options_name).upper() else 'PE'

            row = [
                timestamp, symbol, options_name, signal_type,
                orderbook_entry.get('entry_time', ''),
                orderbook_entry.get('exit_time', ''),
                f'{entry_price:.2f}' if entry_price else '0',
                f'{exit_price:.2f}' if exit_price else '0',
                qty,
                f'{pnl:.2f}' if pnl else '0',
                f'{pnl_pct:.6f}',
                exit_reason,
                f'{sl:.2f}' if sl else '0',
                f'{tsl:.2f}' if tsl else '0',
                f'{target:.2f}' if target else '0'
            ]

            self._append_row(RL_TRADE_LOG_PATH, row)
            print(f"[RL Logger] Trade logged: {symbol} | {exit_reason} | PnL: {pnl:.2f}")

        except Exception as e:
            print(f"[RL Logger] Error logging trade completion: {e}")

    def log_skip_observation(self, symbol, observation, signal_type, hypothetical_entry_price=0.0):
        """
        Log observation for a trade the RL agent decided to skip.
        Used for counterfactual learning.

        Args:
            symbol: Stock symbol
            observation: np.ndarray of shape (ENTRY_OBS_DIM,)
            signal_type: 'CE' or 'PE'
            hypothetical_entry_price: What the entry price would have been
        """
        try:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row = [timestamp, symbol, signal_type, f'{hypothetical_entry_price:.2f}']
            if observation is not None:
                row.extend([f'{v:.6f}' for v in observation])
            else:
                row.extend(['0.0'] * ENTRY_OBS_DIM)

            self._append_row(RL_SKIP_LOG_PATH, row)
        except Exception as e:
            print(f"[RL Logger] Error logging skip observation: {e}")

    def _append_row(self, filepath, row):
        """Append a row to a CSV file (thread-safe with simple file append)."""
        try:
            with open(filepath, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            print(f"[RL Logger] Error appending to {filepath}: {e}")

    def get_trade_count(self):
        """Get the number of completed trades logged."""
        try:
            if not os.path.exists(RL_TRADE_LOG_PATH):
                return 0
            with open(RL_TRADE_LOG_PATH, 'r') as f:
                return sum(1 for _ in f) - 1  # Subtract header
        except Exception:
            return 0
