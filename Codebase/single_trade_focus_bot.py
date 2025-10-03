import pdb
import time
import datetime
import traceback
from ta.volume import volume_weighted_average_price
from ta.volume import VolumeWeightedAveragePrice
from Dhan_Tradehull_V3 import Tradehull
import pandas as pd
from pprint import pprint
import talib
import pandas_ta as pta
import xlwings as xw
import winsound
import sqn_lib
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
token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU5NTc5MDQxLCJpYXQiOjE3NTk0OTI2NDEsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.8JM32NffKxJwZ9Dktwc63waPuR2Ljf7EruR7qrQSO8HV1tyqdKpEAP6b17gQNynBrHfMxEjnB7oJsZOQ_F69qA"
tsl = Tradehull(client_code, token_id)

# ============================
# RISK MANAGEMENT PARAMETERS
# ============================
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

max_order_for_today = 2
risk_per_trade = (max_risk_for_today / max_order_for_today)
atr_multipler = 3
risk_reward = 3

# ============================
# TELEGRAM CONFIGURATION
# ============================
bot_token = "8333626494:AAElu5g-jy0ilYkg5-pqpujIH-jWVsdXeLs"
receiver_chat_id = "509536698"

# ============================
# TRADING CONFIGURATION
# ============================
reentry = "yes"  # "yes/no"

# ============================
# TIMING PARAMETERS (SINGLE TRADE FOCUS)
# ============================
MONITOR_INTERVAL = 5    # Check every 5 seconds when IN a position
SCAN_INTERVAL = 30      # Scan for entry every 30 seconds when NO position

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

# Initialize orderbook
for name in watchlist:
    orderbook[name] = single_order.copy()


# ============================
# FETCH HISTORICAL WITH RATE LIMITER
# ============================
def fetch_historical(name):
    """Fetch historical data for a symbol with rate limiting"""
    exchange = "INDEX" if name == "NIFTY" else "NSE"
    data_api_limiter.wait(
        call_description=f"tsl.get_historical_data(tradingsymbol='{name}', exchange='{exchange}', timeframe='1')")
    fetch_time = datetime.datetime.now()
    print(f"📊 Fetching historical data for {name} at {fetch_time.strftime('%H:%M:%S')}")
    
    Data = tsl.get_historical_data(tradingsymbol=name, exchange=exchange, timeframe="1")
    if Data is None:
        print(f"[ERROR] Failed to fetch historical data for {name}. Returned None.")
        return name, None, fetch_time
    
    chart = tsl.resample_timeframe(Data, timeframe="3T")
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
        chart['rsi'] = talib.RSI(chart['close'], timeperiod=14)
        chart['ma_rsi'] = talib.SMA(chart['rsi'], timeperiod=20)
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

        return chart
    except Exception as e:
        print(f"❌ Error computing indicators: {e}")
        traceback.print_exc()
        return chart


# ============================
# CHECK IF POSITION ACTIVE
# ============================
def is_position_active():
    """Check if there's any active position in the orderbook"""
    orderbook_df = pd.DataFrame(orderbook).T
    active_positions = orderbook_df[orderbook_df['qty'] > 0]
    return len(active_positions) > 0, active_positions


# ============================
# GET ACTIVE POSITION SYMBOL
# ============================
def get_active_position_symbol():
    """Get the symbol name of the active position"""
    orderbook_df = pd.DataFrame(orderbook).T
    active_positions = orderbook_df[orderbook_df['qty'] > 0]
    if len(active_positions) > 0:
        return active_positions.index[0]
    return None


