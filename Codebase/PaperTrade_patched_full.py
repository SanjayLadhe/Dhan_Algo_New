import pdb
import time
import datetime
import traceback
import random  # For simulating order IDs
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
from logging.handlers import TimedRotatingFileHandler # Import for log rotation

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
                    self.logger.info(f"RATE_LIMIT_HIT - {self.name} - {call_description} - Sleeping for {sleep_time:.3f} seconds. Queue size: {len(self.calls)}")
                    print(f"[{self.name}] Rate limit reached for '{call_description}'. Sleeping for {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    # After sleep, clean up again
                    now = time.time()
                    while self.calls and self.calls[0] <= now - self.period:
                        self.calls.popleft()

            # Add current call timestamp
            self.calls.append(now)
            active_calls = len(self.calls)
            self.logger.info(f"CALL_ALLOWED - {self.name} - {call_description} - Queue size after add: {active_calls}, Max allowed: {self.max_calls}")
            print(f"[{self.name}] ✅ Call allowed for '{call_description}' at {now:.2f}. Active calls in window: {active_calls}")

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
                 general_api_logger.warning(f"[RETRY] Rate limit error detected for {func.__name__}: {e}. Applying longer backoff.")
                 # Apply longer backoff for rate limits
                 time.sleep(delay * 2 * (attempt + 1))
                 continue # Retry immediately after rate limit backoff

            if attempt == retries - 1:  # Last attempt
                general_api_logger.error(f"[RETRY] Failed after {retries} attempts for {func.__name__}: {e}")
                raise e
            general_api_logger.warning(f"[RETRY] Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay} seconds...")
            print(f"[RETRY] Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    return None # Should not reach here due to raise, but good practice

# ============================
# ✅ INITIALIZE RATE LIMITERS (Based on official limits)
# ============================
# Data API Limiter: 5 calls per second (Official limit)
data_api_limiter = RateLimiter(max_calls=5, period=1.0, name="DATA_API", logger=rate_limit_logger)

# Non Trading API Limiter: 18 calls per second (Slightly under 20/sec official limit)
ntrading_api_limiter = RateLimiter(max_calls=18, period=1.0, name="NTRADING_API", logger=general_api_logger)

# Order API Limiter: 25 calls per second (Official limit)
order_api_limiter = RateLimiter(max_calls=25, period=1.0, name="ORDER_API", logger=general_api_logger)

ltp_api_limiter=RateLimiter(max_calls=1, period=1.0, name="LTP_API", logger=general_api_logger)


# Configure pandas display
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

client_code = "1106090196"
token_id    = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU5ODQ2NzIzLCJpYXQiOjE3NTcyNTQ3MjMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.rPFraaBkmAg2QiJvctdffiiyyaA3FfqZ0vDd0gNW0uD4uWNGCfYOqG5mYOxdxI3-i4gMml0exNvgAQPv9-zp8g"

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
                'entry_orderid': None, 'sl_orderid': None, 'options_name': None, 'tsl': None, 'max_holding_time': None}
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
    data_api_limiter.wait(call_description=f"tsl.get_historical_data(tradingsymbol='{name}', exchange='{exchange}', timeframe='1')")
    fetch_time = datetime.datetime.now()
    print(f"Fetching historical data for {name} {fetch_time}")
    Data = tsl.get_historical_data(tradingsymbol=name, exchange=exchange, timeframe="1")
    if Data is None:
        print(f"[ERROR] Failed to fetch historical data for {name}. Returned None.")
        return name, None, fetch_time # Return None chart if fetch fails
    chart = tsl.resample_timeframe(Data, timeframe="3T")
    Data = Data.reset_index()
    complete_time = datetime.datetime.now()
    print(f"Completed fetching for {name} at {complete_time}")
    return name, chart, complete_time


# ============================
# ✅ SIMULATE ORDER PLACEMENT (PAPER TRADING)
# ============================
def simulate_order_placement(tradingsymbol, exchange, quantity, order_type, transaction_type, price=0, trigger_price=0, trade_type='MIS'):
    """
    Simulate order placement for paper trading. Returns a simulated order ID.
    """
    simulated_id = f"SIM_{random.randint(100000, 999999)}_{tradingsymbol}_{transaction_type}"
    print(f"[PAPER] Simulated {transaction_type} order placed for {tradingsymbol}: ID={simulated_id}, Qty={quantity}, Type={order_type}")
    return simulated_id


# ============================
# ✅ SIMULATE GET EXECUTED PRICE (PAPER TRADING)
# ============================
def simulate_get_executed_price(orderid, current_ltp=None):
    """
    Simulate executed price. For market orders, use provided LTP. For SL, use trigger_price or LTP.
    """
    # In paper trading, we can derive from order details, but for simplicity, use provided LTP
    if current_ltp is not None:
        return current_ltp
    return 0  # Fallback


# ============================
# ✅ SIMULATE CANCEL ORDER (PAPER TRADING)
# ============================
def simulate_cancel_order(order_id):
    """
    Simulate canceling an order.
    """
    print(f"[PAPER] Simulated cancel order: {order_id}")
    return True


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
            print("buy ", name, "\t")

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
            data_api_limiter.wait(call_description=f"tsl.get_historical_data(tradingsymbol='{ce_name}', exchange='NFO', timeframe='1')")
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
                 print(f"[ERROR] Missing required columns in CE Option data for {ce_name}. Columns: {options_chart_Res.columns.tolist()}")
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
                print("buy ce_name", ce_name, "\t")

                orderbook[name]['name'] = name
                orderbook[name]['options_name'] = ce_name # ✅ Correct assignment for CE

                orderbook[name]['date'] = str(process_start_time.date())
                orderbook[name]['entry_time'] = str(process_start_time.time())[:8]
                orderbook[name]['max_holding_time'] = datetime.datetime.now() + datetime.timedelta(hours=2)

                orderbook[name]['buy_sell'] = "BUY"
                sl_points = rc_options['ATR'] * atr_multipler
                orderbook[name]['qty'] = lot_size

                try:
                    # SIMULATE: Fetch LTP for entry price
                    ltp_api_limiter.wait(call_description=f"tsl.get_ltp_data(names=['{ce_name}'])")
                    options_ltp_data = retry_api_call(tsl.get_ltp_data, retries=3, delay=1.0, names=[ce_name])
                    if options_ltp_data is None or ce_name not in options_ltp_data:
                        print(f"[PAPER] Failed to get LTP for {ce_name}. Using last close {last_close} as entry.")
                        entry_price = last_close
                    else:
                        entry_price = options_ltp_data[ce_name]

                    # SIMULATE: Entry order
                    order_api_limiter.wait(call_description=f"simulate_order_placement(tradingsymbol='{ce_name}', transaction_type='BUY')")
                    entry_orderid = simulate_order_placement(tradingsymbol=orderbook[name]['options_name'], exchange='NFO',
                                                             quantity=orderbook[name]['qty'], price=0, trigger_price=0,
                                                             order_type='MARKET', transaction_type='BUY', trade_type='MIS')
                    orderbook[name]['entry_orderid'] = entry_orderid

                    # SIMULATE: Executed price (use LTP)
                    orderbook[name]['entry_price'] = entry_price

                    orderbook[name]['sl'] = round(orderbook[name]['entry_price'] - sl_points, 1)
                    orderbook[name]['tsl'] = orderbook[name]['sl']

                    price = orderbook[name]['sl'] - 0.05

                    # SIMULATE: SL order
                    order_api_limiter.wait(call_description=f"simulate_order_placement(tradingsymbol='{ce_name}', transaction_type='SELL')")
                    sl_orderid = simulate_order_placement(tradingsymbol=orderbook[name]['options_name'], exchange='NFO',
                                                          quantity=orderbook[name]['qty'], price=price,
                                                          trigger_price=orderbook[name]['sl'], order_type='STOPLIMIT',
                                                          transaction_type='SELL', trade_type='MIS')
                    orderbook[name]['sl_orderid'] = sl_orderid
                    orderbook[name]['traded'] = "yes"

                    message = "\n".join(f"'{key}': {repr(value)}" for key, value in orderbook[name].items())
                    message = f"[PAPER] Entry_done {name} \n\n {message}"
                    print(message)  # Log to console instead of Telegram for paper
                    #tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

                except Exception as e:
                    print(f"[PAPER] Error in entry simulation for {name}: {e}")
                    traceback.print_exc()

        # ============================
        # ✅ SELL ENTRY (Actually buying PE) (PAPER TRADING)
        # ============================
        if sc1 and sc2 and sc3 and sc4 and sc5 and sc6 and sc7:
            print("Sell ", name, "\t")

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
            data_api_limiter.wait(call_description=f"tsl.get_historical_data(tradingsymbol='{pe_name}', exchange='NFO', timeframe='1')")
            options_chart = tsl.get_historical_data(tradingsymbol=pe_name, exchange='NFO', timeframe="1")
            if options_chart is None:
                print(f"[ERROR] Failed to fetch data for PE Option {pe_name}. Returned None.")
                return name, "skip_option_fetch_pe"

            options_chart_Res = tsl.resample_timeframe(options_chart, timeframe='3T')
            # Add check if resampling returns valid data
            if options_chart_Res is None or options_chart_Res.empty:
                 print(f"[ERROR] Resampling failed or returned empty data for PE Option {pe_name}.")
                 return name, "skip_option_resample_pe"

            options_chart = options_chart.reset_index()

            # Defensive check for required columns before VWAP
            required_cols = ['high', 'low', 'close', 'volume', 'timestamp']
            if not all(col in options_chart_Res.columns for col in required_cols):
                 print(f"[ERROR] Missing required columns in PE Option data for {pe_name}. Columns: {options_chart_Res.columns.tolist()}")
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
            # Use rc_options for stop and fractal
            long_stop_opt = pd.to_numeric(rc_options['Long_Stop'], errors='coerce')
            fractal_low_opt = pd.to_numeric(rc_options['fractal_low'], errors='coerce')
            vwap_opt = pd.to_numeric(rc_options['vwap'], errors='coerce')
            Crossbelow_opt = pta.below(options_chart_Res['rsi'], options_chart_Res['ma_rsi'])

            # Buy entry conditions for option (PE)
            bc1_opt = rc_options_cc['rsi'] > 60 # Note: This condition might need review for Sell logic
            bc2_opt = bool(Crossbelow_opt.iloc[-2]) # Note: This condition might need review for Sell logic
            bc3_opt = cc_close < long_stop_opt
            bc4_opt = cc_close < fractal_low_opt
            bc5_opt = cc_close < vwap_opt
            bc6_opt = orderbook[name]['traded'] is None
            bc7_opt = no_of_orders_placed < 5

            print(
                f" Buy Condition for pe_name {pe_name} (Sell Signal) : {bc1_opt}, {bc2_opt}, {bc3_opt}, {bc4_opt}, {bc5_opt} : {process_start_time} \n")

            # Note: The buy conditions for PE (which represents a sell signal for the underlying)
            # might need adjustment based on your specific strategy logic.
            # The original code checked 'sc' conditions for the underlying but then used 'bc' conditions for the option.
            # This part assumes you want to proceed with the buy logic on the option if the underlying sell signal triggers.
            # You might need to adjust the option buy conditions (bc1_opt etc.) based on your strategy for selling (buying PE).
            if bc1_opt and bc2_opt and bc3_opt and bc4_opt and bc5_opt and bc6_opt and bc7_opt:
                print("buy pe_name (Sell Signal)", pe_name, "\t")

                orderbook[name]['name'] = name
                orderbook[name]['options_name'] = pe_name  # ✅ FIXED: was ce_name earlier

                orderbook[name]['date'] = str(process_start_time.date())
                orderbook[name]['entry_time'] = str(process_start_time.time())[:8]
                orderbook[name]['max_holding_time'] = datetime.datetime.now() + datetime.timedelta(hours=2)

                orderbook[name]['buy_sell'] = "BUY" # Buying the PE option
                sl_points = rc_options['ATR'] * atr_multipler
                orderbook[name]['qty'] = lot_size

                try:
                     # SIMULATE: Fetch LTP for entry price
                    ltp_api_limiter.wait(call_description=f"tsl.get_ltp_data(names=['{pe_name}'])")
                    options_ltp_data = retry_api_call(tsl.get_ltp_data, retries=3, delay=1.0, names=[pe_name])
                    if options_ltp_data is None or pe_name not in options_ltp_data:
                        print(f"[PAPER] Failed to get LTP for {pe_name}. Using last close {last_close} as entry.")
                        entry_price = last_close
                    else:
                        entry_price = options_ltp_data[pe_name]

                    # SIMULATE: Entry order
                    order_api_limiter.wait(call_description=f"simulate_order_placement(tradingsymbol='{pe_name}', transaction_type='BUY')")
                    entry_orderid = simulate_order_placement(tradingsymbol=orderbook[name]['options_name'], exchange='NFO',
                                                             quantity=orderbook[name]['qty'], price=0, trigger_price=0,
                                                             order_type='MARKET', transaction_type='BUY', trade_type='MIS')
                    orderbook[name]['entry_orderid'] = entry_orderid

                    # SIMULATE: Executed price (use LTP)
                    orderbook[name]['entry_price'] = entry_price

                    orderbook[name]['sl'] = round(orderbook[name]['entry_price'] - sl_points, 1)
                    orderbook[name]['tsl'] = orderbook[name]['sl']

                    price = orderbook[name]['sl'] - 0.05

                    # SIMULATE: SL order
                    order_api_limiter.wait(call_description=f"simulate_order_placement(tradingsymbol='{pe_name}', transaction_type='SELL')")
                    sl_orderid = simulate_order_placement(tradingsymbol=orderbook[name]['options_name'], exchange='NFO',
                                                          quantity=orderbook[name]['qty'], price=price,
                                                          trigger_price=orderbook[name]['sl'], order_type='STOPLIMIT',
                                                          transaction_type='SELL', trade_type='MIS')
                    orderbook[name]['sl_orderid'] = sl_orderid
                    orderbook[name]['traded'] = "yes"

                    message = "\n".join(f"'{key}': {repr(value)}" for key, value in orderbook[name].items())
                    message = f"[PAPER] Entry_done {name} (PE Buy/Sell Signal) \n\n {message}"
                    print(message)  # Log to console instead of Telegram for paper
                    #tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

                except Exception as e:
                    print(f"[PAPER] Error in entry simulation for {name} (PE): {e}")
                    traceback.print_exc()

        # ============================
        # ✅ CHECK EXIT CONDITIONS (PAPER TRADING)
        # ============================
        if orderbook[name]['traded'] == "yes":
            options_name = orderbook[name]['options_name']
            if not options_name:
                print(f"[PAPER] No options_name for {name}. Skipping exit check.")
                return name, "skip_exit_no_option"

            bought = orderbook[name]['buy_sell'] == "BUY"

            if bought:
                try:
                    # SIMULATE: Fetch current LTP for option to check conditions
                    ltp_api_limiter.wait(call_description=f"tsl.get_ltp_data(names=['{options_name}'])")
                    options_ltp_data = retry_api_call(tsl.get_ltp_data, retries=3, delay=1.0, names=[options_name])
                    if options_ltp_data is None or options_name not in options_ltp_data:
                        print(f"[PAPER] Failed to get LTP for {options_name}. Skipping exit checks.")
                        return name, "skip_exit_ltp"
                    current_option_ltp = options_ltp_data[options_name]

                    # SIMULATE: Check if SL hit (LTP <= SL)
                    sl_hit = current_option_ltp <= orderbook[name]['sl']

                    holding_time_exceeded = datetime.datetime.now() > orderbook[name]['max_holding_time']
                    current_pnl = round((current_option_ltp - orderbook[name]['entry_price']) * orderbook[name]['qty'], 1)

                except Exception as e:
                    print(f"[PAPER] Error checking SL for {name}: {e}")
                    traceback.print_exc()
                    return name, f"error_exit_check: {str(e)}"

                if sl_hit:
                    try:
                        orderbook[name]['exit_time'] = str(process_start_time.time())[:8]

                        # SIMULATE: Exit at SL price
                        exit_price = orderbook[name]['sl']  # Assume filled at SL

                        orderbook[name]['exit_price'] = exit_price

                        orderbook[name]['pnl'] = round(
                            (orderbook[name]['exit_price'] - orderbook[name]['entry_price']) * orderbook[name]['qty'],
                            1)
                        orderbook[name]['remark'] = "Bought_SL_hit"

                        message = "\n".join(f"'{key}': {repr(value)}" for key, value in orderbook[name].items())
                        message = f"[PAPER] SL_HIT {name} \n\n {message}"
                        print(message)  # Log to console

                        if reentry == "yes":
                            completed_orders.append(orderbook[name].copy())
                            orderbook[name] = single_order.copy()

                    except Exception as e:
                        print(f"[PAPER] Error in SL hit processing for {name}: {e}")
                        traceback.print_exc()

                if holding_time_exceeded and (current_pnl < 0):
                    try:
                        # SIMULATE: Cancel SL (no effect in paper)
                        order_api_limiter.wait(call_description=f"simulate_cancel_order(order_id='{orderbook[name]['sl_orderid']}')")
                        simulate_cancel_order(order_id=orderbook[name]['sl_orderid'])
                        time.sleep(2)

                        # SIMULATE: Square off at market (current LTP)
                        order_api_limiter.wait(call_description=f"simulate_order_placement(tradingsymbol='{options_name}', transaction_type='SELL')")
                        square_off_buy_order = simulate_order_placement(tradingsymbol=options_name,
                                                                        exchange='NFO', quantity=orderbook[name]['qty'],
                                                                        price=0, trigger_price=0, order_type='MARKET',
                                                                        transaction_type='SELL', trade_type='MIS')

                        orderbook[name]['exit_time'] = str(process_start_time.time())[:8]

                        # SIMULATE: Executed price (use current LTP)
                        exit_price = current_option_ltp

                        orderbook[name]['exit_price'] = exit_price

                        orderbook[name]['pnl'] = (orderbook[name]['exit_price'] - orderbook[name]['entry_price']) * \
                                                 orderbook[name]['qty']
                        orderbook[name]['remark'] = "holding_time_exceeded_and_I_am_still_facing_loss"

                        message = "\n".join(f"'{key}': {repr(value)}" for key, value in orderbook[name].items())
                        message = f"[PAPER] holding_time_exceeded_and_I_am_still_facing_loss {name} \n\n {message}"
                        print(message)  # Log to console

                        if reentry == "yes":
                            completed_orders.append(orderbook[name].copy())
                            orderbook[name] = single_order.copy()

                        winsound.Beep(1500, 10000)

                    except Exception as e:
                        print(f"[PAPER] Error in time exceeded processing for {name}: {e}")
                        traceback.print_exc()

                # ============================
                # ✅ TSL UPDATE — SIMULATED (PAPER TRADING)
                # ============================
                try:
                    if not options_name: # Defensive check
                         print(f"[WARNING] No options_name found for {name} during TSL update. Skipping.")
                         return name, "skip_tsl_no_option"

                    # ⬇️ RATE LIMITED: Data API
                    data_api_limiter.wait(call_description=f"tsl.get_historical_data(tradingsymbol='{options_name}', exchange='NFO', timeframe='5')")
                    options_chart_tsl = tsl.get_historical_data(tradingsymbol=options_name, exchange='NFO', timeframe="5")
                    if options_chart_tsl is None:
                         print(f"[WARNING] Failed to fetch TSL data for {options_name}. Skipping update.")
                         return name, "skip_tsl_fetch"

                    # Defensive check for required columns before ATR
                    if not all(col in options_chart_tsl.columns for col in ['high', 'low', 'close']):
                         print(f"[ERROR] Missing required columns for ATR in TSL data for {options_name}. Columns: {options_chart_tsl.columns.tolist()}")
                         return name, "skip_tsl_missing_cols"

                    options_chart_tsl['atr'] = talib.ATR(options_chart_tsl['high'], options_chart_tsl['low'],
                                                     options_chart_tsl['close'], timeperiod=14)
                    rc_options_tsl = options_chart_tsl.iloc[-1]
                    sl_points_tsl = rc_options_tsl['atr'] * atr_multipler  # Note: Use 'atr' column

                    # Fetch LTP for TSL calculation
                    ltp_api_limiter.wait(call_description=f"tsl.get_ltp_data(names=['{options_name}'])")
                    options_ltp_data_tsl = retry_api_call(tsl.get_ltp_data, retries=1, delay=1.0, names=[options_name])
                    if options_ltp_data_tsl is None or options_name not in options_ltp_data_tsl:
                         print(f"[WARNING] Failed to get LTP for {options_name} during TSL update. Skipping.")
                         return name, "skip_tsl_ltp"
                    options_ltp_tsl = options_ltp_data_tsl[options_name]

                    tsl_level = options_ltp_tsl - sl_points_tsl

                    if tsl_level > orderbook[name]['tsl']:
                        # SIMULATE: Modify order (just update in orderbook)
                        orderbook[name]['tsl'] = tsl_level
                        print(f"[PAPER][TSL] Updated TSL for {name} ({options_name}) to {tsl_level} (simulated)")
                except Exception as e:
                    print(f"[PAPER] Error updating TSL for {name}: {e}")
                    # traceback.print_exc()  # optional — you may want to keep this silent or log instead

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
# ✅ SIMULATE CANCEL ALL ORDERS (PAPER TRADING)
# ============================
def simulate_cancel_all_orders():
    """
    Simulate canceling all orders for paper trading.
    """
    print("[PAPER] Simulated cancel all orders. All positions closed at current LTP (logged in Excel).")
    # In paper, we handle closes in the loop, so this is just a log


# ============================
# ✅ MAIN LOOP (PAPER TRADING)
# ============================
while True:
    print("starting while Loop \n\n")

    current_time = datetime.datetime.now().time()
    if current_time < datetime.time(9, 15):
        print(f"Wait for market to start {current_time}")
        time.sleep(1)
        #continue
        pass

    live_pnl = tsl.get_live_pnl()  # Keep for risk check, but in paper, this might be simulated or from Excel
    max_loss_hit = live_pnl < (max_risk_for_today * -1)
    market_over = current_time > datetime.time(15, 15)

    if max_loss_hit or market_over:
        # SIMULATE: Cancel all orders and close positions at current LTP
        try:
            # Fetch LTP for all active options and close
            active_options = [order['options_name'] for order in orderbook.values() if order['traded'] == 'yes' and order['options_name']]
            if active_options:
                ltp_api_limiter.wait(call_description="tsl.get_ltp_data(names=active_options)")
                all_active_ltp = retry_api_call(tsl.get_ltp_data, retries=3, delay=1.0, names=active_options)
                for name, order in orderbook.items():
                    if order['traded'] == 'yes' and order['options_name'] in active_options:
                        if all_active_ltp and order['options_name'] in all_active_ltp:
                            exit_price = all_active_ltp[order['options_name']]
                            order['exit_price'] = exit_price
                            order['pnl'] = round((exit_price - order['entry_price']) * order['qty'], 1)
                            order['remark'] = "Market_Over_or_Max_Loss"
                            order['exit_time'] = str(current_time)[:8]
                            if reentry == "yes":
                                completed_orders.append(order.copy())
                            order['traded'] = None  # Reset
                update_excel_sheets()
            simulate_cancel_all_orders()
            print(f"[PAPER] Market over or max loss. Closing all simulated trades !! Bye Bye See you Tomorrow {current_time}")
        except Exception as e:
             print(f"[PAPER] Error during simulate_cancel_all_orders: {e}")
        # break  # optional — uncomment if you want to exit

    # ⬇️ RATE LIMITED: Non Trading API
    # --- Original LTP Fetch (Fetches for entire watchlist) ---
    ltp_api_limiter.wait(call_description="tsl.get_ltp_data(names=watchlist)")
    all_ltp_raw = retry_api_call(tsl.get_ltp_data, retries=1, delay=1.0, names=watchlist)
    # --- End Original LTP Fetch ---

    if all_ltp_raw is None:
        print("[ERROR] Failed to fetch LTP data after retries. Skipping this cycle.")
        time.sleep(5) # Wait before retrying main loop
        continue
    all_ltp = all_ltp_raw # Use the fetched data

    # Process symbols in batches of 3
    batch_size = 3 # Kept at 1 as per your original code
    for i in range(0, len(watchlist), batch_size):
        batch_symbols = watchlist[i:i + batch_size]
        print(f"Processing batch: {batch_symbols}")

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
                    print(f"Error fetching data for {name}: {e}")
                    traceback.print_exc()
                    continue

        # Then, process all fetched data concurrently
        with ThreadPoolExecutor(max_workers=batch_size) as process_executor:
            future_to_name_process = {
                process_executor.submit(process_symbol, name, chart_data[0], all_ltp): name
                for name, chart_data in fetched_data.items() if chart_data[0] is not None # Only process if chart fetched successfully
            }

            processed_count = 0
            for future in as_completed(future_to_name_process):
                try:
                    name, result = future.result()
                    processed_count += 1
                    # Optional: Print result for debugging
                    # print(f"Completed processing for {name}: {result}")
                except Exception as e:
                    name = future_to_name_process[future]
                    print(f"Error processing {name}: {e}")
                    traceback.print_exc()
                    continue

        # Update Excel sheets after each batch
        update_excel_sheets()

        # Small delay between batches to avoid overwhelming the system/API
        time.sleep(1)