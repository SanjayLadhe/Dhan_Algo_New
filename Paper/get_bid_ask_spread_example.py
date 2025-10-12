# -*- coding: utf-8 -*-
"""
Fixed Example: How to Get Bid-Ask Spread from Dhan API
=======================================================

This script demonstrates how to get bid-ask spread for stocks and options.
Fixed version that handles API response issues properly.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), 'Paper'))

from Dhan_Tradehull_V3 import Tradehull

# Initialize Dhan API
CLIENT_CODE = "1106090196"
TOKEN_ID = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzYwMDcwNDg1LCJpYXQiOjE3NTk5ODQwODUsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.XKcfhAj9zzhYe-48SzIqYdyMETwJyRrxnfI-M9X0gtzV3EenqWOvq_8jFfK9WhPguZvmacGhFba8HD7nsRFPeQ"
tsl = Tradehull(CLIENT_CODE, TOKEN_ID)

print("\n" + "=" * 80)
print("BID-ASK SPREAD EXAMPLE - FIXED VERSION")
print("=" * 80)


# ============================
# METHOD 1: Using get_quote_data() for STOCKS - FIXED
# ============================
def get_stock_bid_ask_spread(symbol):
    """
    Get bid-ask spread for a stock using quote data
    Fixed version that handles missing bid/ask data

    Args:
        symbol: Stock symbol (e.g., 'RELIANCE', 'TCS')

    Returns:
        dict with bid, ask, spread info
    """
    print(f"\n📊 Getting bid-ask for STOCK: {symbol}")

    try:
        # Get quote data (includes bid/ask)
        quote_data = tsl.get_quote_data([symbol])
        print(f"  Debug - Raw quote data keys: {quote_data.keys() if quote_data else 'None'}")

        if quote_data and symbol in quote_data:
            data = quote_data[symbol]
            print(f"  Debug - Available data fields: {list(data.keys())[:10]}...")  # Show first 10 fields

            # Extract bid-ask prices - check different possible field names
            bid_price = data.get('top_bid_price') or data.get('bid_price') or data.get('bid')
            ask_price = data.get('top_ask_price') or data.get('ask_price') or data.get('ask')
            bid_qty = data.get('top_bid_quantity') or data.get('bid_qty') or data.get('bid_quantity')
            ask_qty = data.get('top_ask_quantity') or data.get('ask_qty') or data.get('ask_quantity')
            ltp = data.get('last_price') or data.get('ltp') or data.get('close')

            # If no bid/ask, try to get from depth
            if not bid_price and 'depth' in data:
                depth = data['depth']
                if 'buy' in depth and len(depth['buy']) > 0:
                    bid_price = depth['buy'][0].get('price')
                    bid_qty = depth['buy'][0].get('quantity')
                if 'sell' in depth and len(depth['sell']) > 0:
                    ask_price = depth['sell'][0].get('price')
                    ask_qty = depth['sell'][0].get('quantity')

            # Calculate spread
            if bid_price and ask_price:
                spread = ask_price - bid_price
                spread_pct = (spread / ltp * 100) if ltp else 0
            else:
                spread = None
                spread_pct = None

            result = {
                'symbol': symbol,
                'bid_price': bid_price,
                'bid_qty': bid_qty,
                'ask_price': ask_price,
                'ask_qty': ask_qty,
                'ltp': ltp,
                'spread': spread,
                'spread_pct': spread_pct
            }

            # Pretty print
            print(f"  Last Price:    ₹{ltp}")
            if bid_price and ask_price:
                print(f"  Bid Price:     ₹{bid_price} (Qty: {bid_qty})")
                print(f"  Ask Price:     ₹{ask_price} (Qty: {ask_qty})")
                print(f"  Spread:        ₹{spread:.2f}")
                print(f"  Spread %:      {spread_pct:.3f}%")
            else:
                print(f"  ⚠️ Bid-Ask data not available (market may be closed)")
                print(f"  💡 Try using get_ltp() or get_historical_data() for last traded prices")

            return result
        else:
            print(f"  ❌ No data found for {symbol}")
            return None

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================
# METHOD 2: Using get_option_chain() for OPTIONS - FIXED
# ============================
def get_option_bid_ask_spread(underlying, expiry, strike, option_type='CE'):
    """
    Get bid-ask spread for an option using option chain
    Fixed version that handles expiry date properly

    Args:
        underlying: Underlying symbol (e.g., 'NIFTY', 'BANKNIFTY')
        expiry: Expiry date - can be:
                - 0 for nearest expiry
                - datetime object
                - string in format 'DD-MMM-YYYY' (e.g., '31-OCT-2024')
        strike: Strike price
        option_type: 'CE' for call, 'PE' for put

    Returns:
        dict with bid, ask, spread info
    """
    print(f"\n📈 Getting bid-ask for OPTION: {underlying} {strike} {option_type}")
    print(f"  Debug - Expiry parameter: {expiry}")

    try:
        # Handle different expiry formats
        if isinstance(expiry, int) and expiry == 0:
            # Get nearest expiry - let the API handle it
            print("  Using nearest expiry...")
            expiry_str = None  # Will use API's default
        elif isinstance(expiry, datetime):
            # Convert datetime to DD-MMM-YYYY format
            expiry_str = expiry.strftime('%d-%b-%Y').upper()
            print(f"  Using expiry date: {expiry_str}")
        elif isinstance(expiry, str):
            # Assume it's already in correct format
            expiry_str = expiry
            print(f"  Using expiry string: {expiry_str}")
        else:
            expiry_str = None

        # Try getting option chain with proper expiry format
        print(f"  Calling get_option_chain with expiry: {expiry_str}")
        result = tsl.get_option_chain(underlying, "NFO", expiry_str)

        # Check if result is None or a tuple
        if result is None:
            print("  ❌ get_option_chain returned None")
            print("  💡 Trying alternative: get_option_chain_data")

            # Alternative: Try get_option_chain_data if available
            if hasattr(tsl, 'get_option_chain_data'):
                option_chain = tsl.get_option_chain_data(underlying, expiry_str)
                atm_strike = strike  # Use provided strike as ATM
            else:
                print("  ❌ get_option_chain_data not available")
                return None
        elif isinstance(result, tuple):
            atm_strike, option_chain = result
            print(f"  ✅ Got option chain with ATM strike: {atm_strike}")
        else:
            # Result is the option chain directly
            option_chain = result
            atm_strike = strike

        if option_chain is not None and not option_chain.empty:
            print(f"  Debug - Option chain columns: {list(option_chain.columns)[:10]}...")

            # Find the row for this strike
            strike_data = option_chain[option_chain['Strike Price'] == strike]

            if not strike_data.empty:
                row = strike_data.iloc[0]

                if option_type == 'CE':
                    bid_price = row.get('CE Bid') or row.get('CE_Bid') or row.get('ce_bid')
                    ask_price = row.get('CE Ask') or row.get('CE_Ask') or row.get('ce_ask')
                    bid_qty = row.get('CE Bid Qty') or row.get('CE_Bid_Qty') or row.get('ce_bid_qty')
                    ask_qty = row.get('CE Ask Qty') or row.get('CE_Ask_Qty') or row.get('ce_ask_qty')
                    ltp = row.get('CE LTP') or row.get('CE_LTP') or row.get('ce_ltp')
                else:  # PE
                    bid_price = row.get('PE Bid') or row.get('PE_Bid') or row.get('pe_bid')
                    ask_price = row.get('PE Ask') or row.get('PE_Ask') or row.get('pe_ask')
                    bid_qty = row.get('PE Bid Qty') or row.get('PE_Bid_Qty') or row.get('pe_bid_qty')
                    ask_qty = row.get('PE Ask Qty') or row.get('PE_Ask_Qty') or row.get('pe_ask_qty')
                    ltp = row.get('PE LTP') or row.get('PE_LTP') or row.get('pe_ltp')

                # Calculate spread
                if bid_price and ask_price:
                    spread = ask_price - bid_price
                    spread_pct = (spread / ltp * 100) if ltp else 0
                else:
                    spread = None
                    spread_pct = None

                result = {
                    'underlying': underlying,
                    'strike': strike,
                    'option_type': option_type,
                    'bid_price': bid_price,
                    'bid_qty': bid_qty,
                    'ask_price': ask_price,
                    'ask_qty': ask_qty,
                    'ltp': ltp,
                    'spread': spread,
                    'spread_pct': spread_pct
                }

                # Pretty print
                print(f"  Last Price:    ₹{ltp}")
                if bid_price and ask_price:
                    print(f"  Bid Price:     ₹{bid_price} (Qty: {bid_qty})")
                    print(f"  Ask Price:     ₹{ask_price} (Qty: {ask_qty})")
                    print(f"  Spread:        ₹{spread:.2f}")
                    print(f"  Spread %:      {spread_pct:.3f}%")
                else:
                    print(f"  ⚠️ Bid-Ask data not available (market may be closed)")

                return result
            else:
                print(f"  ❌ Strike {strike} not found in option chain")
                print(f"  Available strikes: {sorted(option_chain['Strike Price'].unique())[:10]}...")
                return None
        else:
            print(f"  ❌ No option chain data found")
            return None

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================
# METHOD 3: Alternative using direct API call
# ============================
def get_bid_ask_alternative(symbol):
    """
    Alternative method to get bid-ask using market depth or LTP

    Args:
        symbol: Trading symbol

    Returns:
        dict with available price data
    """
    print(f"\n🔄 Alternative method for: {symbol}")

    try:
        # Method 1: Try to get LTP
        if hasattr(tsl, 'get_ltp'):
            ltp_data = tsl.get_ltp([symbol])
            if ltp_data and symbol in ltp_data:
                print(f"  LTP: ₹{ltp_data[symbol]}")

        # Method 2: Try to get market depth
        if hasattr(tsl, 'get_market_depth'):
            depth_data = tsl.get_market_depth(symbol)
            if depth_data:
                print(f"  Market depth available: {depth_data}")

        # Method 3: Get historical data for recent prices
        if hasattr(tsl, 'get_historical_data'):
            from datetime import datetime, timedelta
            to_date = datetime.now()
            from_date = to_date - timedelta(days=1)

            hist_data = tsl.get_historical_data(
                symbol,
                exchange='NSE',
                timeframe='1m',
                from_date=from_date,
                to_date=to_date
            )

            if hist_data is not None and not hist_data.empty:
                latest = hist_data.iloc[-1]
                print(
                    f"  Latest candle - Open: ₹{latest['open']}, High: ₹{latest['high']}, Low: ₹{latest['low']}, Close: ₹{latest['close']}")

    except Exception as e:
        print(f"  Error in alternative method: {e}")


# ============================
# EXAMPLE USAGE
# ============================
if __name__ == "__main__":

    print("\n" + "=" * 80)
    print("EXAMPLE 1: Get bid-ask spread for a STOCK")
    print("=" * 80)

    # Example: Get bid-ask for RELIANCE stock
    stock_data = get_stock_bid_ask_spread('RELIANCE')

    # If bid-ask not available, try alternative
    if stock_data and not stock_data['bid_price']:
        get_bid_ask_alternative('RELIANCE')

    print("\n" + "=" * 80)
    print("EXAMPLE 2: Get bid-ask spread for an OPTION")
    print("=" * 80)

    # First, try to get ATM strike properly
    try:
        atm_result = tsl.ATM_Strike_Selection('NIFTY', 0)
        if isinstance(atm_result, tuple):
            ce_symbol, pe_symbol, atm_strike = atm_result
            print(f"  ATM Strike for NIFTY: {atm_strike}")
            print(f"  CE Symbol: {ce_symbol}")
            print(f"  PE Symbol: {pe_symbol}")
        else:
            atm_strike = 25200  # Use a default if ATM selection fails
            print(f"  Using default strike: {atm_strike}")
    except:
        atm_strike = 25200  # Fallback strike
        print(f"  Using fallback strike: {atm_strike}")

    # Try different expiry formats
    from datetime import datetime, timedelta

    # Method 1: Try with nearest expiry (0)
    option_data = get_option_bid_ask_spread(
        underlying='NIFTY',
        expiry=0,
        strike=atm_strike,
        option_type='CE'
    )

    # Method 2: If that fails, try with specific date format
    if not option_data:
        # Get next Thursday (typical expiry day)
        today = datetime.now()
        days_ahead = 3 - today.weekday()  # Thursday is 3
        if days_ahead <= 0:
            days_ahead += 7
        next_thursday = today + timedelta(days=days_ahead)
        expiry_str = next_thursday.strftime('%d-%b-%Y').upper()

        print(f"\n  Retrying with specific expiry: {expiry_str}")
        option_data = get_option_bid_ask_spread(
            underlying='NIFTY',
            expiry=expiry_str,
            strike=atm_strike,
            option_type='CE'
        )

    print("\n" + "=" * 80)
    print("TROUBLESHOOTING TIPS")
    print("=" * 80)
    print("""
Common issues and solutions:

1. Bid-Ask data showing None:
   - Market might be closed (bid-ask only available during market hours)
   - Use get_ltp() for last traded price
   - Use historical data for analysis when market is closed

2. Invalid Expiry Date error:
   - Use format: 'DD-MMM-YYYY' (e.g., '31-OCT-2024')
   - For nearest expiry, use 0 or None
   - Check available expiries using get_expiry_list() if available

3. Symbol not found:
   - Verify symbol format (e.g., 'RELIANCE' for equity, 'NIFTY24O3125200CE' for options)
   - Check if symbol is listed and active
   - Use search_scrip() or get_instrument_list() to find correct symbol

4. API rate limits:
   - Add delays between requests
   - Cache data when possible
   - Use bulk requests where available
    """)

    print("\n" + "=" * 80)
    print("✅ FIXED VERSION COMPLETE!")
    print("=" * 80 + "\n")