"""
Paper Trading Configuration
============================

Enable/disable paper trading mode and configure simulation parameters.
"""

# ============================
# PAPER TRADING MODE
# ============================
PAPER_TRADING_ENABLED = True  # Set to False for live trading

# ============================
# SIMULATION PARAMETERS
# ============================

# Price simulation settings
SLIPPAGE_PERCENTAGE = 0.1  # 0.1% slippage on market orders
SLIPPAGE_POINTS = 0.5      # Additional fixed slippage in points

# Execution delay simulation (in seconds)
ORDER_EXECUTION_DELAY = 0.5  # Simulate order processing time

# Failure simulation (for testing error handling)
SIMULATE_ORDER_FAILURES = False
ORDER_FAILURE_RATE = 0.0  # 0.0 = no failures, 0.1 = 10% failure rate

# Stop loss execution simulation
SL_ALWAYS_EXECUTES = True  # If True, SL always triggers at exact price

# Logging
PAPER_TRADING_LOG_FILE = "paper_trading_log.txt"
VERBOSE_LOGGING = True  # Print detailed simulation logs

# ============================
# INITIAL PAPER TRADING CAPITAL
# ============================
PAPER_TRADING_BALANCE = 50000  # Starting balance for paper trading
