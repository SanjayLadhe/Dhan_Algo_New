"""
WebSocket Manager for Real-time Market Data
============================================

This module manages WebSocket connections for real-time market data streaming.
Used for monitoring active positions with live bid/ask/LTP updates.

Features:
- Real-time LTP, Bid, Ask prices using DhanFeed WebSocket
- Market depth streaming
- Automatic reconnection
- Subscription management for active positions
"""

import asyncio
import json
import time
import traceback
from datetime import datetime
from threading import Thread, Lock
from collections import defaultdict
import pandas as pd
import os
import glob
from dhanhq import marketfeed


class WebSocketMarketData:
    """
    Manages WebSocket connection for real-time option market data using DhanFeed API.

    This provides continuous streaming of:
    - Last Traded Price (LTP)
    - Bid/Ask prices and quantities
    - Market depth (top 5 levels)
    - Volume and Open Interest
    """

    def __init__(self, client_id, access_token, instrument_file=None):
        """
        Initialize WebSocket manager with DhanFeed.

        Args:
            client_id: Dhan client ID
            access_token: Dhan access token
            instrument_file: Path to instrument master CSV file (optional, will auto-detect from Dependencies folder)
        """
        self.client_id = client_id
        self.access_token = access_token
        self.instrument_file = instrument_file or self._find_instrument_file()
        self.subscribed_instruments = {}  # {symbol: security_id}
        self.market_data = defaultdict(dict)  # {symbol: {ltp, bid, ask, ...}}
        self.lock = Lock()
        self.ws_thread = None
        self.is_running = False
        self._instrument_df = None  # Will be loaded on first use
        self.dhan_feed = None  # DhanFeed instance
        self.instruments_list = []  # List of (exchange_segment, security_id) tuples for DhanFeed

        print("✅ WebSocket Market Data Manager initialized (DhanFeed)")
        if self.instrument_file:
            print(f"   📂 Instrument file: {self.instrument_file}")

    def _find_instrument_file(self):
        """
        Auto-detect instrument CSV file from Dependencies folder.

        Returns:
            str: Path to instrument file or None if not found
        """
        try:
            # Look for Dependencies folder in current directory and parent directory
            search_paths = [
                "Dependencies",
                "./Dependencies",
                "../Dependencies",
                "../../Dependencies"
            ]

            for search_path in search_paths:
                if os.path.exists(search_path) and os.path.isdir(search_path):
                    # Search for any CSV file in Dependencies folder
                    csv_files = glob.glob(os.path.join(search_path, "*.csv"))

                    if csv_files:
                        # Prefer files with "instrument" or "scrip" in the name
                        preferred_files = [f for f in csv_files if 'instrument' in f.lower() or 'scrip' in f.lower()]

                        if preferred_files:
                            instrument_file = preferred_files[0]
                        else:
                            instrument_file = csv_files[0]

                        print(f"   🔍 Auto-detected instrument file: {instrument_file}")
                        return instrument_file

            print("   ⚠️ Could not auto-detect instrument file in Dependencies folder")
            return None

        except Exception as e:
            print(f"   ⚠️ Error finding instrument file: {e}")
            return None

    def subscribe(self, option_symbol, security_id=None):
        """
        Subscribe to real-time data for an option symbol.

        Args:
            option_symbol: Option trading symbol (e.g., "TECHM 28 OCT 1480 CALL")
            security_id: Dhan security ID (optional, will lookup if not provided)

        Returns:
            bool: True if subscription successful
        """
        try:
            with self.lock:
                if option_symbol in self.subscribed_instruments:
                    print(f"  ℹ️  Already subscribed to {option_symbol}")
                    return True

                # Get security ID if not provided
                if security_id is None:
                    # Try to get from instrument list
                    security_id = self._get_security_id(option_symbol)
                    if security_id is None:
                        print(f"  ❌ Could not find security ID for {option_symbol}")
                        return False

                self.subscribed_instruments[option_symbol] = security_id

                # Initialize market data structure
                self.market_data[option_symbol] = {
                    'ltp': 0,
                    'bid_price': 0,
                    'ask_price': 0,
                    'bid_qty': 0,
                    'ask_qty': 0,
                    'volume': 0,
                    'oi': 0,
                    'last_update': None,
                    'security_id': security_id
                }

                # Add to DhanFeed instruments list (NFO exchange for options)
                self.instruments_list.append((marketfeed.NSE_FNO, str(security_id)))

                print(f"  ✅ Subscribed to {option_symbol} (Security ID: {security_id})")

                # Restart WebSocket with updated instrument list
                if self.is_running:
                    print(f"  🔄 Restarting WebSocket with updated subscriptions...")
                    self.stop()
                    time.sleep(0.5)

                self.start()

                return True

        except Exception as e:
            print(f"  ❌ Error subscribing to {option_symbol}: {e}")
            traceback.print_exc()
            return False

    def unsubscribe(self, option_symbol):
        """
        Unsubscribe from real-time data for an option symbol.

        Args:
            option_symbol: Option trading symbol to unsubscribe

        Returns:
            bool: True if unsubscription successful
        """
        try:
            with self.lock:
                if option_symbol in self.subscribed_instruments:
                    security_id = self.subscribed_instruments[option_symbol]

                    # Remove from instruments list
                    self.instruments_list = [
                        (exch, sid) for exch, sid in self.instruments_list
                        if sid != str(security_id)
                    ]

                    del self.subscribed_instruments[option_symbol]
                    if option_symbol in self.market_data:
                        del self.market_data[option_symbol]

                    print(f"  ✅ Unsubscribed from {option_symbol}")

                    # Restart WebSocket with updated instrument list
                    if self.is_running and len(self.instruments_list) > 0:
                        print(f"  🔄 Restarting WebSocket with updated subscriptions...")
                        self.stop()
                        time.sleep(0.5)
                        self.start()
                    elif len(self.instruments_list) == 0:
                        # No more instruments, stop WebSocket
                        self.stop()

                    return True
                return False

        except Exception as e:
            print(f"  ❌ Error unsubscribing from {option_symbol}: {e}")
            return False

    def get_market_data(self, option_symbol):
        """
        Get latest market data for an option symbol.

        Args:
            option_symbol: Option trading symbol

        Returns:
            dict: Latest market data with LTP, bid, ask, depth, etc.
                  Returns None if no data available
        """
        try:
            with self.lock:
                if option_symbol not in self.market_data:
                    return None

                data = self.market_data[option_symbol].copy()

                # Return None if no valid LTP data yet
                if data.get('ltp', 0) == 0 and data.get('last_update') is None:
                    return None

                return data

        except Exception as e:
            print(f"  ❌ Error getting market data for {option_symbol}: {e}")
            return None

    def get_ltp(self, option_symbol):
        """
        Get just the LTP for an option symbol.

        Args:
            option_symbol: Option trading symbol

        Returns:
            float: Last traded price, or 0 if not available
        """
        data = self.get_market_data(option_symbol)
        return data['ltp'] if data else 0

    def get_bid_ask(self, option_symbol):
        """
        Get bid and ask prices for an option symbol.

        Args:
            option_symbol: Option trading symbol

        Returns:
            tuple: (bid_price, ask_price, bid_qty, ask_qty) or (0, 0, 0, 0) if not available
        """
        data = self.get_market_data(option_symbol)
        if data:
            return (data['bid_price'], data['ask_price'], data['bid_qty'], data['ask_qty'])
        return (0, 0, 0, 0)

    def start(self):
        """
        Start WebSocket connection in background thread.
        """
        if len(self.instruments_list) == 0:
            print("  ⚠️ No instruments to subscribe, skipping WebSocket start")
            return

        if self.is_running:
            print("  ℹ️  WebSocket already running")
            return

        self.is_running = True
        self.ws_thread = Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()
        print("  ✅ WebSocket thread started")

    def stop(self):
        """
        Stop WebSocket connection.
        """
        self.is_running = False

        # Close DhanFeed connection
        if self.dhan_feed:
            try:
                self.dhan_feed.close_connection()
            except:
                pass
            self.dhan_feed = None

        if self.ws_thread:
            self.ws_thread.join(timeout=5)

        print("  ✅ WebSocket stopped")

    def _run_websocket(self):
        """
        Run WebSocket connection (internal method).
        This runs in a background thread using DhanFeed.
        """
        try:
            print("  🔄 WebSocket connection starting with DhanFeed...")
            print(f"  📊 Subscribing to {len(self.instruments_list)} instruments")

            # Create DhanFeed instance with v2 API
            self.dhan_feed = marketfeed.DhanFeed(
                client_id=self.client_id,
                access_token=self.access_token,
                instruments=self.instruments_list,
                version='v2'
            )

            # Set callback for market data updates
            self.dhan_feed.on_ticks = self._on_market_data

            # Run WebSocket (blocking call)
            self.dhan_feed.run_forever()

        except Exception as e:
            print(f"  ❌ Fatal WebSocket error: {e}")
            traceback.print_exc()
        finally:
            self.is_running = False

    def _on_market_data(self, tick_data):
        """
        Callback for market data updates from DhanFeed.

        Args:
            tick_data: Market data packet from DhanFeed
        """
        try:
            # DhanFeed returns data in dictionary format
            # Example: {'type': 'Ticker', 'data': {...}}

            if not tick_data:
                return

            # Process based on data type
            data_type = tick_data.get('type', '')
            data = tick_data.get('data', {})

            if not data:
                return

            # Get security ID from the tick
            security_id = str(data.get('security_id', ''))

            if not security_id:
                return

            # Find the symbol for this security ID
            symbol = None
            with self.lock:
                for sym, sid in self.subscribed_instruments.items():
                    if str(sid) == security_id:
                        symbol = sym
                        break

            if not symbol:
                return

            # Update market data based on packet type
            with self.lock:
                if symbol not in self.market_data:
                    self.market_data[symbol] = {}

                # Extract LTP
                if 'LTP' in data:
                    self.market_data[symbol]['ltp'] = float(data['LTP'])

                # Extract bid/ask from depth data if available
                if 'bid' in data and isinstance(data['bid'], list) and len(data['bid']) > 0:
                    self.market_data[symbol]['bid_price'] = float(data['bid'][0].get('price', 0))
                    self.market_data[symbol]['bid_qty'] = int(data['bid'][0].get('quantity', 0))

                if 'ask' in data and isinstance(data['ask'], list) and len(data['ask']) > 0:
                    self.market_data[symbol]['ask_price'] = float(data['ask'][0].get('price', 0))
                    self.market_data[symbol]['ask_qty'] = int(data['ask'][0].get('quantity', 0))

                # Extract volume and OI
                if 'volume' in data:
                    self.market_data[symbol]['volume'] = int(data.get('volume', 0))

                if 'OI' in data:
                    self.market_data[symbol]['oi'] = int(data.get('OI', 0))

                # Update timestamp
                self.market_data[symbol]['last_update'] = datetime.now()

                # Debug: Print first update for each symbol
                if self.market_data[symbol].get('ltp', 0) > 0:
                    print(f"  📡 WebSocket Update: {symbol} LTP=₹{self.market_data[symbol]['ltp']:.2f}")

        except Exception as e:
            print(f"  ⚠️ Error processing market data: {e}")
            # Don't print full traceback for every tick to avoid spam

    def _get_security_id(self, option_symbol):
        """
        Get Dhan security ID for an option symbol.

        Args:
            option_symbol: Option trading symbol (e.g., "TECHM 28 OCT 1480 CALL")

        Returns:
            str: Security ID (SEM_SMST_SECURITY_ID) or None if not found
        """
        try:
            # Load instrument file (cached for efficiency)
            if self._instrument_df is None:
                if self.instrument_file is None:
                    print(f"  ❌ No instrument file configured")
                    return None

                if not os.path.exists(self.instrument_file):
                    print(f"  ❌ Instrument file not found: {self.instrument_file}")
                    return None

                # Cache the instrument dataframe
                self._instrument_df = pd.read_csv(self.instrument_file, low_memory=False)
                print(f"  📋 Loaded {len(self._instrument_df)} instruments from file")

            # Direct lookup using SEM_CUSTOM_SYMBOL
            result = self._instrument_df[
                self._instrument_df['SEM_CUSTOM_SYMBOL'] == option_symbol
            ]

            if not result.empty:
                security_id = result.iloc[0]['SEM_SMST_SECURITY_ID']
                print(f"  ✅ Found security ID: {security_id} for {option_symbol}")
                return str(security_id)
            else:
                print(f"  ❌ Symbol not found in instrument file: {option_symbol}")
                # Print similar symbols for debugging
                underlying = option_symbol.split()[0] if option_symbol else ""
                if underlying:
                    similar = self._instrument_df[
                        self._instrument_df['SEM_CUSTOM_SYMBOL'].str.startswith(underlying, na=False)
                    ].head(3)
                    if not similar.empty:
                        print(f"     Similar symbols found:")
                        for _, row in similar.iterrows():
                            print(f"       - {row['SEM_CUSTOM_SYMBOL']}")
                return None

        except Exception as e:
            print(f"  ⚠️ Error getting security ID: {e}")
            traceback.print_exc()
            return None


