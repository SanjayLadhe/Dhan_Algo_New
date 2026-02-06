import pdb
import time
import datetime
import traceback
from ta.volume import volume_weighted_average_price
from ta.volume import VolumeWeightedAveragePrice
from paper_trading_wrapper import get_trading_instance
import pandas as pd
from pprint import pprint
import talib
import pandas_ta as pta
import xlwings as xw
import winsound
#import sqn_lib
from VWAP import calculate_vwap_daily
from ATRTrailingStop import ATRTrailingStopIndicator
import Fractal_Chaos_Bands
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from SectorPerformanceAnalyzer import get_sector_watchlist

# ============================
# IMPORT RATE LIMITER MODULE
# ============================
from rate_limiter import (
    data_api_limiter,
    ntrading_api_limiter,
    order_api_limiter,
    ltp_api_limiter,
    retry_api_call
)

# ============================
# IMPORT CE AND PE ENTRY MODULES
# ============================
from ce_entry_logic import execute_ce_entry
from pe_entry_logic import execute_pe_entry

# ============================
# IMPORT EXIT LOGIC MODULE
# ============================
from exit_logic import process_exit_conditions

# Configure pandas display
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

# ============================
# API CREDENTIALS
# ============================
client_code = "1106090196"
token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzcwMjk3NjIzLCJpYXQiOjE3NzAyMTEyMjMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.HhvrxfuiMBUO7CIgqAILgx3JALBOHT_D7p-V8Z2TnYAHKWYFXBPgJhRUtXQHjyJ5UFjliETV9m-1l-yKD4PZUA"
tsl = get_trading_instance(client_code, token_id)
# ============================
# RISK MANAGEMENT PARAMETERS
# ============================all the
opening_balance = 1005000  # tsl.get_balance()
base_capital = 1000000
market_money = opening_balance - base_capital

# Because I am losing money, so I have 0 market money, and I can take risk on the current opening balance
if (market_money < 0):
    market_money = 0
    base_capital = opening_balance

market_money_risk = (market_money * 1) / 100
base_capital_risk = (base_capital * 0.5) / 100
max_risk_for_today = base_capital_risk + market_money_risk

max_order_for_today = 2  # Maximum orders allowed for the day
max_simultaneous_positions = 2  # ✅ NEW: Allow 2 positions at the same time
risk_per_trade = (max_risk_for_today / max_order_for_today)
atr_multipler = 3
risk_reward = 3

# ============================
# OPTION STOP LOSS CONFIGURATION
# ============================
# Percentage-based stop loss for options (more reliable than ATR for volatile premiums)
option_sl_percentage = 0.15  # 15% stop loss from entry price
# This gives options breathing room while still protecting capital

# ============================
    # TELEGRAM CONFIGURATION - DISABLED
# ============================
# Telegram functionality removed in this version

# ============================
# TRADING CONFIGURATION
# ============================
reentry = "no"  # "yes/no"

# ============================
# TIMING PARAMETERS (MULTI-POSITION TRADING)
# ============================
MONITOR_INTERVAL = 5    # Check every 5 seconds when IN position(s)
SCAN_INTERVAL = 30      # Scan for entry every 30 seconds when NOT at max positions
WATCHLIST_REFRESH_INTERVAL = 15 * 60  # Refresh watchlist every 15 minutes (900 seconds)
REENTRY_COOLDOWN = 10 * 60  # Cooldown period after exit before re-entering same symbol (10 minutes)
MIN_HOLD_CANDLES = 3    # Minimum 3 candles (9 minutes on 3-min TF) before RSI/LongStop exit is evaluated

# Track last exit time for each symbol (prevents immediate re-entry)
symbol_exit_times = {}

# Track total orders placed today
# NOTE: This is recalculated from completed_orders on each check to survive bot restarts
total_orders_placed_today = 0

