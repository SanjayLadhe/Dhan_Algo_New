import pdb
import pandas as pd
import talib
from Dhan_Tradehull_V3 import Tradehull
# from ZerodhaATRTrailingStop import ATRTrailingStop
#from ATRTrailingStop_Claude import ATRTrailingStopTrading
from ATRTrailingStop import ATRTrailingStopIndicator
import Fractal_Chaos_Bands

# Configure pandas display
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

# Initialize client
client_code = "1106090196"
token_id    = "J0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzUzMjY5NDEwLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjA5MDE5NiJ9.k33WlpUurItknyrn0VRjNYIgV-eGfyLEhCrdcXXLbV3NYb7tSOvtKEW_eOswdmoPsdPd9Jo725TLv3II0-dFNw"

tsl = Tradehull(client_code, token_id)

watchlist = ["CDSL"]
timeframe = "5"

while True:
    for stock_name in watchlist:
        # Get historical data
        ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying=stock_name, Expiry=0)
        Chart_Ce_name = tsl.get_historical_data(tradingsymbol=ce_name, exchange='NFO', timeframe=timeframe)
        Chart_Pe_name = tsl.get_historical_data(tradingsymbol=pe_name, exchange='NFO', timeframe=timeframe)
        # Add technical indicators
        Chart_Ce_name['rsi'] = talib.RSI(Chart_Ce_name['close'], timeperiod=14)
        Chart_Ce_name['MA_RSI'] = talib.SMA(Chart_Ce_name['rsi'], timeperiod=24)
        Chart_Ce_name['MA(20)_Vol'] = talib.SMA(Chart_Ce_name['volume'], timeperiod=20)
        # Calculate ATR Trailing Stop
        #atr_strategy = ATRTrailingStopTrading(period=21, multiplier=1.0)
        #result_df = atr_strategy.calculate_trading_signals(Chart_Pe_name)
        atr_strategy = ATRTrailingStopIndicator(period=21,multiplier=1.0)
        result_df = atr_strategy.compute_indicator(Chart_Ce_name)
        # Extract ATR values from result_df
        # Chart_Ce_name['ATR_21'] = result_df['ATR_21']
        # Chart_Ce_name['ATR_TrailingStop_21_1'] = result_df['ATR_TrailingStop_21_1']
        # Calculate Fractal Chaos Bands
        df_with_bands = Fractal_Chaos_Bands.fractal_chaos_bands(Chart_Ce_name)
        df_with_signals = Fractal_Chaos_Bands.get_fcb_signals(df_with_bands)


        # Debug inspection
        pdb.set_trace()

        ''''# Display key columns
        print("\nAligned Data Check:")
        print("=" * 50)
        print(Chart_Ce_name[['timestamp', 'close', 'rsi', 'MA_RSI', 'ATR_21', 'ATR_TrailingStop_21_1']].tail(5))

        # Check for NaN values
        print("\nNaN Check:")
        print("=" * 50)
        print(Chart_Ce_name[['ATR_21', 'ATR_TrailingStop_21_1']].isna().sum())'''