"""
PE (Put Option) Entry Logic Module
===================================

This module handles the logic for entering Put Option (PE) trades,
including condition checking, indicator calculation, and order placement.
"""

import datetime
import traceback
import pandas as pd
import talib
import pandas_ta as pta
from VWAP import calculate_vwap_daily
from ATRTrailingStop import ATRTrailingStopIndicator
import Fractal_Chaos_Bands
from rate_limiter import (
    data_api_limiter,
    ntrading_api_limiter,
    order_api_limiter,
    retry_api_call
)


def check_pe_entry_conditions(chart, name, orderbook, no_of_orders_placed):
    """
    Check if PE (Put Option) entry conditions are met for the underlying stock.
    
    Args:
        chart: DataFrame with OHLCV data and indicators
        name: Stock symbol name
        orderbook: Order tracking dictionary
        no_of_orders_placed: Current number of active orders
    
    Returns:
        bool: True if all entry conditions are met, False otherwise
    """
    try:
        last = chart.iloc[-1]
        cc = chart.iloc[-2]
        
        last_close = float(last['close'])
        cc_close = float(cc['close'])
        long_stop = pd.to_numeric(cc['Long_Stop'], errors='coerce')
        fractal_low = pd.to_numeric(cc['fractal_low'], errors='coerce')
        vwap = pd.to_numeric(last['vwap'], errors='coerce')
        Crossbelow = pta.below(chart['rsi'], chart['ma_rsi'])
        
        # Sell entry conditions for underlying (which triggers PE buy)
        sc1 = cc['rsi'] < 60
        sc2 = bool(Crossbelow.iloc[-2])
        sc3 = cc_close < long_stop
        sc4 = cc_close < fractal_low
        sc5 = cc_close < vwap
        sc6 = orderbook[name]['traded'] is None
        sc7 = no_of_orders_placed < 5
        
        print(f" PE Buy Condition {name} : RSI<60={sc1} - {cc['rsi']}, CrossBelow={sc2}-{Crossbelow.iloc[-2]}, "
              f"Close<LongStop={sc3}-{long_stop}, Close<FractalLow={sc4}-{fractal_low}, Close<VWAP={sc5}-{vwap}")
        
        return sc1 and sc2 and sc3 and sc4 and sc5 and sc6 and sc7
        
    except Exception as e:
        print(f"Error checking PE entry conditions for {name}: {e}")
        traceback.print_exc()
        return False


def process_pe_option_data(tsl, pe_name):
    """
    Fetch and process PE option data with indicators.
    
    Args:
        tsl: Tradehull API client instance
        pe_name: PE option symbol name
    
    Returns:
        DataFrame: Processed option chart with indicators, or None if failed
    """
    try:
        # Fetch PE option historical data
        data_api_limiter.wait(call_description=f"tsl.get_historical_data(tradingsymbol='{pe_name}', exchange='NFO', timeframe='1')")
        options_chart = tsl.get_historical_data(tradingsymbol=pe_name, exchange='NFO', timeframe="1")
        
        if options_chart is None:
            print(f"[ERROR] Failed to fetch data for PE Option {pe_name}.")
            return None
        
        # Resample to 3-minute timeframe
        options_chart_Res = tsl.resample_timeframe(options_chart, timeframe='3T')
        
        if options_chart_Res is None or options_chart_Res.empty:
            print(f"[ERROR] Resampling failed for PE Option {pe_name}.")
            return None
        
        # Check for required columns
        required_cols = ['high', 'low', 'close', 'volume', 'timestamp']
        if not all(col in options_chart_Res.columns for col in required_cols):
            print(f"[ERROR] Missing required columns in PE Option data for {pe_name}.")
            return None
        
        # Calculate indicators
        options_chart_Res["vwap"] = calculate_vwap_daily(
            options_chart_Res["high"], options_chart_Res["low"],
            options_chart_Res["close"], options_chart_Res["volume"],
            options_chart_Res["timestamp"]
        )
        options_chart_Res['rsi'] = talib.RSI(options_chart_Res['close'], timeperiod=14)
        options_chart_Res['ma_rsi'] = talib.SMA(options_chart_Res['rsi'], timeperiod=20)
        options_chart_Res['ma'] = pta.sma(options_chart_Res['close'], timeperiod=12)
        
        # PSAR indicator
        para = pta.psar(
            high=options_chart_Res['high'],
            low=options_chart_Res['low'],
            close=options_chart_Res['close'],
            step=0.05,
            max_step=0.2,
            offset=None
        )
        options_chart_Res[['PSARl_0.02_0.2', 'PSARs_0.02_0.2', 'PSARaf_0.02_0.2', 'PSARr_0.02_0.2']] = para[
            ['PSARl_0.02_0.2', 'PSARs_0.02_0.2', 'PSARaf_0.02_0.2', 'PSARr_0.02_0.2']
        ]
        
        # ATR Trailing Stop
        atr_strategy = ATRTrailingStopIndicator(period=21, multiplier=1.0)
        result_df = atr_strategy.compute_indicator(options_chart_Res)
        options_chart_Res[['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']] = result_df[
            ['TR', 'ATR', 'Long_Stop', 'Short_Stop', 'Stop_Loss', 'Position', 'Stop_Distance']
        ]
        
        # Fractal Chaos Bands
        df_with_bands = Fractal_Chaos_Bands.fractal_chaos_bands(options_chart_Res)
        df_with_signals = Fractal_Chaos_Bands.get_fcb_signals(df_with_bands)
        options_chart_Res[['fractal_high', 'fractal_low', 'signal']] = df_with_signals[
            ['fractal_high', 'fractal_low', 'signal']
        ]
        
        return options_chart_Res
        
    except Exception as e:
        print(f"Error processing PE option data for {pe_name}: {e}")
        traceback.print_exc()
        return None