# ============================
# WATCHLIST FUNCTIONS
# ============================
def get_dynamic_watchlist():
    """
    Get watchlist from best performing sectors
    Falls back to static list if sector analysis fails
    """
    try:
        print("Fetching watchlist from best performing sectors...")
        sector_watchlist = get_sector_watchlist()

        if sector_watchlist and len(sector_watchlist) > 10:
            print(f"✅ Using sector-based watchlist with {len(sector_watchlist)} stocks")
            return sector_watchlist
        else:
            print("⚠️ Sector watchlist too small, using static fallback")
            return get_static_watchlist()

    except Exception as e:
        print(f"❌ Error getting sector watchlist: {e}")
        print("Using static watchlist as fallback")
        return get_static_watchlist()


def get_static_watchlist():
    """Static fallback watchlist"""
    return [
        "LTIM", "LUPIN", "M&M", "MANKIND", "MARUTI", "KAYNES", "KEI",
        "MAXHEALTH", "KFINTECH", "MAZDOCK", "KOTAKBANK", "MCX", "KPITTECH",
        "MPHASIS", "MUTHOOTFIN", "LODHA", "NAUKRI", "LT", "NESTLEIND",
        "NUVAMA", "OBEROIRLTY", "OFSS", "PAGEIND", "PATANJALI", "PERSISTENT",
        "PHOENIXLTD", "PIDILITIND", "PIIND", "POLICYBZR", "POLYCAB",
        "PRESTIGE", "RELIANCE", "SBILIFE", "SHREECEM", "SIEMENS",
        "SOLARINDS", "SRF", "SUNPHARMA", "SUPREMEIND", "TATACONSUM",
        "TATAELXSI", "TCS", "TIINDIA", "TITAN", "TORNTPHARM", "TORNTPOWER",
        "TRENT", "TVSMOTOR", "ULTRACEMCO", "UNITDSPR", "UNOMINDA",
        "VOLTAS", "360ONE", "ABB", "ADANIENT", "ALKEM", "ANGELONE",
        "APOLLOHOSP", "ASIANPAINT", "ADANIPORTS", "BAJAJ-AUTO", "BOSCHLTD",
        "BRITANNIA", "BSE", "APLAPOLLO", "AUROPHARMA", "BAJAJFINSV",
        "CDSL", "COFORGE", "COLPAL", "BDL", "CYIENT", "BHARATFORG",
        "DALBHARAT", "BHARTIARTL", "BLUESTARCO", "DMART", "EICHERMOT",
        "GODREJPROP", "GRASIM", "HDFCAMC", "ICICIGI", "INDIGO", "AMBER",
        "INFY", "HEROMOTOCO", "DIVISLAB", "GLENMARK", "GODREJCP", "HAL",
        "HAVELLS", "HINDUNILVR", "ASTRAL", "CAMS", "CUMMINSIND", "DIXON",
        "HCLTECH", "CIPLA"
    ]


# ============================
# EXCEL INITIALIZATION
# ============================
single_order = {'name': None, 'date': None, 'entry_time': None, 'entry_price': None, 'buy_sell': None, 'qty': None,
                'sl': None, 'exit_time': None, 'exit_price': None, 'pnl': None, 'remark': None, 'traded': None}
orderbook = {}
completed_orders = []

wb = xw.Book('Live Trade Data.xlsx')
live_Trading = wb.sheets['Live_Trading']
completed_orders_sheet = wb.sheets['completed_orders']

live_Trading.range("A2:Z100").value = None
completed_orders_sheet.range("A2:Z100").value = None

# Get dynamic watchlist
watchlist = get_dynamic_watchlist()
last_watchlist_refresh_time = time.time()  # Track when watchlist was last refreshed

# Initialize orderbook
for name in watchlist:
    orderbook[name] = single_order.copy()


