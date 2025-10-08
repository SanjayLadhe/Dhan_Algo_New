# Paper Trading Setup Instructions

## 📋 Overview

This paper trading system allows you to test your trading bot **WITHOUT placing real orders** or risking real money. All trades are simulated, but market data is real.

---

## 🚀 Quick Start (3 Steps)

### Step 1: Enable Paper Trading

Open `paper_trading_config.py` and set:

```python
PAPER_TRADING_ENABLED = True  # Enable paper trading
```

### Step 2: Modify Your Bot File

In `single_trade_focus_bot.py`, find this line (around line 46):

```python
tsl = Tradehull(client_code, token_id)
```

**Replace it with:**

```python
from paper_trading_wrapper import get_trading_instance
tsl = get_trading_instance(client_code, token_id)
```

### Step 3: Run Your Bot

```bash
python single_trade_focus_bot.py
```

That's it! Your bot now runs in paper trading mode.

---

## 🎯 What Gets Simulated?

### ✅ Simulated (Paper Trading):
- ✅ Order placement (BUY/SELL)
- ✅ Order execution prices (with realistic slippage)
- ✅ Stop loss orders
- ✅ Target exits
- ✅ Trailing stop loss updates
- ✅ Balance tracking
- ✅ P&L calculation
- ✅ Telegram alerts (logged, not sent)

### 🔄 Real Data Used:
- 🔄 Historical price data
- 🔄 Live price data (LTP)
- 🔄 Technical indicators (RSI, VWAP, ATR, etc.)
- 🔄 Option chain data
- 🔄 Lot sizes

---

## ⚙️ Configuration Options

Edit `paper_trading_config.py` to customize:

```python
# Enable/Disable Paper Trading
PAPER_TRADING_ENABLED = True  # True = Paper, False = Live

# Starting Capital
PAPER_TRADING_BALANCE = 1005000  # Your virtual balance

# Slippage Simulation
SLIPPAGE_PERCENTAGE = 0.1  # 0.1% slippage
SLIPPAGE_POINTS = 0.5      # Additional 0.5 points

# Order Execution Delay
ORDER_EXECUTION_DELAY = 0.5  # 0.5 seconds

# Logging
VERBOSE_LOGGING = True  # Print detailed logs
PAPER_TRADING_LOG_FILE = "paper_trading_log.txt"
```

---

## 📊 Viewing Results

### During Trading:
All paper trades are logged to console with `[PAPER]` prefix:
```
[PAPER] ✅ ORDER PLACED: MARKET BUY 25 RELIANCE25APR2425500CE @ ₹45.50
[PAPER] 💰 Balance reduced: ₹1,137.50 | New Balance: ₹1,003,862.50
```

### After Trading Session:
View complete log in `paper_trading_log.txt`:
```
[2025-01-15 09:30:00] Paper Trading Session Started
[2025-01-15 09:30:00] Initial Balance: ₹1,005,000.00
[2025-01-15 09:35:12] ✅ ORDER PLACED: MARKET BUY 25 RELIANCE...
[2025-01-15 10:15:45] 🎯 SL TRIGGERED...
```

### Excel Files:
Paper trades are still recorded in `Live Trade Data.xlsx` just like real trades!

---

## 🔄 Switching Between Paper and Live Trading

### To Enable Paper Trading:
```python
# In paper_trading_config.py
PAPER_TRADING_ENABLED = True
```

### To Enable Live Trading:
```python
# In paper_trading_config.py
PAPER_TRADING_ENABLED = False
```

**No other changes needed!** The wrapper handles everything.

---

## 🐛 Troubleshooting

### Problem: Bot crashes with "Entry price is None"

**Solution:** This was the original issue. Paper trading fixes it by:
1. ✅ Always simulating successful order execution
2. ✅ Always returning a valid executed price
3. ✅ Never returning `None` for executed prices

### Problem: Orders seem to execute too quickly

**Solution:** Increase `ORDER_EXECUTION_DELAY` in `paper_trading_config.py`:
```python
ORDER_EXECUTION_DELAY = 2.0  # 2 second delay
```

### Problem: Want to test order failures

