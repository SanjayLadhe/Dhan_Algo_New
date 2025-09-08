# Full patched PaperTrade.py (save/replace your file with this)
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
# from finta import TA
import xlwings as xw
import winsound
import sqn_lib
from VWAP import calculate_vwap_daily
from ATRTrailingStop import ATRTrailingStopIndicator
import Fractal_Chaos_Bands
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from collections import deque
import logging
from logging.handlers import TimedRotatingFileHandler
import uuid
import json


# ============================
# ✅ PAPER TRADING CLASSES
# ============================

class PaperTradingEngine:
	def __init__(self, initial_balance=1005000):
		self.initial_balance = initial_balance
		self.current_balance = initial_balance
		self.positions = {}  # {symbol: position_data}
		self.orders = {}  # {order_id: order_data}
		self.trade_history = []
		self.order_counter = 1000

	def generate_order_id(self):
		"""Generate unique order ID for paper trading"""
		self.order_counter += 1
		return f"PAPER_{self.order_counter}"

	def place_order(self, tradingsymbol, exchange, quantity, price, trigger_price,
	                order_type, transaction_type, trade_type):
		"""Simulate order placement"""
		order_id = self.generate_order_id()

		order_data = {
			'order_id': order_id,
			'tradingsymbol': tradingsymbol,
			'exchange': exchange,
			'quantity': quantity,
			'price': price,
			'trigger_price': trigger_price,
			'order_type': order_type,
			'transaction_type': transaction_type,
			'trade_type': trade_type,
			'status': 'PENDING',
			'executed_price': None,
			'timestamp': datetime.datetime.now(),
			'executed_time': None
		}

		self.orders[order_id] = order_data

		# For MARKET orders, execute immediately
		if order_type == 'MARKET':
			self._execute_market_order(order_id)

		print(f"[PAPER TRADING] Order placed: {order_id} - {transaction_type} {quantity} {tradingsymbol}")
		return order_id

	def _execute_market_order(self, order_id):
		"""Execute market order immediately using current LTP"""
		order = self.orders[order_id]

		# Simulate execution at current market price
		# In real implementation, you'd get LTP here
		# For now, we'll use a placeholder that will be updated when we have LTP
		order['status'] = 'TRADED'
		order['executed_time'] = datetime.datetime.now()

		# Mark for LTP update (will be handled in main loop)
		order['needs_ltp_execution'] = True

	def execute_pending_market_orders(self, ltp_data):
		"""Execute pending market orders using current LTP data"""
		for order_id, order in list(self.orders.items()):
			if (order['status'] == 'TRADED' and
					order.get('needs_ltp_execution', False) and
					order['tradingsymbol'] in ltp_data):
				ltp = ltp_data[order['tradingsymbol']]

				# Add some slippage simulation
				slippage = 0.05 if order['transaction_type'] == 'BUY' else -0.05
				executed_price = ltp + slippage

				order['executed_price'] = executed_price
				order['needs_ltp_execution'] = False

				print(f"[PAPER TRADING] Market order executed: {order_id} at ₹{executed_price}")

	def check_stop_loss_orders(self, ltp_data):
		"""Check and execute stop loss orders"""
		for order_id, order in list(self.orders.items()):
			if (order['status'] == 'PENDING' and
					order['order_type'] == 'STOPLIMIT' and
					order['tradingsymbol'] in ltp_data):

				ltp = ltp_data[order['tradingsymbol']]

				# Check if stop loss should trigger
				if (order['transaction_type'] == 'SELL' and
						ltp <= order['trigger_price']):
					# Execute stop loss
					slippage = -0.10  # Negative slippage for SL execution
					executed_price = max(order['price'], ltp + slippage)

					order['status'] = 'TRADED'
					order['executed_price'] = executed_price
					order['executed_time'] = datetime.datetime.now()

					print(f"[PAPER TRADING] Stop Loss triggered: {order_id} at ₹{executed_price}")

	def modify_order(self, order_id, order_type, quantity, price, trigger_price):
		"""Modify existing order"""
		if order_id in self.orders:
			order = self.orders[order_id]
			order['price'] = price
			order['trigger_price'] = trigger_price
			order['quantity'] = quantity
			print(f"[PAPER TRADING] Order modified: {order_id} - New trigger: ₹{trigger_price}")
			return True
		return False

	def cancel_order(self, order_id):
		"""Cancel an order"""
		if order_id in self.orders:
			self.orders[order_id]['status'] = 'CANCELLED'
			print(f"[PAPER TRADING] Order cancelled: {order_id}")
			return True
		return False

	def get_order_status(self, order_id):
		"""Get order status"""
		if order_id in self.orders:
			return self.orders[order_id]['status']
		return 'UNKNOWN'

	def get_executed_price(self, order_id):
		"""Get executed price for an order"""
		if order_id in self.orders and self.orders[order_id]['executed_price']:
			return self.orders[order_id]['executed_price']
		return None

	def calculate_live_pnl(self, ltp_data):
		"""Calculate current unrealized P&L"""
		total_pnl = 0

		for order_id, order in self.orders.items():
			if (order['status'] == 'TRADED' and
					order['executed_price'] and
					order['tradingsymbol'] in ltp_data):

				ltp = ltp_data[order['tradingsymbol']]
				entry_price = order['executed_price']
				quantity = order['quantity']

				if order['transaction_type'] == 'BUY':
					pnl = (ltp - entry_price) * quantity
				else:
					pnl = (entry_price - ltp) * quantity

				total_pnl += pnl

		return total_pnl

	def get_balance(self):
		"""Return current balance"""
		return self.current_balance

	def cancel_all_orders(self):
		"""Cancel all pending orders"""
		cancelled_orders = []
		for order_id, order in self.orders.items():
			if order['status'] == 'PENDING':
				order['status'] = 'CANCELLED'
				cancelled_orders.append(order_id)

		print(f"[PAPER TRADING] Cancelled {len(cancelled_orders)} orders")
		return cancelled_orders


# ============================
# ✅ PAPER TRADING WRAPPER FOR TSL
# ============================