# ============================
# REFRESH WATCHLIST FROM SECTORS
# ============================
def refresh_watchlist_if_needed(last_refresh_time):
    """
    Refresh watchlist from sectors if 15 minutes have passed.

    Args:
        last_refresh_time: Timestamp of last watchlist refresh

    Returns:
        tuple: (new_watchlist, new_refresh_time)
    """
    global watchlist, orderbook

    current_time = time.time()
    time_since_refresh = current_time - last_refresh_time

    if time_since_refresh >= WATCHLIST_REFRESH_INTERVAL:
        print("\n" + "="*80)
        print(f"🔄 REFRESHING WATCHLIST - 15 minutes elapsed since last refresh")
        print("="*80)

        # Get new watchlist from sectors
        new_watchlist = get_dynamic_watchlist()

        # Update orderbook with new symbols (preserve existing active positions)
        for name in new_watchlist:
            if name not in orderbook:
                orderbook[name] = single_order.copy()
                print(f"  ➕ Added new symbol: {name}")

        # Remove symbols no longer in watchlist (only if they have no active position)
        symbols_to_remove = []
        for name in orderbook:
            if name not in new_watchlist and orderbook[name].get('qty', 0) == 0:
                symbols_to_remove.append(name)

        for name in symbols_to_remove:
            del orderbook[name]
            print(f"  ➖ Removed symbol: {name}")

        print(f"✅ Watchlist refreshed: {len(new_watchlist)} symbols")
        print("="*80 + "\n")

        return new_watchlist, current_time

    return watchlist, last_refresh_time


# ============================
# HEIKIN ASHI TRANSFORMATION
# ============================
def heikin_ashi(df):
    """
    Convert regular candlesticks to Heikin Ashi candlesticks
    """
    try:
        if df.empty:
            return df

        # Ensure the DataFrame has the required columns
        required_columns = ['open', 'high', 'low', 'close', 'timestamp']
        if not all(col in df.columns for col in required_columns):
            print(f"⚠️ Warning: DataFrame missing required columns for Heikin Ashi")
            return df

        # Prepare Heikin-Ashi columns
        ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        ha_open = [df['open'].iloc[0]]  # Initialize the first open value
        ha_high = []
        ha_low = []

        # Compute Heikin-Ashi values
        for i in range(1, len(df)):
            ha_open.append((ha_open[-1] + ha_close.iloc[i - 1]) / 2)
            ha_high.append(max(df['high'].iloc[i], ha_open[-1], ha_close.iloc[i]))
            ha_low.append(min(df['low'].iloc[i], ha_open[-1], ha_close.iloc[i]))

        # Append first values for high and low
        ha_high.insert(0, df['high'].iloc[0])
        ha_low.insert(0, df['low'].iloc[0])

        # Create a new DataFrame for Heikin-Ashi values, preserving other columns
        ha_df = df.copy()
        ha_df['open'] = ha_open
        ha_df['high'] = ha_high
        ha_df['low'] = ha_low
        ha_df['close'] = ha_close

        return ha_df
    except Exception as e:
        print(f"❌ Error in Heikin-Ashi calculation: {e}")
        return df


# ============================
# FETCH HISTORICAL WITH RATE LIMITER
# ============================
def fetch_historical(name, use_heikin_ashi=False):
    """
    Fetch historical data for a symbol with rate limiting

    Args:
        name: Symbol name
        use_heikin_ashi: Whether to apply Heikin Ashi transformation (default: False)
    """
    exchange = "INDEX" if name == "NIFTY" else "NSE"
    data_api_limiter.wait(
        call_description=f"tsl.get_historical_data(tradingsymbol='{name}', exchange='{exchange}', timeframe='1')")
    fetch_time = datetime.datetime.now()
    print(f"📊 Fetching historical data for {name} at {fetch_time.strftime('%H:%M:%S')}")

    Data = tsl.get_historical_data(tradingsymbol=name, exchange=exchange, timeframe="1")
    if Data is None:
        print(f"[ERROR] Failed to fetch historical data for {name}. Returned None.")
        return name, None, fetch_time

    # Resample to 3-minute timeframe - NO HEIKIN ASHI TRANSFORMATION
    chart = tsl.resample_timeframe(Data, timeframe="3T")

    # Apply Heikin Ashi transformation ONLY if explicitly requested (disabled by default)
    if use_heikin_ashi:
        chart = heikin_ashi(chart)
        print(f"🕯️ Applied Heikin Ashi transformation to {name}")
    else:
        print(f"📊 Using regular candles for {name} (No Heikin Ashi)")

    Data = Data.reset_index()
    complete_time = datetime.datetime.now()
    print(f"✅ Completed fetching for {name} at {complete_time.strftime('%H:%M:%S')}")
    return name, chart, complete_time


