"""
Exit Logic Module
=================

This module handles exit conditions for active trades including:
- Stop Loss hits
- Target/Profit booking
- Trailing Stop Loss updates
- Time-based exits
- Custom exit conditions
"""

import datetime
import time
import traceback
from rate_limiter import (
    ntrading_api_limiter,
    order_api_limiter,
    retry_api_call
)


def check_sl_hit(tsl, name, orderbook):
    """
    Check if stop loss has been hit.

    Args:
        tsl: Tradehull API client
        name: Stock symbol
        orderbook: Order tracking dictionary

    Returns:
        bool: True if SL was hit
    """
    try:
        ntrading_api_limiter.wait(
            call_description=f"tsl.get_order_status(orderid='{orderbook[name]['sl_orderid']}')"
        )
        sl_status = retry_api_call(
            tsl.get_order_status,
            retries=1,
            delay=1.0,
            orderid=orderbook[name]['sl_orderid']
        )

        if sl_status is None:
            print(f"[WARNING] Failed to get order status for {name}.")
            return False

        return sl_status == "TRADED"

    except Exception as e:
        print(f"Error checking SL for {name}: {e}")
        traceback.print_exc()
        return False


def handle_sl_exit(tsl, name, orderbook, process_start_time,
                   bot_token, receiver_chat_id, reentry, completed_orders, single_order):
    """
    Handle exit when stop loss is hit.

    Args:
        tsl: Tradehull API client
        name: Stock symbol
        orderbook: Order tracking dictionary
        process_start_time: Current processing timestamp
        bot_token: Telegram bot token
        receiver_chat_id: Telegram chat ID
        reentry: Whether to allow re-entry ("yes"/"no")
        completed_orders: List of completed trades
        single_order: Template for new order

    Returns:
        bool: True if exit processed successfully
    """
    try:
        orderbook[name]['exit_time'] = str(process_start_time.time())[:8]

        # Get executed exit price
        ntrading_api_limiter.wait(
            call_description=f"tsl.get_executed_price(orderid='{orderbook[name]['sl_orderid']}')"
        )
        exit_price = retry_api_call(
            tsl.get_executed_price,
            retries=1,
            delay=1.0,
            orderid=orderbook[name]['sl_orderid']
        )

        if exit_price is None:
            print(f"[WARNING] Failed to get SL executed price for {name}. Using 0.")
            exit_price = 0

        orderbook[name]['exit_price'] = exit_price
        orderbook[name]['pnl'] = round(
            (orderbook[name]['exit_price'] - orderbook[name]['entry_price']) * orderbook[name]['qty'],
            1
        )
        orderbook[name]['remark'] = "Stop_Loss_Hit"

        # Send alert - Beautified
        pnl_emoji = "💰" if orderbook[name]['pnl'] >= 0 else "📉"
        message = f"""🛑 STOP LOSS HIT

📊 Symbol: {name}
🎯 Option: {orderbook[name].get('options_name', 'N/A')}

💵 Entry Price: ₹{orderbook[name]['entry_price']:.2f}
💵 Exit Price: ₹{orderbook[name]['exit_price']:.2f}
🔻 Stop Loss: ₹{orderbook[name]['sl']:.2f}

{pnl_emoji} P&L: ₹{orderbook[name]['pnl']:.2f}
📦 Quantity: {orderbook[name]['qty']}

⏰ Entry Time: {orderbook[name]['entry_time']}
⏰ Exit Time: {orderbook[name]['exit_time']}

📝 Remark: {orderbook[name]['remark']}"""
        tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

        print(f"✅ SL Exit processed for {name}, PnL: {orderbook[name]['pnl']}")

        # Always move to completed orders and reset orderbook
        completed_orders.append(orderbook[name].copy())
        orderbook[name] = single_order.copy()

        return True

    except Exception as e:
        print(f"Error in SL exit processing for {name}: {e}")
        traceback.print_exc()
        return False