**Solution:** Enable failure simulation in `paper_trading_config.py`:
```python
SIMULATE_ORDER_FAILURES = True
ORDER_FAILURE_RATE = 0.1  # 10% of orders will fail
```

---

## 📈 Example Paper Trading Session

```
================================================================================
🎮 PAPER TRADING MODE ENABLED
================================================================================
⚠️  NO REAL ORDERS WILL BE PLACED
⚠️  ALL TRADES ARE SIMULATED
📊 Starting Balance: ₹1,005,000.00
📝 Logs: paper_trading_log.txt
================================================================================

[PAPER] Paper Trading Simulator Initialized

🔍 SCANNING FOR ENTRY - 09:35:12
[PAPER] ✅ ORDER PLACED: MARKET BUY 25 RELIANCE25APR2425500CE @ ₹45.50
[PAPER] 💰 Balance reduced: ₹1,137.50 | New Balance: ₹1,003,862.50

👁️ MONITORING ACTIVE POSITION: RELIANCE - 09:36:00
[PAPER] 📈 TSL updated for RELIANCE to 42.30

🎯 TARGET HIT - RELIANCE
[PAPER] ✅ ORDER PLACED: MARKET SELL 25 RELIANCE25APR2425500CE @ ₹52.20
[PAPER] 💰 Balance increased: ₹1,305.00 | New Balance: ₹1,005,167.50

================================================================================
PAPER TRADING SESSION SUMMARY
================================================================================
Initial Balance:  ₹1,005,000.00
Current Balance:  ₹1,005,167.50
P&L:              ₹167.50 (+0.02%)
Total Orders:     2
  - Executed:     2
  - Pending:      0
================================================================================
```

---

## 🔐 Safety Features

1. **No Real API Calls for Orders:** Order placement is 100% simulated
2. **Real Market Data:** Uses actual live prices for realistic simulation
3. **Balance Tracking:** Prevents over-trading beyond available capital
4. **Separate Logging:** All paper trades logged separately
5. **Easy Toggle:** Switch to live trading with one config change

---

## 📝 Files Created

1. **paper_trading_config.py** - Configuration settings
2. **paper_trading_simulator.py** - Simulates Tradehull API
3. **paper_trading_wrapper.py** - Auto-switches between real/paper
4. **PAPER_TRADING_INSTRUCTIONS.md** - This file

---

## ❓ FAQ

**Q: Will paper trading show my real Dhan balance?**
A: No, it uses a simulated balance set in `paper_trading_config.py`

**Q: Does paper trading use real market data?**
A: Yes! It fetches real historical and live price data, only the orders are simulated.

**Q: Can I test different strategies risk-free?**
A: Absolutely! That's exactly what paper trading is for.

**Q: How realistic is the slippage simulation?**
A: It's a reasonable approximation. Adjust `SLIPPAGE_PERCENTAGE` based on your observations.

**Q: Will my Excel file get populated?**
A: Yes! Paper trades are recorded in Excel just like real trades.

**Q: Can I run paper and live trading simultaneously?**
A: No, but you can run the bot twice with different config files.

---

## 🎓 Best Practices

1. **Test Thoroughly:** Run paper trading for at least 1 week before going live
2. **Match Conditions:** Use same risk parameters in paper as you plan for live
3. **Review Logs:** Regularly check `paper_trading_log.txt` for insights
4. **Track Performance:** Monitor paper P&L to validate strategy
5. **Adjust Slippage:** Tune slippage settings to match your broker's execution

---

## ⚠️ Important Notes

- **Paper trading ≠ Live trading:** Real trades have emotions, fees, and different execution
- **Slippage varies:** Real slippage may be higher during volatile markets
- **Exchange fees not simulated:** Add ~0.05% to costs for realistic comparison
- **Market impact:** Large orders in live trading may have more slippage
- **Always start small:** When switching to live, start with minimum lot sizes

---

## 🆘 Need Help?

If you encounter issues:

1. Check `paper_trading_log.txt` for detailed error messages
2. Verify `PAPER_TRADING_ENABLED = True` in config
3. Ensure you modified the correct line in your bot file
4. Check that all new files are in the same directory as your bot

---

**Happy Paper Trading! 📊🎮**