# ============================
# COMPUTE INDICATORS
# ============================
def compute_indicators(chart):
    """Compute all technical indicators for the chart"""
    try:
        # VWAP
        chart["vwap"] = calculate_vwap_daily(chart["high"], chart["low"], chart["close"], chart["volume"],
                                             chart["timestamp"])

        # RSI
        chart['rsi'] = pta.rsi(chart['close'], timeperiod=14)
        chart['ma_rsi'] = pta.sma(chart['rsi'], timeperiod=20)
        chart['ma'] = pta.sma(chart['close'], timeperiod=12)

        # Parabolic SAR
        para = pta.psar(high=chart['high'], low=chart['low'], close=chart['close'], step=0.05, max_step=0.2,
                        offset=None)
        chart[['PSARl_0.02_0.2', 'PSARs_0.02_0.2', 'PSARaf_0.02_0.2', 'PSARr_0.02_0.2']] = para[
            ['PSARl_0.02_0.2', 'PSARs_0.02_0.2', 'PSARaf_0.02_0.2', 'PSARr_0.02_0.2']]

        # ATR Trailing Stop
        atr_strategy = ATRTrailingStopIndicator(period=21, multiplier=1.0)
        result_df = atr_strategy.compute_indicator(chart)
        chart[['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']] = result_df[
            ['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']]

        # Fractal Chaos Bands
        df_with_bands = Fractal_Chaos_Bands.fractal_chaos_bands(chart)
        df_with_signals = Fractal_Chaos_Bands.get_fcb_signals(df_with_bands)
        chart[['fractal_high', 'fractal_low', 'signal']] = df_with_signals[['fractal_high', 'fractal_low', 'signal']]

        # ADX (Average Directional Index) - For directional movement
        from adx_indicator import calculate_adx_indicators
        chart = calculate_adx_indicators(chart, period=14)

        return chart
    except Exception as e:
        print(f"❌ Error computing indicators: {e}")
        traceback.print_exc()
        return chart


# ============================
# CHECK IF POSITION ACTIVE
# ============================
def is_position_active():
    """
    Check if there are any active positions in the orderbook

    Returns:
        tuple: (has_position: bool, active_positions: DataFrame, position_count: int)
    """
    orderbook_df = pd.DataFrame(orderbook).T
    active_positions = orderbook_df[orderbook_df['qty'] > 0]
    position_count = len(active_positions)
    return position_count > 0, active_positions, position_count


# ============================
# CHECK IF CAN TAKE NEW POSITION
# ============================
def can_take_new_position():
    """
    Check if we can take a new position based on max_simultaneous_positions limit

    Returns:
        tuple: (can_enter: bool, current_count: int, max_allowed: int)
    """
    _, _, position_count = is_position_active()
    can_enter = position_count < max_simultaneous_positions
    return can_enter, position_count, max_simultaneous_positions


# ============================
# GET ACTIVE POSITION SYMBOLS
# ============================
def get_active_position_symbols():
    """
    Get all active position symbol names

    Returns:
        list: List of symbol names with active positions
    """
    orderbook_df = pd.DataFrame(orderbook).T
    active_positions = orderbook_df[orderbook_df['qty'] > 0]
    return active_positions.index.tolist()