def check_pe_option_conditions(options_chart_Res, pe_name, name, orderbook, no_of_orders_placed):
    """
    Check if PE option itself meets entry conditions.
    
    Args:
        options_chart_Res: DataFrame with option data and indicators
        pe_name: PE option symbol name
        name: Underlying stock symbol
        orderbook: Order tracking dictionary
        no_of_orders_placed: Current number of active orders
    
    Returns:
        bool: True if all option entry conditions are met, False otherwise
    """
    try:
        rc_options = options_chart_Res.iloc[-1]
        rc_options_cc = options_chart_Res.iloc[-2]
        
        last_close = float(rc_options['close'])
        cc_close = float(rc_options_cc['close'])
        long_stop_opt = pd.to_numeric(rc_options['Long_Stop'], errors='coerce')
        fractal_high_opt = pd.to_numeric(rc_options['fractal_high'], errors='coerce')
        vwap_opt = pd.to_numeric(rc_options['vwap'], errors='coerce')
        Crossabove_opt = pta.above(options_chart_Res['rsi'], options_chart_Res['ma_rsi'])
        
        # Buy entry conditions for PE option (we're buying the PUT)
        bc1_opt = rc_options_cc['rsi'] > 60
        bc2_opt = bool(Crossabove_opt.iloc[-2])
        bc3_opt = cc_close > long_stop_opt
        bc4_opt = cc_close > fractal_high_opt
        bc5_opt = cc_close > vwap_opt
        bc6_opt = orderbook[name]['traded'] is None
        bc7_opt = no_of_orders_placed < 5
        
        print(f" PE Option Buy Condition {pe_name} : RSI>60={bc1_opt} - {rc_options_cc['rsi']}, CrossAbove={bc2_opt}- {Crossabove_opt.iloc[-2]}, "
              f"Close>LongStop={bc3_opt} - {long_stop_opt}, Close>FractalHigh={bc4_opt} - {fractal_high_opt}, Close>VWAP={bc5_opt} - {vwap_opt}")
        
        return bc1_opt and bc2_opt and bc3_opt and bc4_opt and bc5_opt and bc6_opt and bc7_opt
        
    except Exception as e:
        print(f"Error checking PE option conditions for {pe_name}: {e}")
        traceback.print_exc()
        return False


