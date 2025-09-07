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

# Configure pandas display
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

client_code = ""
token_id = ""

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


def fetch_historical(name):
    fetch_time = datetime.datetime.now()
    #print(f"Fetching historical data for {name} {fetch_time}")
    if name == "NIFTY":
        exchange = "INDEX"
    else:
        exchange = "NSE"
    Data = tsl.get_historical_data(tradingsymbol=name, exchange=exchange, timeframe="1")
    chart = tsl.resample_timeframe(Data,timeframe="3T")
    Data = Data.reset_index()
    complete_time = datetime.datetime.now()
    #print(f"Completed fetching for {name} at {complete_time}")
    return name, chart,complete_time


def process_symbol(name, chart, all_ltp):
    """Process a single symbol for buy/sell conditions"""
    try:
        process_start_time = datetime.datetime.now()
        print(f"Scanning        {name} {process_start_time} \n")


        # Compute indicators and conditions
        chart["vwap"] =calculate_vwap_daily(chart["high"],chart["low"],chart["close"],chart["volume"],chart["timestamp"])
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

        Candle_Color_last = pta.candle_color(chart['open'],chart['close']).iloc[-1]
        Candle_Color_CC = pta.candle_color(chart['open'] ,chart['close']).iloc[-2]

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
        #print(cc)

        if bc1 and bc2 and bc3 and bc4 and bc5 and bc6 and bc7:
            print("buy ", name, "\t")

            ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying=name, Expiry=0)
            lot_size = tsl.get_lot_size(tradingsymbol=ce_name)
            options_chart = tsl.get_historical_data(tradingsymbol=ce_name, exchange='NFO', timeframe="1")
            options_chart_Res = tsl.resample_timeframe(options_chart, timeframe='3T')
            options_chart = options_chart.reset_index()

            options_chart_Res["vwap"] = calculate_vwap_daily(options_chart_Res["high"], options_chart_Res["low"], options_chart_Res["close"], options_chart_Res["volume"],options_chart_Res["timestamp"])
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
            options_chart_Res[['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']] = \
            result_df[
                ['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']]

            df_with_bands = Fractal_Chaos_Bands.fractal_chaos_bands(options_chart_Res)
            df_with_signals = Fractal_Chaos_Bands.get_fcb_signals(df_with_bands)
            options_chart_Res[['fractal_high', 'fractal_low', 'signal']] = df_with_signals[
                ['fractal_high', 'fractal_low', 'signal']]
            #options_chart['atr'] = talib.ATR(options_chart['high'], options_chart['low'], options_chart['close'],timeperiod=14)
            rc_options = options_chart_Res.iloc[-1]
            rc_options_cc = options_chart_Res.iloc[-2]

            last_close = float(rc_options['close'])
            cc_close = float(rc_options_cc['close'])
            long_stop = pd.to_numeric(cc['Long_Stop'], errors='coerce')
            fractal_high = pd.to_numeric(cc['fractal_high'], errors='coerce')
            vwap = pd.to_numeric(last['vwap'], errors='coerce')
            Crossabove = pta.above(chart['rsi'], chart['ma_rsi'])

            Candle_Color_last = pta.candle_color(chart['open'], chart['close']).iloc[-1]
            Candle_Color_CC = pta.candle_color(chart['open'], chart['close']).iloc[-2]

            # Buy entry conditions
            bc1 = rc_options_cc['rsi'] > 60
            bc2 = bool(Crossabove.iloc[-2])
            bc3 = cc_close > long_stop
            bc4 = cc_close > fractal_high
            bc5 = cc_close > vwap
            bc6 = orderbook[name]['traded'] is None
            bc7 = no_of_orders_placed < 5

            print(f" Buy Condition for ce_name {ce_name} : {bc1}, {bc2}, {bc3}, {bc4}, {bc5} : {process_start_time} \n")
            #print(rc_options_cc)

            if bc1 and bc2 and bc3 and bc4 and bc5 and bc6 and bc7:
                print("buy ce_name", ce_name, "\t")


                orderbook[name]['name'] = name
                orderbook[name]['options_name'] = ce_name

                orderbook[name]['date'] = str(process_start_time.date())
                orderbook[name]['entry_time'] = str(process_start_time.time())[:8]
                orderbook[name]['max_holding_time'] = datetime.datetime.now() + datetime.timedelta(hours=2)

                orderbook[name]['buy_sell'] = "BUY"
                sl_points = rc_options['atr'] * atr_multipler
                orderbook[name]['qty'] = lot_size

                try:
                    entry_orderid = tsl.order_placement(tradingsymbol=orderbook[name]['options_name'], exchange='NFO',
                                                    quantity=orderbook[name]['qty'], price=0, trigger_price=0,
                                                    order_type='MARKET', transaction_type='BUY', trade_type='MIS')
                    orderbook[name]['entry_orderid'] = entry_orderid
                    orderbook[name]['entry_price'] = tsl.get_executed_price(orderid=orderbook[name]['entry_orderid'])

                    orderbook[name]['sl'] = round(orderbook[name]['entry_price'] - sl_points, 1)
                    orderbook[name]['tsl'] = orderbook[name]['sl']

                    price = orderbook[name]['sl'] - 0.05

                    sl_orderid = tsl.order_placement(tradingsymbol=orderbook[name]['options_name'], exchange='NFO',
                                                 quantity=orderbook[name]['qty'], price=price,
                                                 trigger_price=orderbook[name]['sl'], order_type='STOPLIMIT',
                                                 transaction_type='SELL', trade_type='MIS')
                    orderbook[name]['sl_orderid'] = sl_orderid
                    orderbook[name]['traded'] = "yes"

                    message = "\n".join(f"'{key}': {repr(value)}" for key, value in orderbook[name].items())
                    message = f"Entry_done {name} \n\n {message}"
                    tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

                except Exception as e:
                    print(f"Error in entry order for {name}: {e}")
                    traceback.print_exc()



        if sc1 and sc2 and sc3 and sc4 and sc5 and sc6 and sc7:
            print("Sell ", name, "\t")

            ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying=name, Expiry=0)
            lot_size = tsl.get_lot_size(tradingsymbol=pe_name)
            options_chart = tsl.get_historical_data(tradingsymbol=pe_name, exchange='NFO', timeframe="1")
            options_chart_Res = tsl.resample_timeframe(options_chart,timeframe='3T')

            #options_chart['atr'] = talib.ATR(options_chart['high'], options_chart['low'], options_chart['close'],timeperiod=14)

            options_chart_Res["vwap"] = calculate_vwap_daily(options_chart_Res["high"], options_chart_Res["low"], options_chart_Res["close"], options_chart_Res["volume"],options_chart_Res["timestamp"])
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
            options_chart_Res[['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']] = \
            result_df[
                ['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']]

            df_with_bands = Fractal_Chaos_Bands.fractal_chaos_bands(options_chart_Res)
            df_with_signals = Fractal_Chaos_Bands.get_fcb_signals(df_with_bands)
            options_chart_Res[['fractal_high', 'fractal_low', 'signal']] = df_with_signals[
                ['fractal_high', 'fractal_low', 'signal']]

            rc_options = options_chart_Res.iloc[-1]
            rc_options_cc = options_chart_Res.iloc[-2]

            last_close = float(rc_options['close'])
            cc_close = float(rc_options_cc['close'])
            long_stop = pd.to_numeric(cc['Long_Stop'], errors='coerce')
            fractal_high = pd.to_numeric(cc['fractal_high'], errors='coerce')
            vwap = pd.to_numeric(last['vwap'], errors='coerce')
            Crossabove = pta.above(chart['rsi'], chart['ma_rsi'])

            Candle_Color_last = pta.candle_color(chart['open'], chart['close']).iloc[-1]
            Candle_Color_CC = pta.candle_color(chart['open'], chart['close']).iloc[-2]


            # Buy entry conditions
            bc1 = rc_options_cc['rsi'] > 60
            bc2 = bool(Crossabove.iloc[-2])
            bc3 = cc_close > long_stop
            bc4 = cc_close > fractal_high
            bc5 = cc_close > vwap
            bc6 = orderbook[name]['traded'] is None
            bc7 = no_of_orders_placed < 5

            print(f" Buy Condition for pe_name {pe_name} : {bc1}, {bc2}, {bc3}, {bc4}, {bc5} : {process_start_time} \n")
            #print(rc_options_cc)

            if bc1 and bc2 and bc3 and bc4 and bc5 and bc6 and bc7:
                print("buy pe_name", pe_name, "\t")


                orderbook[name]['name'] = name
                orderbook[name]['options_name'] = ce_name

                orderbook[name]['date'] = str(process_start_time.date())
                orderbook[name]['entry_time'] = str(process_start_time.time())[:8]
                orderbook[name]['max_holding_time'] = datetime.datetime.now() + datetime.timedelta(hours=2)

                orderbook[name]['buy_sell'] = "BUY"
                sl_points = rc_options['atr'] * atr_multipler
                orderbook[name]['qty'] = lot_size

                try:
                    entry_orderid = tsl.order_placement(tradingsymbol=orderbook[name]['options_name'], exchange='NFO',
                                                    quantity=orderbook[name]['qty'], price=0, trigger_price=0,
                                                    order_type='MARKET', transaction_type='BUY', trade_type='MIS')
                    orderbook[name]['entry_orderid'] = entry_orderid
                    orderbook[name]['entry_price'] = tsl.get_executed_price(orderid=orderbook[name]['entry_orderid'])

                    orderbook[name]['sl'] = round(orderbook[name]['entry_price'] - sl_points, 1)
                    orderbook[name]['tsl'] = orderbook[name]['sl']

                    price = orderbook[name]['sl'] - 0.05

                    sl_orderid = tsl.order_placement(tradingsymbol=orderbook[name]['options_name'], exchange='NFO',
                                                 quantity=orderbook[name]['qty'], price=price,
                                                 trigger_price=orderbook[name]['sl'], order_type='STOPLIMIT',
                                                 transaction_type='SELL', trade_type='MIS')
                    orderbook[name]['sl_orderid'] = sl_orderid
                    orderbook[name]['traded'] = "yes"

                    message = "\n".join(f"'{key}': {repr(value)}" for key, value in orderbook[name].items())
                    message = f"Entry_done {name} \n\n {message}"
                    tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

                except Exception as e:
                    print(f"Error in entry order for {name}: {e}")
                    traceback.print_exc()

        # Check exit conditions for already traded symbols
        if orderbook[name]['traded'] == "yes":
            bought = orderbook[name]['buy_sell'] == "BUY"

            if bought:
                try:
                    ltp = all_ltp[name]
                    sl_hit = tsl.get_order_status(orderid=orderbook[name]['sl_orderid']) == "TRADED"

                    holding_time_exceeded = datetime.datetime.now() > orderbook[name]['max_holding_time']
                    current_pnl = round((ltp - orderbook[name]['entry_price']) * orderbook[name]['qty'], 1)

                except Exception as e:
                    print(f"Error checking SL for {name}: {e}")
                    traceback.print_exc()

                if sl_hit:
                    try:
                        orderbook[name]['exit_time'] = str(process_start_time.time())[:8]
                        orderbook[name]['exit_price'] = tsl.get_executed_price(orderid=orderbook[name]['sl_orderid'])
                        orderbook[name]['pnl'] = round(
                            (orderbook[name]['exit_price'] - orderbook[name]['entry_price']) * orderbook[name]['qty'],
                            1)
                        orderbook[name]['remark'] = "Bought_SL_hit"

                        message = "\n".join(f"'{key}': {repr(value)}" for key, value in orderbook[name].items())
                        message = f"SL_HIT {name} \n\n {message}"
                        tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

                        if reentry == "yes":
                            completed_orders.append(orderbook[name].copy())
                            orderbook[name] = single_order.copy()

                    except Exception as e:
                        print(f"Error in SL hit processing for {name}: {e}")
                        traceback.print_exc()

                if holding_time_exceeded and (current_pnl < 0):
                    try:
                        tsl.cancel_order(OrderID=orderbook[name]['sl_orderid'])
                        time.sleep(2)
                        square_off_buy_order = tsl.order_placement(tradingsymbol=orderbook[name]['name'],
                                                                   exchange='NSE', quantity=orderbook[name]['qty'],
                                                                   price=0, trigger_price=0, order_type='MARKET',
                                                                   transaction_type='SELL', trade_type='MIS')

                        orderbook[name]['exit_time'] = str(process_start_time.time())[:8]
                        orderbook[name]['exit_price'] = tsl.get_executed_price(orderid=square_off_buy_order)
                        orderbook[name]['pnl'] = (orderbook[name]['exit_price'] - orderbook[name]['entry_price']) * \
                                                 orderbook[name]['qty']
                        orderbook[name]['remark'] = "holding_time_exceeded_and_I_am_still_facing_loss"

                        message = "\n".join(f"'{key}': {repr(value)}" for key, value in orderbook[name].items())
                        message = f"holding_time_exceeded_and_I_am_still_facing_loss {name} \n\n {message}"
                        tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

                        if reentry == "yes":
                            completed_orders.append(orderbook[name].copy())
                            orderbook[name] = single_order.copy()

                        winsound.Beep(1500, 10000)

                    except Exception as e:
                        print(f"Error in time exceeded processing for {name}: {e}")
                        traceback.print_exc()

                # TSL Update
                try:
                    options_name = orderbook[name]['options_name']
                    options_chart = tsl.get_historical_data(tradingsymbol=options_name, exchange='NFO', timeframe="5")
                    options_chart['atr'] = talib.ATR(options_chart['high'], options_chart['low'],
                                                     options_chart['close'],
                                                     timeperiod=14)
                    rc_options = options_chart.iloc[-1]
                    sl_points = rc_options['atr'] * atr_multipler
                    options_ltp = tsl.get_ltp_data(names=options_name)[options_name]
                    tsl_level = options_ltp - sl_points

                    if tsl_level > orderbook[name]['tsl']:
                        trigger_price = round(tsl_level, 1)
                        price = trigger_price - 0.05
                        tsl.modify_order(order_id=orderbook[name]['sl_orderid'], order_type="STOPLIMIT", quantity=25,
                                         price=price, trigger_price=trigger_price)
                        orderbook[name]['tsl'] = tsl_level
                except Exception as e:
                    print(f"Error updating TSL for {name}: {e}")
            # Don't traceback here as it's not critical

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


