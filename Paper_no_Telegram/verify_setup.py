# -*- coding: utf-8 -*-
"""
Paper Trading Setup Verification & Diagnostics
==============================================

Run this script to verify your paper trading setup is correct.
"""

import os
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

# Safe print function that handles encoding errors
def safe_print(text):
    """Print text with encoding error handling"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace problematic characters with ASCII equivalents
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text)


def check_file_exists(filename, description):
    """Check if a required file exists"""
    exists = os.path.exists(filename)
    status = "[OK]" if exists else "[X]"
    safe_print(f"{status} {description}: {filename}")
    return exists


def check_import(module_name, description):
    """Check if a module can be imported"""
    try:
        __import__(module_name)
        safe_print(f"[OK] {description}: {module_name}")
        return True
    except ImportError as e:
        safe_print(f"[X] {description}: {module_name}")
        safe_print(f"   Error: {e}")
        return False


def check_config():
    """Check paper trading configuration"""
    try:
        import paper_trading_config as pt_config
        
        safe_print("\n[CONFIG] PAPER TRADING CONFIGURATION:")
        safe_print("=" * 80)
        safe_print(f"   PAPER_TRADING_ENABLED:     {pt_config.PAPER_TRADING_ENABLED}")
        safe_print(f"   PAPER_TRADING_BALANCE:     Rs.{pt_config.PAPER_TRADING_BALANCE:,.2f}")
        safe_print(f"   SLIPPAGE_PERCENTAGE:       {pt_config.SLIPPAGE_PERCENTAGE}%")
        safe_print(f"   SLIPPAGE_POINTS:           {pt_config.SLIPPAGE_POINTS}")
        safe_print(f"   ORDER_EXECUTION_DELAY:     {pt_config.ORDER_EXECUTION_DELAY}s")
        safe_print(f"   VERBOSE_LOGGING:           {pt_config.VERBOSE_LOGGING}")
        safe_print(f"   LOG FILE:                  {pt_config.PAPER_TRADING_LOG_FILE}")
        
        if pt_config.PAPER_TRADING_ENABLED:
            safe_print("\n   [PAPER] Paper Trading is ENABLED - Safe mode")
        else:
            safe_print("\n   [LIVE] Live Trading is ENABLED - Real money at risk!")
        
        return True
    except Exception as e:
        safe_print(f"\n[X] Error reading configuration: {e}")
        return False


def verify_bot_modifications():
    """Check if bot file has been modified correctly"""
    safe_print("\n[CHECK] CHECKING BOT FILE MODIFICATIONS:")
    safe_print("=" * 80)
    
    if not os.path.exists('single_trade_focus_bot.py'):
        safe_print("[X] single_trade_focus_bot.py not found in current directory")
        return False
    
    try:
        # Try UTF-8 first (most common)
        with open('single_trade_focus_bot.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            # Try latin-1 as fallback
            with open('single_trade_focus_bot.py', 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception as e:
            safe_print(f"[X] Error reading file (encoding issue): {e}")
            safe_print("\n[TIP] Try saving single_trade_focus_bot.py with UTF-8 encoding")
            return False
    except Exception as e:
        safe_print(f"[X] Error reading file: {e}")
        return False
    
    # Check for wrapper import
    has_wrapper_import = 'from paper_trading_wrapper import get_trading_instance' in content
    has_old_import = 'from Dhan_Tradehull_V3 import Tradehull' in content and \
                    '# from Dhan_Tradehull_V3 import Tradehull' not in content
    
    # Check for get_trading_instance usage
    has_get_trading_instance = 'tsl = get_trading_instance(client_code, token_id)' in content
    has_old_tradehull = 'tsl = Tradehull(client_code, token_id)' in content and \
                        '# tsl = Tradehull(client_code, token_id)' not in content
    
    safe_print(f"{'[OK]' if has_wrapper_import else '[X]'} Wrapper import found: "
          f"from paper_trading_wrapper import get_trading_instance")
    
    safe_print(f"{'[OK]' if not has_old_import else '[WARN]'} Old Tradehull import {'commented out or removed' if not has_old_import else 'STILL ACTIVE'}")
    
    safe_print(f"{'[OK]' if has_get_trading_instance else '[X]'} Using get_trading_instance: "
          f"tsl = get_trading_instance(...)")
    
    safe_print(f"{'[OK]' if not has_old_tradehull else '[WARN]'} Old Tradehull initialization "
          f"{'commented out or removed' if not has_old_tradehull else 'STILL ACTIVE'}")
    
    if has_wrapper_import and has_get_trading_instance and not has_old_tradehull:
        safe_print("\n[OK] Bot modifications look correct!")
        return True
    else:
        safe_print("\n[X] Bot modifications incomplete or incorrect")
        safe_print("\nRequired changes:")
        if not has_wrapper_import:
            safe_print("   1. Add: from paper_trading_wrapper import get_trading_instance")
        if has_old_import:
            safe_print("   2. Comment out or remove: from Dhan_Tradehull_V3 import Tradehull")
        if not has_get_trading_instance:
            safe_print("   3. Change to: tsl = get_trading_instance(client_code, token_id)")
        if has_old_tradehull:
            safe_print("   4. Comment out or remove: tsl = Tradehull(client_code, token_id)")
        
        return False


def run_diagnostics():
    """Run full diagnostics"""
    safe_print("\n" + "="*80)
    safe_print("PAPER TRADING SETUP VERIFICATION & DIAGNOSTICS")
    safe_print("="*80)
    
    all_checks_passed = True
    
    # Check files
    safe_print("\n[FILES] CHECKING REQUIRED FILES:")
    safe_print("=" * 80)
    files_to_check = [
        ('paper_trading_config.py', 'Configuration file'),
        ('paper_trading_simulator.py', 'Simulator module'),
        ('paper_trading_wrapper.py', 'Wrapper module'),
        ('single_trade_focus_bot.py', 'Main bot file'),
        ('ce_entry_logic.py', 'CE entry logic'),
        ('pe_entry_logic.py', 'PE entry logic'),
        ('exit_logic.py', 'Exit logic'),
        ('rate_limiter.py', 'Rate limiter'),
    ]
    
    for filename, description in files_to_check:
        if not check_file_exists(filename, description):
            all_checks_passed = False
    
    # Check imports
    safe_print("\n[MODULES] CHECKING PYTHON MODULES:")
    safe_print("=" * 80)
    modules_to_check = [
        ('paper_trading_config', 'Paper trading config'),
        ('paper_trading_simulator', 'Paper trading simulator'),
        ('paper_trading_wrapper', 'Paper trading wrapper'),
        ('pandas', 'Pandas (required)'),
        ('talib', 'TA-Lib (required)'),
    ]
    
    for module, description in modules_to_check:
        if not check_import(module, description):
            all_checks_passed = False
    
    # Check configuration
    safe_print("")
    if not check_config():
        all_checks_passed = False
    
    # Check bot modifications
    if not verify_bot_modifications():
        all_checks_passed = False
    
    # Final verdict
    safe_print("\n" + "="*80)
    if all_checks_passed:
        safe_print("[SUCCESS] ALL CHECKS PASSED - SETUP IS CORRECT!")
        safe_print("="*80)
        safe_print("\nYou're ready to run paper trading!")
        safe_print("\nNext steps:")
        safe_print("   1. Run test: python test_paper_trading.py")
        safe_print("   2. Run bot:  python single_trade_focus_bot.py")
        safe_print("\n" + "="*80)
    else:
        safe_print("[FAILED] SOME CHECKS FAILED - PLEASE FIX ISSUES ABOVE")
        safe_print("="*80)
        safe_print("\nCommon solutions:")
        safe_print("   1. Ensure all paper trading files are in the same directory as your bot")
        safe_print("   2. Check the instructions for exact code modifications")
        safe_print("   3. Make sure paper_trading_config.py has PAPER_TRADING_ENABLED = True")
        safe_print("\n" + "="*80)
    
    return all_checks_passed


def show_quick_help():
    """Show quick help guide"""
    safe_print("\n" + "="*80)
    safe_print("QUICK HELP")
    safe_print("="*80)
    safe_print("""
If setup verification failed, here's what to do:

1. MISSING FILES:
   - Download all paper trading files
   - Place them in the same directory as single_trade_focus_bot.py

2. IMPORT ERRORS:
   - Install missing packages: pip install pandas talib

3. BOT NOT MODIFIED:
   - Open single_trade_focus_bot.py
   - Add: from paper_trading_wrapper import get_trading_instance
   - Change: tsl = get_trading_instance(client_code, token_id)

4. CONFIGURATION ISSUES:
   - Open paper_trading_config.py
   - Set PAPER_TRADING_ENABLED = True

5. ENCODING ERRORS:
   - Save single_trade_focus_bot.py with UTF-8 encoding
   - In most editors: File > Save As > Encoding: UTF-8

6. STILL HAVING ISSUES:
   - Check that all files are in the same directory
   - Run: python test_paper_trading.py
   - Read the error messages carefully

Need more help? Check the documentation files!
    """)
    safe_print("="*80)


if __name__ == "__main__":
    success = run_diagnostics()
    
    if not success:
        show_quick_help()
    
    safe_print("\n[TIP] Run this script anytime to verify your setup!")
    safe_print("")