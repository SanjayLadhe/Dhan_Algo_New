"""
═══════════════════════════════════════════════════════════════════════════
                    CODE CHANGES VISUAL GUIDE
═══════════════════════════════════════════════════════════════════════════

This file shows EXACTLY what to change in your single_trade_focus_bot.py
"""

print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                         STEP 1: MODIFY IMPORTS                           ║
╚══════════════════════════════════════════════════════════════════════════╝

Find this section at the TOP of single_trade_focus_bot.py (around lines 1-25):
""")

print("""
┌──────────────────────────────────────────────────────────────────────────┐
│ ❌ BEFORE (Original Code)                                                │
└──────────────────────────────────────────────────────────────────────────┘

import pdb
import time
import datetime
import traceback
from ta.volume import volume_weighted_average_price
from ta.volume import VolumeWeightedAveragePrice
from Dhan_Tradehull_V3 import Tradehull  ◄─── FIND THIS LINE
import pandas as pd
from pprint import pprint
import talib
...
""")

print("""
┌──────────────────────────────────────────────────────────────────────────┐
│ ✅ AFTER (Modified Code)                                                 │
└──────────────────────────────────────────────────────────────────────────┘

import pdb
import time
import datetime
import traceback
from ta.volume import volume_weighted_average_price
from ta.volume import VolumeWeightedAveragePrice
# from Dhan_Tradehull_V3 import Tradehull  ◄─── COMMENT OUT OR DELETE
from paper_trading_wrapper import get_trading_instance  ◄─── ADD THIS
import pandas as pd
from pprint import pprint
import talib
...
""")

print("""
═══════════════════════════════════════════════════════════════════════════

╔══════════════════════════════════════════════════════════════════════════╗
║                    STEP 2: MODIFY TSL INITIALIZATION                     ║
╚══════════════════════════════════════════════════════════════════════════╝

Find this section around line 46 in single_trade_focus_bot.py:
""")

print("""
┌──────────────────────────────────────────────────────────────────────────┐
│ ❌ BEFORE (Original Code)                                                │
└──────────────────────────────────────────────────────────────────────────┘

# ============================
# API CREDENTIALS
# ============================
client_code = "1106090196"
token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9..."
tsl = Tradehull(client_code, token_id)  ◄─── FIND THIS LINE
""")

print("""
┌──────────────────────────────────────────────────────────────────────────┐
│ ✅ AFTER (Modified Code)                                                 │
└──────────────────────────────────────────────────────────────────────────┘

# ============================
# API CREDENTIALS
# ============================
client_code = "1106090196"
token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9..."
tsl = get_trading_instance(client_code, token_id)  ◄─── REPLACE WITH THIS
""")

print("""
═══════════════════════════════════════════════════════════════════════════

╔══════════════════════════════════════════════════════════════════════════╗
║                        STEP 3: CONFIGURE MODE                            ║
╚══════════════════════════════════════════════════════════════════════════╝

In paper_trading_config.py:
""")

print("""
┌──────────────────────────────────────────────────────────────────────────┐
│ For PAPER TRADING (No Real Orders):                                     │
└──────────────────────────────────────────────────────────────────────────┘

PAPER_TRADING_ENABLED = True  ✅ Set to True
""")

print("""
┌──────────────────────────────────────────────────────────────────────────┐
│ For LIVE TRADING (Real Orders):                                         │
└──────────────────────────────────────────────────────────────────────────┘

PAPER_TRADING_ENABLED = False  ⚠️  Set to False
""")

print("""
═══════════════════════════════════════════════════════════════════════════

╔══════════════════════════════════════════════════════════════════════════╗
║                            SUMMARY                                       ║
╚══════════════════════════════════════════════════════════════════════════╝

Total Changes Required: 2 lines in single_trade_focus_bot.py

┌─────────────┬────────────────────────────────────┬────────────────────────┐
│ Line Number │ Original                           │ New                    │
├─────────────┼────────────────────────────────────┼────────────────────────┤
│ ~8          │ from Dhan_Tradehull_V3 import...   │ from paper_trading...  │
│ ~46         │ tsl = Tradehull(client_code...)    │ tsl = get_trading...   │
└─────────────┴────────────────────────────────────┴────────────────────────┘

Plus: Set PAPER_TRADING_ENABLED in paper_trading_config.py

═══════════════════════════════════════════════════════════════════════════

✅ THAT'S ALL THE CHANGES NEEDED!

Run your bot: python single_trade_focus_bot.py

═══════════════════════════════════════════════════════════════════════════
""")

# Also create a side-by-side comparison
print("\n\n")
print("="*80)
print("SIDE-BY-SIDE COMPARISON")
print("="*80)
print()

comparison = """
╔═══════════════════════════════════╦═══════════════════════════════════╗
║         ORIGINAL CODE             ║       PAPER TRADING CODE          ║
╠═══════════════════════════════════╬═══════════════════════════════════╣
║ Line ~8:                          ║ Line ~8:                          ║
║                                   ║                                   ║
║ from Dhan_Tradehull_V3 import     ║ from paper_trading_wrapper import ║
║     Tradehull                     ║     get_trading_instance          ║
║                                   ║                                   ║
╠═══════════════════════════════════╬═══════════════════════════════════╣
║ Line ~46:                         ║ Line ~46:                         ║
║                                   ║                                   ║
║ tsl = Tradehull(                  ║ tsl = get_trading_instance(       ║
║     client_code,                  ║     client_code,                  ║
║     token_id                      ║     token_id                      ║
║ )                                 ║ )                                 ║
╚═══════════════════════════════════╩═══════════════════════════════════╝
"""

print(comparison)

print("\n" + "="*80)
print("Everything else in your bot remains EXACTLY THE SAME!")
print("="*80)
