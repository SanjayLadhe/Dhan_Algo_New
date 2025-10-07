"""
Rate Limiter Module for API Call Management
============================================

This module provides rate limiting functionality for different API endpoints
with file-based logging and retry mechanisms.

Features:
- Thread-safe rate limiting using deque and locks
- Separate rate limiters for different API types
- File-based audit logging with daily rotation
- Retry logic with exponential backoff
- Special handling for rate limit errors (DH-805)
"""

import time
import logging
from logging.handlers import TimedRotatingFileHandler
from collections import deque
import threading


# ============================
# LOGGER CONFIGURATION
# ============================

def setup_logger(name, log_file, level=logging.INFO):
    """
    Set up a logger with timed rotating file handler.
    
    Args:
        name: Logger name
        log_file: Log file path
        level: Logging level
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.propagate = False
    
    return logger


# Configure loggers
rate_limit_logger = setup_logger('RateLimiterLogger', 'rate_limit_audit.log')
general_api_logger = setup_logger('GeneralAPILogger', 'general_api_audit.log')


# ============================
# RATE LIMITER CLASS
# ============================

class RateLimiter:
    """
    Thread-safe rate limiter using sliding window algorithm.
    
    Attributes:
        max_calls: Maximum number of calls allowed per period
        period: Time period in seconds
        name: Identifier for the rate limiter
        logger: Logger instance for audit trail
    """
    
    def __init__(self, max_calls, period, name="RateLimiter", logger=None):
        """
        Initialize the rate limiter.
        
        Args:
            max_calls: Maximum calls allowed in the period
            period: Time period in seconds
            name: Name identifier for logging
            logger: Logger instance (defaults to rate_limit_logger)
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self.lock = threading.Lock()
        self.name = name
        self.logger = logger or rate_limit_logger
    
    def wait(self, call_description=""):
        """
        Wait until a call is allowed by the rate limit.
        
        This method blocks if the rate limit is exceeded and logs
        all rate limiting events for audit purposes.
        
        Args:
            call_description: Description of the API call being made
        """
        with self.lock:
            now = time.time()
            
            # Remove calls older than the period (sliding window)
            while self.calls and self.calls[0] <= now - self.period:
                self.calls.popleft()
            
            # Check if rate limit exceeded
            if len(self.calls) >= self.max_calls:
                sleep_time = self.calls[0] + self.period - now
                if sleep_time > 0:
                    self.logger.info(
                        f"RATE_LIMIT_HIT - {self.name} - {call_description} - "
                        f"Sleeping for {sleep_time:.3f} seconds. Queue size: {len(self.calls)}"
                    )
                    print(
                        f"[{self.name}] Rate limit reached for '{call_description}'. "
                        f"Sleeping for {sleep_time:.2f} seconds..."
                    )
                    time.sleep(sleep_time)
                    
                    # Clean up again after sleep
                    now = time.time()
                    while self.calls and self.calls[0] <= now - self.period:
                        self.calls.popleft()
            
            # Add current call timestamp
            self.calls.append(now)
            active_calls = len(self.calls)
            
            self.logger.info(
                f"CALL_ALLOWED - {self.name} - {call_description} - "
                f"Queue size after add: {active_calls}, Max allowed: {self.max_calls}"
            )
            print(
                f"[{self.name}] ✅ Call allowed for '{call_description}' at {now:.2f}. "
                f"Active calls in window: {active_calls}"
            )


# ============================
# RETRY LOGIC
# ============================

def retry_api_call(func, retries=1, delay=1.0, *args, **kwargs):
    """
    Retry an API call with exponential backoff.
    
    Handles both general errors and specific rate limit errors (DH-805).
    Rate limit errors get longer backoff periods.
    
    Args:
        func: Function to call
        retries: Number of retry attempts
        delay: Initial delay in seconds
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func
    
    Returns:
        Result from successful function call
    
    Raises:
        Exception: If all retry attempts fail
    """
    for attempt in range(retries):
        try:
            result = func(*args, **kwargs)
            
            # Log successful retry if not first attempt
            if attempt > 0:
                general_api_logger.info(
                    f"[RETRY] Success on attempt {attempt + 1} for {func.__name__}"
                )
            
            return result
            
        except Exception as e:
            error_str = str(e)
            
            # Check for rate limit error
            is_rate_limit_error = '805' in error_str or 'Too many requests' in error_str
            
            if is_rate_limit_error:
                general_api_logger.warning(
                    f"[RETRY] Rate limit error detected for {func.__name__}: {e}. "
                    f"Applying longer backoff."
                )
                # Apply longer backoff for rate limits
                time.sleep(delay * 2 * (attempt + 1))
                continue
            
            # Last attempt - raise the exception
            if attempt == retries - 1:
                general_api_logger.error(
                    f"[RETRY] Failed after {retries} attempts for {func.__name__}: {e}"
                )
                raise e
            
            # Log retry attempt
            general_api_logger.warning(
                f"[RETRY] Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                f"Retrying in {delay} seconds..."
            )
            print(f"[RETRY] Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
            
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    
    return None


# ============================
# RATE LIMITER INSTANCES
# ============================

# Data API Limiter: 5 calls per second (Official limit for historical data)
data_api_limiter = RateLimiter(
    max_calls=5,
    period=1.0,
    name="DATA_API",
    logger=rate_limit_logger
)

# Non-Trading API Limiter: 18 calls per second (Slightly under 20/sec official limit)
ntrading_api_limiter = RateLimiter(
    max_calls=18,
    period=1.0,
    name="NTRADING_API",
    logger=general_api_logger
)

# Order API Limiter: 25 calls per second (Official limit)
order_api_limiter = RateLimiter(
    max_calls=25,
    period=1.0,
    name="ORDER_API",
    logger=general_api_logger
)

# LTP API Limiter: 1 call per second
ltp_api_limiter = RateLimiter(
    max_calls=1,
    period=1.0,
    name="LTP_API",
    logger=general_api_logger
)


# ============================
# USAGE EXAMPLE
# ============================

if __name__ == "__main__":
    """
    Example usage of the rate limiter.
    """
    print("Testing Rate Limiter...")
    
    # Example: Simulate 10 API calls with 5 calls/second limit
    test_limiter = RateLimiter(max_calls=5, period=1.0, name="TEST_API")
    
    for i in range(10):
        test_limiter.wait(call_description=f"Test API call #{i+1}")
        print(f"Executed call {i+1}")
    
    print("\nRate limiter test completed!")
