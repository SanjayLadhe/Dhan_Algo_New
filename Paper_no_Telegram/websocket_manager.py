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
        self.is_connected = False
        self._instrument_df = None  # Will be loaded on first use
        self.dhan_feed = None  # DhanFeed instance
        self.instruments_list = []  # List of (exchange_segment, security_id, subscription_mode) tuples for DhanFeed

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

    def subscribe(self, option_symbol, security_id=None, subscription_mode=None):
        """
        Subscribe to real-time data for an option symbol.

        Args:
            option_symbol: Option trading symbol (e.g., "TECHM 28 OCT 1480 CALL")
            security_id: Dhan security ID (optional, will lookup if not provided)
            subscription_mode: Data mode - marketfeed.Ticker (15), marketfeed.Quote (17), or marketfeed.Full (21)
                             Default is Full for complete data including depth

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
                    'open': 0,
                    'high': 0,
                    'low': 0,
                    'close': 0,
                    'last_update': None,
                    'security_id': security_id
                }

                # Set default subscription mode to Full (includes depth)
                if subscription_mode is None:
                    subscription_mode = marketfeed.Full

                # Add to DhanFeed instruments list (NFO exchange for options)
                self.instruments_list.append((marketfeed.NSE_FNO, str(security_id), subscription_mode))

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
                        (exch, sid, mode) for exch, sid, mode in self.instruments_list
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
        self.is_connected = False

        # Close DhanFeed connection
        if self.dhan_feed:
            try:
                # ✅ FIX: Properly close the connection and clean up pending tasks
                if hasattr(self.dhan_feed, 'close_connection'):
                    self.dhan_feed.close_connection()
                else:
                    # Fallback: try to call disconnect properly if it's async
                    import asyncio
                    try:
                        # Get the current event loop if it exists
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # If loop is running (shouldn't be in stop), create a new one
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                        except RuntimeError:
                            # No event loop, create a new one
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)

                        # Disconnect and clean up tasks
                        if hasattr(self.dhan_feed, 'disconnect'):
                            loop.run_until_complete(self.dhan_feed.disconnect())

                        # Cancel all pending tasks
                        pending = asyncio.all_tasks(loop)
                        for task in pending:
                            task.cancel()

                        # Wait for all tasks to be cancelled
                        if pending:
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

                        # Close the loop
                        loop.close()
                    except Exception as cleanup_error:
                        # Silently handle cleanup errors
                        pass
            except Exception as e:
                # Silently handle disconnect errors to avoid noise
                pass
            self.dhan_feed = None

        if self.ws_thread:
            self.ws_thread.join(timeout=5)

        print("  ✅ WebSocket stopped")

    def on_connect(self):
        """Callback when WebSocket connects."""
        self.is_connected = True
        print("  ✅ WebSocket connected successfully!")

    def on_disconnect(self):
        """Callback when WebSocket disconnects."""
        self.is_connected = False
        print("  ⚠️ WebSocket disconnected!")

    def on_ticks(self, tick_data):
        """Callback for incoming tick data."""
        self._on_market_data(tick_data)

    def _run_websocket(self):
        """
        Run WebSocket connection (internal method).
        This runs in a background thread using DhanFeed.
        """
        loop = None
        try:
            print("  🔄 WebSocket connection starting with DhanFeed...")
            print(f"  📊 Subscribing to {len(self.instruments_list)} instruments")

            # CRITICAL FIX: Create and set event loop FIRST, before creating DhanFeed
            # This fixes the "There is no current event loop in thread" error
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Now create DhanFeed instance (it will use the loop we just created)
            self.dhan_feed = marketfeed.DhanFeed(
                client_id=self.client_id,
                access_token=self.access_token,
                instruments=self.instruments_list,
                version='v2'
            )

            # IMPORTANT: DhanFeed v2 doesn't support these callbacks, but we'll handle data manually
            print("  ✅ DhanFeed instance created successfully")
            print("  🚀 Starting WebSocket connection...")

            # Run the async connection task
            loop.run_until_complete(self._async_stream())

        except Exception as e:
            print(f"  ❌ Fatal WebSocket error: {e}")
            traceback.print_exc()
        finally:
            self.is_running = False
            self.is_connected = False
            if loop and not loop.is_closed():
                try:
                    loop.close()
                except:
                    pass
            print("  🛑 WebSocket thread ended")

    async def _async_stream(self):
        """
        Async method to connect and continuously receive data.
        """
        reconnect_attempts = 0
        max_reconnect_attempts = 5

        try:
            # Connect to WebSocket
            await self.dhan_feed.connect()
            self.is_connected = True
            print("  ✅ Connected and subscribed! Listening for data...")

            # Continuously receive and process data
            while self.is_running and self.is_connected:
                try:
                    # Get data from WebSocket (this waits for incoming messages)
                    # CRITICAL: This call should be the ONLY place calling recv
                    data = await self.dhan_feed.get_instrument_data()

                    if data:
                        # Process the received data through our callback
                        self._on_market_data(data)
                        # Reset reconnect attempts on successful data reception
                        reconnect_attempts = 0

                except asyncio.CancelledError:
                    print("  ⚠️ WebSocket task cancelled")
                    break
                except Exception as e:
                    if self.is_running:  # Only show errors if we're still supposed to be running
                        print(f"  ⚠️ Error receiving data: {e}")

                        # CRITICAL FIX: Properly close the connection before reconnecting
                        try:
                            self.dhan_feed.close_connection()
                        except:
                            pass

                        self.is_connected = False
                        reconnect_attempts += 1

                        # Check if we've exceeded max reconnection attempts
                        if reconnect_attempts >= max_reconnect_attempts:
                            print(f"  ❌ Max reconnection attempts ({max_reconnect_attempts}) reached. Stopping.")
                            break

                        # Wait before reconnecting (exponential backoff)
                        backoff_delay = min(2 ** reconnect_attempts, 30)  # Cap at 30 seconds
                        await asyncio.sleep(backoff_delay)

                        if self.is_running:
                            print(f"  🔄 Attempting to reconnect... (Attempt {reconnect_attempts}/{max_reconnect_attempts})")
                            try:
                                # Create a fresh connection
                                await self.dhan_feed.connect()
                                self.is_connected = True
                                print("  ✅ Reconnected successfully!")
                            except Exception as reconnect_error:
                                print(f"  ❌ Reconnection failed: {reconnect_error}")
                                self.is_connected = False
                                # Continue loop to try again (will check reconnect_attempts)

        except Exception as e:
            print(f"  ❌ Connection error: {e}")
            traceback.print_exc()
            self.is_connected = False

    def _on_market_data(self, tick_data):
        """
        Callback for market data updates from DhanFeed.

        Args:
            tick_data: Market data packet from DhanFeed (dict format)
                      Example: {'type': 'Ticker Data', 'exchange_segment': 2,
                               'security_id': 1102757, 'LTP': '123.45', 'LTT': '10:30:45'}
        """
        try:
            if not tick_data:
                return

            # DhanFeed passes the processed dict directly from marketfeed.py
            # The 'type' field indicates the packet type
            data_type = tick_data.get('type', '')
            security_id = str(tick_data.get('security_id', ''))

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

                # Extract data based on type
                if data_type in ['Ticker Data', 'Quote Data', 'Full Data']:
                    # Extract LTP (comes as string from DhanFeed, need to convert)
                    if 'LTP' in tick_data:
                        try:
                            self.market_data[symbol]['ltp'] = float(tick_data['LTP'])
                        except (ValueError, TypeError):
                            pass

                if data_type in ['Quote Data', 'Full Data']:
                    # Extract volume and OHLC fields
                    if 'volume' in tick_data:
                        try:
                            self.market_data[symbol]['volume'] = int(tick_data['volume'])
                        except (ValueError, TypeError):
                            pass

                    if 'open' in tick_data:
                        try:
                            self.market_data[symbol]['open'] = float(tick_data['open'])
                        except (ValueError, TypeError):
                            pass

                    if 'high' in tick_data:
                        try:
                            self.market_data[symbol]['high'] = float(tick_data['high'])
                        except (ValueError, TypeError):
                            pass

                    if 'low' in tick_data:
                        try:
                            self.market_data[symbol]['low'] = float(tick_data['low'])
                        except (ValueError, TypeError):
                            pass

                    if 'close' in tick_data:
                        try:
                            self.market_data[symbol]['close'] = float(tick_data['close'])
                        except (ValueError, TypeError):
                            pass

                if data_type == 'Full Data':
                    # Extract OI
                    if 'OI' in tick_data:
                        try:
                            self.market_data[symbol]['oi'] = int(tick_data['OI'])
                        except (ValueError, TypeError):
                            pass

                    # Extract bid/ask from depth (Full packet has depth)
                    if 'depth' in tick_data and isinstance(tick_data['depth'], list) and len(tick_data['depth']) > 0:
                        try:
                            best_depth = tick_data['depth'][0]
                            self.market_data[symbol]['bid_price'] = float(best_depth.get('bid_price', 0))
                            self.market_data[symbol]['bid_qty'] = int(best_depth.get('bid_quantity', 0))
                            self.market_data[symbol]['ask_price'] = float(best_depth.get('ask_price', 0))
                            self.market_data[symbol]['ask_qty'] = int(best_depth.get('ask_quantity', 0))
                        except (ValueError, TypeError, KeyError):
                            pass

                if data_type == 'Market Depth':
                    # Extract bid/ask from depth (Market Depth packet)
                    if 'depth' in tick_data and isinstance(tick_data['depth'], list) and len(tick_data['depth']) > 0:
                        try:
                            best_depth = tick_data['depth'][0]
                            self.market_data[symbol]['bid_price'] = float(best_depth.get('bid_price', 0))
                            self.market_data[symbol]['bid_qty'] = int(best_depth.get('bid_quantity', 0))
                            self.market_data[symbol]['ask_price'] = float(best_depth.get('ask_price', 0))
                            self.market_data[symbol]['ask_qty'] = int(best_depth.get('ask_quantity', 0))
                        except (ValueError, TypeError, KeyError):
                            pass

                if data_type == 'OI Data':
                    # OI-only packet
                    if 'OI' in tick_data:
                        try:
                            self.market_data[symbol]['oi'] = int(tick_data['OI'])
                        except (ValueError, TypeError):
                            pass

                # Update timestamp
                self.market_data[symbol]['last_update'] = datetime.now()

                # Debug: Print updates (only when LTP is available)
                ltp = self.market_data[symbol].get('ltp', 0)
                if ltp > 0:
                    bid = self.market_data[symbol].get('bid_price', 0)
                    ask = self.market_data[symbol].get('ask_price', 0)
                    print(f"  📡 {symbol}: LTP=₹{ltp:.2f} Bid=₹{bid:.2f} Ask=₹{ask:.2f} [{data_type}]")

        except Exception as e:
            print(f"  ⚠️ Error processing market data: {e}")
            # Only print traceback for unexpected errors, not every tick
            if not isinstance(e, (ValueError, TypeError, KeyError)):
                traceback.print_exc()

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