# Global WebSocket manager instance (singleton pattern)
_ws_manager = None


def get_websocket_manager(client_id=None, access_token=None):
    """
    Get or create the global WebSocket manager instance.

    Args:
        client_id: Dhan client ID (required for first call)
        access_token: Dhan access token (required for first call)

    Returns:
        WebSocketMarketData: Global WebSocket manager instance
    """
    global _ws_manager

    if _ws_manager is None:
        if client_id is None or access_token is None:
            raise ValueError("client_id and access_token required for first initialization")
        _ws_manager = WebSocketMarketData(client_id, access_token)

    return _ws_manager


def subscribe_for_position(client_id, access_token, option_symbol):
    """
    Convenience function to subscribe to market data for an active position.

    Args:
        client_id: Dhan client ID
        access_token: Dhan access token
        option_symbol: Option symbol to monitor

    Returns:
        bool: True if subscription successful
    """
    ws_manager = get_websocket_manager(client_id, access_token)
    return ws_manager.subscribe(option_symbol)


def unsubscribe_position(option_symbol):
    """
    Convenience function to unsubscribe when position is closed.

    Args:
        option_symbol: Option symbol to stop monitoring

    Returns:
        bool: True if unsubscription successful
    """
    global _ws_manager
    if _ws_manager:
        return _ws_manager.unsubscribe(option_symbol)
    return False


def get_live_market_data(option_symbol):
    """
    Get live market data for an option from WebSocket feed.

    Args:
        option_symbol: Option symbol

    Returns:
        dict: Live market data or None
    """
    global _ws_manager
    if _ws_manager:
        return _ws_manager.get_market_data(option_symbol)
    return None