# ============================
# SCAN FOR ENTRY (ALL SYMBOLS)
# ============================
def scan_for_entry(all_ltp):
    """
    Scan all symbols in watchlist for entry opportunities
    Only called when NO position is active
    """
    print("\n" + "="*80)
    print(f"🔍 SCANNING FOR ENTRY - {datetime.datetime.now().strftime('%H:%M:%S')}")
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
                    bot_token=bot_token,
                    receiver_chat_id=receiver_chat_id
                )

                if ce_success:
                    print(f"\n{'='*80}")
                    print(f"✅ ENTRY EXECUTED: {ce_message}")
                    print(f"{'='*80}\n")
                    update_excel_sheets()
                    return True  # Entry executed, stop scanning

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
                    bot_token=bot_token,
                    receiver_chat_id=receiver_chat_id
                )

                if pe_success:
                    print(f"\n{'='*80}")
                    print(f"✅ ENTRY EXECUTED: {pe_message}")
                    print(f"{'='*80}\n")
                    update_excel_sheets()
                    return True  # Entry executed, stop scanning

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
            bot_token=bot_token,
            receiver_chat_id=receiver_chat_id,
            reentry=reentry,
            completed_orders=completed_orders,
            single_order=single_order,
            risk_reward=risk_reward
        )

        if exit_status in ["sl_hit", "target_hit", "rsi_longstop_exit", "time_exit"]:
            print(f"\n{'='*80}")
            print(f"🚪 EXIT EXECUTED: {exit_status} for {symbol_name}")
            print(f"{'='*80}\n")
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
    """
    print("\n" + "="*100)
    print("🚀 SINGLE TRADE FOCUS BOT STARTED")
    print("="*100)
    print(f"📊 Strategy: Focus on ONE high-quality trade at a time")
    print(f"⏰ Scan Interval (No Position): {SCAN_INTERVAL} seconds")
    print(f"👁️ Monitor Interval (In Position): {MONITOR_INTERVAL} seconds")
    print(f"💰 Risk per Trade: ₹{risk_per_trade:,.2f}")
    print(f"📈 Risk Reward Ratio: 1:{risk_reward}")
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
                continue

            if market_status in ["market_closed", "max_loss_hit"]:
                print(f"\n{'='*80}")
                if market_status == "market_closed":
                    print(f"🔔 MARKET CLOSED at {current_time.strftime('%H:%M:%S')}")
                else:
                    print(f"⛔ MAX LOSS HIT - Stopping trading at {current_time.strftime('%H:%M:%S')}")
                print(f"{'='*80}")
                
                """
                try:
                    order_details = tsl.cancel_all_orders()
                    print("✅ All pending orders cancelled")
                except Exception as e:
                    print(f"⚠️ Error cancelling orders: {e}")
                
                print("\n👋 Bot stopped. See you tomorrow!")
                break
                """

            # Fetch LTP for watchlist
            ltp_api_limiter.wait(call_description="tsl.get_ltp_data(names=watchlist)")
            all_ltp_raw = retry_api_call(tsl.get_ltp_data, retries=1, delay=1.0, names=watchlist)

            if all_ltp_raw is None:
                print("⚠️ Failed to fetch LTP data. Retrying in 5 seconds...")
                time.sleep(5)
                continue

            all_ltp = all_ltp_raw

            # Check if we have an active position
            has_position, active_positions = is_position_active()

            if has_position:
                # ============================
                # MONITOR MODE - Check every 5 seconds
                # ============================
                active_symbol = get_active_position_symbol()
                position_exited = monitor_active_position(active_symbol, all_ltp)
                
                if position_exited:
                    print(f"✅ Position exited for {active_symbol}")
                    # Reset scan timer to start looking for next entry
                    last_scan_time = time.time() - SCAN_INTERVAL
                
                # Wait MONITOR_INTERVAL before next check
                time.sleep(MONITOR_INTERVAL)

            else:
                # ============================
                # SCAN MODE - Check every 30 seconds
                # ============================
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
            break
        except Exception as e:
            print(f"\n❌ ERROR in main loop: {e}")
            traceback.print_exc()
            print("⏸️ Waiting 10 seconds before retry...")
            time.sleep(10)


# ============================
# RUN THE BOT
# ============================
if __name__ == "__main__":
    main()
