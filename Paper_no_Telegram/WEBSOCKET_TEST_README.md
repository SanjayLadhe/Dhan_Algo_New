# WebSocket Testing Guide

## Quick Start

### Method 1: Automated Testing (Predefined Symbols)

1. **Edit `test_websocket.py`** and add symbols to test:

```python
TEST_SYMBOLS = [
    "ICICIGI 28 OCT 1860 CALL",
    "RELIANCE 28 OCT 1300 CALL",
    "INFY 28 OCT 1900 PUT",
]
```

2. **Run the test:**

```bash
cd Paper_no_Telegram
python test_websocket.py
```

3. **Watch the output** - You'll see real-time updates every 5 seconds for 60 seconds

---

### Method 2: Interactive Testing (Manual Entry)

1. **Keep `TEST_SYMBOLS` empty** in `test_websocket.py`:

```python
TEST_SYMBOLS = []  # Empty list for manual mode
```

2. **Run the test:**

```bash
cd Paper_no_Telegram
python test_websocket.py
```

3. **Enter symbols interactively:**

```
➤ Enter symbol or command: RELIANCE 28 OCT 1300 CALL
```

**Available Commands:**
- Enter option symbol → Subscribe to that symbol
- `list` → Show all subscribed symbols
- `status` → Show current data for all symbols
- `quit` or `exit` → Stop testing

---

## Option Symbol Format

**Format:** `UNDERLYING DD MMM STRIKE CALL/PUT`

**Examples:**
```
ICICIGI 28 OCT 1860 CALL
RELIANCE 28 OCT 1300 CALL
INFY 28 OCT 1900 PUT
BAJAJ-AUTO 28 OCT 9500 CALL
HDFCBANK 28 OCT 1700 PUT
```

**Important:**
- Use **EXACT** symbol name from Dhan instrument file
- Month: Use 3-letter abbreviation (JAN, FEB, MAR, APR, etc.)
- Strike: Use exact strike price (no decimals for index options)
- Type: CALL or PUT (uppercase)

---

## Expected Output

### Initial Subscription
```
🔌 Initializing WebSocket Manager...
✅ WebSocket Market Data Manager initialized (DhanFeed)
   📂 Instrument file: Dependencies\all_instrument 2025-10-15.csv

🔄 Subscribing to test symbols...

  Subscribing to: ICICIGI 28 OCT 1860 CALL
  📋 Loaded 211735 instruments from file
  ✅ Found security ID: 89545 for ICICIGI 28 OCT 1860 CALL
  ✅ Subscribed to ICICIGI 28 OCT 1860 CALL (Security ID: 89545)
  ✅ WebSocket thread started
  🔄 WebSocket connection starting with DhanFeed...
  📊 Subscribing to 1 instruments
    ✅ Subscribed
```

### Real-time Data Updates
```
📊 STATUS UPDATE - Elapsed Time: 5s / 60s
================================================================================

  📊 ICICIGI 28 OCT 1860 CALL
  ──────────────────────────────────────────────────────────────────────
  💰 LTP:        ₹   40.75
  📉 Bid:        ₹   40.50
  📈 Ask:        ₹   41.00
  📏 Spread:     ₹    0.50
  📦 Volume:        12,345
  🕐 Updated:    14:35:22

────────────────────────────────────────────────────────────────────────────
📈 Data Received: 1/1 symbols
🔌 Connection: ACTIVE
────────────────────────────────────────────────────────────────────────────
```

---

## Configuration

**Edit these values in `test_websocket.py`:**

```python
# Test duration (seconds)
TEST_DURATION = 60  # Default: 1 minute

# Status update interval (seconds)
STATUS_UPDATE_INTERVAL = 5  # Default: Every 5 seconds

# Your credentials (already set from main bot)
CLIENT_CODE = "1106090196"
TOKEN_ID = "your_token_here"
```

---

## Troubleshooting

### Problem: "Symbol not found in instrument file"

**Solution:**
- Check symbol spelling and format
- Verify the symbol exists in `Dependencies/all_instrument*.csv`
- Use exact symbol name including spaces and case

### Problem: "Waiting for WebSocket data..."

