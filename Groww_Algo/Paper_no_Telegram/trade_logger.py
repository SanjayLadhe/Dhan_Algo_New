"""
Trade Logger Module - Comprehensive Logging and Excel Export

This module provides:
1. Detailed logging of all trading activities
2. Excel export of orders, trades, and P&L
3. Real-time trade tracking

Author: Algo Trading Bot
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
from pathlib import Path

# Configure detailed logger
logger = logging.getLogger(__name__)


class TradeLogger:
    """
    Comprehensive trade logging and Excel export.

    Tracks all orders, executions, and P&L with export to Excel.
    """

    def __init__(self, log_dir: str = "logs", excel_file: str = "trade_log.xlsx"):
        """
        Initialize Trade Logger.

        Args:
            log_dir: Directory for log files
            excel_file: Excel file name for trade export
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        self.excel_file = self.log_dir / excel_file

        # Initialize data storage
        self.orders: List[Dict] = []
        self.trades: List[Dict] = []
        self.positions: List[Dict] = []
        self.pnl_history: List[Dict] = []

        # Session info
        self.session_start = datetime.now()
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")

        # Setup file logging
        self._setup_file_logging()

        logger.info(f"Trade Logger initialized - Session: {self.session_id}")
        logger.info(f"Excel export file: {self.excel_file}")

    def _setup_file_logging(self):
        """Setup detailed file logging."""
        log_file = self.log_dir / f"trading_{self.session_id}.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Add to root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        logger.info(f"Log file: {log_file}")

    def log_order(
        self,
        order_id: str,
        symbol: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        price: float,
        status: str,
        **kwargs
    ):
        """
        Log an order.

        Args:
            order_id: Order ID
            symbol: Trading symbol
            transaction_type: BUY/SELL
            quantity: Order quantity
            order_type: MARKET/LIMIT/SL
            price: Order price
            status: Order status
            **kwargs: Additional order details
        """
        order_record = {
            "timestamp": datetime.now(),
            "order_id": order_id,
            "symbol": symbol,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "order_type": order_type,
            "price": price,
            "status": status,
            "session_id": self.session_id,
            **kwargs
        }

        self.orders.append(order_record)

        # Log to file
        logger.info(f"ORDER | {transaction_type} | {symbol} | Qty: {quantity} | "
                   f"Price: {price:.2f} | Type: {order_type} | Status: {status} | "
                   f"ID: {order_id}")

        # Auto-save to Excel
        self._save_to_excel()

    def log_trade(
        self,
        trade_id: str,
        order_id: str,
        symbol: str,
        transaction_type: str,
        quantity: int,
        executed_price: float,
        **kwargs
    ):
        """
        Log an executed trade.

        Args:
            trade_id: Trade ID
            order_id: Related order ID
            symbol: Trading symbol
            transaction_type: BUY/SELL
            quantity: Executed quantity
            executed_price: Execution price
            **kwargs: Additional trade details
        """
        trade_record = {
            "timestamp": datetime.now(),
            "trade_id": trade_id,
            "order_id": order_id,
            "symbol": symbol,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "executed_price": executed_price,
            "value": quantity * executed_price,
            "session_id": self.session_id,
            **kwargs
        }

        self.trades.append(trade_record)

        logger.info(f"TRADE | {transaction_type} | {symbol} | Qty: {quantity} | "
                   f"Executed: {executed_price:.2f} | Value: {quantity * executed_price:.2f}")

        self._save_to_excel()

    def log_position_open(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        stop_loss: float,
        target: float,
        option_type: str = "",
        **kwargs
    ):
        """
        Log position opening.

        Args:
            symbol: Trading symbol
            entry_price: Entry price
            quantity: Position quantity
            stop_loss: Stop loss price
            target: Target price
            option_type: CE/PE for options
            **kwargs: Additional details
        """
        position_record = {
            "open_time": datetime.now(),
            "close_time": None,
            "symbol": symbol,
            "entry_price": entry_price,
            "exit_price": None,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "target": target,
            "option_type": option_type,
            "status": "OPEN",
            "pnl": 0,
            "pnl_pct": 0,
            "exit_reason": None,
            "session_id": self.session_id,
            **kwargs
        }

        self.positions.append(position_record)

        logger.info("=" * 60)
        logger.info(f"POSITION OPENED: {symbol}")
        logger.info(f"  Entry Price: {entry_price:.2f}")
        logger.info(f"  Quantity: {quantity}")
        logger.info(f"  Stop Loss: {stop_loss:.2f} ({((stop_loss/entry_price)-1)*100:.1f}%)")
        logger.info(f"  Target: {target:.2f} ({((target/entry_price)-1)*100:.1f}%)")
        logger.info(f"  Option Type: {option_type}")
        logger.info("=" * 60)

        self._save_to_excel()

    def log_position_close(
        self,
        symbol: str,
        exit_price: float,
        exit_reason: str
    ):
        """
        Log position closing.

        Args:
            symbol: Trading symbol
            exit_price: Exit price
            exit_reason: Reason for exit (SL/TARGET/TSL/MANUAL)
        """
        # Find the open position
        for pos in self.positions:
            if pos["symbol"] == symbol and pos["status"] == "OPEN":
                pos["close_time"] = datetime.now()
                pos["exit_price"] = exit_price
                pos["status"] = "CLOSED"
                pos["exit_reason"] = exit_reason

                # Calculate P&L
                entry = pos["entry_price"]
                qty = pos["quantity"]
                pos["pnl"] = (exit_price - entry) * qty
                pos["pnl_pct"] = ((exit_price / entry) - 1) * 100

                # Log P&L history
                self.pnl_history.append({
                    "timestamp": datetime.now(),
                    "symbol": symbol,
                    "pnl": pos["pnl"],
                    "pnl_pct": pos["pnl_pct"],
                    "exit_reason": exit_reason
                })

                logger.info("=" * 60)
                logger.info(f"POSITION CLOSED: {symbol}")
                logger.info(f"  Entry: {entry:.2f} | Exit: {exit_price:.2f}")
                logger.info(f"  P&L: {pos['pnl']:.2f} ({pos['pnl_pct']:.1f}%)")
                logger.info(f"  Reason: {exit_reason}")
                logger.info("=" * 60)

                break

        self._save_to_excel()

    def log_tsl_update(self, symbol: str, old_tsl: float, new_tsl: float):
        """Log trailing stop loss update."""
        logger.info(f"TSL UPDATE | {symbol} | Old: {old_tsl:.2f} -> New: {new_tsl:.2f}")

    def log_scan(self, symbol: str, signal_type: str, details: Dict):
        """Log market scan results."""
        logger.debug(f"SCAN | {symbol} | Signal: {signal_type} | {details}")

    def log_indicator(self, symbol: str, indicators: Dict):
        """Log indicator values."""
        logger.debug(f"INDICATORS | {symbol} | {indicators}")

    def _save_to_excel(self):
        """Save all data to Excel file."""
        try:
            with pd.ExcelWriter(self.excel_file, engine='openpyxl') as writer:
                # Orders sheet
                if self.orders:
                    orders_df = pd.DataFrame(self.orders)
                    orders_df.to_excel(writer, sheet_name='Orders', index=False)

                # Trades sheet
                if self.trades:
                    trades_df = pd.DataFrame(self.trades)
                    trades_df.to_excel(writer, sheet_name='Trades', index=False)

                # Positions sheet
                if self.positions:
                    positions_df = pd.DataFrame(self.positions)
                    positions_df.to_excel(writer, sheet_name='Positions', index=False)

                # P&L History sheet
                if self.pnl_history:
                    pnl_df = pd.DataFrame(self.pnl_history)
                    pnl_df.to_excel(writer, sheet_name='PnL_History', index=False)

                # Summary sheet
                summary_data = self._generate_summary()
                summary_df = pd.DataFrame([summary_data])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

            logger.debug(f"Excel saved: {self.excel_file}")

        except Exception as e:
            logger.error(f"Error saving Excel: {e}")

    def _generate_summary(self) -> Dict:
        """Generate trading session summary."""
        total_trades = len([p for p in self.positions if p["status"] == "CLOSED"])
        winning = len([p for p in self.positions if p["status"] == "CLOSED" and p["pnl"] > 0])
        losing = len([p for p in self.positions if p["status"] == "CLOSED" and p["pnl"] < 0])

        total_pnl = sum(p["pnl"] for p in self.positions if p["status"] == "CLOSED")

        return {
            "session_id": self.session_id,
            "session_start": self.session_start,
            "last_update": datetime.now(),
            "total_orders": len(self.orders),
            "total_trades": total_trades,
            "open_positions": len([p for p in self.positions if p["status"] == "OPEN"]),
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": (winning / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": total_pnl,
            "avg_pnl_per_trade": total_pnl / total_trades if total_trades > 0 else 0
        }

    def print_summary(self):
        """Print trading session summary to console."""
        summary = self._generate_summary()

        print("\n" + "=" * 60)
        print("TRADING SESSION SUMMARY")
        print("=" * 60)
        print(f"Session ID:        {summary['session_id']}")
        print(f"Session Start:     {summary['session_start']}")
        print("-" * 60)
        print(f"Total Orders:      {summary['total_orders']}")
        print(f"Total Trades:      {summary['total_trades']}")
        print(f"Open Positions:    {summary['open_positions']}")
        print("-" * 60)
        print(f"Winning Trades:    {summary['winning_trades']}")
        print(f"Losing Trades:     {summary['losing_trades']}")
        print(f"Win Rate:          {summary['win_rate']:.1f}%")
        print("-" * 60)
        print(f"Total P&L:         {summary['total_pnl']:,.2f}")
        print(f"Avg P&L/Trade:     {summary['avg_pnl_per_trade']:,.2f}")
        print("=" * 60)
        print(f"\nExcel file: {self.excel_file}")
        print()

    def get_open_positions(self) -> List[Dict]:
        """Get list of open positions."""
        return [p for p in self.positions if p["status"] == "OPEN"]

    def get_closed_positions(self) -> List[Dict]:
        """Get list of closed positions."""
        return [p for p in self.positions if p["status"] == "CLOSED"]


