"""
WebSocket Live Monitor - Single Symbol
=======================================

Continuously monitors and displays real-time market data for a single option symbol.
"""

import time
import sys
from datetime import datetime
import os


class MockDhanClient:
    """
    Mock Dhan client for testing without actual API connection.
    """
    def __init__(self):
        self.name = "Mock Dhan Client"

    def get_ltp_data(self, names):
        """
        Mock LTP data for testing.
        Returns dummy prices that change slightly each time.
        """
        import random
        ltp_data = {}
        for name in names:
            # Base price around 18-20 for PUT option
            base_price = 18.50
            # Add random variation of +/- 0.50
            variation = random.uniform(-0.50, 0.50)
            ltp_data[name] = round(base_price + variation, 2)
        return ltp_data


def clear_screen():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(symbol, security_id):
    """Print header with symbol information."""
    print("=" * 80)
    print(f"  LIVE MARKET DATA MONITOR")
    print("=" * 80)
    print(f"  Symbol:      {symbol}")
    print(f"  Security ID: {security_id}")
    print(f"  Started:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()


def format_price_change(current, previous):
    """Format price change with color indicator."""
    if previous == 0:
        return "  --  "

    change = current - previous
    change_pct = (change / previous) * 100 if previous != 0 else 0

    if change > 0:
        return f"📈 +{change:.2f} (+{change_pct:.2f}%)"
    elif change < 0:
        return f"📉 {change:.2f} ({change_pct:.2f}%)"
    else:
        return f"➡️  {change:.2f} ({change_pct:.2f}%)"


def monitor_option_live(symbol, security_id=None, refresh_interval=1.0):
    """
    Monitor a single option symbol with continuous updates.

    Args:
        symbol: Option symbol to monitor
        security_id: Optional security ID
        refresh_interval: Update interval in seconds (default 1.0)
    """
    try:
        from websocket_manager import WebSocketMarketData

        print("\n🔄 Initializing WebSocket manager...")
        mock_client = MockDhanClient()
        ws_manager = WebSocketMarketData(mock_client)

        print(f"✅ WebSocket manager initialized")
        print(f"   Instrument file: {ws_manager.instrument_file}\n")

        # Subscribe to the symbol
        print(f"🔌 Subscribing to {symbol}...")
        result = ws_manager.subscribe(symbol, security_id)

        if not result:
            print(f"❌ Failed to subscribe to {symbol}")
            return

        print(f"✅ Successfully subscribed!")
        print(f"\n⏳ Waiting 2 seconds for initial data...")
        time.sleep(2)

        # Clear screen and start monitoring
        clear_screen()
        print_header(symbol, security_id or "Auto-detected")

        print("Press Ctrl+C to stop monitoring\n")
        print("-" * 80)

        update_count = 0
        previous_ltp = 0
        start_time = time.time()

        # Store historical data
        ltp_history = []
        max_ltp = 0
        min_ltp = float('inf')

        while True:
            # Get market data
            market_data = ws_manager.get_market_data(symbol)

            if market_data:
                current_ltp = market_data['ltp']
                bid_price = market_data['bid_price']
                ask_price = market_data['ask_price']
                bid_qty = market_data['bid_qty']
                ask_qty = market_data['ask_qty']
                volume = market_data['volume']
                oi = market_data['oi']
                last_update = market_data['last_update']

                # Track LTP statistics
                if current_ltp > 0:
                    ltp_history.append(current_ltp)
                    max_ltp = max(max_ltp, current_ltp)
                    min_ltp = min(min_ltp, current_ltp)

                # Calculate spread
                spread = ask_price - bid_price if (ask_price > 0 and bid_price > 0) else 0
                mid_price = (bid_price + ask_price) / 2 if (ask_price > 0 and bid_price > 0) else current_ltp
                spread_pct = (spread / mid_price * 100) if mid_price > 0 else 0

                # Clear previous line and print update
                update_count += 1
                elapsed = int(time.time() - start_time)

                print(f"\r[Update #{update_count:04d}] {datetime.now().strftime('%H:%M:%S')} | "
                      f"Elapsed: {elapsed}s", end="")
                print()

                # Price information
                print(f"\n  💰 PRICE INFORMATION")
                print(f"  {'-' * 76}")
                print(f"  LTP:           ₹{current_ltp:>8.2f}  {format_price_change(current_ltp, previous_ltp)}")
                print(f"  Bid:           ₹{bid_price:>8.2f}  (Qty: {bid_qty:>6.0f})")
                print(f"  Ask:           ₹{ask_price:>8.2f}  (Qty: {ask_qty:>6.0f})")
                print(f"  Mid Price:     ₹{mid_price:>8.2f}")
                print(f"  Spread:        ₹{spread:>8.2f}  ({spread_pct:.2f}%)")

                # Statistics
                print(f"\n  📊 SESSION STATISTICS")
                print(f"  {'-' * 76}")
                if ltp_history:
                    avg_ltp = sum(ltp_history) / len(ltp_history)
                    print(f"  High:          ₹{max_ltp:>8.2f}")
                    print(f"  Low:           ₹{min_ltp:>8.2f}")
                    print(f"  Average:       ₹{avg_ltp:>8.2f}")
                    print(f"  Range:         ₹{(max_ltp - min_ltp):>8.2f}")

                # Volume and OI
                print(f"\n  📈 VOLUME & OPEN INTEREST")
                print(f"  {'-' * 76}")
                print(f"  Volume:        {volume:>12,.0f}")
                print(f"  Open Interest: {oi:>12,.0f}")

                # Update info
                print(f"\n  ⏰ LAST UPDATE")
                print(f"  {'-' * 76}")
                if last_update:
                    print(f"  Time:          {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    print(f"  Time:          Not updated yet")

                print(f"\n  {'=' * 76}")
                print(f"\n  Press Ctrl+C to stop monitoring...")

                previous_ltp = current_ltp

            else:
                print(f"\r[Update #{update_count:04d}] {datetime.now().strftime('%H:%M:%S')} | "
                      f"⚠️ No data available yet...", end="", flush=True)

            # Wait before next update
            time.sleep(refresh_interval)

            # Clear screen for next update (optional - comment out if you want scrolling)
            if update_count % 1 == 0:  # Clear every update
                time.sleep(0.5)  # Brief pause to read
                clear_screen()
                print_header(symbol, security_id or "Auto-detected")

    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("  MONITORING STOPPED")
        print("=" * 80)
        print(f"\n  Total updates: {update_count}")
        print(f"  Duration:      {int(time.time() - start_time)} seconds")

        if ltp_history:
            print(f"\n  📊 FINAL STATISTICS:")
            print(f"  {'-' * 76}")
            print(f"  High:          ₹{max_ltp:.2f}")
            print(f"  Low:           ₹{min_ltp:.2f}")
            print(f"  Average:       ₹{sum(ltp_history)/len(ltp_history):.2f}")
            print(f"  Final LTP:     ₹{ltp_history[-1]:.2f}")

        print("\n  ✅ WebSocket unsubscribed and stopped")
        print("=" * 80 + "\n")

        # Cleanup
        try:
            ws_manager.unsubscribe(symbol)
            ws_manager.stop()
        except:
            pass

    except Exception as e:
        print(f"\n\n❌ Error during monitoring: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function to run the live monitor."""

    # Symbol to monitor
    SYMBOL = "GODREJCP 28 OCT 1100 PUT"
    SECURITY_ID = "83429"  # Optional, will auto-detect if None
    REFRESH_INTERVAL = 1.0  # Update every 1 second

    print("\n" + "🔴" * 40)
    print("  WEBSOCKET LIVE MONITOR - SINGLE SYMBOL")
    print("🔴" * 40)
    print(f"\n  Monitoring: {SYMBOL}")
    print(f"  Security ID: {SECURITY_ID}")
    print(f"  Refresh Rate: {REFRESH_INTERVAL} second(s)")
    print("\n" + "🔴" * 40 + "\n")

    monitor_option_live(SYMBOL, SECURITY_ID, REFRESH_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)