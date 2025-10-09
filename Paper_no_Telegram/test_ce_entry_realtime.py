#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-Time CE Entry Logic Test Script
=====================================

This script uses REAL market data to test CE entry logic:
- Fetches live historical data from Dhan API
- Calculates actual indicators (RSI, VWAP, ATR, Fractals, etc.)
- Tests entry conditions with real values
- No orders placed (read-only mode)

Usage:
    python test_ce_entry_realtime.py
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import traceback

# Import required modules
try:
	from Dhan_Tradehull_V3 import Tradehull
	import talib
	import pandas_ta as pta
	from VWAP import calculate_vwap_daily
	from ATRTrailingStop import ATRTrailingStopIndicator
	import Fractal_Chaos_Bands

	MODULES_AVAILABLE = True
except ImportError as e:
	print(f"⚠️  Import Error: {e}")
	print("Some modules not available. Will use fallback calculations.")
	MODULES_AVAILABLE = False


# ==========================================
# FALLBACK INDICATOR CALCULATIONS
# ==========================================

def calculate_rsi_fallback(prices, period=14):
	"""Calculate RSI if talib not available"""
	delta = prices.diff()
	gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
	loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
	rs = gain / loss
	rsi = 100 - (100 / (1 + rs))
	return rsi


def calculate_sma_fallback(prices, period=20):
	"""Calculate SMA if talib not available"""
	return prices.rolling(window=period).mean()


def calculate_vwap_fallback(high, low, close, volume):
	"""Calculate VWAP if module not available"""
	typical_price = (high + low + close) / 3
	return (typical_price * volume).cumsum() / volume.cumsum()


# ==========================================
# INDICATOR CALCULATION
# ==========================================