def check_target_hit(name, orderbook, all_ltp, target_percentage=None):
    """
    Check if profit target has been reached.

    Args:
        name: Stock symbol
        orderbook: Order tracking dictionary
        all_ltp: Dictionary of current prices (must include option symbols)
        target_percentage: Target profit percentage (default from risk_reward)

    Returns:
        bool: True if target is hit
    """
    try:
        if 'entry_price' not in orderbook[name] or orderbook[name]['entry_price'] is None:
            return False

        entry_price = orderbook[name]['entry_price']
        sl = orderbook[name].get('sl', 0)

        if sl == 0:
            return False

        # Calculate risk and target
        risk_per_unit = abs(entry_price - sl)

        # Use risk_reward ratio (default 3:1)
        if target_percentage is None:
            risk_reward = 3
            target_price = entry_price + (risk_per_unit * risk_reward)
        else:
            target_price = entry_price * (1 + target_percentage / 100)

        # ✅ FIX: Get OPTION LTP, not stock LTP
        option_symbol = orderbook[name].get('options_name') or orderbook[name].get('tradingsymbol')

        if not option_symbol:
            print(f"⚠️ No option symbol found in orderbook for {name}")
            return False

        ltp = all_ltp.get(option_symbol, 0)

        # Fallback if option not in all_ltp
        if ltp == 0:
            print(f"⚠️ Option LTP not found in all_ltp for {option_symbol}")
            return False

        # Check if target reached
        target_hit = ltp >= target_price

        if target_hit:
            print(f"🎯 Target hit for {name}! Entry: {entry_price}, Target: {target_price}, Option LTP: {ltp}")

        return target_hit

    except Exception as e:
        print(f"Error checking target for {name}: {e}")
        traceback.print_exc()
        return False


def handle_target_exit(tsl, name, orderbook, process_start_time,
                       bot_token, receiver_chat_id, reentry, completed_orders, single_order):
    """
    Handle exit when profit target is reached.

    Args:
        tsl: Tradehull API client
        name: Stock symbol
        orderbook: Order tracking dictionary
        process_start_time: Current processing timestamp
        bot_token: Telegram bot token
        receiver_chat_id: Telegram chat ID
        reentry: Whether to allow re-entry
        completed_orders: List of completed trades
        single_order: Template for new order

    Returns:
        bool: True if exit processed successfully
    """
    try:
        # Cancel existing SL order
        order_api_limiter.wait(
            call_description=f"tsl.cancel_order(OrderID='{orderbook[name]['sl_orderid']}')"
        )
        tsl.cancel_order(OrderID=orderbook[name]['sl_orderid'])
        time.sleep(1)

        # Place market exit order
        order_api_limiter.wait(
            call_description=f"tsl.order_placement(tradingsymbol='{orderbook[name]['options_name']}', SELL MARKET)"
        )
        exit_orderid = tsl.order_placement(
            tradingsymbol=orderbook[name]['options_name'],
            exchange='NFO',
            quantity=orderbook[name]['qty'],
            price=0,
            trigger_price=0,
            order_type='MARKET',
            transaction_type='SELL',
            trade_type='MIS'
        )

        orderbook[name]['exit_time'] = str(process_start_time.time())[:8]

        # Get executed exit price
        ntrading_api_limiter.wait(
            call_description=f"tsl.get_executed_price(orderid='{exit_orderid}')"
        )
        exit_price = retry_api_call(
            tsl.get_executed_price,
            retries=1,
            delay=1.0,
            orderid=exit_orderid
        )

        if exit_price is None:
            print(f"[WARNING] Failed to get target exit price for {name}. Using 0.")
            exit_price = 0

        orderbook[name]['exit_price'] = exit_price
        orderbook[name]['pnl'] = round(
            (orderbook[name]['exit_price'] - orderbook[name]['entry_price']) * orderbook[name]['qty'],
            1
        )
        orderbook[name]['remark'] = "Target_Reached"

        # Send alert - Beautified
        message = f"""🎯 TARGET REACHED! 🎉

📊 Symbol: {name}
🎯 Option: {orderbook[name].get('options_name', 'N/A')}

💵 Entry Price: ₹{orderbook[name]['entry_price']:.2f}
💵 Exit Price: ₹{orderbook[name]['exit_price']:.2f}

💰 P&L: ₹{orderbook[name]['pnl']:.2f} ✅
📦 Quantity: {orderbook[name]['qty']}

⏰ Entry Time: {orderbook[name]['entry_time']}
⏰ Exit Time: {orderbook[name]['exit_time']}

📝 Remark: {orderbook[name]['remark']}"""
        tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

        print(f"✅ Target exit processed for {name}, PnL: {orderbook[name]['pnl']}")

        # Always move to completed orders and reset orderbook
        completed_orders.append(orderbook[name].copy())
        orderbook[name] = single_order.copy()

        return True

    except Exception as e:
        print(f"Error in target exit processing for {name}: {e}")
        traceback.print_exc()
        return False


