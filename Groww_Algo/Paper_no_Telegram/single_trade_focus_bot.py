"""
Groww Algo Trading Bot - Single Trade Focus Bot

This is the main trading bot for the Groww broker platform.
Adapted from Dhan_Algo_New for compatibility with Groww API.

Features:
- Multi-position trading (configurable max simultaneous positions)
- Dynamic watchlist from sector performance analysis
- Technical indicator-based entry signals (VWAP, ATR, ADX, Fractal)
- Options trading (CE/PE) with risk management
- Stop loss and trailing stop loss management
- Paper trading mode for testing

Groww API Documentation: https://groww.in/trade-api/docs/python-sdk
Package: pip install growwapi (version 1.5.0+)

Author: Algo Trading Bot
Date: 2026
"""

# =============================================================================
# IMPORTS
# =============================================================================

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Groww API Wrapper
# For Paper Trading: Replace with paper_trading_wrapper
from Groww_Tradehull import Tradehull
# Uncomment for paper trading:
# from paper_trading_wrapper import get_trading_instance

# Entry/Exit Logic Modules
from ce_entry_logic import execute_ce_entry, check_ce_entry_conditions
from pe_entry_logic import execute_pe_entry, check_pe_entry_conditions
from exit_logic import check_exit_conditions, execute_exit, update_trailing_stop

# Technical Indicators
from VWAP import calculate_vwap
from ATRTrailingStop import calculate_atr, calculate_atr_trailing_stop
from adx_indicator import calculate_adx
from Fractal_Chaos_Bands import calculate_fractal_chaos_bands

# Utility Modules
from rate_limiter import RateLimiter, get_data_api_limiter, get_order_api_limiter
from websocket_manager import WebSocketManager
from SectorPerformanceAnalyzer import get_dynamic_watchlist

# Paper Trading Config
from paper_trading_config import PAPER_TRADING_ENABLED

# Trade Logger for Excel export
from trade_logger import TradeLogger, init_trade_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Trade logger instance
trade_logger: TradeLogger = None

# =============================================================================
# CONFIGURATION
# =============================================================================

# API Credentials (Replace with your actual credentials)
# Get your API key from: https://groww.in/trade-api
API_KEY = "YOUR_GROWW_API_KEY"
API_SECRET = "YOUR_GROWW_API_SECRET"  # Optional

# Trading Parameters
OPENING_BALANCE = 1005000           # Account opening balance
BASE_CAPITAL = 1000000              # Base capital for risk calculation
MARKET_MONEY_RISK_PCT = 0.01        # 1% risk on market gains
BASE_CAPITAL_RISK_PCT = 0.005       # 0.5% risk on base capital

MAX_ORDERS_TODAY = 2                # Maximum orders per day
MAX_SIMULTANEOUS_POSITIONS = 2      # Maximum simultaneous positions

RISK_PER_TRADE = None               # Calculated dynamically

ATR_MULTIPLIER = 3                  # ATR multiplier for stop loss
RISK_REWARD_RATIO = 3               # Risk to reward ratio
OPTION_SL_PERCENTAGE = 0.15         # 15% stop loss for options

# Timing Configuration
MONITOR_INTERVAL = 5                # Seconds between position checks
SCAN_INTERVAL = 30                  # Seconds between entry scans
WATCHLIST_REFRESH_INTERVAL = 900    # 15 minutes (900 seconds)

# Market Hours (IST)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30

# No new trades after this time
NO_NEW_TRADE_HOUR = 14
NO_NEW_TRADE_MINUTE = 45

# =============================================================================
# GLOBAL VARIABLES
# =============================================================================

# Trading instance
tsl = None

# Active positions tracking
active_positions: Dict[str, Dict] = {}

# Today's statistics
todays_orders = 0
todays_pnl = 0.0

# Watchlist
watchlist: List[str] = []
last_watchlist_refresh = None

# WebSocket manager
ws_manager = None

# Rate limiters
data_limiter = None
order_limiter = None

# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize_bot():
    """Initialize the trading bot."""
    global tsl, ws_manager, data_limiter, order_limiter, watchlist
    global RISK_PER_TRADE, trade_logger

    logger.info("=" * 60)
    logger.info("GROWW ALGO TRADING BOT - INITIALIZATION")
    logger.info("=" * 60)

    # Initialize trade logger for Excel export
    trade_logger = init_trade_logger(log_dir="logs", excel_file="trade_log.xlsx")
    logger.info(f"Trade Logger initialized - Excel: logs/trade_log.xlsx")

    # Calculate risk parameters
    market_gains = OPENING_BALANCE - BASE_CAPITAL
    market_risk = market_gains * MARKET_MONEY_RISK_PCT if market_gains > 0 else 0
    base_risk = BASE_CAPITAL * BASE_CAPITAL_RISK_PCT
    max_risk_today = market_risk + base_risk
    RISK_PER_TRADE = max_risk_today / MAX_ORDERS_TODAY

    logger.info(f"Opening Balance: {OPENING_BALANCE:,.2f}")
    logger.info(f"Max Risk Today: {max_risk_today:,.2f}")
    logger.info(f"Risk Per Trade: {RISK_PER_TRADE:,.2f}")
    logger.info(f"Max Simultaneous Positions: {MAX_SIMULTANEOUS_POSITIONS}")

    # Initialize Groww API
    if PAPER_TRADING_ENABLED:
        logger.info("Paper Trading Mode: ENABLED")
        from paper_trading_wrapper import get_trading_instance
        tsl = get_trading_instance(API_KEY, API_SECRET)
    else:
        logger.info("Live Trading Mode: ENABLED")
        tsl = Tradehull(API_KEY, API_SECRET)

    # Initialize rate limiters
    data_limiter = get_data_api_limiter()
    order_limiter = get_order_api_limiter()

    # Initialize WebSocket manager
    ws_manager = WebSocketManager(API_KEY)

    # Get initial watchlist
    watchlist = get_dynamic_watchlist()
    logger.info(f"Watchlist loaded: {len(watchlist)} symbols")

    logger.info("Bot initialization complete!")
    logger.info("=" * 60)

    return True


def is_market_hours() -> bool:
    """Check if current time is within market hours."""
    now = datetime.now()
    market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0)
    market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0)

    return market_open <= now <= market_close


def can_place_new_trade() -> bool:
    """Check if new trades are allowed."""
    now = datetime.now()
    cutoff = now.replace(hour=NO_NEW_TRADE_HOUR, minute=NO_NEW_TRADE_MINUTE, second=0)

    if now > cutoff:
        return False

    if todays_orders >= MAX_ORDERS_TODAY:
        return False

    if len(active_positions) >= MAX_SIMULTANEOUS_POSITIONS:
        return False

    return True


# =============================================================================
# POSITION MANAGEMENT
# =============================================================================

def add_position(
    symbol: str,
    order_id: str,
    entry_price: float,
    quantity: int,
    option_type: str,
    stop_loss: float,
    target: float
) -> None:
    """Add a new position to tracking."""
    global todays_orders

    active_positions[symbol] = {
        "order_id": order_id,
        "entry_price": entry_price,
        "quantity": quantity,
        "option_type": option_type,
        "stop_loss": stop_loss,
        "target": target,
        "trailing_stop": stop_loss,
        "entry_time": datetime.now(),
        "highest_price": entry_price,
        "lowest_price": entry_price
    }

    todays_orders += 1
    logger.info(f"Position added: {symbol} @ {entry_price}")
    logger.info(f"  SL: {stop_loss}, Target: {target}, Qty: {quantity}")

    # Log to trade logger for Excel export
    if trade_logger:
        trade_logger.log_order(
            order_id=order_id,
            symbol=symbol,
            transaction_type="BUY",
            quantity=quantity,
            order_type="MARKET",
            price=entry_price,
            status="COMPLETE",
            option_type=option_type
        )
        trade_logger.log_trade(
            trade_id=f"TRD_{order_id}",
            order_id=order_id,
            symbol=symbol,
            transaction_type="BUY",
            quantity=quantity,
            executed_price=entry_price
        )
        trade_logger.log_position_open(
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            target=target,
            option_type=option_type
        )


def remove_position(symbol: str, exit_price: float, reason: str) -> float:
    """Remove a position and calculate P&L."""
    global todays_pnl

    if symbol not in active_positions:
        logger.warning(f"Position not found: {symbol}")
        return 0.0

    position = active_positions[symbol]
    entry_price = position["entry_price"]
    quantity = position["quantity"]

    pnl = (exit_price - entry_price) * quantity
    todays_pnl += pnl

    logger.info(f"Position closed: {symbol}")
    logger.info(f"  Entry: {entry_price}, Exit: {exit_price}")
    logger.info(f"  P&L: {pnl:,.2f}, Reason: {reason}")

    # Log to trade logger for Excel export
    if trade_logger:
        trade_logger.log_order(
            order_id=f"EXIT_{position['order_id']}",
            symbol=symbol,
            transaction_type="SELL",
            quantity=quantity,
            order_type="MARKET",
            price=exit_price,
            status="COMPLETE",
            exit_reason=reason
        )
        trade_logger.log_trade(
            trade_id=f"TRD_EXIT_{position['order_id']}",
            order_id=f"EXIT_{position['order_id']}",
            symbol=symbol,
            transaction_type="SELL",
            quantity=quantity,
            executed_price=exit_price
        )
        trade_logger.log_position_close(
            symbol=symbol,
            exit_price=exit_price,
            exit_reason=reason
        )

    # Unsubscribe from WebSocket
    if ws_manager:
        ws_manager.unsubscribe(symbol)

    del active_positions[symbol]
    return pnl