def place_pe_entry_order(tsl, name, pe_name, lot_size, options_chart_Res, atr_multipler, 
                         orderbook, bot_token, receiver_chat_id):
    """
    Place PE entry order with stop loss.
    
    Args:
        tsl: Tradehull API client instance
        name: Underlying stock symbol
        pe_name: PE option symbol name
        lot_size: Lot size for the option
        options_chart_Res: DataFrame with option data
        atr_multipler: ATR multiplier for stop loss
        orderbook: Order tracking dictionary
        bot_token: Telegram bot token
        receiver_chat_id: Telegram chat ID for alerts
    
    Returns:
        bool: True if order placed successfully, False otherwise
    """
    try:
        process_start_time = datetime.datetime.now()
        rc_options = options_chart_Res.iloc[-1]
        
        print(f"Placing PE entry order for {name} ({pe_name})")
        
        # Populate orderbook entry
        orderbook[name]['name'] = name
        orderbook[name]['options_name'] = pe_name
        orderbook[name]['date'] = str(process_start_time.date())
        orderbook[name]['entry_time'] = str(process_start_time.time())[:8]
        orderbook[name]['max_holding_time'] = datetime.datetime.now() + datetime.timedelta(hours=2)
        orderbook[name]['buy_sell'] = "BUY"
        orderbook[name]['qty'] = lot_size
        
        # Calculate stop loss
        sl_points = rc_options['ATR'] * atr_multipler
        
        # Place market entry order
        order_api_limiter.wait(call_description=f"tsl.order_placement(tradingsymbol='{pe_name}', BUY MARKET)")
        entry_orderid = tsl.order_placement(
            tradingsymbol=pe_name,
            exchange='NFO',
            quantity=lot_size,
            price=0,
            trigger_price=0,
            order_type='MARKET',
            transaction_type='BUY',
            trade_type='MIS'
        )
        orderbook[name]['entry_orderid'] = entry_orderid
        
        # Get executed price
        ntrading_api_limiter.wait(call_description=f"tsl.get_executed_price(orderid='{entry_orderid}')")
        exec_price = retry_api_call(tsl.get_executed_price, retries=3, delay=1.0, orderid=entry_orderid)
        
        if exec_price is None:
            raise Exception("Failed to get executed price after retries")
        
        orderbook[name]['entry_price'] = exec_price
        orderbook[name]['sl'] = round(exec_price - sl_points, 1)
        orderbook[name]['tsl'] = orderbook[name]['sl']
        
        # Place stop loss order
        price = orderbook[name]['sl'] - 0.05
        order_api_limiter.wait(call_description=f"tsl.order_placement(tradingsymbol='{pe_name}', SELL STOPLIMIT)")
        sl_orderid = tsl.order_placement(
            tradingsymbol=pe_name,
            exchange='NFO',
            quantity=lot_size,
            price=price,
            trigger_price=orderbook[name]['sl'],
            order_type='STOPLIMIT',
            transaction_type='SELL',
            trade_type='MIS'
        )
        orderbook[name]['sl_orderid'] = sl_orderid
        orderbook[name]['traded'] = "yes"

        # Send Telegram alert - Beautified
        risk = abs(orderbook[name]['entry_price'] - orderbook[name]['sl'])
        target_price = orderbook[name]['entry_price'] + (risk * 3)  # 3:1 risk-reward

        message = f"""📉 PUT OPTION ENTRY

📊 Symbol: {name}
🎯 Option: {pe_name}
📍 Strike: ATM

💵 Entry Price: ₹{orderbook[name]['entry_price']:.2f}
🔻 Stop Loss: ₹{orderbook[name]['sl']:.2f}
🎯 Target: ₹{target_price:.2f}

📦 Quantity: {orderbook[name]['qty']}
💰 Position Value: ₹{(orderbook[name]['entry_price'] * orderbook[name]['qty']):.2f}

⏰ Entry Time: {orderbook[name]['entry_time']}
📊 Direction: {orderbook[name]['buy_sell']}

🔄 Trade Type: {orderbook[name].get('trade_type', 'MIS')}
📝 Status: Position ACTIVE"""
        tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)
        
        print(f"PE entry order placed successfully for {name}")
        return True
        
    except Exception as e:
        print(f"Error placing PE entry order for {name}: {e}")
        traceback.print_exc()
        return False


def execute_pe_entry(tsl, name, chart, orderbook, no_of_orders_placed, atr_multipler,
                     bot_token, receiver_chat_id):
    """
    Main function to execute PE entry logic.
    
    Args:
        tsl: Tradehull API client instance
        name: Underlying stock symbol
        chart: DataFrame with underlying stock data
        orderbook: Order tracking dictionary
        no_of_orders_placed: Current number of active orders
        atr_multipler: ATR multiplier for stop loss
        bot_token: Telegram bot token
        receiver_chat_id: Telegram chat ID for alerts
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Check underlying entry conditions
        if not check_pe_entry_conditions(chart, name, orderbook, no_of_orders_placed):
            return False, "PE entry conditions not met for underlying"
        
        print(f"PE Sell signal detected for {name}")
        
        # Get ATM strike
        ntrading_api_limiter.wait(call_description=f"tsl.ATM_Strike_Selection(Underlying='{name}', Expiry=0)")
        atm_result = retry_api_call(tsl.ATM_Strike_Selection, retries=1, delay=1.0, Underlying=name, Expiry=0)
        
        if atm_result is None:
            return False, "Failed to get ATM strike"
        
        ce_name, pe_name, strike = atm_result
        
        # Get lot size
        ntrading_api_limiter.wait(call_description=f"tsl.get_lot_size(tradingsymbol='{pe_name}')")
        lot_size = retry_api_call(tsl.get_lot_size, retries=1, delay=1.0, tradingsymbol=pe_name)
        
        if lot_size is None:
            return False, f"Failed to get lot size for {pe_name}"
        
        # Process PE option data
        options_chart_Res = process_pe_option_data(tsl, pe_name)
        
        if options_chart_Res is None:
            return False, f"Failed to process PE option data for {pe_name}"
        
        # Check PE option conditions
        if not check_pe_option_conditions(options_chart_Res, pe_name, name, orderbook, no_of_orders_placed):
            return False, "PE option conditions not met"
        
        # Place entry order
        success = place_pe_entry_order(
            tsl, name, pe_name, lot_size, options_chart_Res,
            atr_multipler, orderbook, bot_token, receiver_chat_id
        )
        
        if success:
            return True, f"PE entry executed successfully for {name} ({pe_name})"
        else:
            return False, "Failed to place PE entry order"
        
    except Exception as e:
        error_msg = f"Error in PE entry execution for {name}: {e}"
        print(error_msg)
        traceback.print_exc()
        return False, error_msg