def check_time_exit(name, orderbook):
    """
    Check if maximum holding time has been exceeded.

    Args:
        name: Stock symbol
        orderbook: Order tracking dictionary

    Returns:
        bool: True if time limit exceeded
    """
    try:
        if 'max_holding_time' not in orderbook[name]:
            return False

        max_holding_time = orderbook[name]['max_holding_time']
        time_exceeded = datetime.datetime.now() > max_holding_time

        if time_exceeded:
            print(f"⏰ Max holding time exceeded for {name}")

        return time_exceeded

    except Exception as e:
        print(f"Error checking time exit for {name}: {e}")
        traceback.print_exc()
        return False


def handle_time_exit(tsl, name, orderbook, process_start_time, all_ltp,
                     bot_token, receiver_chat_id, reentry, completed_orders, single_order):
    """
    Handle exit when holding time is exceeded.
    Only exits if position is in loss.

    Args:
        tsl: Tradehull API client
        name: Stock symbol
        orderbook: Order tracking dictionary
        process_start_time: Current processing timestamp
        all_ltp: Dictionary of current prices (must include option symbols)
        bot_token: Telegram bot token
        receiver_chat_id: Telegram chat ID
        reentry: Whether to allow re-entry
        completed_orders: List of completed trades
        single_order: Template for new order

    Returns:
        bool: True if exit processed successfully
    """
    try:
        # ✅ FIX: Get OPTION LTP for PnL calculation
        option_symbol = orderbook[name].get('options_name') or orderbook[name].get('tradingsymbol')

        if not option_symbol:
            print(f"⚠️ No option symbol found in orderbook for {name}")
            return False

        ltp = all_ltp.get(option_symbol, 0)

        if ltp == 0:
            print(f"⚠️ Option LTP not found for {option_symbol}. Cannot check time exit.")
            return False

        # Calculate current PnL using OPTION price
        current_pnl = round((ltp - orderbook[name]['entry_price']) * orderbook[name]['qty'], 1)

        # Only exit if in loss
        if current_pnl >= 0:
            print(f"⏰ Time exceeded for {name} but position is profitable (PnL: {current_pnl}). Not exiting.")
            return False

        print(f"⏰ Time exceeded for {name} and position is in loss (PnL: {current_pnl}). Exiting...")

        # Cancel existing SL order
        order_api_limiter.wait(
            call_description=f"tsl.cancel_order(OrderID='{orderbook[name]['sl_orderid']}')"
        )
        tsl.cancel_order(OrderID=orderbook[name]['sl_orderid'])
        time.sleep(2)

        # Place market exit order
        order_api_limiter.wait(
            call_description=f"tsl.order_placement(tradingsymbol='{orderbook[name]['options_name']}', SELL MARKET)"
        )
        exit_orderid = tsl.order_placement(
            tradingsymbol=orderbook[name]['options_name'],
            exchange='NFO',
            quantity=orderbook[name]['qty'],
            price=0,
            trigger_price=0,
            order_type='MARKET',
            transaction_type='SELL',
            trade_type='MIS'
        )

        orderbook[name]['exit_time'] = str(process_start_time.time())[:8]

        # Get executed exit price
        ntrading_api_limiter.wait(
            call_description=f"tsl.get_executed_price(orderid='{exit_orderid}')"
        )
        exit_price = retry_api_call(
            tsl.get_executed_price,
            retries=1,
            delay=1.0,
            orderid=exit_orderid
        )

        if exit_price is None:
            print(f"[WARNING] Failed to get time exit price for {name}. Using 0.")
            exit_price = 0

        orderbook[name]['exit_price'] = exit_price
        orderbook[name]['pnl'] = round(
            (orderbook[name]['exit_price'] - orderbook[name]['entry_price']) * orderbook[name]['qty'],
            1
        )
        orderbook[name]['remark'] = "Time_Exit_Loss"

        # Send alert - Beautified
        message = f"""⏰ TIME EXIT - LOSS

📊 Symbol: {name}
🎯 Option: {orderbook[name].get('options_name', 'N/A')}

💵 Entry Price: ₹{orderbook[name]['entry_price']:.2f}
💵 Exit Price: ₹{orderbook[name]['exit_price']:.2f}

📉 P&L: ₹{orderbook[name]['pnl']:.2f}
📦 Quantity: {orderbook[name]['qty']}

⏰ Entry Time: {orderbook[name]['entry_time']}
⏰ Exit Time: {orderbook[name]['exit_time']}
⌛ Reason: Max holding time exceeded

📝 Remark: {orderbook[name]['remark']}"""
        tsl.send_telegram_alert(message=message, receiver_chat_id=receiver_chat_id, bot_token=bot_token)

        print(f"✅ Time exit processed for {name}, PnL: {orderbook[name]['pnl']}")

        # Always move to completed orders and reset orderbook
        completed_orders.append(orderbook[name].copy())
        orderbook[name] = single_order.copy()

        return True

    except Exception as e:
        print(f"Error in time exit processing for {name}: {e}")
        traceback.print_exc()
        return False


