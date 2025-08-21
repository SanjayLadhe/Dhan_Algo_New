import pdb
import time
import talib
from numpy import nan as npNaN
import pandas_ta
import bamboo_ta as bta
import pandas as pd

from fixed_zerodha_wrapper import ZerodhaWrapper
from kite_wrapper_comprehensive import KiteConnectWrapper
#from Kite_Wrapper_com_enhance import KiteConnectWrapper,LiveDataManager
import os
from kiteconnect import KiteConnect
from dotenv import load_dotenv
import logging
from kiteconnect import KiteTicker
from ATRTrailingStop import ATRTrailingStopIndicator
import Fractal_Chaos_Bands
# Configure pandas display
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)
# Load credentials from .env
load_dotenv()
API_KEY = os.getenv("API_KEY")

# Initialize Zerodha wrapper
zerodha = KiteConnectWrapper(api_key=API_KEY)

Stock_Watchlist = ['CDSL','CUMMINSIND']
Stocks_To_Trade = []

while True:
    for Stock_name in Stock_Watchlist:
        time.sleep(2)
        Token = zerodha.get_instrument_token(tradingsymbol=Stock_name, exchange="NSE")
        Chart_Price = zerodha.get_historical_data(instrument_token=Token,from_date="2025-07-21",to_date="2025-07-22",interval="3minute")
        pdb.set_trace()
        # Compute indicators
        Chart_Price['RSI'] = pandas_ta.rsi(Chart_Price['close'], timeperiod=14)
        Chart_Price['MA_RSI'] = pandas_ta.sma(Chart_Price['RSI'], timeperiod=14)
        Chart_Price['MA'] = pandas_ta.sma(Chart_Price['close'], timeperiod=12)
        para = pandas_ta.psar(high=Chart_Price['high'], low=Chart_Price['low'], close=Chart_Price['close'], step=0.05, max_step=0.2, offset=None)
        Chart_Price[['PSARl_0.02_0.2', 'PSARs_0.02_0.2', 'PSARaf_0.02_0.2', 'PSARr_0.02_0.2']] = para[['PSARl_0.02_0.2','PSARs_0.02_0.2','PSARaf_0.02_0.2','PSARr_0.02_0.2']]
        # Calculate ATR Trailing Stop
        atr_strategy = ATRTrailingStopIndicator(period=21, multiplier=1.0)
        result_df = atr_strategy.compute_indicator(Chart_Price)

        Chart_Price[['TR','ATR','Long_Stop','Short_Stop','Stop_Loss','Position','Stop_Distance']] = result_df[['TR','ATR','Long_Stop','Short_Stop','Stop_Loss','Position','Stop_Distance']]
        # Calculate Fractal Chaos Bands
        df_with_bands = Fractal_Chaos_Bands.fractal_chaos_bands(Chart_Price)
        df_with_signals = Fractal_Chaos_Bands.get_fcb_signals(df_with_bands)
        Chart_Price[['fractal_high', 'fractal_low', 'signal']] = df_with_signals[['fractal_high', 'fractal_low', 'signal']]
        pdb.set_trace()





