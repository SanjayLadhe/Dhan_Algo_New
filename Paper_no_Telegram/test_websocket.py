"""
WebSocket Testing Tool
======================

Standalone testing tool for Dhan WebSocket real-time market data.
Test by providing option symbol names directly.

Usage:
    python test_websocket.py

Features:
- Subscribe to multiple option symbols
- Real-time LTP, Bid, Ask updates
- Connection status monitoring
- Easy symbol addition/removal
"""

import time
import datetime
from websocket_manager import WebSocketMarketData

# ============================
# CONFIGURATION
# ============================

# Your Dhan credentials (same as in single_trade_focus_bot.py)
CLIENT_CODE = "1106090196"
TOKEN_ID = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzYwNTU3MDE0LCJpYXQiOjE3NjA0NzA2MTQsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.bqQgOLmUX0yO8qy7aZdnL8rsecUa1-3mDdq2KkUo_xJhrCWIDZZSpXmN12h6A1a3gF4SvABB-2c7MWS-gEPshg"

# ============================
# TEST SYMBOLS
# ============================
# Add your option symbols here to test
# Format: "UNDERLYING DD MMM STRIKE CALL/PUT"
# Example: "RELIANCE 28 OCT 1300 CALL"

TEST_SYMBOLS = [
    # "ICICIGI 28 OCT 1860 CALL",
    # "RELIANCE 28 OCT 1300 CALL",
    # "INFY 28 OCT 1900 PUT",
]

# How long to run the test (in seconds)
TEST_DURATION = 60  # 1 minute

# Update interval for status display (in seconds)
STATUS_UPDATE_INTERVAL = 5


def print_header():
    """Print test header"""
    print("\n" + "=" * 80)
    print("🔌 DHAN WEBSOCKET TESTING TOOL")
    print("=" * 80)
    print(f"📅 Test Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Test Duration: {TEST_DURATION} seconds")
    print(f"📊 Symbols to Test: {len(TEST_SYMBOLS)}")
    print("=" * 80 + "\n")


def print_symbol_data(ws_manager, symbol):
    """Print market data for a symbol"""
    data = ws_manager.get_market_data(symbol)

    if data and data.get('ltp', 0) > 0:
        ltp = data.get('ltp', 0)
        bid = data.get('bid_price', 0)
        ask = data.get('ask_price', 0)
        volume = data.get('volume', 0)
        last_update = data.get('last_update')

        # Calculate spread
        spread = ask - bid if (bid > 0 and ask > 0) else 0

        print(f"\n  📊 {symbol}")
        print(f"  {'─' * 70}")
        print(f"  💰 LTP:        ₹{ltp:>8.2f}")
        print(f"  📉 Bid:        ₹{bid:>8.2f}")
        print(f"  📈 Ask:        ₹{ask:>8.2f}")
        print(f"  📏 Spread:     ₹{spread:>8.2f}")
        print(f"  📦 Volume:     {volume:>10,}")
        print(f"  🕐 Updated:    {last_update.strftime('%H:%M:%S') if last_update else 'N/A'}")
        return True
    else:
        print(f"\n  ⏳ {symbol}")
        print(f"  {'─' * 70}")
        print(f"  ⚠️  Waiting for WebSocket data...")
        return False


def print_status_summary(ws_manager, symbols, elapsed_time):
    """Print status summary"""
    print("\n" + "=" * 80)
    print(f"📊 STATUS UPDATE - Elapsed Time: {elapsed_time:.0f}s / {TEST_DURATION}s")
    print("=" * 80)

    symbols_with_data = 0
    for symbol in symbols:
        has_data = print_symbol_data(ws_manager, symbol)
        if has_data:
            symbols_with_data += 1

    print("\n" + "─" * 80)
    print(f"📈 Data Received: {symbols_with_data}/{len(symbols)} symbols")
    print(f"🔌 Connection: {'ACTIVE' if ws_manager.is_running else 'INACTIVE'}")
    print("─" * 80 + "\n")