# time.sleep(4)

while True:
    print("starting while Loop \n\n")

    current_time = datetime.datetime.now().time()
    if current_time < datetime.time(9, 15):
        print(f"Wait for market to start {current_time}")
        time.sleep(1)
        continue

    live_pnl = tsl.get_live_pnl()
    max_loss_hit = live_pnl < (max_risk_for_today * -1)
    market_over = current_time > datetime.time(15, 15)

    if max_loss_hit or market_over:
        order_details = tsl.cancel_all_orders()
        print(f"Market over Closing all trades !! Bye Bye See you Tomorrow {current_time}")
        #break

    all_ltp = tsl.get_ltp_data(names=watchlist)

    # Process symbols in batches of 3
    batch_size = 1
    for i in range(0, len(watchlist), batch_size):
        batch_symbols = watchlist[i:i + batch_size]
        print(f"Processing batch: {batch_symbols}")

        # First, fetch data for all symbols in batch concurrently
        fetched_data = {}
        with ThreadPoolExecutor(max_workers=batch_size) as fetch_executor:
            # Submit fetch tasks
            future_to_name_fetch = {fetch_executor.submit(fetch_historical, name): name for name in batch_symbols}

            # Collect fetched data as they complete
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
            # Submit processing tasks for each fetched symbol
            future_to_name_process = {
                process_executor.submit(process_symbol, name, chart_data[0], all_ltp): name
                for name, chart_data in fetched_data.items()
            }

            # Wait for all processing to complete
            processed_count = 0
            for future in as_completed(future_to_name_process):
                try:
                    name, result = future.result()
                    # print(f"Completed processing for {name}: {result}")
                    processed_count += 1
                except Exception as e:
                    name = future_to_name_process[future]
                    print(f"Error processing {name}: {e}")
                    traceback.print_exc()
                    continue

        # Update Excel sheets after each batch
        update_excel_sheets()

        # Small delay between batches to avoid overwhelming the system/API
        time.sleep(1)