# =============================================================================
# ENTRY LOGIC
# =============================================================================

def scan_for_entry():
    """Scan watchlist for entry opportunities."""
    global watchlist, last_watchlist_refresh

    if not can_place_new_trade():
        return

    # Refresh watchlist periodically
    now = datetime.now()
    if (last_watchlist_refresh is None or
        (now - last_watchlist_refresh).total_seconds() > WATCHLIST_REFRESH_INTERVAL):
        watchlist = get_dynamic_watchlist()
        last_watchlist_refresh = now
        logger.info(f"Watchlist refreshed: {len(watchlist)} symbols")

    logger.debug(f"Scanning {len(watchlist)} symbols for entry...")

    for symbol in watchlist:
        if symbol in active_positions:
            continue

        try:
            # Rate limit API calls
            data_limiter.wait_if_needed()

            # Get candle data
            df = tsl.get_candles(symbol, tsl.NSE, "5m", 100)

            if df.empty or len(df) < 50:
                continue

            # Calculate indicators
            df = calculate_vwap(df)
            df = calculate_atr(df)
            df = calculate_adx(df)
            df = calculate_fractal_chaos_bands(df)

            # Check CE entry conditions
            ce_signal = check_ce_entry_conditions(df, symbol, tsl)
            if ce_signal["valid"]:
                execute_ce_trade(symbol, df, ce_signal)
                if not can_place_new_trade():
                    return

            # Check PE entry conditions
            pe_signal = check_pe_entry_conditions(df, symbol, tsl)
            if pe_signal["valid"]:
                execute_pe_trade(symbol, df, pe_signal)
                if not can_place_new_trade():
                    return

            # Rate limit between symbols
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            continue


def execute_ce_trade(symbol: str, df: pd.DataFrame, signal: Dict) -> None:
    """Execute a CE (Call) trade."""
    try:
        logger.info(f"CE Entry Signal for {symbol}")

        result = execute_ce_entry(
            tsl=tsl,
            symbol=symbol,
            df=df,
            signal=signal,
            risk_per_trade=RISK_PER_TRADE,
            atr_multiplier=ATR_MULTIPLIER,
            option_sl_pct=OPTION_SL_PERCENTAGE
        )

        if result["success"]:
            add_position(
                symbol=result["option_symbol"],
                order_id=result["order_id"],
                entry_price=result["entry_price"],
                quantity=result["quantity"],
                option_type="CE",
                stop_loss=result["stop_loss"],
                target=result["target"]
            )

            # Subscribe to WebSocket for live updates
            if ws_manager:
                ws_manager.subscribe(result["option_symbol"])

    except Exception as e:
        logger.error(f"CE trade execution error: {e}")


def execute_pe_trade(symbol: str, df: pd.DataFrame, signal: Dict) -> None:
    """Execute a PE (Put) trade."""
    try:
        logger.info(f"PE Entry Signal for {symbol}")

        result = execute_pe_entry(
            tsl=tsl,
            symbol=symbol,
            df=df,
            signal=signal,
            risk_per_trade=RISK_PER_TRADE,
            atr_multiplier=ATR_MULTIPLIER,
            option_sl_pct=OPTION_SL_PERCENTAGE
        )

        if result["success"]:
            add_position(
                symbol=result["option_symbol"],
                order_id=result["order_id"],
                entry_price=result["entry_price"],
                quantity=result["quantity"],
                option_type="PE",
                stop_loss=result["stop_loss"],
                target=result["target"]
            )

            # Subscribe to WebSocket for live updates
            if ws_manager:
                ws_manager.subscribe(result["option_symbol"])

    except Exception as e:
        logger.error(f"PE trade execution error: {e}")


# =============================================================================
# EXIT LOGIC
# =============================================================================

