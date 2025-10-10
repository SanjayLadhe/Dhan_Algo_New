# -*- coding: utf-8 -*-
"""
Option Chain Bid-Ask Spread Calculator & Tester
===============================================

Fetches the latest expiry option chain for a stock and calculates
Bid, Ask, and Bid-Ask Spread for each strike, then demonstrates
how to use the spread in trading logic.

- Uses Dhan Tradehull.get_option_chain()
- expiry=0 → automatically picks latest expiry
- Rate limited to 1 call per second
"""

import time
import pandas as pd
from Dhan_Tradehull_V3 import Tradehull
from rate_limiter import ltp_api_limiter, retry_api_call


# ==================================
# DHAN API CREDENTIALS
# ==================================
CLIENT_CODE = "1106090196"
TOKEN_ID = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzYwMTU3ODc0LCJpYXQiOjE3NjAwNzE0NzQsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.ImOjfGYDGG-ZSlSVBXEtCi563cyJoJY5jwosRpcr64O99LzUdG_j4LnW7zAPVsA3LSROy-LGy-Apdn4vtRjnrw"
tsl = Tradehull(CLIENT_CODE, TOKEN_ID)


# ==================================
# FUNCTION: GET OPTION CHAIN DATA
# ==================================
def get_option_chain_with_spread(symbol: str, num_strikes: int = 0):
    """
    Fetch option chain for latest expiry (expiry=0) and calculate bid-ask spread.
    """
    try:
        # Enforce 1 req/sec
        ltp_api_limiter.wait(call_description=f"get_option_chain({symbol})")

        # ✅ Correct: positional args only, matching working call
        result = retry_api_call(
            tsl.get_option_chain,  # target function
            2,                     # retries
            1.0,                   # delay (seconds)
            symbol,                # positional arg 1
            "NFO",                 # positional arg 2
            0,                     # expiry = 0 (latest)
            num_strikes            # positional arg 4 (num_strikes)
        )

        if not isinstance(result, tuple) or len(result) < 2:
            print(f"⚠️ Invalid response for {symbol}: {result}")
            return None

        atm_strike, option_chain = result

        if option_chain is None or option_chain.empty:
            print(f"⚠️ No option chain data returned for {symbol}")
            return None

        # Compute bid-ask spreads
        option_chain["CE Spread"] = option_chain["CE Ask"] - option_chain["CE Bid"]
        option_chain["PE Spread"] = option_chain["PE Ask"] - option_chain["PE Bid"]

        columns_to_show = [
            "Strike Price",
            "CE Bid", "CE Ask", "CE Spread",
            "PE Bid", "PE Ask", "PE Spread"
        ]
        df = option_chain[columns_to_show].copy().round(2)

        print(f"\n✅ {symbol} Option Chain (Latest Expiry)\nATM Strike: {atm_strike}\n")
        print(df)

        csv_filename = f"{symbol}_option_spread.csv"
        df.to_csv(csv_filename, index=False)
        print(f"\n📁 Saved: {csv_filename}")

        return df

    except Exception as e:
        print(f"❌ Error fetching option chain for {symbol}: {e}")
        return None


# ==================================
# MAIN EXECUTION + TESTING
# ==================================
if __name__ == "__main__":
    print("\n=================================")
    print("🔍 OPTION CHAIN BID-ASK SPREAD TOOL")
    print("=================================\n")

    symbol = "LUPIN"
    num_strikes = 2   # 0 = full chain, else ±N strikes around ATM

    df = get_option_chain_with_spread(symbol, num_strikes)

    # ==============================
    # 🧪 TESTING: USING SPREAD VALUES
    # ==============================
    if df is not None and not df.empty:
        print("\n==============================")
        print("🧪 TESTING BID–ASK SPREAD USAGE")
        print("==============================")

        # Pick ATM or desired strike
        strike_index = min(2, len(df) - 1)
        strike_data = df.iloc[strike_index]

        ce_bid = strike_data["CE Bid"]
        ce_ask = strike_data["CE Ask"]
        ce_spread = ce_ask - ce_bid
        ce_mid = (ce_ask + ce_bid) / 2
        ce_spread_pct = round((ce_spread / ce_mid) * 100, 2)

        pe_bid = strike_data["PE Bid"]
        pe_ask = strike_data["PE Ask"]
        pe_spread = pe_ask - pe_bid
        pe_mid = (pe_ask + pe_bid) / 2
        pe_spread_pct = round((pe_spread / pe_mid) * 100, 2)

        print(f"\nStrike: {strike_data['Strike Price']}")
        print(f"CALL → Bid: {ce_bid}, Ask: {ce_ask}, Spread: {ce_spread:.2f} ({ce_spread_pct:.2f}%)")
        print(f"PUT  → Bid: {pe_bid}, Ask: {pe_ask}, Spread: {pe_spread:.2f} ({pe_spread_pct:.2f}%)")

        print("\n📊 Tips:")
        print("- Tighter spreads → better liquidity")
        print("- Wider spreads → higher transaction cost")
        print("- Use spread % to compare across prices")
        print("- Avoid trading illiquid options (spread% > 1%)")