# ============================
# SCAN FOR ENTRY (ALL SYMBOLS)
# ============================
def scan_for_entry(all_ltp):
    """
    Scan all symbols in watchlist for entry opportunities
    Stops scanning when max_simultaneous_positions is reached
    """
    # Check if we can take new position
    can_enter, current_positions, max_positions = can_take_new_position()

    global total_orders_placed_today

    if not can_enter:
        print(f"\n⏸️ Max positions reached ({current_positions}/{max_positions}) - No scanning")
        return False

    # ✅ FIX: Derive total_orders_placed_today from completed_orders + active positions
    # This survives bot restarts (completed_orders may be empty on restart, but active positions persist)
    active_count = sum(1 for v in orderbook.values() if isinstance(v, dict) and v.get('traded') == "yes")
    total_orders_placed_today = len(completed_orders) + active_count

    # Enforce max_order_for_today (total trades for the day, not just active)
    if total_orders_placed_today >= max_order_for_today:
        print(f"\n⛔ Daily order limit reached ({total_orders_placed_today}/{max_order_for_today}) - No more trades today")
        return False

    print("\n" + "="*80)
    print(f"🔍 SCANNING FOR ENTRY - {datetime.datetime.now().strftime('%H:%M:%S')}")
    print(f"📊 Current Positions: {current_positions}/{max_positions} | Daily Orders: {total_orders_placed_today}/{max_order_for_today}")
    print("="*80)

    # Calculate current number of orders placed
    orderbook_df = pd.DataFrame(orderbook).T
    no_of_orders_placed = orderbook_df[orderbook_df['qty'] > 0].shape[0]
    
    # Process symbols in smaller batches for faster scanning
    batch_size = 5
    for i in range(0, len(watchlist), batch_size):
        batch_symbols = watchlist[i:i + batch_size]
        print(f"\n📦 Processing batch {i//batch_size + 1}: {batch_symbols}")

        # Fetch data for batch concurrently
        fetched_data = {}
        with ThreadPoolExecutor(max_workers=batch_size) as fetch_executor:
            future_to_name_fetch = {fetch_executor.submit(fetch_historical, name): name for name in batch_symbols}

            for future in as_completed(future_to_name_fetch):
                try:
                    name, chart, fetch_time = future.result()
                    fetched_data[name] = (chart, fetch_time)
                except Exception as e:
                    name = future_to_name_fetch[future]
                    print(f"❌ Error fetching data for {name}: {e}")
                    traceback.print_exc()
                    continue

        # Process each symbol for entry
        for name, (chart, fetch_time) in fetched_data.items():
            if chart is None:
                print(f"⏭️ Skipping {name} - No chart data")
                continue

            # ✅ CHECK COOLDOWN - Prevent re-entry too soon after exit
            if name in symbol_exit_times:
                time_since_exit = time.time() - symbol_exit_times[name]
                if time_since_exit < REENTRY_COOLDOWN:
                    remaining_cooldown = REENTRY_COOLDOWN - time_since_exit
                    print(f"⏸️ Skipping {name} - Cooldown active ({remaining_cooldown/60:.1f} min remaining)")
                    continue
                else:
                    # Cooldown expired, remove from tracking
                    del symbol_exit_times[name]

            try:
                # Compute indicators
                chart = compute_indicators(chart)

                # ============================
                # ✅ CE ENTRY - Using Modular Function
                # ============================
                ce_success, ce_message = execute_ce_entry(
                    tsl=tsl,
                    name=name,
                    chart=chart,
                    orderbook=orderbook,
                    no_of_orders_placed=no_of_orders_placed,
                    atr_multipler=atr_multipler,
                    bot_token=None,
                    receiver_chat_id=None
                )

                if ce_success:
                    total_orders_placed_today += 1
                    print(f"\n{'='*80}")
                    print(f"✅ ENTRY EXECUTED: {ce_message}")
                    print(f"📊 Daily Orders: {total_orders_placed_today}/{max_order_for_today}")
                    print(f"{'='*80}\n")
                    update_excel_sheets()

                    # Check if we've reached max positions
                    _, new_position_count, _ = can_take_new_position()
                    if not can_take_new_position()[0]:  # Max positions reached
                        print(f"🛑 Max positions ({max_simultaneous_positions}) reached - Stopping scan")
                        return True
                    else:
                        print(f"✅ Position {new_position_count + 1}/{max_simultaneous_positions} taken - Can take 1 more")
                        return True  # Entry executed, stop this scan iteration

                # ============================
                # ✅ PE ENTRY - Using Modular Function
                # ============================
                pe_success, pe_message = execute_pe_entry(
                    tsl=tsl,
                    name=name,
                    chart=chart,
                    orderbook=orderbook,
                    no_of_orders_placed=no_of_orders_placed,
                    atr_multipler=atr_multipler,
                    bot_token=None,
                    receiver_chat_id=None
                )

                if pe_success:
                    total_orders_placed_today += 1
                    print(f"\n{'='*80}")
                    print(f"✅ ENTRY EXECUTED: {pe_message}")
                    print(f"📊 Daily Orders: {total_orders_placed_today}/{max_order_for_today}")
                    print(f"{'='*80}\n")
                    update_excel_sheets()

                    # Check if we've reached max positions
                    _, new_position_count, _ = can_take_new_position()
                    if not can_take_new_position()[0]:  # Max positions reached
                        print(f"🛑 Max positions ({max_simultaneous_positions}) reached - Stopping scan")
                        return True
                    else:
                        print(f"✅ Position {new_position_count + 1}/{max_simultaneous_positions} taken - Can take 1 more")
                        return True  # Entry executed, stop this scan iteration

            except Exception as e:
                print(f"❌ Error processing {name}: {e}")
                traceback.print_exc()
                continue

        # Small delay between batches
        time.sleep(0.5)

    print(f"\n⏸️ No entry signal found - Will scan again in {SCAN_INTERVAL} seconds")
    return False