def calculate_all_indicators(chart_data):
	"""
	Calculate all required indicators for CE entry logic

	Args:
		chart_data: DataFrame with OHLCV data

	Returns:
		DataFrame with all indicators added
	"""
	try:
		print("\n[CALC] Calculating indicators...")
		df = chart_data.copy()

		# 1. VWAP
		print("   • VWAP...")
		try:
			if MODULES_AVAILABLE:
				df['vwap'] = calculate_vwap_daily(
					df['high'], df['low'], df['close'],
					df['volume'], df['timestamp']
				)
			else:
				df['vwap'] = calculate_vwap_fallback(
					df['high'], df['low'], df['close'], df['volume']
				)
		except Exception as e:
			print(f"     ⚠️  VWAP calculation failed: {e}")
			df['vwap'] = df['close']  # Fallback

		# 2. RSI
		print("   • RSI (14)...")
		try:
			if MODULES_AVAILABLE:
				df['rsi'] = talib.RSI(df['close'], timeperiod=14)
			else:
				df['rsi'] = calculate_rsi_fallback(df['close'], period=14)
		except Exception as e:
			print(f"     ⚠️  RSI calculation failed: {e}")
			df['rsi'] = 50.0  # Neutral fallback

		# 3. MA of RSI
		print("   • MA RSI (20)...")
		try:
			if MODULES_AVAILABLE:
				df['ma_rsi'] = talib.SMA(df['rsi'], timeperiod=20)
			else:
				df['ma_rsi'] = calculate_sma_fallback(df['rsi'], period=20)
		except Exception as e:
			print(f"     ⚠️  MA RSI calculation failed: {e}")
			df['ma_rsi'] = df['rsi']

		# 4. Moving Average
		print("   • SMA (12)...")
		try:
			if MODULES_AVAILABLE:
				df['ma'] = pta.sma(df['close'], length=12)
			else:
				df['ma'] = calculate_sma_fallback(df['close'], period=12)
		except Exception as e:
			print(f"     ⚠️  MA calculation failed: {e}")
			df['ma'] = df['close']

		# 5. PSAR (Parabolic SAR)
		print("   • PSAR...")
		try:
			if MODULES_AVAILABLE:
				para = pta.psar(
					high=df['high'],
					low=df['low'],
					close=df['close'],
					step=0.05,
					max_step=0.2
				)
				df['PSARl_0.02_0.2'] = para['PSARl_0.02_0.2']
				df['PSARs_0.02_0.2'] = para['PSARs_0.02_0.2']
				df['PSARaf_0.02_0.2'] = para['PSARaf_0.02_0.2']
				df['PSARr_0.02_0.2'] = para['PSARr_0.02_0.2']
			else:
				# Simple fallback - set to close
				df['PSARl_0.02_0.2'] = df['close'] * 0.98
				df['PSARs_0.02_0.2'] = df['close'] * 1.02
				df['PSARaf_0.02_0.2'] = 0.02
				df['PSARr_0.02_0.2'] = 0
		except Exception as e:
			print(f"     ⚠️  PSAR calculation failed: {e}")

		# 6. ATR Trailing Stop
		print("   • ATR Trailing Stop...")
		try:
			if MODULES_AVAILABLE:
				atr_strategy = ATRTrailingStopIndicator(period=21, multiplier=1.0)
				result_df = atr_strategy.compute_indicator(df)
				df['TR'] = result_df['TR']
				df['ATR'] = result_df['ATR']
				df['Long_Stop'] = result_df['Long_Stop']
				df['Short_Stop'] = result_df['Short_Stop']
				df['Stop_Loss'] = result_df['Stop_Loss']
				df['Position'] = result_df['Position']
				df['Stop_Distance'] = result_df['Stop_Distance']
			else:
				# Simple ATR fallback
				high_low = df['high'] - df['low']
				high_close = abs(df['high'] - df['close'].shift())
				low_close = abs(df['low'] - df['close'].shift())
				df['TR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
				df['ATR'] = df['TR'].rolling(window=21).mean()
				df['Long_Stop'] = df['close'] - (df['ATR'] * 1.0)
				df['Short_Stop'] = df['close'] + (df['ATR'] * 1.0)
				df['Stop_Loss'] = df['Long_Stop']
				df['Position'] = 1
				df['Stop_Distance'] = df['ATR']
		except Exception as e:
			print(f"     ⚠️  ATR calculation failed: {e}")
			df['ATR'] = df['close'] * 0.02
			df['Long_Stop'] = df['close'] * 0.98
			df['Short_Stop'] = df['close'] * 1.02

		# 7. Fractal Chaos Bands
		print("   • Fractal Chaos Bands...")
		try:
			if MODULES_AVAILABLE:
				df_with_bands = Fractal_Chaos_Bands.fractal_chaos_bands(df)
				df_with_signals = Fractal_Chaos_Bands.get_fcb_signals(df_with_bands)
				df['fractal_high'] = df_with_signals['fractal_high']
				df['fractal_low'] = df_with_signals['fractal_low']
				df['signal'] = df_with_signals['signal']
			else:
				# Simple fractal fallback - use rolling max/min
				df['fractal_high'] = df['high'].rolling(window=5, center=True).max()
				df['fractal_low'] = df['low'].rolling(window=5, center=True).min()
				df['signal'] = 0
		except Exception as e:
			print(f"     ⚠️  Fractal calculation failed: {e}")
			df['fractal_high'] = df['high'].rolling(window=5).max()
			df['fractal_low'] = df['low'].rolling(window=5).min()

		print("   ✅ All indicators calculated")
		return df

	except Exception as e:
		print(f"[ERROR] Indicator calculation failed: {e}")
		traceback.print_exc()
		return None


# ==========================================
# CE ENTRY CONDITION CHECKER
# ==========================================

def check_ce_entry_conditions_realtime(chart, name, no_of_orders_placed=0):
	"""
	Check CE entry conditions with real market data

	Args:
		chart: DataFrame with OHLCV and indicators
		name: Stock symbol
		no_of_orders_placed: Current number of orders

	Returns:
		dict with condition results and details
	"""
	try:
		print(f"\n{'=' * 80}")
		print(f"Testing CE Entry Conditions: {name}")
		print(f"{'=' * 80}")

		# Get last two candles
		last = chart.iloc[-1]
		cc = chart.iloc[-2]

		# Extract values
		last_close = float(last['close'])
		cc_close = float(last['close'])
		cc_rsi = float(last['rsi'])
		cc_ma_rsi = float(last['ma_rsi'])
		long_stop = float(last['Long_Stop'])
		fractal_high = float(last['fractal_high'])
		vwap = float(last['vwap'])

		# Print market data with both candles
		print(f"\n📊 Market Data ({name}):")
		print(f"\n   📍 CURRENT CANDLE (CC - Previous Candle Used for Conditions):")
		print(f"      Timestamp: {last['timestamp']}")
		print(f"      Open:  ₹{last['open']:.2f}")
		print(f"      High:  ₹{last['high']:.2f}")
		print(f"      Low:   ₹{last['low']:.2f}")
		print(f"      Close: ₹{last_close:.2f}")
		print(f"      Volume: {last['volume']:,.0f}")

		print(f"\n   📍 LAST CANDLE (Most Recent Candle):")
		print(f"      Timestamp: {last['timestamp']}")
		print(f"      Open:  ₹{last['open']:.2f}")
		print(f"      High:  ₹{last['high']:.2f}")
		print(f"      Low:   ₹{last['low']:.2f}")
		print(f"      Close: ₹{last_close:.2f}")
		print(f"      Volume: {last['volume']:,.0f}")

		print(f"\n   📈 Price Movement:")
		price_change = last_close - cc_close
		price_change_pct = (price_change / cc_close) * 100
		print(f"      Change: ₹{price_change:+.2f} ({price_change_pct:+.2f}%)")
		print(f"      Direction: {'🟢 UP' if price_change > 0 else '🔴 DOWN' if price_change < 0 else '⚪ FLAT'}")

		print(f"\n📈 Indicator Values:")
		print(f"   RSI: {cc_rsi:.2f}")
		print(f"   MA RSI: {cc_ma_rsi:.2f}")
		print(f"   Long Stop (ATR): ₹{long_stop:.2f}")
		print(f"   Fractal High: ₹{fractal_high:.2f}")
		print(f"   VWAP: ₹{vwap:.2f}")
		print(f"   ATR: ₹{cc['ATR']:.2f}")

		# Calculate crossabove
		try:
			if MODULES_AVAILABLE:
				Crossabove = pta.above(chart['rsi'], chart['ma_rsi'])
				crossabove = bool(Crossabove.iloc[-2])
			else:
				# Fallback: check if RSI just crossed above MA RSI
				prev_below = chart.iloc[-3]['rsi'] <= chart.iloc[-3]['ma_rsi']
				curr_above = cc['rsi'] > cc['ma_rsi']
				crossabove = prev_below and curr_above
		except:
			crossabove = cc_rsi > cc_ma_rsi

		# Check all conditions
		bc1 = cc_rsi > 60
		bc2 = crossabove
		bc3 = cc_close > long_stop
		bc4 = cc_close > fractal_high
		bc5 = cc_close > vwap
		bc6 = True  # Assume no position (read-only test)
		bc7 = no_of_orders_placed < 5

		# Print condition results
		print(f"\n✅ CE Entry Conditions:")
		print(f"   BC1: RSI > 60           : {bc1:5} (RSI={cc_rsi:.2f})")
		print(f"   BC2: RSI Cross Above    : {bc2:5} (CrossAbove={crossabove})")
		print(
			f"   BC3: Close > Long Stop  : {bc3:5} (₹{cc_close:.2f} > ₹{long_stop:.2f}, diff=₹{cc_close - long_stop:.2f})")
		print(
			f"   BC4: Close > Fractal    : {bc4:5} (₹{cc_close:.2f} > ₹{fractal_high:.2f}, diff=₹{cc_close - fractal_high:.2f})")
		print(f"   BC5: Close > VWAP       : {bc5:5} (₹{cc_close:.2f} > ₹{vwap:.2f}, diff=₹{cc_close - vwap:.2f})")
		print(f"   BC6: Not Traded         : {bc6:5}")
		print(f"   BC7: Order Limit OK     : {bc7:5} (Orders={no_of_orders_placed}/5)")

		all_conditions_met = bc1 and bc2 and bc3 and bc4 and bc5 and bc6 and bc7

		print(f"\n{'=' * 80}")
		if all_conditions_met:
			print(f"🎯 Result: ✅ ALL CONDITIONS MET - ENTRY SIGNAL GENERATED")
		else:
			print(f"🎯 Result: ❌ CONDITIONS NOT MET - NO ENTRY SIGNAL")
		print(f"{'=' * 80}")

		# Calculate potential entry details
		entry_details = None
		if all_conditions_met:
			atr_multiplier = 1.5
			sl_points = cc['ATR'] * atr_multiplier
			entry_price = last_close
			sl_price = entry_price - sl_points
			target_price = entry_price + (sl_points * 3)  # 3:1 RR

			entry_details = {
				'entry_price': entry_price,
				'sl_price': sl_price,
				'target_price': target_price,
				'risk_points': sl_points,
				'reward_points': sl_points * 3,
				'atr': cc['ATR']
			}

			print(f"\n💰 Potential Trade Setup:")
			print(f"   Entry: ₹{entry_price:.2f}")
			print(f"   Stop Loss: ₹{sl_price:.2f}")
			print(f"   Target (3:1): ₹{target_price:.2f}")
			print(f"   Risk: ₹{sl_points:.2f} per share")
			print(f"   Reward: ₹{sl_points * 3:.2f} per share")
			print(f"   Risk/Reward: 1:3")

		result = {
			'symbol': name,
			'current_candle_cc': {
				'timestamp': str(cc['timestamp']),
				'open': float(cc['open']),
				'high': float(cc['high']),
				'low': float(cc['low']),
				'close': cc_close,
				'volume': int(cc['volume'])
			},
			'last_candle': {
				'timestamp': str(last['timestamp']),
				'open': float(last['open']),
				'high': float(last['high']),
				'low': float(last['low']),
				'close': last_close,
				'volume': int(last['volume'])
			},
			'price_movement': {
				'change': float(last_close - cc_close),
				'change_percent': float((last_close - cc_close) / cc_close * 100)
			},
			'conditions': {
				'bc1_rsi_gt_60': bc1,
				'bc2_rsi_crossabove': bc2,
				'bc3_close_gt_longstop': bc3,
				'bc4_close_gt_fractal': bc4,
				'bc5_close_gt_vwap': bc5,
				'bc6_not_traded': bc6,
				'bc7_order_limit': bc7
			},
			'indicators': {
				'rsi': cc_rsi,
				'ma_rsi': cc_ma_rsi,
				'long_stop': long_stop,
				'fractal_high': fractal_high,
				'vwap': vwap,
				'atr': float(cc['ATR'])
			},
			'all_conditions_met': all_conditions_met,
			'entry_details': entry_details
		}

		return result

	except Exception as e:
		print(f"[ERROR] Condition check failed: {e}")
		traceback.print_exc()
		return None


# ==========================================
# MAIN TEST FUNCTION
# ==========================================

def test_realtime_ce_entry(tsl, stocks_to_test, save_charts=False):
	"""
	Test CE entry logic with real-time data

	Args:
		tsl: Tradehull instance
		stocks_to_test: List of stock symbols
		save_charts: Whether to save chart data to CSV

	Returns:
		List of test results
	"""
	results = []

	print("\n" + "=" * 80)
	print("REAL-TIME CE ENTRY LOGIC TEST")
	print("=" * 80)
	print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
	print(f"Stocks to Test: {', '.join(stocks_to_test)}")
	print("=" * 80)

	for stock in stocks_to_test:
		try:
			print(f"\n\n{'#' * 80}")
			print(f"# Testing: {stock}")
			print(f"{'#' * 80}")

			# 1. Fetch historical data
			print(f"\n[API] Fetching historical data for {stock}...")
			chart = tsl.get_historical_data(
				tradingsymbol=stock,
				exchange='NFO',
				timeframe='1'  # 1-minute candles
			)

			if chart is None or chart.empty:
				print(f"[ERROR] No data received for {stock}")
				continue

			print(f"[DATA] Received {len(chart)} candles")
			print(f"       Date Range: {chart['timestamp'].min()} to {chart['timestamp'].max()}")

			# 2. Resample to 3-minute timeframe
			print(f"\n[PROCESS] Resampling to 3-minute timeframe...")
			chart_3min = tsl.resample_timeframe(chart, timeframe='3T')

			if chart_3min is None or chart_3min.empty:
				print(f"[ERROR] Resampling failed for {stock}")
				continue

			print(f"[DATA] After resampling: {len(chart_3min)} candles")

			# 3. Calculate indicators
			chart_with_indicators = calculate_all_indicators(chart_3min)

			if chart_with_indicators is None:
				print(f"[ERROR] Indicator calculation failed for {stock}")
				continue

			# 4. Save chart data if requested
			if save_charts:
				filename = f"chart_data_{stock}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
				chart_with_indicators.to_csv(filename, index=False)
				print(f"\n[SAVE] Chart data saved to: {filename}")

			# 5. Check entry conditions
			result = check_ce_entry_conditions_realtime(
				chart_with_indicators,
				stock
			)

			if result:
				results.append(result)

			# 6. Get ATM strike if conditions met
			if result and result['all_conditions_met']:
				print(f"\n[API] Getting ATM strike for {stock}...")
				try:
					ce_name, pe_name, strike = tsl.ATM_Strike_Selection(
						Underlying=stock,
						Expiry=0
					)
					print(f"   CE Option: {ce_name}")
					print(f"   PE Option: {pe_name}")
					print(f"   Strike: {strike}")

					result['atm_strike'] = {
						'ce_name': ce_name,
						'pe_name': pe_name,
						'strike': strike
					}

					# Get lot size
					lot_size = tsl.get_lot_size(tradingsymbol=ce_name)
					print(f"   Lot Size: {lot_size}")

					result['atm_strike']['lot_size'] = lot_size

					# Calculate position details
					if result['entry_details']:
						entry = result['entry_details']['entry_price']
						sl = result['entry_details']['sl_price']
						target = result['entry_details']['target_price']
						risk_per_share = result['entry_details']['risk_points']

						print(f"\n📊 Full Position Details:")
						print(f"   Underlying: {stock} @ ₹{entry:.2f}")
						print(f"   Option: {ce_name}")
						print(f"   Lot Size: {lot_size}")
						print(f"   Entry: ₹{entry:.2f}")
						print(f"   Stop Loss: ₹{sl:.2f}")
						print(f"   Target: ₹{target:.2f}")
						print(f"   Risk per share: ₹{risk_per_share:.2f}")
						print(f"   Total Risk (1 lot): ₹{risk_per_share * lot_size:.2f}")
						print(f"   Target Profit (1 lot): ₹{(target - entry) * lot_size:.2f}")

				except Exception as e:
					print(f"[ERROR] Failed to get ATM strike: {e}")

			print(f"\n{'-' * 80}\n")

		except Exception as e:
			print(f"[ERROR] Test failed for {stock}: {e}")
			traceback.print_exc()
			continue

	return results


# ==========================================
# SUMMARY AND EXPORT
# ==========================================

def print_summary(results):
	"""Print summary of all test results"""

	print("\n" + "=" * 80)
	print("TEST SUMMARY")
	print("=" * 80)

	if not results:
		print("No results to display.")
		return

	print(f"\nTotal Stocks Tested: {len(results)}")

	entry_signals = [r for r in results if r['all_conditions_met']]
	no_entry = [r for r in results if not r['all_conditions_met']]

	print(f"Entry Signals: {len(entry_signals)}")
	print(f"No Entry: {len(no_entry)}")

	if entry_signals:
		print(f"\n{'=' * 80}")
		print("🎯 STOCKS WITH ENTRY SIGNALS:")
		print(f"{'=' * 80}")
		for r in entry_signals:
			print(f"\n✅ {r['symbol']}")
			print(f"   CC Candle: {r['current_candle_cc']['timestamp']}")
			print(f"   CC Close: ₹{r['current_candle_cc']['close']:.2f}")
			print(f"   Last Candle: {r['last_candle']['timestamp']}")
			print(f"   Last Close: ₹{r['last_candle']['close']:.2f}")
			print(f"   Change: ₹{r['price_movement']['change']:+.2f} ({r['price_movement']['change_percent']:+.2f}%)")
			print(f"   RSI: {r['indicators']['rsi']:.2f}")
			if r.get('entry_details'):
				ed = r['entry_details']
				print(f"   Entry: ₹{ed['entry_price']:.2f}")
				print(f"   Target: ₹{ed['target_price']:.2f}")
				print(f"   Risk: ₹{ed['risk_points']:.2f}")
			if r.get('atm_strike'):
				print(f"   Option: {r['atm_strike']['ce_name']}")

	if no_entry:
		print(f"\n{'=' * 80}")
		print("❌ STOCKS WITHOUT ENTRY SIGNALS:")
		print(f"{'=' * 80}")
		for r in no_entry:
			print(f"\n• {r['symbol']}")
			print(f"   CC Candle: {r['current_candle_cc']['timestamp']}")
			print(f"   CC Close: ₹{r['current_candle_cc']['close']:.2f}")
			print(f"   Last Close: ₹{r['last_candle']['close']:.2f}")
			print(f"   Change: ₹{r['price_movement']['change']:+.2f} ({r['price_movement']['change_percent']:+.2f}%)")
			print(f"   RSI: {r['indicators']['rsi']:.2f}")

			# Show which conditions failed
			failed = [k for k, v in r['conditions'].items() if not v]
			if failed:
				print(f"   Failed: {', '.join(failed)}")

	print(f"\n{'=' * 80}\n")


def save_results_to_json(results, filename=None):
	"""Save results to JSON file"""

	if filename is None:
		filename = f"ce_entry_realtime_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

	try:
		with open(filename, 'w') as f:
			json.dump(results, f, indent=2, default=str)
		print(f"[SAVE] Results saved to: {filename}")
		return filename
	except Exception as e:
		print(f"[ERROR] Failed to save results: {e}")
		return None


# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
	"""Main function"""

	print("\n" + "=" * 80)
	print("CE ENTRY LOGIC - REAL-TIME TEST")
	print("=" * 80)
	print("\nThis script uses REAL market data to test CE entry logic.")
	print("No orders will be placed (read-only mode).\n")

	# Configuration
	client_code = "1106090196"
	token_id = ("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzYwMDcwNDg1LCJpYXQiOjE3NTk5ODQwODUsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA2MDkwMTk2In0.XKcfhAj9zzhYe-48SzIqYdyMETwJyRrxnfI-M9X0gtzV3EenqWOvq_8jFfK9WhPguZvmacGhFba8HD7nsRFPeQ")

	# Default stocks to test
	default_stocks = ["RELIANCE", "TATASTEEL", "INFY", "SBIN", "HDFCBANK"]

	# User input
	print("Enter stock symbols to test (comma-separated)")
	print(f"Press Enter to use defaults: {', '.join(default_stocks)}")
	user_input = input("\nStocks: ").strip()

	if user_input:
		stocks_to_test = [s.strip().upper() for s in user_input.split(',')]
	else:
		stocks_to_test = default_stocks

	# Ask if user wants to save chart data
	save_charts_input = input("\nSave chart data to CSV? (y/n): ").strip().lower()
	save_charts = save_charts_input == 'y'

	# Initialize Tradehull
	print("\n[INIT] Initializing Tradehull API...")
	try:
		tsl = Tradehull(client_code, token_id)
		print("[INIT] ✅ API initialized successfully")
	except Exception as e:
		print(f"[ERROR] Failed to initialize API: {e}")
		print("\nMake sure:")
		print("1. Dhan_Tradehull_V3.py is in the same directory")
		print("2. Your credentials are correct")
		print("3. You have internet connection")
		return

	# Run tests
	try:
		results = test_realtime_ce_entry(tsl, stocks_to_test, save_charts)

		# Print summary
		print_summary(results)

		# Save results
		json_file = save_results_to_json(results)

		print("\n" + "=" * 80)
		print("TEST COMPLETE")
		print("=" * 80)
		print(f"\nResults saved to: {json_file}")
		if save_charts:
			print("Chart data saved to individual CSV files")
		print("\n")

	except KeyboardInterrupt:
		print("\n\n[STOP] Test interrupted by user")
	except Exception as e:
		print(f"\n[ERROR] Test failed: {e}")
		traceback.print_exc()


if __name__ == "__main__":
	main()