class PaperTradingWrapper:
	def __init__(self, original_tsl, paper_engine):
		self.tsl = original_tsl  # Original Tradehull instance for data
		self.paper_engine = paper_engine

	# Data methods - use original TSL
	def get_historical_data(self, tradingsymbol, exchange, timeframe):
		return self.tsl.get_historical_data(tradingsymbol, exchange, timeframe)

	def resample_timeframe(self, data, timeframe):
		return self.tsl.resample_timeframe(data, timeframe)

	def get_ltp_data(self, names):
		return self.tsl.get_ltp_data(names)

	def ATM_Strike_Selection(self, Underlying, Expiry):
		return self.tsl.ATM_Strike_Selection(Underlying, Expiry)

	def get_lot_size(self, tradingsymbol):
		return self.tsl.get_lot_size(tradingsymbol)

	# Trading methods - use paper engine
	def order_placement(self, tradingsymbol, exchange, quantity, price, trigger_price,
	                    order_type, transaction_type, trade_type):
		return self.paper_engine.place_order(tradingsymbol, exchange, quantity, price,
		                                     trigger_price, order_type, transaction_type, trade_type)

	def modify_order(self, order_id, order_type, quantity, price, trigger_price):
		return self.paper_engine.modify_order(order_id, order_type, quantity, price, trigger_price)

	def cancel_order(self, OrderID):
		return self.paper_engine.cancel_order(OrderID)

	def get_order_status(self, orderid):
		return self.paper_engine.get_order_status(orderid)

	def get_executed_price(self, orderid):
		return self.paper_engine.get_executed_price(orderid)

	def get_live_pnl(self):
		# This will be calculated in main loop with current LTP
		return getattr(self, '_current_pnl', 0)

	def get_balance(self):
		return self.paper_engine.get_balance()

	def cancel_all_orders(self):
		return self.paper_engine.cancel_all_orders()

	def send_telegram_alert(self, message, receiver_chat_id, bot_token):
		# For paper trading, just print the message
		print(f"[TELEGRAM ALERT] {message}")


# ============================
# ✅ CONFIGURE FILE-BASED LOGGER FOR RATE LIMITER (Historical Data)
# ============================
rate_limit_logger = logging.getLogger('RateLimiterLogger')
rate_limit_logger.setLevel(logging.INFO)

if not rate_limit_logger.handlers:
	file_handler = TimedRotatingFileHandler(
		'rate_limit_audit.log',
		when='midnight',
		interval=1,
		backupCount=7,
		encoding='utf-8'
	)
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	file_handler.setFormatter(formatter)
	rate_limit_logger.addHandler(file_handler)
	rate_limit_logger.propagate = False

# ============================
# ✅ CONFIGURE FILE-BASED LOGGER FOR GENERAL API (LTP, Orders, etc.)
# ============================
general_api_logger = logging.getLogger('GeneralAPILogger')
general_api_logger.setLevel(logging.INFO)

if not general_api_logger.handlers:
	file_handler = TimedRotatingFileHandler(
		'general_api_audit.log',
		when='midnight',
		interval=1,
		backupCount=7,
		encoding='utf-8'
	)
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	file_handler.setFormatter(formatter)
	general_api_logger.addHandler(file_handler)
	general_api_logger.propagate = False


# ============================
# ✅ ENHANCED RATE LIMITER WITH FILE LOGGING AND CALL DESCRIPTION
# ============================
class RateLimiter:
	def __init__(self, max_calls, period, name="RateLimiter", logger=None):
		self.max_calls = max_calls
		self.period = period  # in seconds
		self.calls = deque()
		self.lock = threading.Lock()
		self.name = name
		self.logger = logger or rate_limit_logger

	def wait(self, call_description=""):
		"""
		Wait until a call is allowed by the rate limit.
		Logs the specific call being rate-limited.
		"""
		with self.lock:
			now = time.time()
			# Remove calls older than period
			while self.calls and self.calls[0] <= now - self.period:
				self.calls.popleft()

			sleep_time = 0.0
			if len(self.calls) >= self.max_calls:
				sleep_time = self.calls[0] + self.period - now
				if sleep_time > 0:
					self.logger.info(
						f"RATE_LIMIT_HIT - {self.name} - {call_description} - Sleeping for {sleep_time:.3f} seconds. Queue size: {len(self.calls)}")
					print(
						f"[{self.name}] Rate limit reached for '{call_description}'. Sleeping for {sleep_time:.2f} seconds...")
					time.sleep(sleep_time)
					# After sleep, clean up again
					now = time.time()
					while self.calls and self.calls[0] <= now - self.period:
						self.calls.popleft()

			# Add current call timestamp
			self.calls.append(now)
			active_calls = len(self.calls)
			self.logger.info(
				f"CALL_ALLOWED - {self.name} - {call_description} - Queue size after add: {active_calls}, Max allowed: {self.max_calls}")
			print(
				f"[{self.name}] ✅ Call allowed for '{call_description}' at {now:.2f}. Active calls in window: {active_calls}")