# ============================
# MONITOR ACTIVE POSITION
# ============================
def monitor_active_position(symbol_name, all_ltp):
    """
    Monitor the active position for exit conditions
    Only called when a position IS active
    """
    print("\n" + "="*80)
    print(f"👁️ MONITORING ACTIVE POSITION: {symbol_name} - {datetime.datetime.now().strftime('%H:%M:%S')}")
    print("="*80)
    
    try:
        # Fetch fresh data for the active symbol
        name, chart, fetch_time = fetch_historical(symbol_name)
        
        if chart is None:
            print(f"⚠️ Warning: Could not fetch data for {symbol_name}")
            return False

        # Compute indicators
        chart = compute_indicators(chart)

        # Process start time for logging
        process_start_time = datetime.datetime.now()

        # ============================
        # ✅ CHECK EXIT CONDITIONS - Using Modular Function
        # ============================
        exit_status = process_exit_conditions(
            tsl=tsl,
            name=symbol_name,
            orderbook=orderbook,
            all_ltp=all_ltp,
            process_start_time=process_start_time,
            atr_multipler=atr_multipler,
            bot_token=None,
            receiver_chat_id=None,
            reentry=reentry,
            completed_orders=completed_orders,
            single_order=single_order,
            risk_reward=risk_reward
        )

        if exit_status in ["sl_hit", "target_hit", "rsi_longstop_exit", "time_exit"]:
            print(f"\n{'='*80}")
            print(f"🚪 EXIT EXECUTED: {exit_status} for {symbol_name}")
            print(f"{'='*80}\n")

            # ✅ Record exit time for cooldown tracking
            symbol_exit_times[symbol_name] = time.time()
            print(f"⏰ Cooldown started for {symbol_name} ({REENTRY_COOLDOWN/60:.0f} minutes)")

            update_excel_sheets()
            return True  # Position exited
        elif exit_status == "tsl_updated":
            print(f"📈 TSL updated for {symbol_name}")
            update_excel_sheets()

        return False  # Position still active

    except Exception as e:
        print(f"❌ Error monitoring {symbol_name}: {e}")
        traceback.print_exc()
        return False


# ============================
# UPDATE EXCEL SHEETS
# ============================
def update_excel_sheets():
    """Update Excel sheets with current orderbook and completed orders"""
    try:
        orderbook_df = pd.DataFrame(orderbook).T
        live_Trading.range('A1').value = orderbook_df

        if len(completed_orders) > 0:
            completed_orders_df = pd.DataFrame(completed_orders)
            completed_orders_sheet.range('A1').value = completed_orders_df
    except Exception as e:
        print(f"⚠️ Error updating Excel sheets: {e}")
        traceback.print_exc()


# ============================
# CHECK MARKET CONDITIONS
# ============================
def check_market_conditions():
    """Check if market is open and risk limits not hit"""
    current_time = datetime.datetime.now().time()
    
    # Check if market has started
    if current_time < datetime.time(9, 15):
        return "market_not_started", current_time
    
    # Check if market has closed
    if current_time > datetime.time(15, 15):
        return "market_closed", current_time
    
    # Check max loss
    live_pnl = tsl.get_live_pnl()
    max_loss_hit = live_pnl < (max_risk_for_today * -1)
    
    if max_loss_hit:
        return "max_loss_hit", current_time
    
    return "market_active", current_time