def monitor_positions():
    """Monitor active positions for exit conditions."""
    if not active_positions:
        return

    logger.debug(f"Monitoring {len(active_positions)} active positions...")

    for symbol, position in list(active_positions.items()):
        try:
            # Get current price
            current_price = ws_manager.get_ltp(symbol) if ws_manager else 0

            if current_price == 0:
                data_limiter.wait_if_needed()
                current_price = tsl.get_ltp(symbol, tsl.NFO)

            if current_price == 0:
                logger.warning(f"Could not get price for {symbol}")
                continue

            # Update high/low tracking
            position["highest_price"] = max(position["highest_price"], current_price)
            position["lowest_price"] = min(position["lowest_price"], current_price)

            # Check exit conditions
            exit_signal = check_exit_conditions(
                position=position,
                current_price=current_price,
                option_type=position["option_type"]
            )

            if exit_signal["should_exit"]:
                execute_position_exit(symbol, current_price, exit_signal["reason"])
            else:
                # Update trailing stop if applicable
                new_tsl = update_trailing_stop(
                    position=position,
                    current_price=current_price,
                    atr_multiplier=ATR_MULTIPLIER
                )
                if new_tsl > position["trailing_stop"]:
                    old_tsl = position["trailing_stop"]
                    position["trailing_stop"] = new_tsl
                    logger.info(f"TSL updated for {symbol}: {new_tsl:.2f}")
                    if trade_logger:
                        trade_logger.log_tsl_update(symbol, old_tsl, new_tsl)

        except Exception as e:
            logger.error(f"Error monitoring {symbol}: {e}")


def execute_position_exit(symbol: str, exit_price: float, reason: str) -> None:
    """Execute position exit."""
    try:
        position = active_positions[symbol]

        result = execute_exit(
            tsl=tsl,
            symbol=symbol,
            quantity=position["quantity"],
            exit_price=exit_price
        )

        if result["success"]:
            remove_position(symbol, result["executed_price"], reason)
        else:
            logger.error(f"Exit failed for {symbol}: {result['message']}")

    except Exception as e:
        logger.error(f"Exit execution error: {e}")


# =============================================================================
# MAIN TRADING LOOP
# =============================================================================

def run_trading_loop():
    """Main trading loop."""
    logger.info("Starting trading loop...")

    last_scan_time = None
    last_monitor_time = None

    while True:
        try:
            now = datetime.now()

            # Check market hours
            if not is_market_hours():
                if now.hour >= MARKET_CLOSE_HOUR:
                    logger.info("Market closed. Ending session.")
                    break
                else:
                    logger.info("Waiting for market to open...")
                    time.sleep(60)
                    continue

            # Monitor existing positions
            if active_positions:
                if (last_monitor_time is None or
                    (now - last_monitor_time).total_seconds() >= MONITOR_INTERVAL):
                    monitor_positions()
                    last_monitor_time = now

            # Scan for new entries
            if can_place_new_trade():
                if (last_scan_time is None or
                    (now - last_scan_time).total_seconds() >= SCAN_INTERVAL):
                    scan_for_entry()
                    last_scan_time = now

            # Short sleep to prevent CPU overload
            time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)

    # End of day summary
    print_session_summary()


def print_session_summary():
    """Print end of session summary."""
    logger.info("=" * 60)
    logger.info("SESSION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Orders: {todays_orders}")
    logger.info(f"Total P&L: {todays_pnl:,.2f}")
    logger.info(f"Open Positions: {len(active_positions)}")

    if active_positions:
        logger.info("\nOpen Positions:")
        for symbol, pos in active_positions.items():
            logger.info(f"  {symbol}: Entry={pos['entry_price']:.2f}, "
                       f"TSL={pos['trailing_stop']:.2f}")

    logger.info("=" * 60)

    # Print trade logger summary with Excel file location
    if trade_logger:
        trade_logger.print_summary()
        logger.info(f"Trade log Excel file: {trade_logger.excel_file}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point."""
    print("""
    ============================================
    GROWW ALGO TRADING BOT
    ============================================

    Groww API Documentation:
    https://groww.in/trade-api/docs/python-sdk

    Package: pip install growwapi

    ============================================
    """)

    # Check if paper trading
    if PAPER_TRADING_ENABLED:
        print("MODE: PAPER TRADING (Simulated)")
    else:
        print("MODE: LIVE TRADING (Real Money)")

    print(f"\nStarting at: {datetime.now()}")
    print("-" * 50)

    try:
        # Initialize
        if not initialize_bot():
            logger.error("Bot initialization failed!")
            return

        # Run trading loop
        run_trading_loop()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
