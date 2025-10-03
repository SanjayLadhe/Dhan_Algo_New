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

client_code = "1106090196"
token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU5ODQ2NzIzLCJpYXQiOjE3NTcyNTQ3MjMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.rPFraaBkmAg2QiJvctdffiiyyaA3FfqZ0vDd0gNW0uD4uWNGCfYOqG5mYOxdxI3-i4gMml0exNvgAQPv9-zp8g"
tsl = Tradehull(client_code, token_id)

opening_balance = 1005000  # tsl.get_balance()
base_capital = 1000000
market_money = opening_balance - base_capital

# because I am loosing money, so I have 0  market money, and I can take risk on the current opening balance and not on the base capital
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


# Function to get dynamic watchlist from best performing sectors
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


# Get dynamic watchlist from sectors
watchlist = get_dynamic_watchlist()

single_order = {'name': None, 'date': None, 'entry_time': None, 'entry_price': None, 'buy_sell': None, 'qty': None,
                'sl': None, 'exit_time': None, 'exit_price': None, 'pnl': None, 'remark': None, 'traded': None}
orderbook = {}
wb = xw.Book('Live Trade Data.xlsx')
live_Trading = wb.sheets['Live_Trading']
completed_orders_sheet = wb.sheets['completed_orders']
reentry = "yes"  # "yes/no"
completed_orders = []

bot_token = "8333626494:AAElu5g-jy0ilYkg5-pqpujIH-jWVsdXeLs"
receiver_chat_id = "509536698"

live_Trading.range("A2:Z100").value = None
completed_orders_sheet.range("A2:Z100").value = None

for name in watchlist:
	orderbook[name] = single_order.copy()


# ============================
# ✅ FETCH HISTORICAL WITH RATE LIMITER
# ============================
def fetch_historical(name):
	exchange = "INDEX" if name == "NIFTY" else "NSE"
	data_api_limiter.wait(
		call_description=f"tsl.get_historical_data(tradingsymbol='{name}', exchange='{exchange}', timeframe='1')")
	fetch_time = datetime.datetime.now()
	print(f"Fetching historical data for {name} {fetch_time}")
	Data = tsl.get_historical_data(tradingsymbol=name, exchange=exchange, timeframe="1")
	if Data is None:
		print(f"[ERROR] Failed to fetch historical data for {name}. Returned None.")
		return name, None, fetch_time
	chart = tsl.resample_timeframe(Data, timeframe="3T")
	Data = Data.reset_index()
	complete_time = datetime.datetime.now()
	print(f"Completed fetching for {name} at {complete_time}")
	return name, chart, complete_time


