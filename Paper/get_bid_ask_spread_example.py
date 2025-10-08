# -*- coding: utf-8 -*-
"""
Example: How to Get Bid-Ask Spread from Dhan API
=================================================

This script demonstrates how to get bid-ask spread for stocks and options.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Paper'))

from Dhan_Tradehull_V3 import Tradehull

# Initialize Dhan API
CLIENT_CODE = "1106090196"
TOKEN_ID = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU5OTg1NTkzLCJpYXQiOjE3NTk4OTkxOTMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.bqF4PigSwXUam1Cn7EKlWxagPwgu9sflmuiA7ouO1IBNd0KAPHnD69mGTyCN6nv5bdbKHfDbv-Wiox3nTYYlRw"

tsl = Tradehull(CLIENT_CODE, TOKEN_ID)

print("\n" + "="*80)
print("BID-ASK SPREAD EXAMPLE")
print("="*80)


# ============================
# METHOD 1: Using get_quote_data() for STOCKS
# ============================
def get_stock_bid_ask_spread(symbol):
    """
    Get bid-ask spread for a stock using quote data

    Args:
        symbol: Stock symbol (e.g., 'RELIANCE', 'TCS')

    Returns:
        dict with bid, ask, spread info
    """
    print(f"\n📊 Getting bid-ask for STOCK: {symbol}")

    try:
        # Get quote data (includes bid/ask)
        quote_data = tsl.get_quote_data([symbol])

        if symbol in quote_data:
            data = quote_data[symbol]

            # Extract bid-ask prices
            bid_price = data.get('top_bid_price', None)
            ask_price = data.get('top_ask_price', None)
            bid_qty = data.get('top_bid_quantity', None)
            ask_qty = data.get('top_ask_quantity', None)
            ltp = data.get('last_price', None)

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
            print(f"  Bid Price:     ₹{bid_price} (Qty: {bid_qty})")
            print(f"  Ask Price:     ₹{ask_price} (Qty: {ask_qty})")
            print(f"  Spread:        ₹{spread:.2f}" if spread else "  Spread:        N/A")
            print(f"  Spread %:      {spread_pct:.3f}%" if spread_pct else "  Spread %:      N/A")

            return result
        else:
            print(f"  ❌ No data found for {symbol}")
            return None

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


# ============================
# METHOD 2: Using get_option_chain_data() for OPTIONS
# ============================
def get_option_bid_ask_spread(underlying, expiry, strike, option_type='CE'):
    """
    Get bid-ask spread for an option using option chain

    Args:
        underlying: Underlying symbol (e.g., 'NIFTY', 'BANKNIFTY')
        expiry: Expiry date in format YYYY-MM-DD or datetime object
        strike: Strike price
        option_type: 'CE' for call, 'PE' for put

    Returns:
        dict with bid, ask, spread info
    """
    print(f"\n📈 Getting bid-ask for OPTION: {underlying} {strike} {option_type}")

    try:
        # Get option chain data
        option_chain = tsl.get_option_chain(underlying, expiry=0,exchange = "NFO")

        if option_chain is not None and not option_chain.empty:
            # Find the row for this strike
            strike_data = option_chain[option_chain['Strike Price'] == strike]

            if not strike_data.empty:
                row = strike_data.iloc[0]

                if option_type == 'CE':
                    bid_price = row.get('CE Bid', None)
                    ask_price = row.get('CE Ask', None)
                    bid_qty = row.get('CE Bid Qty', None)
                    ask_qty = row.get('CE Ask Qty', None)
                    ltp = row.get('CE LTP', None)
                else:  # PE
                    bid_price = row.get('PE Bid', None)
                    ask_price = row.get('PE Ask', None)
                    bid_qty = row.get('PE Bid Qty', None)
                    ask_qty = row.get('PE Ask Qty', None)
                    ltp = row.get('PE LTP', None)

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
                print(f"  Bid Price:     ₹{bid_price} (Qty: {bid_qty})")
                print(f"  Ask Price:     ₹{ask_price} (Qty: {ask_qty})")
                print(f"  Spread:        ₹{spread:.2f}" if spread else "  Spread:        N/A")
                print(f"  Spread %:      {spread_pct:.3f}%" if spread_pct else "  Spread %:      N/A")

                return result
            else:
                print(f"  ❌ Strike {strike} not found in option chain")
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
# METHOD 3: Get bid-ask for specific option symbol
# ============================
def get_option_symbol_bid_ask(option_symbol):
    """
    Get bid-ask spread for a specific option symbol

    Args:
        option_symbol: Option trading symbol (e.g., 'NIFTY24O1024900CE')

    Returns:
        dict with bid, ask, spread info
    """
    print(f"\n📊 Getting bid-ask for OPTION SYMBOL: {option_symbol}")

    try:
        # Get quote data for option symbol
        quote_data = tsl.get_quote_data([option_symbol])

        if option_symbol in quote_data:
            data = quote_data[option_symbol]

            # Extract bid-ask prices
            bid_price = data.get('top_bid_price', None)
            ask_price = data.get('top_ask_price', None)
            bid_qty = data.get('top_bid_quantity', None)
            ask_qty = data.get('top_ask_quantity', None)
            ltp = data.get('last_price', None)

            # Calculate spread
            if bid_price and ask_price:
                spread = ask_price - bid_price
                spread_pct = (spread / ltp * 100) if ltp else 0
            else:
                spread = None
                spread_pct = None

            result = {
                'symbol': option_symbol,
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
            print(f"  Bid Price:     ₹{bid_price} (Qty: {bid_qty})")
            print(f"  Ask Price:     ₹{ask_price} (Qty: {ask_qty})")
            print(f"  Spread:        ₹{spread:.2f}" if spread else "  Spread:        N/A")
            print(f"  Spread %:      {spread_pct:.3f}%" if spread_pct else "  Spread %:      N/A")

            return result
        else:
            print(f"  ❌ No data found for {option_symbol}")
            return None

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


# ============================
# EXAMPLE USAGE
# ============================
if __name__ == "__main__":

    print("\n" + "="*80)
    print("EXAMPLE 1: Get bid-ask spread for a STOCK")
    print("="*80)

    # Example: Get bid-ask for RELIANCE stock
    stock_data = get_stock_bid_ask_spread('RELIANCE')


    print("\n" + "="*80)
    print("EXAMPLE 2: Get bid-ask spread for an OPTION via Option Chain")
    print("="*80)

    # Example: Get bid-ask for NIFTY option
    # First, get ATM strike
    atm_strike = tsl.ATM_Strike_Selection('NIFTY', 0)
    print(f"\n  ATM Strike for NIFTY: {atm_strike}")

    # Get bid-ask for ATM Call option
    option_data = get_option_bid_ask_spread(
        underlying='NIFTY',
        expiry=0,  # Nearest expiry
        strike=atm_strike,
        option_type='CE'
    )


    print("\n" + "="*80)
    print("EXAMPLE 3: Get bid-ask spread for OPTION by Symbol Name")
    print("="*80)

    # If you know the exact option symbol, use this method
    # Example: NIFTY24O1024900CE means NIFTY expiring Oct 10, 2024, 24900 strike, CE
    # You'll need to construct the symbol based on your needs
    # option_symbol_data = get_option_symbol_bid_ask('NIFTY24O1024900CE')

    print("\n" + "="*80)
    print("USAGE IN TRADING BOT")
    print("="*80)
    print("""
To use bid-ask spread in your trading bot:

1. For STOCKS:
   quote_data = tsl.get_quote_data(['RELIANCE'])
   bid = quote_data['RELIANCE']['top_bid_price']
   ask = quote_data['RELIANCE']['top_ask_price']
   spread = ask - bid

2. For OPTIONS (via option chain):
   option_chain = tsl.get_option_chain_data('NIFTY', 0)
   strike_data = option_chain[option_chain['Strike Price'] == 24900]
   ce_bid = strike_data['CE Bid'].values[0]
   ce_ask = strike_data['CE Ask'].values[0]
   ce_spread = ce_ask - ce_bid

3. For OPTIONS (via symbol):
   quote_data = tsl.get_quote_data(['NIFTY24O1024900CE'])
   bid = quote_data['NIFTY24O1024900CE']['top_bid_price']
   ask = quote_data['NIFTY24O1024900CE']['top_ask_price']
   spread = ask - bid

TIPS:
- Tighter spreads = better liquidity
- Wider spreads = higher transaction costs
- Use spread % to compare across different price ranges
- Consider spread when placing limit orders
    """)

    print("\n" + "="*80)
    print("✅ DONE!")
    print("="*80 + "\n")