def manual_test_mode(ws_manager):
    """
    Manual testing mode - add symbols interactively
    """
    print("\n" + "=" * 80)
    print("🎯 MANUAL TESTING MODE")
    print("=" * 80)
    print("Enter option symbols to test (one per line)")
    print("Format: UNDERLYING DD MMM STRIKE CALL/PUT")
    print("Example: RELIANCE 28 OCT 1300 CALL")
    print("\nCommands:")
    print("  - Enter symbol: Subscribe to that symbol")
    print("  - 'list': Show all subscribed symbols")
    print("  - 'status': Show current data for all symbols")
    print("  - 'quit' or 'exit': Stop testing")
    print("=" * 80 + "\n")

    subscribed_symbols = []

    while True:
        try:
            user_input = input("\n➤ Enter symbol or command: ").strip()

            if not user_input:
                continue

            # Check for commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Stopping test...")
                break

            elif user_input.lower() == 'list':
                print(f"\n📋 Subscribed Symbols ({len(subscribed_symbols)}):")
                for i, sym in enumerate(subscribed_symbols, 1):
                    print(f"  {i}. {sym}")
                continue

            elif user_input.lower() == 'status':
                if not subscribed_symbols:
                    print("\n⚠️  No symbols subscribed yet")
                else:
                    print_status_summary(ws_manager, subscribed_symbols, 0)
                continue

            # Otherwise, treat as symbol to subscribe
            symbol = user_input.upper()

            if symbol in subscribed_symbols:
                print(f"  ℹ️  Already subscribed to {symbol}")
                continue

            print(f"\n🔄 Subscribing to {symbol}...")
            success = ws_manager.subscribe(symbol)

            if success:
                subscribed_symbols.append(symbol)
                print(f"  ✅ Subscribed successfully!")
                print(f"  ⏳ Waiting for WebSocket data...")

                # Wait a bit for data to arrive
                time.sleep(3)

                # Show initial data
                print_symbol_data(ws_manager, symbol)
            else:
                print(f"  ❌ Failed to subscribe to {symbol}")
                print(f"  💡 Check symbol format and instrument file")

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user (Ctrl+C)")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


def automated_test_mode(ws_manager, test_symbols):
    """
    Automated testing mode - subscribe to predefined symbols
    """
    print("🔄 Subscribing to test symbols...\n")

    subscribed = []
    for symbol in test_symbols:
        print(f"  Subscribing to: {symbol}")
        success = ws_manager.subscribe(symbol)
        if success:
            subscribed.append(symbol)
            print(f"    ✅ Subscribed")
        else:
            print(f"    ❌ Failed")
        time.sleep(0.5)

    if not subscribed:
        print("\n❌ No symbols subscribed successfully")
        return

    print(f"\n✅ Successfully subscribed to {len(subscribed)}/{len(test_symbols)} symbols")
    print(f"\n⏳ Running test for {TEST_DURATION} seconds...")
    print("   (Press Ctrl+C to stop early)\n")

    start_time = time.time()
    last_status_time = start_time

    try:
        while True:
            elapsed = time.time() - start_time

            # Check if test duration exceeded
            if elapsed >= TEST_DURATION:
                print("\n⏰ Test duration completed!")
                break

            # Print status update at intervals
            if elapsed - (last_status_time - start_time) >= STATUS_UPDATE_INTERVAL:
                print_status_summary(ws_manager, subscribed, elapsed)
                last_status_time = time.time()

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Test stopped by user (Ctrl+C)")

    # Final summary
    print("\n" + "=" * 80)
    print("🏁 FINAL TEST SUMMARY")
    print("=" * 80)
    print_status_summary(ws_manager, subscribed, elapsed)


def main():
    """Main test function"""
    print_header()

    # Initialize WebSocket manager
    print("🔌 Initializing WebSocket Manager...")
    ws_manager = WebSocketMarketData(CLIENT_CODE, TOKEN_ID)
    print()

    # Decide test mode
    if TEST_SYMBOLS:
        # Automated mode with predefined symbols
        automated_test_mode(ws_manager, TEST_SYMBOLS)
    else:
        # Manual mode - user enters symbols
        manual_test_mode(ws_manager)

    # Cleanup
    print("\n🧹 Cleaning up...")
    ws_manager.stop()
    print("✅ WebSocket stopped")

    print("\n" + "=" * 80)
    print(f"👋 Test Completed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
