"""
Simple WebSocket Test
=====================

Quick and simple test to verify WebSocket is working.
Just run and watch the live data stream!

Usage:
    python test_websocket_simple.py
"""

import time
from websocket_manager import WebSocketMarketData

# Your Dhan credentials
CLIENT_CODE = "1106090196"
TOKEN_ID = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzYxMDI0ODYyLCJpYXQiOjE3NjA5Mzg0NjIsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.jCJYvHIUG3xy1J607hE70aL4k-camDpaNqX4UsimbyDm0XEBmS4k3WZXbrzkqj3MIFkBPledGgIszuN67qJs4Q"
# ============================
# CHANGE THIS TO YOUR SYMBOL
# ============================
TEST_SYMBOL = "ADANIGREEN 28 OCT 1040 PUT"  # Replace with your option symbol

# How many updates to show (each update is 2 seconds apart)
NUM_UPDATES = 30  # 30 updates = 1 minute


def main():
    print("\n" + "="*60)
    print("🔌 SIMPLE WEBSOCKET TEST")
    print("="*60)
    print(f"Testing Symbol: {TEST_SYMBOL}")
    print(f"Updates to show: {NUM_UPDATES}")
    print("="*60 + "\n")

    # Initialize WebSocket
    print("Initializing WebSocket...")
    ws = WebSocketMarketData(CLIENT_CODE, TOKEN_ID)
    print()

    # Subscribe to symbol
    print(f"Subscribing to {TEST_SYMBOL}...")
    success = ws.subscribe(TEST_SYMBOL)
    print()

    if not success:
        print("❌ Subscription failed!")
        print("💡 Tip: Check symbol format and spelling")
        return

    print("✅ Subscription successful!")
    print("⏳ Waiting for live data...\n")
    print("─"*60)

    # Show updates
    update_count = 0
    while update_count < NUM_UPDATES:
        time.sleep(2)  # Wait 2 seconds between updates

        # Get latest data
        data = ws.get_market_data(TEST_SYMBOL)

        if data and data.get('ltp', 0) > 0:
            ltp = data['ltp']
            bid = data.get('bid_price', 0)
            ask = data.get('ask_price', 0)
            volume = data.get('volume', 0)
            last_update = data.get('last_update')

            update_count += 1

            # Print update
            print(f"[{update_count:02d}] "
                  f"LTP: ₹{ltp:7.2f}  "
                  f"Bid: ₹{bid:7.2f}  "
                  f"Ask: ₹{ask:7.2f}  "
                  f"Vol: {volume:>8,}  "
                  f"Time: {last_update.strftime('%H:%M:%S') if last_update else 'N/A'}")
        else:
            print(f"[--] Waiting for data...")

    print("─"*60)
    print("\n✅ Test completed successfully!")
    print("🛑 Stopping WebSocket...")

    ws.stop()

    print("👋 Done!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