**Possible Causes:**
1. **Market is closed** → WebSocket won't receive data outside market hours (9:15 AM - 3:30 PM)
2. **Symbol has no trades** → LTP will be 0 until first trade
3. **Connection issue** → Check internet connection

**What to do:**
- Wait 5-10 seconds for data to arrive
- Check if market is currently open
- Try a more liquid option (like NIFTY, BANKNIFTY)

### Problem: "Too many requests" error

**Solution:**
- This test tool uses WebSocket **only** (no API polling)
- Should not cause rate limit errors
- If you see this, your main bot might be running simultaneously

### Problem: WebSocket not connecting

**Check:**
1. **Token validity** → Your token might be expired (tokens expire after some time)
2. **Internet connection** → WebSocket needs stable internet
3. **Firewall** → Check if WebSocket port is blocked

---

## Testing Best Practices

### 1. Test During Market Hours
```
Recommended: 9:30 AM - 3:15 PM (Indian market hours)
Avoid: Pre-market or post-market (no live data)
```

### 2. Start with Liquid Options
```
Good for testing:
- NIFTY 28 OCT 24000 CALL
- BANKNIFTY 28 OCT 51000 CALL
- RELIANCE 28 OCT 1300 CALL

Avoid for first test:
- Very far OTM options
- Weekly expiries on Monday morning
- Illiquid stocks
```

### 3. Test Multiple Symbols
```python
TEST_SYMBOLS = [
    "NIFTY 28 OCT 24000 CALL",      # Index option
    "BANKNIFTY 28 OCT 51000 CALL",  # Bank index
    "RELIANCE 28 OCT 1300 CALL",    # Stock option
]
```

---

## Integration with Main Bot

Once WebSocket testing is successful, your main bot (`single_trade_focus_bot.py`) will automatically:

1. ✅ Subscribe to WebSocket when trade is placed
2. ✅ Use WebSocket data for monitoring (faster, no API limits)
3. ✅ Fallback to API if WebSocket data unavailable
4. ✅ Unsubscribe from WebSocket when position is exited

**No changes needed** - it's already integrated!

---

## Sample Test Session

```bash
# Terminal output
$ python test_websocket.py

🔌 DHAN WEBSOCKET TESTING TOOL
================================================================================
📅 Test Started: 2025-10-15 14:30:00
⏱️  Test Duration: 60 seconds
📊 Symbols to Test: 0
================================================================================

🎯 MANUAL TESTING MODE
================================================================================
Enter option symbols to test (one per line)
Format: UNDERLYING DD MMM STRIKE CALL/PUT
Example: RELIANCE 28 OCT 1300 CALL
================================================================================

➤ Enter symbol or command: ICICIGI 28 OCT 1860 CALL

🔄 Subscribing to ICICIGI 28 OCT 1860 CALL...
  ✅ Found security ID: 89545 for ICICIGI 28 OCT 1860 CALL
  ✅ Subscribed to ICICIGI 28 OCT 1860 CALL (Security ID: 89545)
  ✅ Subscribed successfully!
  ⏳ Waiting for WebSocket data...

  📊 ICICIGI 28 OCT 1860 CALL
  ──────────────────────────────────────────────────────────────────────
  💰 LTP:        ₹   40.75
  📉 Bid:        ₹   40.50
  📈 Ask:        ₹   41.00
  📏 Spread:     ₹    0.50
  📦 Volume:        12,345
  🕐 Updated:    14:35:22

➤ Enter symbol or command: list

📋 Subscribed Symbols (1):
  1. ICICIGI 28 OCT 1860 CALL

➤ Enter symbol or command: quit

👋 Stopping test...
✅ WebSocket stopped
```

---

## Need Help?

**Check these files for reference:**
- `websocket_manager.py` - WebSocket implementation
- `single_trade_focus_bot.py` - Bot integration example
- `ce_entry_logic.py` / `pe_entry_logic.py` - Subscribe on entry examples

**Common Issues:**
- Symbol format → Check exact spelling in instrument CSV
- No data → Ensure market is open (9:15 AM - 3:30 PM IST)
- Connection errors → Check token validity and internet

Happy Testing! 🚀