# ============================
# MAIN LOOP - SINGLE TRADE FOCUS
# ============================
def main():
    """
    Main trading loop with single-trade focus strategy
    - Scans every 30 seconds when NO position
    - Monitors every 5 seconds when IN position
    - Refreshes watchlist from sectors every 15 minutes
    - Enforces cooldown period after exits to prevent immediate re-entry
    """
    global watchlist, last_watchlist_refresh_time, symbol_exit_times

    print("\n" + "="*100)
    print("🚀 MULTI-POSITION TRADING BOT STARTED")
    print("="*100)
    print(f"📊 Strategy: Manage up to {max_simultaneous_positions} simultaneous positions")
    print(f"⏰ Scan Interval (No Position): {SCAN_INTERVAL} seconds")
    print(f"👁️ Monitor Interval (In Position): {MONITOR_INTERVAL} seconds")
    print(f"🔄 Watchlist Refresh Interval: {WATCHLIST_REFRESH_INTERVAL // 60} minutes")
    print(f"⏸️ Re-Entry Cooldown: {REENTRY_COOLDOWN // 60} minutes (prevents immediate re-entry)")
    print(f"💰 Risk per Trade: ₹{risk_per_trade:,.2f}")
    print(f"📈 Risk Reward Ratio: 1:{risk_reward}")
    print(f"🔢 Max Simultaneous Positions: {max_simultaneous_positions}")
    print(f"📋 Watchlist: {len(watchlist)} symbols")
    print("="*100 + "\n")

    last_scan_time = time.time() - SCAN_INTERVAL  # Force immediate first scan

    while True:
        try:
            # Check market conditions
            market_status, current_time = check_market_conditions()

            if market_status == "market_not_started":
                print(f"⏰ Waiting for market to start... Current time: {current_time.strftime('%H:%M:%S')}")
                time.sleep(10)
                continue  # ✅ FIX: Skip all trading logic until market opens

            if market_status in ["market_closed", "max_loss_hit"]:
                print(f"\n{'='*80}")
                if market_status == "market_closed":
                    print(f"🔔 MARKET CLOSED at {current_time.strftime('%H:%M:%S')}")
                else:
                    print(f"⛔ MAX LOSS HIT - Stopping trading at {current_time.strftime('%H:%M:%S')}")
                print(f"{'='*80}")

                # ✅ FIX: Uncommented - actually stop the bot
                try:
                    order_details = tsl.cancel_all_orders()
                    print("✅ All pending orders cancelled")
                except Exception as e:
                    print(f"⚠️ Error cancelling orders: {e}")

                print("\n👋 Bot stopped. See you tomorrow!")
                break

            # Check if we have any active positions
            has_position, active_positions, position_count = is_position_active()

            # Build LTP fetch list
            all_ltp = {}

            if has_position:
                # ============================
                # POSITION ACTIVE: Try WebSocket first, fallback to API
                # ============================

                # Get option symbol from active position
                for symbol_name in active_positions.index:
                    option_symbol = orderbook[symbol_name].get('options_name')

                    if option_symbol:
                        # Try to get WebSocket data first
                        try:
                            from websocket_manager import get_live_market_data
                            ws_data = get_live_market_data(option_symbol)

                            if ws_data and ws_data.get('ltp', 0) > 0:
                                all_ltp[option_symbol] = ws_data['ltp']
                                print(f"📡 WebSocket LTP for {option_symbol}: ₹{ws_data['ltp']:.2f}")
                            else:
                                # WebSocket data not available, use API
                                print(f"⚠️ WebSocket data not available for {option_symbol}, using API fallback")
                                ltp_api_limiter.wait(call_description=f"tsl.get_ltp_data(names=['{option_symbol}'])")
                                api_ltp = retry_api_call(tsl.get_ltp_data, retries=1, delay=1.0, names=[option_symbol])
                                if api_ltp:
                                    all_ltp.update(api_ltp)
                        except Exception as e:
                            print(f"⚠️ Error getting WebSocket data for {option_symbol}: {e}")
                            print(f"   Using API fallback...")
                            # Fallback to API
                            ltp_api_limiter.wait(call_description=f"tsl.get_ltp_data(names=['{option_symbol}'])")
                            api_ltp = retry_api_call(tsl.get_ltp_data, retries=1, delay=1.0, names=[option_symbol])
                            if api_ltp:
                                all_ltp.update(api_ltp)

            else:
                # ============================
                # NO POSITION: Fetch LTP for watchlist using API
                # ============================
                ltp_fetch_list = watchlist.copy()

                ltp_api_limiter.wait(call_description=f"tsl.get_ltp_data(names={len(ltp_fetch_list)} symbols)")
                all_ltp_raw = retry_api_call(tsl.get_ltp_data, retries=1, delay=1.0, names=ltp_fetch_list)

                if all_ltp_raw is None:
                    print("⚠️ Failed to fetch LTP data. Retrying in 5 seconds...")
                    time.sleep(5)
                    continue

                all_ltp = all_ltp_raw

            if has_position:
                # ============================
                # MONITOR MODE - Check ALL active positions every 5 seconds
                # ============================
                active_symbols = get_active_position_symbols()
                print(f"\n📊 Monitoring {len(active_symbols)} active position(s): {', '.join(active_symbols)}")

                any_position_exited = False
                for active_symbol in active_symbols:
                    position_exited = monitor_active_position(active_symbol, all_ltp)
                    if position_exited:
                        print(f"✅ Position exited for {active_symbol}")
                        any_position_exited = True

                if any_position_exited:
                    # Reset scan timer to start looking for next entry
                    last_scan_time = time.time() - SCAN_INTERVAL

                # Wait MONITOR_INTERVAL before next check
                time.sleep(MONITOR_INTERVAL)

                # ✅ NEW: Check if we can take another position while monitoring
                can_enter, current_pos, max_pos = can_take_new_position()
                if can_enter and (time.time() - last_scan_time >= SCAN_INTERVAL):
                    # We have room for another position and it's time to scan
                    print(f"\n🔍 Room for another position ({current_pos}/{max_pos}) - Initiating scan while monitoring")
                    scan_for_entry(all_ltp)
                    last_scan_time = time.time()

            else:
                # ============================
                # SCAN MODE - Check every 30 seconds
                # ============================

                # Refresh watchlist from sectors if 15 minutes have passed
                watchlist, last_watchlist_refresh_time = refresh_watchlist_if_needed(last_watchlist_refresh_time)

                current_time_sec = time.time()
                time_since_last_scan = current_time_sec - last_scan_time

                if time_since_last_scan >= SCAN_INTERVAL:
                    entry_executed = scan_for_entry(all_ltp)
                    last_scan_time = current_time_sec

                    if entry_executed:
                        # Position entered, switch to monitor mode immediately
                        continue
                    else:
                        # No entry, wait full scan interval
                        time.sleep(SCAN_INTERVAL)
                else:
                    # Not time to scan yet, wait remaining time
                    remaining_time = SCAN_INTERVAL - time_since_last_scan
                    print(f"⏸️ Next scan in {remaining_time:.0f} seconds...")
                    time.sleep(min(5, remaining_time))

        except KeyboardInterrupt:
            print("\n⚠️ Bot stopped by user (Ctrl+C)")
            print("🛑 Cleaning up WebSocket connections...")

            # Cleanup WebSocket connections
            try:
                from websocket_manager import _ws_manager
                if _ws_manager:
                    _ws_manager.stop()
                    print("✅ WebSocket cleanup complete")
            except Exception as cleanup_error:
                print(f"⚠️ WebSocket cleanup warning: {cleanup_error}")

            break
        except Exception as e:
            print(f"\n❌ ERROR in main loop: {e}")
            traceback.print_exc()
            print("⏸️ Waiting 10 seconds before retry...")
            time.sleep(10)


# ============================
# CLEANUP FUNCTION
# ============================
def cleanup_on_exit():
    """Cleanup resources on bot exit"""
    try:
        from websocket_manager import _ws_manager
        if _ws_manager:
            print("\n🛑 Cleaning up WebSocket connections...")
            _ws_manager.stop()
            print("✅ WebSocket cleanup complete")
    except:
        pass


# ============================
# RUN THE BOT
# ============================
if __name__ == "__main__":
    import atexit
    # Register cleanup function to run on exit
    atexit.register(cleanup_on_exit)

    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Bot interrupted")
    finally:
        cleanup_on_exit()
