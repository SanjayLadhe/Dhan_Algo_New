import pdb
import bamboo_ta as bta
import pandas as pd
import talib
import time
import datetime
from Dhan_Tradehull_V3 import Tradehull
#from ATRTrailingStopIndicator import ATRTrailingStop
from ATRTrailingStop import  ATRTrailingStopIndicator
pd.set_option('display.max_rows', None)       # Show all rows
pd.set_option('display.max_columns', None)    # Show all columns
pd.set_option('display.width', None)          # Don't break into multiple lines
pd.set_option('display.expand_frame_repr', False)  # Disable wrapping

client_code = "1106090196"
token_id    = "J0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU4MzYxNDQ5LCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjA5MDE5NiJ9.kwmV2Nt5zzkChEaKLoHtT9oQLYvwTPa8sUf_LUgpWWx0zJKwrBHcCbiCmHXVnYBEAU9LXZ2YcTqDlJc0dROFVw"
tsl = Tradehull(client_code, token_id)

available_balance = tsl.get_balance()
leveraged_margin = available_balance * 5
max_trades = 3
per_trade_margin = leveraged_margin / max_trades
max_loss = (available_balance * 3) / 100 * -1

watchlist = ["CDSL"]  # test with 1 stock first
traded_watchlist = []

while True:
    live_pnl = tsl.get_live_pnl()
    current_time = datetime.datetime.now().time()

    for stock_name in watchlist:
        time.sleep(1)
        ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying=stock_name, Expiry=0)
        Chart_Ce_name = tsl.get_historical_data(tradingsymbol=ce_name, exchange='NFO', timeframe="5")
        Chart_Pe_name = tsl.get_historical_data(tradingsymbol=pe_name, exchange='NFO', timeframe="5")
        # Compute indicators
        Chart_Ce_name['rsi'] = talib.RSI(Chart_Ce_name['close'], timeperiod=14)
        Chart_Ce_name['MA_RSI'] = talib.SMA(Chart_Ce_name['rsi'], timeperiod=24)
        #Chart_Ce_name['ATR_21'] = bta.average_true_range(Chart_Ce_name, period=21)
        Chart_Pe_name['rsi'] = talib.RSI(Chart_Pe_name['close'], timeperiod=14)
        Chart_Pe_name['MA_RSI'] = talib.SMA(Chart_Pe_name['rsi'], timeperiod=24)
        # Fill signal with 0 (or implement logic for real signals)
        cc_1 = Chart_Ce_name.iloc[-2]
        cross_over = cc_1['rsi'] > cc_1['MA_RSI']
        cc_2 = Chart_Pe_name.iloc[-2]
        cross_over2 = cc_2['rsi'] > cc_2['MA_RSI']

        atr_strategy = ATRTrailingStopIndicator(period=21, multiplier=1.0)
        result_df = atr_strategy.compute_indicator(Chart_Ce_name)

        Chart_Ce_name[['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']] = result_df[['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']]
        pdb.set_trace()
        #Chart_Ce_name.reset_index(drop=True, inplace=True)

        # Apply ATR SL/TP logic
        #Strategy = ATRS.KiteATRTrailingStopSquarewave(period=21, multiplier=1)
        pdb.set_trace()  # Inspect full result here

        # Use your values as needed
        print(Chart_Ce_name[['rsi', 'MA_RSI', 'ATR_21', 'signal']].tail())