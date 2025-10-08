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
Paper Trading Wrapper
=====================

This wrapper automatically switches between real and paper trading
based on the configuration in paper_trading_config.py

Usage:
    Instead of:
        from Dhan_Tradehull_V3 import Tradehull
        tsl = Tradehull(client_code, token_id)
    
    Use:
        from paper_trading_wrapper import get_trading_instance
        tsl = get_trading_instance(client_code, token_id)
"""

import paper_trading_config as pt_config


def get_trading_instance(client_code, token_id):
    """
    Get trading instance - either real or paper trading based on config.
    
    Args:
        client_code: Dhan client code
        token_id: Dhan token ID
    
    Returns:
        Trading instance (real Tradehull or PaperTradingSimulator)
    """
    if pt_config.PAPER_TRADING_ENABLED:
        print("\n" + "="*80)
        print("🎮 PAPER TRADING MODE ENABLED")
        print("="*80)
        print("⚠️  NO REAL ORDERS WILL BE PLACED")
        print("⚠️  ALL TRADES ARE SIMULATED")
        print(f" Starting Balance: {pt_config.PAPER_TRADING_BALANCE:,.2f}")
        print(f" Logs: {pt_config.PAPER_TRADING_LOG_FILE}")
        print("="*80 + "\n")
        
        # Import real Tradehull for data fetching
        from Dhan_Tradehull_V3 import Tradehull
        real_tsl = Tradehull(client_code, token_id)
        
        # Import and create paper trading simulator
        from paper_trading_simulator import PaperTradingSimulator
        paper_tsl = PaperTradingSimulator(real_tsl)
        
        return paper_tsl
    
    else:
        print("\n" + "="*80)
        print("🔴 LIVE TRADING MODE ENABLED")
        print("="*80)
        print("⚠️  REAL ORDERS WILL BE PLACED")
        print("⚠️  REAL MONEY AT RISK")
        print("="*80 + "\n")
        
        from Dhan_Tradehull_V3 import Tradehull
        return Tradehull(client_code, token_id)


def is_paper_trading():
    """Check if paper trading is enabled"""
    return pt_config.PAPER_TRADING_ENABLED


def get_paper_trading_summary(tsl_instance):
    """
    Get paper trading summary (if applicable).
    
    Args:
        tsl_instance: Trading instance
    
    Returns:
        dict: Summary or None if not paper trading
    """
    if is_paper_trading():
        return tsl_instance.get_paper_trading_summary()
    return None


def print_paper_trading_summary(tsl_instance):
    """
    Print paper trading summary (if applicable).
    
    Args:
        tsl_instance: Trading instance
    """
    if is_paper_trading():
        tsl_instance.print_summary()
    else:
        print("Not in paper trading mode - no summary available")


# ============================
# USAGE EXAMPLE
# ============================

if __name__ == "__main__":
    print("Paper Trading Wrapper Module")
    print("\nQuick Start Guide:")
    print("-" * 80)
    print("\n1. Configure paper trading in paper_trading_config.py:")
    print("   PAPER_TRADING_ENABLED = True  # For paper trading")
    print("   PAPER_TRADING_ENABLED = False # For live trading")
    print("\n2. In your bot file, replace:")
    print("   from Dhan_Tradehull_V3 import Tradehull")
    print("   tsl = Tradehull(client_code, token_id)")
    print("\n   With:")
    print("   from paper_trading_wrapper import get_trading_instance")
    print("   tsl = get_trading_instance(client_code, token_id)")
    print("\n3. Everything else remains the same!")
    print("-" * 80)
