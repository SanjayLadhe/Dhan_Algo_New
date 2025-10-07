"""
QUICK START: How to Enable Paper Trading
=========================================

ONLY ONE LINE NEEDS TO CHANGE IN YOUR BOT FILE!
"""

# ============================================================================
# BEFORE (Original - Live Trading)
# ============================================================================

"""
# Around line 46 in single_trade_focus_bot.py:

client_code = "1106090196"
token_id = "eyJ0eXAiOiJKV1QiLCJhbGc..."
tsl = Tradehull(client_code, token_id)  # <-- THIS LINE
"""


# ============================================================================
# AFTER (Modified - Paper Trading)
# ============================================================================

"""
# Around line 46 in single_trade_focus_bot.py:

client_code = "1106090196"
token_id = "eyJ0eXAiOiJKV1QiLCJhbGc..."
from paper_trading_wrapper import get_trading_instance
tsl = get_trading_instance(client_code, token_id)  # <-- REPLACE WITH THIS
"""


# ============================================================================
# COMPLETE EXAMPLE
# ============================================================================

# Step 1: Set paper trading to True
# In paper_trading_config.py:
PAPER_TRADING_ENABLED = True


# Step 2: In your single_trade_focus_bot.py, find the imports section at the top:

"""
ORIGINAL imports (lines 1-45):
-----------------------------
import pdb
import time
import datetime
import traceback
from ta.volume import volume_weighted_average_price
from ta.volume import VolumeWeightedAveragePrice
from Dhan_Tradehull_V3 import Tradehull  # <-- Remove or comment this
import pandas as pd
...
"""

# Replace the Tradehull import with:
"""
NEW imports:
-----------
import pdb
import time
import datetime
import traceback
from ta.volume import volume_weighted_average_price
from ta.volume import VolumeWeightedAveragePrice
# from Dhan_Tradehull_V3 import Tradehull  # <-- Commented out
from paper_trading_wrapper import get_trading_instance  # <-- Add this
import pandas as pd
...
"""


# Step 3: Find where tsl is created (around line 46):

"""
ORIGINAL code:
-------------
client_code = "1106090196"
token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9..."
tsl = Tradehull(client_code, token_id)  # <-- Replace this line
"""

# Replace with:
"""
NEW code:
--------
client_code = "1106090196"
token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9..."
tsl = get_trading_instance(client_code, token_id)  # <-- Use this instead
"""


# ============================================================================
# That's it! Your bot now uses paper trading!
# ============================================================================

print("""
✅ CHANGES SUMMARY:

1. In paper_trading_config.py:
   PAPER_TRADING_ENABLED = True

2. In single_trade_focus_bot.py (top of file, ~line 8):
   REMOVE: from Dhan_Tradehull_V3 import Tradehull
   ADD:    from paper_trading_wrapper import get_trading_instance

3. In single_trade_focus_bot.py (~line 46):
   REMOVE: tsl = Tradehull(client_code, token_id)
   ADD:    tsl = get_trading_instance(client_code, token_id)

🎮 Run your bot: python single_trade_focus_bot.py
📊 View logs: paper_trading_log.txt
📈 Excel file still works the same way!

⚠️  To switch back to LIVE trading:
   Set PAPER_TRADING_ENABLED = False in paper_trading_config.py
   (No code changes needed!)
""")
