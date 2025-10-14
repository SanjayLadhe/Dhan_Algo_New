# -*- coding: utf-8 -*-
import sys
import io

# ============================
# FIX WINDOWS CONSOLE ENCODING
# ============================
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)


"""
Paper Trading Simulator
=======================

This module simulates the Tradehull API for paper trading.
It mocks all trading operations without placing real orders.
"""

import time
import random
import datetime
import pandas as pd
from collections import defaultdict
import paper_trading_config as pt_config


class PaperTradingSimulator:
    """
    Simulates trading operations for paper trading.
    Mocks the Tradehull API interface.
    """
    
    def __init__(self, real_tsl_instance):
        """
        Initialize paper trading simulator.
        
        Args:
            real_tsl_instance: Real Tradehull instance (used for data fetching only)
        """
        self.real_tsl = real_tsl_instance
        self.balance = pt_config.PAPER_TRADING_BALANCE
        self.order_counter = 1000
        self.orders = {}  # order_id -> order_details
        self.positions = defaultdict(dict)
        self.log_file = pt_config.PAPER_TRADING_LOG_FILE
        
        # Initialize log file
        with open(self.log_file, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Paper Trading Session Started: {datetime.datetime.now()}\n")
            f.write(f"Initial Balance: {self.balance:,.2f}\n")
            f.write(f"{'='*80}\n\n")
        
        self._log(f"Paper Trading Simulator Initialized")
    
    def _log(self, message):
        """Log message to file and optionally print"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        with open(self.log_file, 'a',encoding="utf-8") as f:
            f.write(log_entry + '\n')
        
        if pt_config.VERBOSE_LOGGING:
            print(f"[PAPER] {message}")
    
    def _generate_order_id(self):
        """Generate unique order ID"""
        order_id = f"PAPER_{self.order_counter}"
        self.order_counter += 1
        return order_id
    
    def _simulate_slippage(self, price, transaction_type):
        """
        Simulate realistic slippage on market orders.
        
        Args:
            price: Base price
            transaction_type: 'BUY' or 'SELL'
        
        Returns:
            float: Price with slippage applied
        """
        slippage_pct = price * (pt_config.SLIPPAGE_PERCENTAGE / 100)
        slippage_total = slippage_pct + pt_config.SLIPPAGE_POINTS
        
        if transaction_type == 'BUY':
            # Buy at slightly higher price
            return round(price + slippage_total, 2)
        else:
            # Sell at slightly lower price
            return round(price - slippage_total, 2)
    
    def _should_order_fail(self):
        """Check if order should fail (for testing)"""
        if not pt_config.SIMULATE_ORDER_FAILURES:
            return False
        return random.random() < pt_config.ORDER_FAILURE_RATE
    
    # ============================
    # MARKET DATA METHODS (PASS THROUGH TO REAL API)
    # ============================
    
    def get_historical_data(self, tradingsymbol, exchange, timeframe):
        """Pass through to real API for historical data"""
        return self.real_tsl.get_historical_data(
            tradingsymbol=tradingsymbol,
            exchange=exchange,
            timeframe=timeframe
        )
    
    def resample_timeframe(self, data, timeframe):
        """Pass through to real API"""
        return self.real_tsl.resample_timeframe(data, timeframe)
    
    def get_ltp_data(self, names):
        """Pass through to real API for LTP data"""
        return self.real_tsl.get_ltp_data(names)

    def get_quote_data(self, names, debug="NO"):
        """Pass through to real API for quote data (bid-ask spreads)"""
        return self.real_tsl.get_quote_data(names, debug)

    def ATM_Strike_Selection(self, Underlying, Expiry):
        """Pass through to real API"""
        return self.real_tsl.ATM_Strike_Selection(Underlying, Expiry)
    
    def get_lot_size(self, tradingsymbol):
        """Pass through to real API"""
        return self.real_tsl.get_lot_size(tradingsymbol)
    
    def get_balance(self):
        """Return paper trading balance"""
        self._log(f"Balance queried: {self.balance:,.2f}")
        return self.balance
    
    def get_live_pnl(self):
        """Calculate paper trading P&L"""
        total_pnl = 0
        # Calculate unrealized P&L from open positions
        # For now, return 0 (can be enhanced)
        return total_pnl
    
    # ============================
    # ORDER PLACEMENT (SIMULATED)
    # ============================
    
    def order_placement(self, tradingsymbol, exchange, quantity, price, 
                       trigger_price, order_type, transaction_type, trade_type):
        """
        Simulate order placement.
        
        Returns:
            str: Simulated order ID
        """
        # Check if order should fail
        if self._should_order_fail():
            self._log(f" SIMULATED FAILURE: Order for {tradingsymbol} failed")
            raise Exception(f"Paper Trading: Simulated order failure for {tradingsymbol}")
        
        # Generate order ID
        order_id = self._generate_order_id()
        
        # Simulate execution delay
        time.sleep(pt_config.ORDER_EXECUTION_DELAY)
        
        # Get current LTP for execution price
        try:
            ltp_data = self.get_ltp_data([tradingsymbol])
            current_ltp = ltp_data.get(tradingsymbol, price if price > 0 else 100)
        except:
            current_ltp = price if price > 0 else 100
        
        # Calculate executed price based on order type
        if order_type == 'MARKET':
            executed_price = self._simulate_slippage(current_ltp, transaction_type)
        elif order_type == 'LIMIT':
            executed_price = price
        elif order_type == 'STOPLIMIT':
            # For SL orders, use trigger price
            executed_price = trigger_price
        else:
            executed_price = current_ltp
        
        # Store order details
        order_details = {
            'order_id': order_id,
            'tradingsymbol': tradingsymbol,
            'exchange': exchange,
            'quantity': quantity,
            'price': price,
            'trigger_price': trigger_price,
            'order_type': order_type,
            'transaction_type': transaction_type,
            'trade_type': trade_type,
            'executed_price': executed_price,
            'status': 'TRADED' if order_type in ['MARKET', 'LIMIT'] else 'PENDING',
            'timestamp': datetime.datetime.now()
        }
        
        self.orders[order_id] = order_details
        
        # Log order
        self._log(f" ORDER PLACED: {order_type} {transaction_type} {quantity} {tradingsymbol} @ {executed_price:.2f} (Order ID: {order_id})")
        
        # Update balance for executed orders
        if order_details['status'] == 'TRADED':
            cost = executed_price * quantity
            if transaction_type == 'BUY':
                self.balance -= cost
                self._log(f"    Balance reduced: {cost:,.2f} | New Balance: {self.balance:,.2f}")
            else:
                self.balance += cost
                self._log(f"    Balance increased: {cost:,.2f} | New Balance: {self.balance:,.2f}")
        
        return order_id
    
    def get_executed_price(self, orderid):
        """
        Get executed price for an order.
        
        Args:
            orderid: Order ID
        
        Returns:
            float: Executed price or None
        """
        if orderid not in self.orders:
            self._log(f"  Order ID {orderid} not found")
            return None
        
        order = self.orders[orderid]
        executed_price = order.get('executed_price', None)
        
        self._log(f" Executed Price for {orderid}: {executed_price:.2f}")
        return executed_price
    
    def get_order_status(self, orderid):
        """
        Get order status.
        
        Args:
            orderid: Order ID
        
        Returns:
            str: Order status ('TRADED', 'PENDING', 'CANCELLED', 'REJECTED')
        """
        if orderid not in self.orders:
            self._log(f"  Order ID {orderid} not found")
            return 'REJECTED'
        
        order = self.orders[orderid]
        status = order.get('status', 'PENDING')
        
        # Simulate SL trigger for stop loss orders
        if order['order_type'] == 'STOPLIMIT' and status == 'PENDING':
            if pt_config.SL_ALWAYS_EXECUTES:
                # In paper trading, we can simulate SL trigger by checking current price
                # For now, return PENDING (will be triggered by exit logic)
                pass
        
        self._log(f" Order Status for {orderid}: {status}")
        return status
    
    def modify_order(self, order_id, order_type, quantity, price, trigger_price):
        """
        Modify an existing order (for TSL updates).
        
        Args:
            order_id: Order ID to modify
            order_type: New order type
            quantity: New quantity
            price: New price
            trigger_price: New trigger price
        """
        if order_id not in self.orders:
            self._log(f" Cannot modify - Order ID {order_id} not found")
            return False
        
        old_trigger = self.orders[order_id].get('trigger_price', 0)
        
        # Update order
        self.orders[order_id].update({
            'order_type': order_type,
            'quantity': quantity,
            'price': price,
            'trigger_price': trigger_price,
            'modified_at': datetime.datetime.now()
        })
        
        self._log(f"  ORDER MODIFIED: {order_id} | TSL: {old_trigger:.2f} → {trigger_price:.2f}")
        return True
    
    def cancel_order(self, OrderID):
        """
        Cancel an order.
        
        Args:
            OrderID: Order ID to cancel
        """
        if OrderID not in self.orders:
            self._log(f"️  Cannot cancel - Order ID {OrderID} not found")
            return False
        
        self.orders[OrderID]['status'] = 'CANCELLED'
        self._log(f" ORDER CANCELLED: {OrderID}")
        return True
    
    def cancel_all_orders(self):
        """Cancel all pending orders"""
        cancelled_count = 0
        for order_id, order in self.orders.items():
            if order['status'] == 'PENDING':
                order['status'] = 'CANCELLED'
                cancelled_count += 1
        
        self._log(f" CANCELLED ALL ORDERS: {cancelled_count} orders cancelled")
        return {'cancelled': cancelled_count}
    
    # ============================
    # TELEGRAM ALERTS - DISABLED IN THIS VERSION
    # ============================

    def send_telegram_alert(self, message, receiver_chat_id, bot_token):
        """
        Telegram alerts disabled in this version.

        Args:
            message: Alert message
            receiver_chat_id: Chat ID
            bot_token: Bot token
        """
        # Telegram functionality disabled - just log the message
        if bot_token and receiver_chat_id:
            self._log(f"📱 [Telegram Disabled] Would have sent:\n{message}\n")
        return True
    
    # ============================
    # SIMULATION METHODS FOR TESTING SL TRIGGERS
    # ============================
    
    def simulate_sl_trigger(self, order_id):
        """
        Manually trigger a stop loss order (for testing).
        
        Args:
            order_id: Order ID to trigger
        """
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if order['order_type'] == 'STOPLIMIT' and order['status'] == 'PENDING':
            # Execute the order
            order['status'] = 'TRADED'
            order['executed_price'] = order['trigger_price']
            
            # Update balance
            cost = order['executed_price'] * order['quantity']
            if order['transaction_type'] == 'BUY':
                self.balance -= cost
            else:
                self.balance += cost
            
            self._log(f" SL TRIGGERED (SIMULATED): {order_id} @ {order['executed_price']:.2f}")
            return True
        
        return False
    
    def get_paper_trading_summary(self):
        """Get summary of paper trading session"""
        total_orders = len(self.orders)
        executed_orders = sum(1 for o in self.orders.values() if o['status'] == 'TRADED')
        pending_orders = sum(1 for o in self.orders.values() if o['status'] == 'PENDING')
        
        pnl = self.balance - pt_config.PAPER_TRADING_BALANCE
        
        summary = {
            'Initial Balance': pt_config.PAPER_TRADING_BALANCE,
            'Current Balance': self.balance,
            'P&L': pnl,
            'P&L %': (pnl / pt_config.PAPER_TRADING_BALANCE) * 100,
            'Total Orders': total_orders,
            'Executed': executed_orders,
            'Pending': pending_orders
        }
        
        return summary
    
    def print_summary(self):
        """Print paper trading summary"""
        summary = self.get_paper_trading_summary()
        
        print("\n" + "="*80)
        print("PAPER TRADING SESSION SUMMARY")
        print("="*80)
        print(f"Initial Balance:  {summary['Initial Balance']:,.2f}")
        print(f"Current Balance:  {summary['Current Balance']:,.2f}")
        print(f"P&L:              {summary['P&L']:,.2f} ({summary['P&L %']:+.2f}%)")
        print(f"Total Orders:     {summary['Total Orders']}")
        print(f"  - Executed:     {summary['Executed']}")
        print(f"  - Pending:      {summary['Pending']}")
        print("="*80 + "\n")


# ============================
# USAGE EXAMPLE
# ============================

if __name__ == "__main__":
    print("Paper Trading Simulator Module")
    print("This module is meant to be imported, not run directly.")
    print("\nTo use paper trading:")
    print("1. Set PAPER_TRADING_ENABLED = True in paper_trading_config.py")
    print("2. Use PaperTradingWrapper in your main bot file")
