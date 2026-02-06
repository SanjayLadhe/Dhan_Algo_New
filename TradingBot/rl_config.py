"""
RL Configuration
================
Configuration for the Reinforcement Learning enhancement layer.
The RL agent acts as a filter on top of existing rule-based signals.
"""

import os

# ============================
# RL MASTER SWITCH
# ============================
RL_ENABLED = False  # Set to True to enable RL filtering (start with False to collect data)

# Individual toggles
RL_ENTRY_FILTER_ENABLED = True   # Filter entry signals with RL
RL_EXIT_FILTER_ENABLED = True    # Filter exit signals with RL (only RSI/LongStop exits)

# ============================
# MODEL PATHS
# ============================
RL_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RL_MODEL_DIR = os.path.join(RL_BASE_DIR, "rl_models")
RL_ENTRY_MODEL_PATH = os.path.join(RL_MODEL_DIR, "entry_model.zip")
RL_EXIT_MODEL_PATH = os.path.join(RL_MODEL_DIR, "exit_model.zip")
RL_ENTRY_SCALER_PATH = os.path.join(RL_MODEL_DIR, "entry_scaler.pkl")
RL_EXIT_SCALER_PATH = os.path.join(RL_MODEL_DIR, "exit_scaler.pkl")

# ============================
# TRAINING DATA PATHS
# ============================
RL_DATA_DIR = os.path.join(RL_BASE_DIR, "rl_data")
RL_TRADE_LOG_PATH = os.path.join(RL_DATA_DIR, "trade_log.csv")
RL_ENTRY_OBS_LOG_PATH = os.path.join(RL_DATA_DIR, "entry_observations.csv")
RL_EXIT_OBS_LOG_PATH = os.path.join(RL_DATA_DIR, "exit_observations.csv")
RL_SKIP_LOG_PATH = os.path.join(RL_DATA_DIR, "skip_observations.csv")

# ============================
# OBSERVATION SPACE
# ============================
ENTRY_OBS_DIM = 19   # 19 features for entry decisions
EXIT_OBS_DIM = 23    # 19 + 4 position features for exit decisions

# ============================
# ACTION SPACE
# ============================
# Entry actions
ACTION_SKIP = 0          # Don't take this trade
ACTION_TAKE = 1          # Take with normal lot size
ACTION_TAKE_REDUCED = 2  # Take with half lot size

# Exit actions
ACTION_HOLD = 0       # Override exit signal, keep holding
ACTION_EXIT = 1       # Agree with exit signal
ACTION_TIGHTEN = 2    # Stay in trade but tighten SL

NUM_ENTRY_ACTIONS = 3
NUM_EXIT_ACTIONS = 3

# ============================
# CONFIDENCE THRESHOLD
# ============================
# RL decision is only used if model confidence exceeds this
RL_CONFIDENCE_THRESHOLD = 0.6

# ============================
# FALLBACK BEHAVIOR
# ============================
# If True, use rule-based behavior when RL model is unavailable
RL_FALLBACK_TO_RULES = True

# ============================
# REWARD FUNCTION PARAMETERS
# ============================
REWARD_SCALE = 10.0           # Scale P&L% to this range
REWARD_TARGET_BONUS = 1.0     # Bonus for target hit
REWARD_SL_PENALTY = -0.5      # Penalty for SL hit
REWARD_TIME_EXIT_PENALTY = -0.3  # Penalty for time exit in loss
REWARD_CORRECT_SKIP = 0.5     # Reward for correctly skipping a loser
REWARD_MISSED_WINNER = -0.3   # Penalty for skipping a winner

# ============================
# TRAINING PARAMETERS
# ============================
RL_LEARNING_RATE = 3e-4
RL_BATCH_SIZE = 64
RL_N_EPOCHS = 10
RL_GAMMA = 0.99          # Discount factor
RL_GAE_LAMBDA = 0.95     # GAE lambda
RL_CLIP_RANGE = 0.2      # PPO clip range
RL_MIN_TRAINING_TRADES = 50   # Minimum trades before training is meaningful
RL_DEFAULT_TIMESTEPS = 20000  # Default training timesteps

# ============================
# LOGGING
# ============================
RL_LOG_DECISIONS = True   # Log all RL decisions for analysis
RL_LOG_FILE = os.path.join(RL_BASE_DIR, "rl_decisions.log")