# ============================
# ✅ RETRY LOGIC FOR API CALLS WITH RATE LIMIT SPECIFIC HANDLING
# ============================
def retry_api_call(func, retries=1, delay=1.0, *args, **kwargs):
	"""
	Retry an API call with exponential backoff.
	Specifically handles rate limit errors (DH-805).
	"""
	for attempt in range(retries):
		try:
			result = func(*args, **kwargs)
			# Log successful retry attempt if it wasn't the first try
			if attempt > 0:
				general_api_logger.info(f"[RETRY] Success on attempt {attempt + 1} for {func.__name__}")
			return result
		except Exception as e:
			error_str = str(e)
			# Check if it's a rate limit error
			is_rate_limit_error = '805' in error_str or 'Too many requests' in error_str
			if is_rate_limit_error:
				general_api_logger.warning(
					f"[RETRY] Rate limit error detected for {func.__name__}: {e}. Applying longer backoff.")
				# Apply longer backoff for rate limits
				time.sleep(delay * 2 * (attempt + 1))
				continue  # Retry immediately after rate limit backoff

			if attempt == retries - 1:  # Last attempt
				general_api_logger.error(f"[RETRY] Failed after {retries} attempts for {func.__name__}: {e}")
				raise e
			general_api_logger.warning(
				f"[RETRY] Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay} seconds...")
			print(f"[RETRY] Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
			time.sleep(delay)
			delay *= 2  # Exponential backoff
	return None  # Should not reach here due to raise, but good practice


# ============================
# ✅ INITIALIZE RATE LIMITERS (Based on official limits)
# ============================
# Data API Limiter: 5 calls per second (Official limit)
data_api_limiter = RateLimiter(max_calls=5, period=1.0, name="DATA_API", logger=rate_limit_logger)

# Non Trading API Limiter: 18 calls per second (Slightly under 20/sec official limit)
ntrading_api_limiter = RateLimiter(max_calls=18, period=1.0, name="NTRADING_API", logger=general_api_logger)

# Order API Limiter: 25 calls per second (Official limit) - Not needed for paper trading but kept for consistency
order_api_limiter = RateLimiter(max_calls=25, period=1.0, name="ORDER_API", logger=general_api_logger)

ltp_api_limiter = RateLimiter(max_calls=1, period=1.0, name="LTP_API", logger=general_api_logger)

# Configure pandas display
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

# ============================
# ✅ INITIALIZE PAPER TRADING
# ============================
client_code = "1106090196"
token_id = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU5ODQ2NzIzLCJpYXQiOjE3NTcyNTQ3MjMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.rPFraaBkmAg2QiJvctdffiiyyaA3FfqZ0vDd0gNW0uD4uWNGCfYOqG5mYOxdxI3-i4gMml0exNvgAQPv9-zp8g"

# Create original TSL instance for data
original_tsl = Tradehull(client_code, token_id)

# Create paper trading engine
paper_engine = PaperTradingEngine(initial_balance=1005000)

# Create paper trading wrapper
tsl = PaperTradingWrapper(original_tsl, paper_engine)

opening_balance = 1005000  # Using paper trading balance
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

# watchlist = ["LODHA"]
watchlist = [
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

single_order = {'name': None, 'date': None, 'entry_time': None, 'entry_price': None, 'buy_sell': None, 'qty': None,
                'sl': None, 'exit_time': None, 'exit_price': None, 'pnl': None, 'remark': None, 'traded': None,
                'options_name': None, 'entry_orderid': None, 'sl_orderid': None, 'tsl': None, 'max_holding_time': None}
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
	# ⬇️ RATE LIMITED: Data API
	data_api_limiter.wait(
		call_description=f"tsl.get_historical_data(tradingsymbol='{name}', exchange='{exchange}', timeframe='1')")
	fetch_time = datetime.datetime.now()
	print(f"Fetching historical data for {name} {fetch_time}")
	Data = tsl.get_historical_data(tradingsymbol=name, exchange=exchange, timeframe="1")
	if Data is None:
		print(f"[ERROR] Failed to fetch historical data for {name}. Returned None.")
		return name, None, fetch_time  # Return None chart if fetch fails
	chart = tsl.resample_timeframe(Data, timeframe="3T")
	Data = Data.reset_index()
	complete_time = datetime.datetime.now()
	print(f"Completed fetching for {name} at {complete_time}")
	return name, chart, complete_time


# ============================
# ✅ PROCESS SYMBOL WITH RATE LIMITER FOR OPTIONS & GENERAL API
# ============================
def process_symbol(name, chart, all_ltp):
	"""Process a single symbol for buy/sell conditions"""
	try:
		# Check if chart data was successfully fetched
		if chart is None:
			print(f"[SKIP] Skipping processing for {name} due to failed historical data fetch.")
			return name, "skip_processing_no_chart"

		process_start_time = datetime.datetime.now()
		print(f"Scanning        {name} {process_start_time} \n")

		# Compute indicators and conditions
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

		last = chart.iloc[-1]
		cc = chart.iloc[-2]

		orderbook_df = pd.DataFrame(orderbook).T
		no_of_orders_placed = orderbook_df[orderbook_df['qty'] > 0].shape[0]
		last_close = float(last['close'])
		cc_close = float(cc['close'])
		long_stop = pd.to_numeric(cc['Long_Stop'], errors='coerce')
		fractal_high = pd.to_numeric(cc['fractal_high'], errors='coerce')
		vwap = pd.to_numeric(last['vwap'], errors='coerce')
		Crossabove = pta.above(chart['rsi'], chart['ma_rsi'])

		Candle_Color_last = pta.candle_color(chart['open'], chart['close']).iloc[-1]
		Candle_Color_CC = pta.candle_color(chart['open'], chart['close']).iloc[-2]

		# Buy entry conditions
		bc1 = cc['rsi'] > 60
		bc2 = bool(Crossabove.iloc[-2])
		bc3 = cc_close > long_stop
		bc4 = cc_close > fractal_high
		bc5 = cc_close > vwap
		bc6 = orderbook[name]['traded'] is None
		bc7 = no_of_orders_placed < 5

		# Sell conditions
		fractal_low = pd.to_numeric(cc['fractal_low'], errors='coerce')
		Crossbelow = pta.below(chart['rsi'], chart['ma_rsi'])

		# Sell entry conditions
		sc1 = cc['rsi'] < 60
		sc2 = bool(Crossbelow.iloc[-2])
		sc3 = cc_close < long_stop
		sc4 = cc_close < fractal_low
		sc5 = cc_close < vwap
		sc6 = orderbook[name]['traded'] is None
		sc7 = no_of_orders_placed < 5

		print(f" Buy Condition {name} : {bc1}, {bc2}, {bc3}, {bc4}, {bc5} : {process_start_time} \n")
		print(f" Sell Condition {name} : {sc1}, {sc2}, {sc3}, {sc4}, {sc5} : {process_start_time} \n")

		# ============================
		# ✅ BUY ENTRY (PAPER TRADING)
		# ============================
		if bc1 and bc2 and bc3 and bc4 and bc5 and bc6 and bc7:
			print("[PAPER TRADING] buy ", name, "\t")

			# ⬇️ RATE LIMITED: Non Trading API
			ntrading_api_limiter.wait(call_description=f"tsl.ATM_Strike_Selection(Underlying='{name}', Expiry=0)")
			atm_result = retry_api_call(tsl.ATM_Strike_Selection, retries=1, delay=1.0, Underlying=name, Expiry=0)
			if atm_result is None:
				print(f"[SKIP] Failed to get ATM strike for {name} after retries.")
				return name, "skip_atm_strike"
			ce_name, pe_name, strike = atm_result

			# ⬇️ RATE LIMITED: Non Trading API
			ntrading_api_limiter.wait(call_description=f"tsl.get_lot_size(tradingsymbol='{ce_name}')")
			lot_size = retry_api_call(tsl.get_lot_size, retries=1, delay=1.0, tradingsymbol=ce_name)
			if lot_size is None:
				print(f"[SKIP] Failed to get lot size for {ce_name}")
				return name, "skip_lot_size"

			# ⬇️ RATE LIMITED: Data API
			data_api_limiter.wait(
				call_description=f"tsl.get_historical_data(tradingsymbol='{ce_name}', exchange='NFO', timeframe='1')")
			options_chart = tsl.get_historical_data(tradingsymbol=ce_name, exchange='NFO', timeframe="1")
			if options_chart is None:
				print(f"[ERROR] Failed to fetch data for CE Option {ce_name}. Returned None.")
				return name, "skip_option_fetch_ce"

			options_chart_Res = tsl.resample_timeframe(options_chart, timeframe='3T')
			# Add check if resampling returns valid data
			if options_chart_Res is None or options_chart_Res.empty:
				print(f"[ERROR] Resampling failed or returned empty data for CE Option {ce_name}.")
				return name, "skip_option_resample_ce"

			options_chart = options_chart.reset_index()

			# Defensive check for required columns before VWAP
			required_cols = ['high', 'low', 'close', 'volume', 'timestamp']
			if not all(col in options_chart_Res.columns for col in required_cols):
				print(
					f"[ERROR] Missing required columns in CE Option data for {ce_name}. Columns: {options_chart_Res.columns.tolist()}")
				return name, "skip_option_missing_cols_ce"

			options_chart_Res["vwap"] = calculate_vwap_daily(options_chart_Res["high"], options_chart_Res["low"],
			                                                 options_chart_Res["close"], options_chart_Res["volume"],
			                                                 options_chart_Res["timestamp"])
			options_chart_Res['rsi'] = talib.RSI(options_chart_Res['close'], timeperiod=14)
			options_chart_Res['ma_rsi'] = talib.SMA(options_chart_Res['rsi'], timeperiod=20)
			options_chart_Res['ma'] = pta.sma(options_chart_Res['close'], timeperiod=12)

			para = pta.psar(high=options_chart_Res['high'], low=options_chart_Res['low'],
			                close=options_chart_Res['close'], step=0.05, max_step=0.2,
			                offset=None)
			options_chart_Res[['PSARl_0.02_0.2', 'PSARs_0.02_0.2', 'PSARaf_0.02_0.2', 'PSARr_0.02_0.2']] = para[
				['PSARl_0.02_0.2', 'PSARs_0.02_0.2', 'PSARaf_0.02_0.2', 'PSARr_0.02_0.2']]

			atr_strategy = ATRTrailingStopIndicator(period=21, multiplier=1.0)
			result_df = atr_strategy.compute_indicator(options_chart_Res)
			options_chart_Res[
				['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']] = result_df[
				['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']]

			df_with_bands = Fractal_Chaos_Bands.fractal_chaos_bands(options_chart_Res)
			df_with_signals = Fractal_Chaos_Bands.get_fcb_signals(df_with_bands)
			options_chart_Res[['fractal_high', 'fractal_low', 'signal']] = df_with_signals[
				['fractal_high', 'fractal_low', 'signal']]

			rc_options = options_chart_Res.iloc[-1]
			rc_options_cc = options_chart_Res.iloc[-2]

			last_close = float(rc_options['close'])
			cc_close = float(rc_options_cc['close'])
			# Use rc_options for stop and fractal
			long_stop_opt = pd.to_numeric(rc_options['Long_Stop'], errors='coerce')
			fractal_high_opt = pd.to_numeric(rc_options['fractal_high'], errors='coerce')
			vwap_opt = pd.to_numeric(rc_options['vwap'], errors='coerce')
			Crossabove_opt = pta.above(options_chart_Res['rsi'], options_chart_Res['ma_rsi'])

			# Buy entry conditions for option (CE)
			bc1_opt = rc_options_cc['rsi'] > 60
			bc2_opt = bool(Crossabove_opt.iloc[-2])
			bc3_opt = cc_close > long_stop_opt
			bc4_opt = cc_close > fractal_high_opt
			bc5_opt = cc_close > vwap_opt
			bc6_opt = orderbook[name]['traded'] is None
			bc7_opt = no_of_orders_placed < 5

			print(
				f" Buy Condition for ce_name {ce_name} : {bc1_opt}, {bc2_opt}, {bc3_opt}, {bc4_opt}, {bc5_opt} : {process_start_time} \n")

			if bc1_opt and bc2_opt and bc3_opt and bc4_opt and bc5_opt and bc6_opt and bc7_opt:
				print("[PAPER TRADING] buy ce_name", ce_name, "\t")

				orderbook[name]['name'] = name
				orderbook[name]['options_name'] = ce_name
				orderbook[name]['date'] = str(process_start_time.date())
				orderbook[name]['entry_time'] = str(process_start_time.time())[:8]
				orderbook[name]['max_holding_time'] = datetime.datetime.now() + datetime.timedelta(hours=2)
				orderbook[name]['buy_sell'] = "BUY"
				sl_points = rc_options['ATR'] * atr_multipler
				orderbook[name]['qty'] = lot_size

				try:
					# ⬇️ PAPER TRADING: Simulate order placement
					entry_orderid = tsl.order_placement(tradingsymbol=ce_name, exchange='NFO',
					                                    quantity=lot_size, price=0, trigger_price=0,
					                                    order_type='MARKET', transaction_type='BUY', trade_type='MIS')
					orderbook[name]['entry_orderid'] = entry_orderid

					# For paper trading, we'll set executed price when we get LTP
					# For now, mark it as pending execution
					print(f"[PAPER TRADING] Market order placed for {ce_name}. Waiting for LTP execution...")

					message = f"[PAPER TRADING] Entry order placed for {name} (CE: {ce_name})"
					#tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

				except Exception as e:
					print(f"[PAPER TRADING] Error in entry order simulation for {name}: {e}")
					traceback.print_exc()

		# ============================
		# ✅ SELL ENTRY (PAPER TRADING - Actually buying PE)
		# ============================
		if sc1 and sc2 and sc3 and sc4 and sc5 and sc6 and sc7:
			print("[PAPER TRADING] Sell ", name, "\t")

			# ⬇️ RATE LIMITED: Non Trading API
			ntrading_api_limiter.wait(call_description=f"tsl.ATM_Strike_Selection(Underlying='{name}', Expiry=0)")
			atm_result = retry_api_call(tsl.ATM_Strike_Selection, retries=1, delay=1.0, Underlying=name, Expiry=0)
			if atm_result is None:
				print(f"[SKIP] Failed to get ATM strike for {name} (PE) after retries.")
				return name, "skip_atm_strike_pe"
			ce_name, pe_name, strike = atm_result

			# ⬇️ RATE LIMITED: Non Trading API
			ntrading_api_limiter.wait(call_description=f"tsl.get_lot_size(tradingsymbol='{pe_name}')")
			lot_size = retry_api_call(tsl.get_lot_size, retries=1, delay=1.0, tradingsymbol=pe_name)
			if lot_size is None:
				print(f"[SKIP] Failed to get lot size for {pe_name}")
				return name, "skip_lot_size_pe"

			# ⬇️ RATE LIMITED: Data API
			data_api_limiter.wait(
				call_description=f"tsl.get_historical_data(tradingsymbol='{pe_name}', exchange='NFO', timeframe='1')")
			options_chart = tsl.get_historical_data(tradingsymbol=pe_name, exchange='NFO', timeframe="1")
			if options_chart is None:
				print(f"[ERROR] Failed to fetch data for PE Option {pe_name}. Returned None.")
				return name, "skip_option_fetch_pe"

			options_chart_Res = tsl.resample_timeframe(options_chart, timeframe='3T')
			if options_chart_Res is None or options_chart_Res.empty:
				print(f"[ERROR] Resampling failed or returned empty data for PE Option {pe_name}.")
				return name, "skip_option_resample_pe"

			options_chart = options_chart.reset_index()

			# Defensive check for required columns before VWAP
			required_cols = ['high', 'low', 'close', 'volume', 'timestamp']
			if not all(col in options_chart_Res.columns for col in required_cols):
				print(
					f"[ERROR] Missing required columns in PE Option data for {pe_name}. Columns: {options_chart_Res.columns.tolist()}")
				return name, "skip_option_missing_cols_pe"

			options_chart_Res["vwap"] = calculate_vwap_daily(options_chart_Res["high"], options_chart_Res["low"],
			                                                 options_chart_Res["close"], options_chart_Res["volume"],
			                                                 options_chart_Res["timestamp"])
			options_chart_Res['rsi'] = talib.RSI(options_chart_Res['close'], timeperiod=14)
			options_chart_Res['ma_rsi'] = talib.SMA(options_chart_Res['rsi'], timeperiod=20)
			options_chart_Res['ma'] = pta.sma(options_chart_Res['close'], timeperiod=12)

			para = pta.psar(high=options_chart_Res['high'], low=options_chart_Res['low'],
			                close=options_chart_Res['close'], step=0.05, max_step=0.2,
			                offset=None)
			options_chart_Res[['PSARl_0.02_0.2', 'PSARs_0.02_0.2', 'PSARaf_0.02_0.2', 'PSARr_0.02_0.2']] = para[
				['PSARl_0.02_0.2', 'PSARs_0.02_0.2', 'PSARaf_0.02_0.2', 'PSARr_0.02_0.2']]

			atr_strategy = ATRTrailingStopIndicator(period=21, multiplier=1.0)
			result_df = atr_strategy.compute_indicator(options_chart_Res)
			options_chart_Res[
				['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']] = result_df[
				['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']]

			df_with_bands = Fractal_Chaos_Bands.fractal_chaos_bands(options_chart_Res)
			df_with_signals = Fractal_Chaos_Bands.get_fcb_signals(df_with_bands)
			options_chart_Res[['fractal_high', 'fractal_low', 'signal']] = df_with_signals[
				['fractal_high', 'fractal_low', 'signal']]

			rc_options = options_chart_Res.iloc[-1]
			rc_options_cc = options_chart_Res.iloc[-2]

			last_close = float(rc_options['close'])
			cc_close = float(rc_options_cc['close'])
			long_stop_opt = pd.to_numeric(rc_options['Long_Stop'], errors='coerce')
			fractal_low_opt = pd.to_numeric(rc_options['fractal_low'], errors='coerce')
			vwap_opt = pd.to_numeric(rc_options['vwap'], errors='coerce')
			Crossbelow_opt = pta.below(options_chart_Res['rsi'], options_chart_Res['ma_rsi'])

			# Buy entry conditions for option (PE)
			bc1_opt = rc_options_cc['rsi'] > 60
			bc2_opt = bool(Crossbelow_opt.iloc[-2])
			bc3_opt = cc_close < long_stop_opt
			bc4_opt = cc_close < fractal_low_opt
			bc5_opt = cc_close < vwap_opt
			bc6_opt = orderbook[name]['traded'] is None
			bc7_opt = no_of_orders_placed < 5

			print(
				f" Buy Condition for pe_name {pe_name} (Sell Signal) : {bc1_opt}, {bc2_opt}, {bc3_opt}, {bc4_opt}, {bc5_opt} : {process_start_time} \n")

			if bc1_opt and bc2_opt and bc3_opt and bc4_opt and bc5_opt and bc6_opt and bc7_opt:
				print("[PAPER TRADING] buy pe_name (Sell Signal)", pe_name, "\t")

				orderbook[name]['name'] = name
				orderbook[name]['options_name'] = pe_name
				orderbook[name]['date'] = str(process_start_time.date())
				orderbook[name]['entry_time'] = str(process_start_time.time())[:8]
				orderbook[name]['max_holding_time'] = datetime.datetime.now() + datetime.timedelta(hours=2)
				orderbook[name]['buy_sell'] = "BUY"
				sl_points = rc_options['ATR'] * atr_multipler
				orderbook[name]['qty'] = lot_size

				try:
					# ⬇️ PAPER TRADING: Simulate order placement
					entry_orderid = tsl.order_placement(tradingsymbol=pe_name, exchange='NFO',
					                                    quantity=lot_size, price=0, trigger_price=0,
					                                    order_type='MARKET', transaction_type='BUY', trade_type='MIS')
					orderbook[name]['entry_orderid'] = entry_orderid

					print(f"[PAPER TRADING] Market order placed for {pe_name}. Waiting for LTP execution...")

					message = f"[PAPER TRADING] Entry order placed for {name} (PE: {pe_name}) - Sell Signal"
					#tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

				except Exception as e:
					print(f"[PAPER TRADING] Error in entry order simulation for {name} (PE): {e}")
					traceback.print_exc()

		# ============================
		# ✅ CHECK EXIT CONDITIONS (PAPER TRADING)
		# ============================
		if orderbook[name]['traded'] == "yes":
			bought = orderbook[name]['buy_sell'] == "BUY"

			if bought:
				try:
					options_name = orderbook[name]['options_name']
					if not options_name:
						print(f"[WARNING] No options_name found for {name} during exit check.")
						return name, "skip_exit_no_option"

					# Get current LTP for the option
					if options_name in all_ltp:
						ltp = all_ltp[options_name]
					else:
						print(f"[WARNING] No LTP found for {options_name}. Skipping exit check.")
						return name, "skip_exit_no_ltp"

					sl_status = tsl.get_order_status(orderbook[name]['sl_orderid'])
					sl_hit = sl_status == "TRADED"

					holding_time_exceeded = datetime.datetime.now() > orderbook[name]['max_holding_time']
					current_pnl = round((ltp - orderbook[name]['entry_price']) * orderbook[name]['qty'], 1)

				except Exception as e:
					print(f"[PAPER TRADING] Error checking SL for {name}: {e}")
					traceback.print_exc()

				if sl_hit:
					try:
						orderbook[name]['exit_time'] = str(process_start_time.time())[:8]
						exit_price = tsl.get_executed_price(orderbook[name]['sl_orderid'])
						if exit_price is None:
							print(f"[WARNING] Failed to get SL executed price for {name}. Using 0.")
							exit_price = 0
						orderbook[name]['exit_price'] = exit_price

						orderbook[name]['pnl'] = round(
							(orderbook[name]['exit_price'] - orderbook[name]['entry_price']) * orderbook[name]['qty'],
							1)
						orderbook[name]['remark'] = "Bought_SL_hit"

						message = f"[PAPER TRADING] SL HIT for {name} - P&L: ₹{orderbook[name]['pnl']}"
						#tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

						if reentry == "yes":
							completed_orders.append(orderbook[name].copy())
							orderbook[name] = single_order.copy()

					except Exception as e:
						print(f"[PAPER TRADING] Error in SL hit processing for {name}: {e}")
						traceback.print_exc()

				if holding_time_exceeded and (current_pnl < 0):
					try:
						# ⬇️ PAPER TRADING: Simulate square off
						tsl.cancel_order(orderbook[name]['sl_orderid'])
						time.sleep(2)

						square_off_order = tsl.order_placement(tradingsymbol=orderbook[name]['options_name'],
						                                       exchange='NFO', quantity=orderbook[name]['qty'],
						                                       price=0, trigger_price=0, order_type='MARKET',
						                                       transaction_type='SELL', trade_type='MIS')

						orderbook[name]['exit_time'] = str(process_start_time.time())[:8]
						exit_price = tsl.get_executed_price(square_off_order)
						if exit_price is None:
							exit_price = 0
						orderbook[name]['exit_price'] = exit_price

						orderbook[name]['pnl'] = (orderbook[name]['exit_price'] - orderbook[name]['entry_price']) * \
						                         orderbook[name]['qty']
						orderbook[name]['remark'] = "holding_time_exceeded_and_I_am_still_facing_loss"

						message = f"[PAPER TRADING] Time exceeded exit for {name} - P&L: ₹{orderbook[name]['pnl']}"
						#tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

						if reentry == "yes":
							completed_orders.append(orderbook[name].copy())
							orderbook[name] = single_order.copy()

						print(f"[PAPER TRADING] Time exceeded - Position closed for {name}")

					except Exception as e:
						print(f"[PAPER TRADING] Error in time exceeded processing for {name}: {e}")
						traceback.print_exc()

				# ============================
				# ✅ TSL UPDATE (PAPER TRADING)
				# ============================
				try:
					options_name = orderbook[name]['options_name']
					if not options_name:
						print(f"[WARNING] No options_name found for {name} during TSL update. Skipping.")
						return name, "skip_tsl_no_option"

					# ⬇️ RATE LIMITED: Data API
					data_api_limiter.wait(
						call_description=f"tsl.get_historical_data(tradingsymbol='{options_name}', exchange='NFO', timeframe='5')")
					options_chart_tsl = tsl.get_historical_data(tradingsymbol=options_name, exchange='NFO',
					                                            timeframe="5")
					if options_chart_tsl is None:
						print(f"[WARNING] Failed to fetch TSL data for {options_name}. Skipping update.")
						return name, "skip_tsl_fetch"

					if not all(col in options_chart_tsl.columns for col in ['high', 'low', 'close']):
						print(f"[ERROR] Missing required columns for ATR in TSL data for {options_name}.")
						return name, "skip_tsl_missing_cols"

					options_chart_tsl['atr'] = talib.ATR(options_chart_tsl['high'], options_chart_tsl['low'],
					                                     options_chart_tsl['close'], timeperiod=14)
					rc_options_tsl = options_chart_tsl.iloc[-1]
					sl_points_tsl = rc_options_tsl['ATR'] * atr_multipler

					if options_name in all_ltp:
						options_ltp = all_ltp[options_name]
						tsl_level = options_ltp - sl_points_tsl

						if tsl_level > orderbook[name]['tsl']:
							trigger_price = round(tsl_level, 1)
							price = trigger_price - 0.05
							tsl_qty = orderbook[name].get('qty', 0)
							if tsl_qty <= 0:
								print(f"[WARNING] Invalid quantity {tsl_qty} for TSL update for {name}.")
								return name, "skip_tsl_invalid_qty"

							# ⬇️ PAPER TRADING: Simulate TSL modification
							tsl.modify_order(order_id=orderbook[name]['sl_orderid'], order_type="STOPLIMIT",
							                 quantity=tsl_qty, price=price, trigger_price=trigger_price)
							orderbook[name]['tsl'] = tsl_level
							print(f"[PAPER TRADING] TSL updated for {name} ({options_name}) to ₹{tsl_level}")
					else:
						print(f"[WARNING] No LTP found for {options_name} during TSL update.")
				except Exception as e:
					print(f"[PAPER TRADING] Error updating TSL for {name}: {e}")

		process_end_time = datetime.datetime.now()
		processing_time = (process_end_time - process_start_time).total_seconds()
		print(f"Completed processing {name} in {processing_time:.2f} seconds")
		return name, "processed"

	except Exception as e:
		print(f"[PAPER TRADING] Error processing {name}: {e}")
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
# ✅ PAPER TRADING EXECUTION HELPER FUNCTIONS
# (Moved above the main loop so they are defined before use)
# ============================

def execute_paper_entry_orders():
	"""Execute pending paper trading entry orders when LTP is available"""
	for name, order_data in orderbook.items():
		if (order_data.get('entry_orderid') and
				order_data.get('entry_price') is None and
				order_data.get('options_name')):

			options_name = order_data['options_name']
			entry_order = paper_engine.orders.get(order_data['entry_orderid'])

			# Use current global all_ltp if available
			global all_ltp
			# If all_ltp is not defined or missing option LTP, try to get LTP for this option on-demand
			if 'all_ltp' not in globals() or not all_ltp:
				try:
					ltp_api_limiter.wait(call_description=f"tsl.get_ltp_data(names=[{options_name}]) for entry execution")
					all_ltp_res = retry_api_call(tsl.get_ltp_data, retries=1, delay=1.0, names=[options_name])
					if all_ltp_res:
						# merge into global all_ltp
						if 'all_ltp' in globals() and isinstance(all_ltp, dict):
							all_ltp.update(all_ltp_res)
						else:
							all_ltp = all_ltp_res
				except Exception as e:
					print(f"[ENTRY EXEC] Could not fetch LTP for {options_name}: {e}")

			if (entry_order and
					entry_order.get('needs_ltp_execution') and
					options_name in globals() and options_name in all_ltp):
				# Execute the entry order
				ltp = all_ltp[options_name]
				slippage = 0.05  # Add slippage for buy orders
				executed_price = ltp + slippage

				# Update order in paper engine
				entry_order['executed_price'] = executed_price
				entry_order['needs_ltp_execution'] = False

				# Update orderbook
				orderbook[name]['entry_price'] = executed_price

				# Calculate stop loss
				# Try to fetch ATR from a recent options chart if available, otherwise use fallback
				sl_points = None
				try:
					# Try to fetch a small timeframe history for the option to compute ATR
					data_api_limiter.wait(call_description=f"tsl.get_historical_data(tradingsymbol='{options_name}', exchange='NFO', timeframe='1')")
					opt_hist = retry_api_call(tsl.get_historical_data, retries=1, delay=1.0, tradingsymbol=options_name, exchange='NFO', timeframe="1")
					if opt_hist is not None and not opt_hist.empty:
						opt_res = tsl.resample_timeframe(opt_hist, timeframe='3T')
						opt_res['atr'] = talib.ATR(opt_res['high'], opt_res['low'], opt_res['close'], timeperiod=14)
						sl_points = float(opt_res['atr'].iloc[-1]) * atr_multipler if 'atr' in opt_res.columns else None
				except Exception as e:
					print(f"[ENTRY EXEC] Failed to compute ATR for {options_name}: {e}")

				if sl_points is None:
					# fallback - small default stop distance
					sl_points = 0.5

				orderbook[name]['sl'] = round(executed_price - sl_points, 2)
				orderbook[name]['tsl'] = orderbook[name]['sl']

				# Place stop loss order
				price = orderbook[name]['sl'] - 0.05
				sl_orderid = tsl.order_placement(
					tradingsymbol=options_name,
					exchange='NFO',
					quantity=orderbook[name]['qty'],
					price=price,
					trigger_price=orderbook[name]['sl'],
					order_type='STOPLIMIT',
					transaction_type='SELL',
					trade_type='MIS'
				)

				orderbook[name]['sl_orderid'] = sl_orderid
				orderbook[name]['traded'] = "yes"

				message = f"[PAPER TRADING] Entry executed for {name} at {executed_price:.2f}. SL set at {orderbook[name]['sl']:.2f}"
				print(message)
				#tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)


def print_paper_trading_summary():
	"""Print a summary of current paper trading positions"""
	print("\n" + "=" * 60)
	print("PAPER TRADING SUMMARY")
	print("=" * 60)

	active_positions = 0
	total_unrealized_pnl = 0

	for name, order_data in orderbook.items():
		if order_data.get('traded') == 'yes' and order_data.get('options_name'):
			active_positions += 1
			options_name = order_data['options_name']

			if options_name in globals() and order_data.get('entry_price'):
				current_price = all_ltp.get(options_name, 0)
				entry_price = order_data['entry_price']
				qty = order_data.get('qty', 0)

				unrealized_pnl = (current_price - entry_price) * qty
				total_unrealized_pnl += unrealized_pnl

				print(
					f"{name:10} | {options_name:20} | Entry: {entry_price:7.2f} | Current: {current_price:7.2f} | P&L: {unrealized_pnl:8.2f}")

	print("-" * 60)
	print(f"Active Positions: {active_positions}")
	print(f"Total Unrealized P&L: {total_unrealized_pnl:,.2f}")
	print(f"Completed Trades: {len(completed_orders)}")

	if completed_orders:
		total_realized_pnl = sum(order.get('pnl', 0) for order in completed_orders)
		print(f"Total Realized P&L: {total_realized_pnl:,.2f}")
		print(f"Net P&L: {total_unrealized_pnl + total_realized_pnl:,.2f}")

	print("=" * 60)


# ============================
# ✅ ENHANCED ERROR HANDLING AND LOGGING
# ============================

def log_paper_trade(action, symbol, details):
	"""Log paper trading actions to file"""
	log_entry = {
		'timestamp': datetime.datetime.now().isoformat(),
		'action': action,
		'symbol': symbol,
		'details': details
	}

	try:
		with open(f'paper_trades_{datetime.date.today()}.log', 'a') as f:
			f.write(json.dumps(log_entry) + '\n')
	except Exception as e:
		print(f"Error logging trade: {e}")


def validate_paper_trading_setup():
	"""Validate that paper trading is set up correctly"""
	print("Validating paper trading setup...")

	# Check if we have market data access
	try:
		test_ltp = tsl.get_ltp_data(['RELIANCE'])
		if test_ltp and 'RELIANCE' in test_ltp:
			print("Market data access: OK")
		else:
			print("WARNING: Market data access may be limited")
	except Exception as e:
		print(f"ERROR: Market data access failed - {e}")
		return False

	# Check Excel file access
	try:
		live_Trading.range('A1').value = "Paper Trading Test"
		print("Excel file access: OK")
	except Exception as e:
		print(f"WARNING: Excel file access failed - {e}")

	# Check paper trading engine
	if paper_engine and hasattr(paper_engine, 'place_order'):
		print("Paper trading engine: OK")
	else:
		print("ERROR: Paper trading engine not properly initialized")
		return False

	print("Paper trading setup validation complete.")
	return True


# ============================
# ✅ STARTUP VALIDATION
# ============================

if __name__ == "__main__":
	print("Starting Paper Trading System...")

	if validate_paper_trading_setup():
		print("All systems ready. Starting paper trading loop...")
	else:
		print("Setup validation failed. Please check configuration.")
		exit(1)


# ============================
# ✅ MAIN LOOP (PAPER TRADING)
# ============================
print("=" * 60)
print("🎯 PAPER TRADING MODE ACTIVATED")
print("=" * 60)
print(f"📊 Initial Balance: ₹{paper_engine.initial_balance:,}")
print(f"📈 Max Risk for Today: ₹{max_risk_for_today:,}")
print(f"📋 Watchlist: {len(watchlist)} symbols")
print("=" * 60)

# Define a global all_ltp container that will be used by helper functions
all_ltp = {}

while True:
	print("🔄 Starting Paper Trading Loop")

	current_time = datetime.datetime.now().time()
	if current_time < datetime.time(9, 15):
		print(f"⏰ Market not started. Current time: {current_time}. Waiting...")
		time.sleep(60)  # Wait 1 minute before checking again
		continue

	# Calculate paper trading P&L
	ltp_api_limiter.wait(call_description="tsl.get_ltp_data(names=watchlist) for P&L calculation")
	all_ltp_raw = retry_api_call(tsl.get_ltp_data, retries=1, delay=1.0, names=watchlist)

	if all_ltp_raw is None:
		print("[ERROR] Failed to fetch LTP data for P&L calculation. Skipping this cycle.")
		time.sleep(5)
		continue

	# Get LTP for options as well (for positions)
	active_options = [order['options_name'] for order in orderbook.values()
	                  if order.get('options_name') and order.get('traded') == 'yes']

	if active_options:
		ltp_api_limiter.wait(call_description="tsl.get_ltp_data for active options")
		options_ltp_raw = retry_api_call(tsl.get_ltp_data, retries=1, delay=1.0, names=active_options)
		if options_ltp_raw:
			all_ltp_raw.update(options_ltp_raw)

	all_ltp = all_ltp_raw

	# Update paper trading engine with current LTP
	paper_engine.execute_pending_market_orders(all_ltp)
	paper_engine.check_stop_loss_orders(all_ltp)

	# ===== NEW: Execute pending entry orders so Excel shows entry price, SL, TSL, P&L
	try:
		execute_paper_entry_orders()
	except Exception as e:
		print(f"[ERROR] execute_paper_entry_orders failed: {e}")
		traceback.print_exc()

	# Update Excel immediately so user sees changes
	try:
		update_excel_sheets()
	except Exception as e:
		print(f"[ERROR] update_excel_sheets failed: {e}")
		traceback.print_exc()

	# Calculate current P&L
	current_pnl = paper_engine.calculate_live_pnl(all_ltp)
	tsl._current_pnl = current_pnl  # Store for get_live_pnl() method

	max_loss_hit = current_pnl < (max_risk_for_today * -1)
	market_over = current_time > datetime.time(15, 15)

	print(f"💰 Current Paper Trading P&L: ₹{current_pnl:,.2f}")
	print(f"🎯 Max Loss Limit: ₹{max_risk_for_today * -1:,.2f}")

	if max_loss_hit:
		print("🚨 MAX LOSS HIT! Closing all paper positions...")
		try:
			paper_engine.cancel_all_orders()
			print("📊 All paper trading positions closed due to max loss.")
		except Exception as e:
			print(f"Error during cancel_all_orders: {e}")

	if market_over:
		print(f"📅 Market Over! Final Paper Trading P&L: ₹{current_pnl:,.2f}")
		try:
			paper_engine.cancel_all_orders()
			print("🏁 Paper trading session completed for the day.")

			# Save paper trading results to file
			paper_results = {
				'date': str(datetime.date.today()),
				'initial_balance': paper_engine.initial_balance,
				'final_pnl': current_pnl,
				'total_orders': len([o for o in paper_engine.orders.values() if o['status'] == 'TRADED']),
				'completed_trades': len(completed_orders)
			}

			with open(f'paper_trading_results_{datetime.date.today()}.json', 'w') as f:
				json.dump(paper_results, f, indent=2, default=str)

			print(f"📁 Results saved to paper_trading_results_{datetime.date.today()}.json")

		except Exception as e:
			print(f"Error during end-of-day cleanup: {e}")
		break

	# Process symbols in batches
	batch_size = 3
	for i in range(0, len(watchlist), batch_size):
		batch_symbols = watchlist[i:i + batch_size]
		print(f"📊 Processing batch: {batch_symbols}")

		# First, fetch data for all symbols in batch concurrently
		fetched_data = {}
		with ThreadPoolExecutor(max_workers=batch_size) as fetch_executor:
			future_to_name_fetch = {fetch_executor.submit(fetch_historical, name): name for name in batch_symbols}

			for future in as_completed(future_to_name_fetch):
				try:
					name, chart, fetch_time = future.result()
					fetched_data[name] = (chart, fetch_time)
				except Exception as e:
					name = future_to_name_fetch[future]
					print(f"[PAPER TRADING] Error fetching data for {name}: {e}")
					continue

		# Then, process all fetched data concurrently
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
					print(f"[PAPER TRADING] Error processing {name}: {e}")
					continue

		# Update Excel sheets after each batch
		update_excel_sheets()

		# Small delay between batches to avoid overwhelming the system/API
		time.sleep(1)

	# Brief pause before next main loop iteration
	time.sleep(5)


# ============================
# ✅ ADDITIONAL PAPER TRADING FEATURES
# ============================

def export_paper_trading_results():
	"""Export paper trading results to CSV"""
	try:
		# Export completed orders
		if completed_orders:
			df_completed = pd.DataFrame(completed_orders)
			filename = f'paper_trading_completed_{datetime.date.today()}.csv'
			df_completed.to_csv(filename, index=False)
			print(f"Completed orders exported to {filename}")

		# Export current positions
		active_orders = {name: data for name, data in orderbook.items() if data.get('traded') == 'yes'}
		if active_orders:
			df_active = pd.DataFrame(active_orders).T
			filename = f'paper_trading_active_{datetime.date.today()}.csv'
			df_active.to_csv(filename, index=False)
			print(f"Active positions exported to {filename}")

		# Export paper engine orders
		if paper_engine.orders:
			df_engine = pd.DataFrame(paper_engine.orders).T
			filename = f'paper_engine_orders_{datetime.date.today()}.csv'
			df_engine.to_csv(filename, index=False)
			print(f"Paper engine orders exported to {filename}")

	except Exception as e:
		print(f"Error exporting results: {e}")


def calculate_paper_trading_metrics():
	"""Calculate trading performance metrics"""
	if not completed_orders:
		return None

	pnls = [order.get('pnl', 0) for order in completed_orders if order.get('pnl') is not None]

	if not pnls:
		return None

	metrics = {
		'total_trades': len(pnls),
		'winning_trades': len([p for p in pnls if p > 0]),
		'losing_trades': len([p for p in pnls if p < 0]),
		'total_pnl': sum(pnls),
		'avg_pnl': sum(pnls) / len(pnls),
		'max_profit': max(pnls),
		'max_loss': min(pnls),
		'win_rate': len([p for p in pnls if p > 0]) / len(pnls) * 100 if pnls else 0
	}

	return metrics


# Print initial setup information
print("\n" + "=" * 60)
print("PAPER TRADING CONFIGURATION")
print("=" * 60)
print(f"Initial Balance: {paper_engine.initial_balance:,}")
print(f"Base Capital: {base_capital:,}")
print(f"Market Money: {market_money:,}")
print(f"Max Risk Today: {max_risk_for_today:,}")
print(f"Risk Per Trade: {risk_per_trade:,}")
print(f"ATR Multiplier: {atr_multipler}")
print(f"Risk Reward Ratio: {risk_reward}")
print(f"Watchlist Size: {len(watchlist)} symbols")
print(f"Max Orders Today: {max_order_for_today}")
print("=" * 60)
print("Paper trading will simulate all order placement and execution.")
print("No real money will be used. All P&L is virtual.")
print("=" * 60)