def update_trailing_stop_loss(tsl, name, orderbook, atr_multipler, options_chart_3min=None):
    """
    Update trailing stop loss if price has moved favorably.
    Uses ATRTrailingStop custom indicator for ATR calculation.

    Args:
        tsl: Tradehull API client
        name: Stock symbol
        orderbook: Order tracking dictionary
        atr_multipler: ATR multiplier for stop loss calculation
        options_chart_3min: Pre-fetched 3-minute resampled data (optional, to avoid duplicate API calls)

    Returns:
        bool: True if TSL was updated
    """
    try:
        from ATRTrailingStop import ATRTrailingStopIndicator
        from rate_limiter import data_api_limiter, ltp_api_limiter

        options_name = orderbook[name].get('options_name')
        if not options_name:
            return False

        # ✅ Use pre-fetched data if available, otherwise fetch it
        options_chart_tsl_3min = options_chart_3min

        if options_chart_tsl_3min is None or options_chart_tsl_3min.empty:
            # Fetch 1-minute option data for ATR calculation
            data_api_limiter.wait(
                call_description=f"tsl.get_historical_data(tradingsymbol='{options_name}', exchange='NFO', timeframe='1')"
            )
            options_chart_tsl = tsl.get_historical_data(
                tradingsymbol=options_name,
                exchange='NFO',
                timeframe="1"
            )

            if options_chart_tsl is None or options_chart_tsl.empty:
                return False

            if not all(col in options_chart_tsl.columns for col in ['high', 'low', 'close']):
                return False

            # Set timestamp as index for resampling
            options_chart_tsl = options_chart_tsl.set_index('timestamp')

            # Resample 1-minute data to 3-minute timeframe
            options_chart_tsl_3min = options_chart_tsl.resample('3T').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()

            # Reset index for next time use
            options_chart_tsl_3min = options_chart_tsl_3min.reset_index()

        if options_chart_tsl_3min.empty:
            return False

        # ✅ Calculate ATR using ATRTrailingStop custom indicator
        atr_indicator = ATRTrailingStopIndicator(period=14, multiplier=atr_multipler)
        result_df = atr_indicator.compute_indicator(options_chart_tsl_3min)

        # Get ATR value from the result
        if 'ATR' in result_df.columns:
            rc_options_tsl = result_df.iloc[-1]
            sl_points_tsl = rc_options_tsl['ATR']
        else:
            # Fallback: calculate manually if ATR column not available
            atr_values = result_df.get('Long_Stop', options_chart_tsl_3min['close'])
            sl_points_tsl = abs(options_chart_tsl_3min['close'].iloc[-1] - atr_values.iloc[-1])

        # Get current LTP
        ltp_api_limiter.wait(
            call_description=f"tsl.get_ltp_data(names=['{options_name}'])"
        )
        options_ltp_data = retry_api_call(
            tsl.get_ltp_data,
            retries=1,
            delay=1.0,
            names=[options_name]
        )

        if options_ltp_data is None or options_name not in options_ltp_data:
            return False

        options_ltp = options_ltp_data[options_name]
        tsl_level = options_ltp - sl_points_tsl

        # Only update if new TSL is higher than current
        if tsl_level > orderbook[name]['tsl']:
            trigger_price = round(tsl_level, 1)
            price = trigger_price - 0.05
            tsl_qty = orderbook[name].get('qty', 0)

            if tsl_qty <= 0:
                return False

            # Modify SL order
            order_api_limiter.wait(
                call_description=f"tsl.modify_order(order_id='{orderbook[name]['sl_orderid']}', STOPLIMIT)"
            )
            tsl.modify_order(
                order_id=orderbook[name]['sl_orderid'],
                order_type="STOPLIMIT",
                quantity=tsl_qty,
                price=price,
                trigger_price=trigger_price
            )

            orderbook[name]['tsl'] = tsl_level
            print(f"📈 TSL updated for {name} ({options_name}) to {tsl_level}")
            return True

        return False

    except Exception as e:
        print(f"Error updating TSL for {name}: {e}")
        traceback.print_exc()
        return False