# ============================
# ✅ PROCESS SYMBOL - SIMPLIFIED WITH MODULAR ENTRY LOGIC
# ============================
def process_symbol(name, chart, all_ltp):
	"""Process a single symbol for buy/sell conditions"""
	try:
		# Check if chart data was successfully fetched
		if chart is None:
			print(f"[SKIP] Skipping processing for {name} due to failed historical data fetch.")
			return name, "skip_processing_no_chart"

		process_start_time = datetime.datetime.now()
		print(f"Scanning {name} {process_start_time}\n")

		# Compute indicators for underlying stock
		chart["vwap"] = calculate_vwap_daily(chart["high"], chart["low"], chart["close"], chart["volume"],
		                                     chart["timestamp"])
		chart['rsi'] = talib.RSI(chart['close'], timeperiod=14)
		chart['ma_rsi'] = talib.SMA(chart['rsi'], timeperiod=20)
		chart['ma'] = pta.sma(chart['close'], timeperiod=12)

		para = pta.psar(high=chart['high'], low=chart['low'], close=chart['close'], step=0.05, max_step=0.2,
		                offset=None)
		chart[['PSARl_0.02_0.2', 'PSARs_0.02_0.2', 'PSARaf_0.02_0.2', 'PSARr_0.02_0.2']] = para[
			['PSARl_0.02_0.2', 'PSARs_0.02_0.2', 'PSARaf_0.02_0.2', 'PSARr_0.02_0.2']]

		atr_strategy = ATRTrailingStopIndicator(period=21, multiplier=1.0)
		result_df = atr_strategy.compute_indicator(chart)
		chart[['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']] = result_df[
			['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']]

		df_with_bands = Fractal_Chaos_Bands.fractal_chaos_bands(chart)
		df_with_signals = Fractal_Chaos_Bands.get_fcb_signals(df_with_bands)
		chart[['fractal_high', 'fractal_low', 'signal']] = df_with_signals[['fractal_high', 'fractal_low', 'signal']]

		# Calculate current number of orders placed
		orderbook_df = pd.DataFrame(orderbook).T
		no_of_orders_placed = orderbook_df[orderbook_df['qty'] > 0].shape[0]

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
			print(f"✅ {ce_message}")
			return name, "ce_entry_executed"

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
			print(f"✅ {pe_message}")
			return name, "pe_entry_executed"

		# ============================
		# ✅ CHECK EXIT CONDITIONS - Using Modular Function
		# ============================
		exit_status = process_exit_conditions(
			tsl=tsl,
			name=name,
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
			print(f"✅ Exit processed: {exit_status} for {name}")
			return name, exit_status
		elif exit_status == "tsl_updated":
			print(f"📈 TSL updated for {name}")

		# Continue processing other symbols

		process_end_time = datetime.datetime.now()
		processing_time = (process_end_time - process_start_time).total_seconds()
		print(f"Completed processing {name} in {processing_time:.2f} seconds")
		return name, "processed"

	except Exception as e:
		print(f"Error processing {name}: {e}")
		traceback.print_exc()
		return name, f"error: {str(e)}"


def update_excel_sheets():
	"""Update Excel sheets with current orderbook and completed orders"""
	try:
		orderbook_df = pd.DataFrame(orderbook).T
		live_Trading.range('A1').value = orderbook_df

		completed_orders_df = pd.DataFrame(completed_orders)
		completed_orders_sheet.range('A1').value = completed_orders_df
	except Exception as e:
		print(f"Error updating Excel sheets: {e}")
		traceback.print_exc()


# ============================
# ✅ MAIN LOOP
# ============================
while True:
	print("starting while Loop \n\n")

	current_time = datetime.datetime.now().time()
	if current_time < datetime.time(9, 15):
		print(f"Wait for market to start {current_time}")
		time.sleep(1)
		pass

	live_pnl = tsl.get_live_pnl()
	max_loss_hit = live_pnl < (max_risk_for_today * -1)
	market_over = current_time > datetime.time(15, 15)

	if max_loss_hit or market_over:
		try:
			order_details = tsl.cancel_all_orders()
			print(f"Market over Closing all trades !! Bye Bye See you Tomorrow {current_time}")
		except Exception as e:
			print(f"Error during cancel_all_orders: {e}")

	# Fetch LTP for watchlist
	ltp_api_limiter.wait(call_description="tsl.get_ltp_data(names=watchlist)")
	all_ltp_raw = retry_api_call(tsl.get_ltp_data, retries=1, delay=1.0, names=watchlist)

	if all_ltp_raw is None:
		print("[ERROR] Failed to fetch LTP data after retries. Skipping this cycle.")
		time.sleep(5)
		continue
	all_ltp = all_ltp_raw

	# Process symbols in batches
	batch_size = 3
	for i in range(0, len(watchlist), batch_size):
		batch_symbols = watchlist[i:i + batch_size]
		print(f"Processing batch: {batch_symbols}")

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
					print(f"Error fetching data for {name}: {e}")
					traceback.print_exc()
					continue

		# Process fetched data concurrently
		with ThreadPoolExecutor(max_workers=batch_size) as process_executor:
			future_to_name_process = {
				process_executor.submit(process_symbol, name, chart_data[0], all_ltp): name
				for name, chart_data in fetched_data.items() if chart_data[0] is not None
			}

			processed_count = 0
			for future in as_completed(future_to_name_process):
				try:
					name, result = future.result()
					processed_count += 1
				except Exception as e:
					name = future_to_name_process[future]
					print(f"Error processing {name}: {e}")
					traceback.print_exc()
					continue

		# Update Excel sheets after each batch
		update_excel_sheets()

		# Small delay between batches
		time.sleep(1)