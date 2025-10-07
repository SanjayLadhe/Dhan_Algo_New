# -*- coding: utf-8 -*-
"""
Paper Trading Test Script - Fixed for Windows Encoding
=======================================================

This script tests the paper trading simulator without running the full bot.
Use this to verify everything is working correctly.
"""

import sys
import io
sys.stdout.reconfigure(encoding='utf-8')

# ============================
# FIX WINDOWS CONSOLE ENCODING
# ============================
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import time
from paper_trading_wrapper import get_trading_instance, print_paper_trading_summary

# ============================
# CONFIGURATION
# ============================
client_code = "1106090196"
token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU5ODExNTE3LCJpYXQiOjE3NTk3MjUxMTcsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.qkI4lnw8cOtmo5MPnm67kGMpB5r40gkG3StTMkaLh-W1REV4nuRvB9XrifQQSNuewrK1aXIO1-CO8UVLKD7Faw"


def test_paper_trading():
    """Test paper trading functionality"""
    
    print("\n" + "="*80)
    print("PAPER TRADING TEST SCRIPT")
    print("="*80)
    
    # Initialize trading instance (will use paper trading if enabled)
    print("\n[1] Initializing trading instance...")
    tsl = get_trading_instance(client_code, token_id)
    
    # Test: Get balance
    print("\n[2] Testing balance query...")
    balance = tsl.get_balance()
    print(f"   Current Balance: Rs.{balance:,.2f}")
    
    # Test: Get historical data (should use real API)
    print("\n[3] Testing historical data fetch...")
    try:
        data = tsl.get_historical_data(tradingsymbol="RELIANCE", exchange="NSE", timeframe="1")
        if data is not None and not data.empty:
            print(f"   [OK] Historical data fetched: {len(data)} candles")
            print(f"   Latest close: Rs.{data['close'].iloc[-1]:.2f}")
        else:
            print("   [WARN] No data returned")
    except Exception as e:
        print(f"   [X] Error: {e}")
    
    # Test: Simulate a paper trade
    print("\n[4] Simulating paper trade...")
    try:
        # Place BUY order
        print("   [DATA] Placing BUY order...")
        order_id = tsl.order_placement(
            tradingsymbol="RELIANCE25APR2425500CE",
            exchange="NFO",
            quantity=25,
            price=0,
            trigger_price=0,
            order_type="MARKET",
            transaction_type="BUY",
            trade_type="MIS"
        )
        print(f"   [OK] Order placed: {order_id}")
        
        # Get executed price
        print("   [DATA] Getting executed price...")
        exec_price = tsl.get_executed_price(orderid=order_id)
        print(f"   [OK] Executed at: Rs.{exec_price:.2f}")
        
        # Place stop loss order
        print("   [DATA] Placing STOP LOSS order...")
        sl_order_id = tsl.order_placement(
            tradingsymbol="RELIANCE25APR2425500CE",
            exchange="NFO",
            quantity=25,
            price=exec_price - 5.0,
            trigger_price=exec_price - 4.0,
            order_type="STOPLIMIT",
            transaction_type="SELL",
            trade_type="MIS"
        )
        print(f"   [OK] SL order placed: {sl_order_id}")
        
        # Modify SL order (trailing stop loss)
        print("   [DATA] Modifying SL order (TSL update)...")
        tsl.modify_order(
            order_id=sl_order_id,
            order_type="STOPLIMIT",
            quantity=25,
            price=exec_price - 2.0,
            trigger_price=exec_price - 1.0
        )
        print(f" SL order modified")
        
        # Place exit order
        print(f" Placing EXIT order...")
        exit_order_id = tsl.order_placement(
            tradingsymbol="RELIANCE25APR2425500CE",
            exchange="NFO",
            quantity=25,
            price=0,
            trigger_price=0,
            order_type="MARKET",
            transaction_type="SELL",
            trade_type="MIS"
        )
        print(f" [OK] Exit order placed: {exit_order_id}")
        
        # Get exit price
        exit_price = tsl.get_executed_price(orderid=exit_order_id)
        print(f" [OK] Exited at: Rs.{exit_price:.2f}")
        
        # Calculate P&L
        pnl = (exit_price - exec_price) * 25
        print(f" [MONEY] P&L: Rs.{pnl:+,.2f}")
        
    except Exception as e:
        print(f" [X] Error during trade simulation: {e}")
        import traceback
        traceback.print_exc()
    
    # Show summary
    print("\n[5] Paper Trading Summary:")
    print_paper_trading_summary(tsl)
    
    print("\n" + "="*80)
    print("[OK] PAPER TRADING TEST COMPLETE")
    print("="*80)
    print("\n[NOTE] Check 'paper_trading_log.txt' for detailed logs")
    print("[DATA] Now you can run your full bot with paper trading enabled!\n")


def main():
    """Main function"""
    
    # Check if paper trading is enabled
    import paper_trading_config as pt_config
    
    if not pt_config.PAPER_TRADING_ENABLED:
        print("\n" + "="*80)
        print("[WARN] WARNING: Paper Trading is DISABLED")
        print("="*80)
        print("\nTo enable paper trading:")
        print("1. Open 'paper_trading_config.py'")
        print("2. Set: PAPER_TRADING_ENABLED = True")
        print("3. Run this script again")
        print("\n" + "="*80 + "\n")
        
        response = input("Do you want to continue with LIVE trading test? (yes/no): ")
        if response.lower() != 'yes':
            print("\n[X] Test cancelled. Please enable paper trading first.")
            return
    
    # Run test
    test_paper_trading()


if __name__ == "__main__":
    main()