def check_rsi_longstop_exit(tsl, name, orderbook, options_chart_3min=None):
    """
    Check if exit condition met:
    - RSI closes below MA-RSI OR
    - Latest candle closes below Long_Stop

    Uses ATRTrailingStop custom indicator for Long_Stop calculation.

    Args:
        tsl: Tradehull API client
        name: Stock symbol
        orderbook: Order tracking dictionary
        options_chart_3min: Pre-fetched 3-minute resampled data (optional, to avoid duplicate API calls)

    Returns:
        tuple: (bool, str) - (condition_met, reason)
    """
    try:
        import talib
        import pandas as pd
        from ATRTrailingStop import ATRTrailingStopIndicator
        from rate_limiter import data_api_limiter

        options_name = orderbook[name].get('options_name')
        if not options_name:
            return False, "no_option_name"

        # ✅ Use pre-fetched data if available, otherwise fetch it
        if options_chart_3min is None or options_chart_3min.empty:
            # Fetch 1-minute data
            data_api_limiter.wait(
                call_description=f"tsl.get_historical_data(tradingsymbol='{options_name}', exchange='NFO', timeframe='1')"
            )
            options_chart = tsl.get_historical_data(
                tradingsymbol=options_name,
                exchange='NFO',
                timeframe="1"
            )

            if options_chart is None or options_chart.empty:
                print(f"[WARNING] Failed to fetch option data for RSI/LongStop check: {options_name}")
                return False, "data_fetch_failed"

            # Set timestamp as index for resampling
            options_chart = options_chart.set_index('timestamp')

            # Resample 1-minute data to 3-minute timeframe
            options_chart_3min = options_chart.resample('3T').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()

            # Reset index for next time use
            options_chart_3min = options_chart_3min.reset_index()

        if options_chart_3min.empty:
            print(f"[WARNING] Resampled 3-minute data is empty for {options_name}")
            return False, "resample_failed"

        # Calculate RSI and MA-RSI on 3-minute data
        options_chart_3min['rsi'] = talib.RSI(options_chart_3min['close'], timeperiod=14)
        options_chart_3min['ma_rsi'] = talib.SMA(options_chart_3min['rsi'], timeperiod=20)

        # ✅ Calculate Long_Stop using ATRTrailingStop custom indicator
        atr_strategy = ATRTrailingStopIndicator(period=21, multiplier=1.0)
        result_df = atr_strategy.compute_indicator(options_chart_3min)
        options_chart_3min['Long_Stop'] = result_df['Long_Stop']

        # Get latest candle
        latest = options_chart_3min.iloc[-1]
        previous = options_chart_3min.iloc[-2]

        latest_rsi = latest['rsi']
        latest_ma_rsi = latest['ma_rsi']
        latest_close = float(latest['close'])
        latest_long_stop = float(latest['Long_Stop'])

        # Check conditions
        rsi_below_ma = latest_rsi < latest_ma_rsi
        close_below_longstop = latest_close < latest_long_stop

        # Exit if EITHER condition is met
        if rsi_below_ma:
            print(f"🚨 Exit signal for {name} ({options_name}): RSI ({latest_rsi:.2f}) < MA-RSI ({latest_ma_rsi:.2f})")
            return True, "rsi_below_ma_rsi"

        if close_below_longstop:
            print(f"🚨 Exit signal for {name} ({options_name}): Close ({latest_close:.2f}) < Long_Stop ({latest_long_stop:.2f})")
            return True, "close_below_longstop"

        return False, "conditions_not_met"

    except Exception as e:
        print(f"Error checking RSI/LongStop exit for {name}: {e}")
        traceback.print_exc()
        return False, "error"