# Global trade logger instance
_trade_logger: Optional[TradeLogger] = None


def get_trade_logger() -> TradeLogger:
    """Get or create global trade logger instance."""
    global _trade_logger
    if _trade_logger is None:
        _trade_logger = TradeLogger()
    return _trade_logger


def init_trade_logger(log_dir: str = "logs", excel_file: str = "trade_log.xlsx") -> TradeLogger:
    """Initialize global trade logger with custom settings."""
    global _trade_logger
    _trade_logger = TradeLogger(log_dir=log_dir, excel_file=excel_file)
    return _trade_logger


if __name__ == "__main__":
    # Test the trade logger
    print("Trade Logger Module Test")
    print("=" * 50)

    logger = TradeLogger()

    # Simulate some trades
    logger.log_order(
        order_id="TEST001",
        symbol="NIFTY 30JAN2026 24000 CE",
        transaction_type="BUY",
        quantity=25,
        order_type="MARKET",
        price=150.50,
        status="COMPLETE"
    )

    logger.log_trade(
        trade_id="TRD001",
        order_id="TEST001",
        symbol="NIFTY 30JAN2026 24000 CE",
        transaction_type="BUY",
        quantity=25,
        executed_price=151.00
    )

    logger.log_position_open(
        symbol="NIFTY 30JAN2026 24000 CE",
        entry_price=151.00,
        quantity=25,
        stop_loss=128.35,
        target=218.95,
        option_type="CE"
    )

    logger.print_summary()
    print(f"\nCheck Excel file: {logger.excel_file}")