def handle_rsi_longstop_exit(tsl, name, orderbook, process_start_time, exit_reason,
                              bot_token, receiver_chat_id, reentry, completed_orders, single_order):
    """
    Handle exit when RSI/LongStop condition is met.

    Args:
        tsl: Tradehull API client
        name: Stock symbol
        orderbook: Order tracking dictionary
        process_start_time: Current processing timestamp
        exit_reason: Reason for exit ("rsi_below_ma_rsi" or "close_below_longstop")
        bot_token: Telegram bot token
        receiver_chat_id: Telegram chat ID
        reentry: Whether to allow re-entry
        completed_orders: List of completed trades
        single_order: Template for new order

    Returns:
        bool: True if exit processed successfully
    """
    try:
        # Cancel existing SL order
        order_api_limiter.wait(
            call_description=f"tsl.cancel_order(OrderID='{orderbook[name]['sl_orderid']}')"
        )
        tsl.cancel_order(OrderID=orderbook[name]['sl_orderid'])
        time.sleep(1)

        # Place market exit order
        order_api_limiter.wait(
            call_description=f"tsl.order_placement(tradingsymbol='{orderbook[name]['options_name']}', SELL MARKET)"
        )
        exit_orderid = tsl.order_placement(
            tradingsymbol=orderbook[name]['options_name'],
            exchange='NFO',
            quantity=orderbook[name]['qty'],
            price=0,
            trigger_price=0,
            order_type='MARKET',
            transaction_type='SELL',
            trade_type='MIS'
        )

        orderbook[name]['exit_time'] = str(process_start_time.time())[:8]

        # Get executed exit price
        ntrading_api_limiter.wait(
            call_description=f"tsl.get_executed_price(orderid='{exit_orderid}')"
        )
        exit_price = retry_api_call(
            tsl.get_executed_price,
            retries=1,
            delay=1.0,
            orderid=exit_orderid
        )

        if exit_price is None:
            print(f"[WARNING] Failed to get exit price for {name}. Using 0.")
            exit_price = 0

        orderbook[name]['exit_price'] = exit_price
        orderbook[name]['pnl'] = round(
            (orderbook[name]['exit_price'] - orderbook[name]['entry_price']) * orderbook[name]['qty'],
            1
        )

        # Set remark based on exit reason
        if exit_reason == "rsi_below_ma_rsi":
            orderbook[name]['remark'] = "RSI_Below_MA_Exit"
            reason_text = "RSI crossed below MA-RSI"
            reason_emoji = "📊"
        else:
            orderbook[name]['remark'] = "Close_Below_LongStop_Exit"
            reason_text = "Close below Long_Stop"
            reason_emoji = "📉"

        # Send Telegram alert - Beautified
        pnl_emoji = "💰" if orderbook[name]['pnl'] >= 0 else "📉"
        message = f"""{reason_emoji} TECHNICAL EXIT

📊 Symbol: {name}
🎯 Option: {orderbook[name].get('options_name', 'N/A')}

💵 Entry Price: ₹{orderbook[name]['entry_price']:.2f}
💵 Exit Price: ₹{orderbook[name]['exit_price']:.2f}

{pnl_emoji} P&L: ₹{orderbook[name]['pnl']:.2f}
📦 Quantity: {orderbook[name]['qty']}

⏰ Entry Time: {orderbook[name]['entry_time']}
⏰ Exit Time: {orderbook[name]['exit_time']}

⚠️ Exit Reason: {reason_text}
📝 Remark: {orderbook[name]['remark']}"""
        tsl.send_telegram_alert(message=message,receiver_chat_id=receiver_chat_id,bot_token=bot_token)

        print(f"✅ Technical exit processed for {name}: {reason_text}, PnL: {orderbook[name]['pnl']}")

        # Always move to completed orders and reset orderbook
        completed_orders.append(orderbook[name].copy())
        orderbook[name] = single_order.copy()

        return True

    except Exception as e:
        print(f"Error in RSI/LongStop exit processing for {name}: {e}")
        traceback.print_exc()
        return False


def process_exit_conditions(tsl, name, orderbook, all_ltp, process_start_time,
                            atr_multipler, bot_token, receiver_chat_id,
                            reentry, completed_orders, single_order, risk_reward=3):
    """
    Main function to check and process all exit conditions for a trade.

    Exit priority:
    1. Stop Loss (highest priority)
    2. Target Hit
    3. RSI/LongStop Technical Exit (CUSTOM)
    4. Time Exit (if in loss)
    5. Update TSL (if none of above)

    Args:
        tsl: Tradehull API client
        name: Stock symbol
        orderbook: Order tracking dictionary
        all_ltp: Dictionary of current prices (MUST include option symbols)
        process_start_time: Current processing timestamp
        atr_multipler: ATR multiplier for stop loss
        bot_token: Telegram bot token
        receiver_chat_id: Telegram chat ID
        reentry: Whether to allow re-entry
        completed_orders: List of completed trades
        single_order: Template for new order
        risk_reward: Risk-reward ratio for target calculation

    Returns:
        str: Exit status ("sl_hit", "target_hit", "rsi_exit", "time_exit", "tsl_updated", "no_exit")
    """
    try:
        from rate_limiter import data_api_limiter

        # Only process if trade is active
        if orderbook[name].get('traded') != "yes":
            return "no_active_trade"

        # Check if it's a BUY position
        if orderbook[name].get('buy_sell') != "BUY":
            return "not_buy_position"

        # Priority 1: Check Stop Loss (HIGHEST PRIORITY)
        if check_sl_hit(tsl, name, orderbook):
            if handle_sl_exit(tsl, name, orderbook, process_start_time,
                             bot_token, receiver_chat_id, reentry, completed_orders, single_order):
                return "sl_hit"

        # Priority 2: Check Target
        if check_target_hit(name, orderbook, all_ltp):
            if handle_target_exit(tsl, name, orderbook, process_start_time,
                                 bot_token, receiver_chat_id, reentry, completed_orders, single_order):
                return "target_hit"

        # ✅ OPTIMIZATION: Fetch option historical data ONCE, resample to 3min, and reuse for both functions
        options_name = orderbook[name].get('options_name')
        options_chart_3min = None

        if options_name:
            # Fetch 1-minute data
            data_api_limiter.wait(
                call_description=f"tsl.get_historical_data(tradingsymbol='{options_name}', exchange='NFO', timeframe='1')"
            )
            options_chart_1min = tsl.get_historical_data(
                tradingsymbol=options_name,
                exchange='NFO',
                timeframe="1"
            )

            # Resample to 3-minute if data is available
            if options_chart_1min is not None and not options_chart_1min.empty:
                # Set timestamp as index
                options_chart_1min = options_chart_1min.set_index('timestamp')

                # Resample to 3-minute
                options_chart_3min = options_chart_1min.resample('3T').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()

                # Reset index for further use
                options_chart_3min = options_chart_3min.reset_index()

        # Priority 3: Check RSI/LongStop Technical Exit (CUSTOM CONDITION)
        # Pass pre-fetched 3-min data to avoid duplicate API call
        condition_met, exit_reason = check_rsi_longstop_exit(tsl, name, orderbook, options_chart_3min)
        if condition_met:
            if handle_rsi_longstop_exit(tsl, name, orderbook, process_start_time, exit_reason,
                                       bot_token, receiver_chat_id, reentry, completed_orders, single_order):
                return "rsi_longstop_exit"

        # Priority 4: Check Time Exit
        if check_time_exit(name, orderbook):
            if handle_time_exit(tsl, name, orderbook, process_start_time, all_ltp,
                               bot_token, receiver_chat_id, reentry, completed_orders, single_order):
                return "time_exit"

        # Priority 5: Update TSL
        # Pass pre-fetched 3-min data to avoid duplicate API call
        if update_trailing_stop_loss(tsl, name, orderbook, atr_multipler, options_chart_3min):
            return "tsl_updated"

        return "no_exit"

    except Exception as e:
        print(f"Error in exit conditions processing for {name}: {e}")
        traceback.print_exc()
        return "error"