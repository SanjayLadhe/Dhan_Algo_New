"""
RL Trainer
==========
Offline training script that reads logged trade data and trains
the PPO model. Run this periodically (e.g., weekly) after
accumulating enough trade data.

Usage:
    python rl_trainer.py                          # Train with defaults
    python rl_trainer.py --timesteps 50000        # Custom timesteps
    python rl_trainer.py --min-trades 30          # Lower minimum trades
    python rl_trainer.py --evaluate-only          # Just evaluate existing model
"""

import os
import sys
import argparse
import datetime
import pickle
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces

from rl_config import (
    RL_DATA_DIR, RL_MODEL_DIR, RL_TRADE_LOG_PATH, RL_ENTRY_OBS_LOG_PATH,
    RL_EXIT_OBS_LOG_PATH, RL_ENTRY_MODEL_PATH, RL_EXIT_MODEL_PATH,
    RL_ENTRY_SCALER_PATH, RL_EXIT_SCALER_PATH,
    ENTRY_OBS_DIM, EXIT_OBS_DIM, NUM_ENTRY_ACTIONS, NUM_EXIT_ACTIONS,
    RL_LEARNING_RATE, RL_BATCH_SIZE, RL_N_EPOCHS, RL_GAMMA,
    RL_GAE_LAMBDA, RL_CLIP_RANGE, RL_MIN_TRAINING_TRADES, RL_DEFAULT_TIMESTEPS,
    REWARD_SCALE, REWARD_TARGET_BONUS, REWARD_SL_PENALTY,
    REWARD_TIME_EXIT_PENALTY, REWARD_CORRECT_SKIP, REWARD_MISSED_WINNER,
    ACTION_SKIP, ACTION_TAKE, ACTION_TAKE_REDUCED
)


# ============================
# CUSTOM GYMNASIUM ENVIRONMENTS
# ============================

class EntryFilterEnv(gym.Env):
    """
    Custom Gymnasium environment for training the entry filter.
    Each episode is a single trade decision point (contextual bandit).
    """
    metadata = {'render_modes': []}

    def __init__(self, trade_data, entry_obs_data):
        """
        Args:
            trade_data: DataFrame with completed trade outcomes
            entry_obs_data: DataFrame with entry observations
        """
        super().__init__()

        self.trade_data = trade_data.reset_index(drop=True)
        self.entry_obs_data = entry_obs_data.reset_index(drop=True)

        # Merge observations with outcomes where possible
        self.episodes = self._build_episodes()

        self.observation_space = spaces.Box(
            low=-5.0, high=5.0, shape=(ENTRY_OBS_DIM,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(NUM_ENTRY_ACTIONS)

        self.current_idx = 0

    def _build_episodes(self):
        """Build training episodes from logged data."""
        episodes = []

        for _, trade in self.trade_data.iterrows():
            symbol = trade.get('symbol', '')
            entry_time = trade.get('entry_time', '')
            pnl = float(trade.get('pnl', 0))
            pnl_pct = float(trade.get('pnl_pct', 0))
            exit_reason = trade.get('exit_reason', '')
            entry_price = float(trade.get('entry_price', 0))
            qty = float(trade.get('qty', 0))

            # Find matching observation
            obs_match = self.entry_obs_data[
                (self.entry_obs_data['symbol'] == symbol)
            ]

            if obs_match.empty:
                # Create a dummy observation if no match
                obs_vector = np.zeros(ENTRY_OBS_DIM, dtype=np.float32)
            else:
                # Use the most recent matching observation
                obs_row = obs_match.iloc[-1]
                obs_vector = np.array(
                    [float(obs_row.get(f'obs_{i}', 0)) for i in range(ENTRY_OBS_DIM)],
                    dtype=np.float32
                )

            episodes.append({
                'observation': obs_vector,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'exit_reason': exit_reason,
                'entry_price': entry_price,
                'qty': qty,
            })

        return episodes

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if len(self.episodes) == 0:
            return np.zeros(ENTRY_OBS_DIM, dtype=np.float32), {}

        self.current_idx = self.np_random.integers(0, len(self.episodes))
        obs = self.episodes[self.current_idx]['observation']
        return obs.copy(), {}

    def step(self, action):
        """
        Execute one step. Since this is a contextual bandit, each step ends the episode.
        """
        episode = self.episodes[self.current_idx]
        reward = self._calculate_reward(action, episode)

        # Single step episode
        terminated = True
        truncated = False

        # Move to next for any subsequent reset
        next_idx = (self.current_idx + 1) % max(len(self.episodes), 1)
        next_obs = self.episodes[next_idx]['observation'] if self.episodes else np.zeros(ENTRY_OBS_DIM, dtype=np.float32)

        info = {
            'pnl': episode['pnl'],
            'exit_reason': episode['exit_reason'],
            'action': action,
            'reward': reward
        }

        return next_obs.copy(), reward, terminated, truncated, info

    def _calculate_reward(self, action, episode):
        """Calculate reward based on action taken and trade outcome."""
        pnl_pct = episode['pnl_pct']
        exit_reason = episode['exit_reason']
        trade_profitable = pnl_pct > 0

        if action == ACTION_TAKE or action == ACTION_TAKE_REDUCED:
            # Agent decided to take the trade
            scale = 0.5 if action == ACTION_TAKE_REDUCED else 1.0
            reward = pnl_pct * REWARD_SCALE * scale

            if exit_reason == 'Target_Reached':
                reward += REWARD_TARGET_BONUS * scale
            elif exit_reason == 'Stop_Loss_Hit':
                reward += REWARD_SL_PENALTY * scale
            elif exit_reason == 'Time_Exit_Loss':
                reward += REWARD_TIME_EXIT_PENALTY * scale

        elif action == ACTION_SKIP:
            # Agent decided to skip the trade
            if not trade_profitable:
                reward = REWARD_CORRECT_SKIP  # Correctly avoided a loss
            else:
                reward = REWARD_MISSED_WINNER  # Missed a winner

        else:
            reward = 0.0

        return float(reward)


class ExitFilterEnv(gym.Env):
    """
    Custom Gymnasium environment for training the exit filter.
    Each episode is a single exit decision point.
    """
    metadata = {'render_modes': []}

    def __init__(self, trade_data, exit_obs_data):
        super().__init__()

        self.trade_data = trade_data.reset_index(drop=True)
        self.exit_obs_data = exit_obs_data.reset_index(drop=True)
        self.episodes = self._build_episodes()

        self.observation_space = spaces.Box(
            low=-5.0, high=5.0, shape=(EXIT_OBS_DIM,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(NUM_EXIT_ACTIONS)
        self.current_idx = 0

    def _build_episodes(self):
        """Build training episodes from exit observation data."""
        episodes = []

        # Filter trades that had RSI/LongStop exits
        rsi_trades = self.trade_data[
            self.trade_data['exit_reason'].isin([
                'RSI_Below_MA_Exit', 'Close_Below_LongStop_Exit'
            ])
        ]

        for _, trade in rsi_trades.iterrows():
            symbol = trade.get('symbol', '')
            pnl = float(trade.get('pnl', 0))
            pnl_pct = float(trade.get('pnl_pct', 0))
            exit_reason = trade.get('exit_reason', '')

            obs_match = self.exit_obs_data[
                (self.exit_obs_data['symbol'] == symbol)
            ]

            if obs_match.empty:
                obs_vector = np.zeros(EXIT_OBS_DIM, dtype=np.float32)
            else:
                obs_row = obs_match.iloc[-1]
                obs_vector = np.array(
                    [float(obs_row.get(f'obs_{i}', 0)) for i in range(EXIT_OBS_DIM)],
                    dtype=np.float32
                )

            episodes.append({
                'observation': obs_vector,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'exit_reason': exit_reason,
            })

        # Also include non-RSI exits as "what if we held" examples
        other_trades = self.trade_data[
            ~self.trade_data['exit_reason'].isin([
                'RSI_Below_MA_Exit', 'Close_Below_LongStop_Exit'
            ])
        ]

        for _, trade in other_trades.iterrows():
            pnl_pct = float(trade.get('pnl_pct', 0))
            obs_vector = np.zeros(EXIT_OBS_DIM, dtype=np.float32)

            # Simulate what an exit observation might look like
            obs_vector[19] = pnl_pct  # P&L %

            episodes.append({
                'observation': obs_vector,
                'pnl': float(trade.get('pnl', 0)),
                'pnl_pct': pnl_pct,
                'exit_reason': trade.get('exit_reason', ''),
            })

        return episodes

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if len(self.episodes) == 0:
            return np.zeros(EXIT_OBS_DIM, dtype=np.float32), {}

        self.current_idx = self.np_random.integers(0, len(self.episodes))
        obs = self.episodes[self.current_idx]['observation']
        return obs.copy(), {}

    def step(self, action):
        episode = self.episodes[self.current_idx]
        reward = self._calculate_exit_reward(action, episode)

        terminated = True
        truncated = False

        next_idx = (self.current_idx + 1) % max(len(self.episodes), 1)
        next_obs = self.episodes[next_idx]['observation'] if self.episodes else np.zeros(EXIT_OBS_DIM, dtype=np.float32)

        info = {
            'pnl': episode['pnl'],
            'exit_reason': episode['exit_reason'],
            'action': action,
            'reward': reward
        }

        return next_obs.copy(), reward, terminated, truncated, info

    def _calculate_exit_reward(self, action, episode):
        """Calculate reward for exit decisions."""
        pnl_pct = episode['pnl_pct']
        exit_reason = episode['exit_reason']

        if action == 1:  # EXIT
            # Reward based on whether exiting was the right call
            # If trade ended in loss, exiting early is good
            if pnl_pct < 0:
                reward = 0.5  # Good: exited a loser
            else:
                reward = pnl_pct * REWARD_SCALE * 0.5  # OK: took partial profit

        elif action == 0:  # HOLD
            # If the trade eventually hit target, holding was good
            if exit_reason == 'Target_Reached':
                reward = REWARD_TARGET_BONUS
            elif exit_reason == 'Stop_Loss_Hit':
                reward = REWARD_SL_PENALTY * 1.5  # Worse: held into SL
            else:
                reward = pnl_pct * REWARD_SCALE * 0.3  # Uncertain

        elif action == 2:  # TIGHTEN
            # Moderate approach - good for uncertain situations
            if pnl_pct > 0:
                reward = 0.3  # Locked some profit
            else:
                reward = -0.1  # Slight penalty but not bad

        else:
            reward = 0.0

        return float(reward)


# ============================
# TRAINING FUNCTIONS
# ============================

def load_training_data():
    """Load all training data from CSV files."""
    data = {}

    if os.path.exists(RL_TRADE_LOG_PATH):
        data['trades'] = pd.read_csv(RL_TRADE_LOG_PATH)
        print(f"Loaded {len(data['trades'])} trade records")
    else:
        data['trades'] = pd.DataFrame()
        print("No trade log found")

    if os.path.exists(RL_ENTRY_OBS_LOG_PATH):
        data['entry_obs'] = pd.read_csv(RL_ENTRY_OBS_LOG_PATH)
        print(f"Loaded {len(data['entry_obs'])} entry observations")
    else:
        data['entry_obs'] = pd.DataFrame()
        print("No entry observations found")

    if os.path.exists(RL_EXIT_OBS_LOG_PATH):
        data['exit_obs'] = pd.read_csv(RL_EXIT_OBS_LOG_PATH)
        print(f"Loaded {len(data['exit_obs'])} exit observations")
    else:
        data['exit_obs'] = pd.DataFrame()
        print("No exit observations found")

    return data


def fit_and_save_scaler(obs_data, obs_dim, scaler_path):
    """Fit a StandardScaler on observation data and save it."""
    from sklearn.preprocessing import StandardScaler

    obs_columns = [f'obs_{i}' for i in range(obs_dim)]
    available_cols = [c for c in obs_columns if c in obs_data.columns]

    if not available_cols:
        print(f"No observation columns found for scaler. Skipping.")
        return None

    obs_matrix = obs_data[available_cols].values.astype(np.float32)

    # Replace NaN with 0
    obs_matrix = np.nan_to_num(obs_matrix, nan=0.0, posinf=1.0, neginf=-1.0)

    scaler = StandardScaler()
    scaler.fit(obs_matrix)

    os.makedirs(os.path.dirname(scaler_path), exist_ok=True)
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)

    print(f"Scaler saved to {scaler_path}")
    return scaler


def train_entry_model(data, timesteps=None):
    """
    Train the entry filter PPO model.

    Args:
        data: dict with 'trades' and 'entry_obs' DataFrames
        timesteps: Training timesteps (default from config)

    Returns:
        str: Path to saved model, or None if training failed
    """
    timesteps = timesteps or RL_DEFAULT_TIMESTEPS

    trades = data.get('trades', pd.DataFrame())
    entry_obs = data.get('entry_obs', pd.DataFrame())

    if trades.empty:
        print("No trade data available for entry model training")
        return None

    print(f"\n{'='*60}")
    print(f"TRAINING ENTRY FILTER MODEL")
    print(f"{'='*60}")
    print(f"Trades: {len(trades)} | Observations: {len(entry_obs)} | Timesteps: {timesteps}")

    # Fit scaler on entry observations
    if not entry_obs.empty:
        fit_and_save_scaler(entry_obs, ENTRY_OBS_DIM, RL_ENTRY_SCALER_PATH)

    # Create environment
    env = EntryFilterEnv(trades, entry_obs)

    if len(env.episodes) == 0:
        print("No episodes to train on")
        return None

    print(f"Training episodes: {len(env.episodes)}")

    # Print trade outcome distribution
    outcomes = trades['exit_reason'].value_counts()
    print(f"\nTrade outcomes:")
    for reason, count in outcomes.items():
        print(f"  {reason}: {count}")

    # Create PPO model
    from stable_baselines3 import PPO

    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=RL_LEARNING_RATE,
        batch_size=min(RL_BATCH_SIZE, len(env.episodes)),
        n_epochs=RL_N_EPOCHS,
        gamma=RL_GAMMA,
        gae_lambda=RL_GAE_LAMBDA,
        clip_range=RL_CLIP_RANGE,
        n_steps=min(2048, max(len(env.episodes), 64)),
        verbose=1
    )

    # Train
    print(f"\nStarting training for {timesteps} timesteps...")
    model.learn(total_timesteps=timesteps)

    # Save model
    os.makedirs(RL_MODEL_DIR, exist_ok=True)
    model.save(RL_ENTRY_MODEL_PATH)

    # Save timestamped backup
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(RL_MODEL_DIR, f"entry_model_{timestamp}.zip")
    model.save(backup_path)

    print(f"\nEntry model saved to: {RL_ENTRY_MODEL_PATH}")
    print(f"Backup saved to: {backup_path}")

    # Evaluate
    evaluate_entry_model(model, env)

    return RL_ENTRY_MODEL_PATH


def train_exit_model(data, timesteps=None):
    """
    Train the exit filter PPO model.

    Args:
        data: dict with 'trades' and 'exit_obs' DataFrames
        timesteps: Training timesteps

    Returns:
        str: Path to saved model, or None if training failed
    """
    timesteps = timesteps or RL_DEFAULT_TIMESTEPS

    trades = data.get('trades', pd.DataFrame())
    exit_obs = data.get('exit_obs', pd.DataFrame())

    if trades.empty:
        print("No trade data available for exit model training")
        return None

    print(f"\n{'='*60}")
    print(f"TRAINING EXIT FILTER MODEL")
    print(f"{'='*60}")
    print(f"Trades: {len(trades)} | Observations: {len(exit_obs)} | Timesteps: {timesteps}")

    # Fit scaler on exit observations
    if not exit_obs.empty:
        fit_and_save_scaler(exit_obs, EXIT_OBS_DIM, RL_EXIT_SCALER_PATH)

    # Create environment
    env = ExitFilterEnv(trades, exit_obs)

    if len(env.episodes) == 0:
        print("No episodes to train on")
        return None

    print(f"Training episodes: {len(env.episodes)}")

    from stable_baselines3 import PPO

    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=RL_LEARNING_RATE,
        batch_size=min(RL_BATCH_SIZE, len(env.episodes)),
        n_epochs=RL_N_EPOCHS,
        gamma=RL_GAMMA,
        gae_lambda=RL_GAE_LAMBDA,
        clip_range=RL_CLIP_RANGE,
        n_steps=min(2048, max(len(env.episodes), 64)),
        verbose=1
    )

    print(f"\nStarting training for {timesteps} timesteps...")
    model.learn(total_timesteps=timesteps)

    os.makedirs(RL_MODEL_DIR, exist_ok=True)
    model.save(RL_EXIT_MODEL_PATH)

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(RL_MODEL_DIR, f"exit_model_{timestamp}.zip")
    model.save(backup_path)

    print(f"\nExit model saved to: {RL_EXIT_MODEL_PATH}")
    print(f"Backup saved to: {backup_path}")

    evaluate_exit_model(model, env)

    return RL_EXIT_MODEL_PATH


# ============================
# EVALUATION
# ============================

def evaluate_entry_model(model, env, n_eval=None):
    """Evaluate the entry model on all episodes."""
    n_eval = n_eval or len(env.episodes)

    print(f"\n--- Entry Model Evaluation ({n_eval} episodes) ---")

    actions_taken = {0: 0, 1: 0, 2: 0}  # SKIP, TAKE, TAKE_REDUCED
    total_reward = 0
    correct_skips = 0
    missed_winners = 0
    profitable_takes = 0
    losing_takes = 0

    for i in range(min(n_eval, len(env.episodes))):
        env.current_idx = i
        obs = env.episodes[i]['observation']
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)
        actions_taken[action] = actions_taken.get(action, 0) + 1

        episode = env.episodes[i]
        reward = env._calculate_reward(action, episode)
        total_reward += reward

        trade_profitable = episode['pnl_pct'] > 0

        if action == ACTION_SKIP:
            if not trade_profitable:
                correct_skips += 1
            else:
                missed_winners += 1
        elif action in (ACTION_TAKE, ACTION_TAKE_REDUCED):
            if trade_profitable:
                profitable_takes += 1
            else:
                losing_takes += 1

    total_trades = profitable_takes + losing_takes
    win_rate = profitable_takes / max(total_trades, 1) * 100

    print(f"Action distribution: SKIP={actions_taken[0]}, TAKE={actions_taken[1]}, REDUCED={actions_taken[2]}")
    print(f"Total reward: {total_reward:.2f}")
    print(f"Avg reward: {total_reward / max(n_eval, 1):.4f}")
    print(f"Win rate (of taken trades): {win_rate:.1f}%")
    print(f"Correct skips: {correct_skips} | Missed winners: {missed_winners}")
    print(f"Profitable takes: {profitable_takes} | Losing takes: {losing_takes}")


def evaluate_exit_model(model, env, n_eval=None):
    """Evaluate the exit model."""
    n_eval = n_eval or len(env.episodes)

    print(f"\n--- Exit Model Evaluation ({n_eval} episodes) ---")

    actions_taken = {0: 0, 1: 0, 2: 0}
    total_reward = 0

    for i in range(min(n_eval, len(env.episodes))):
        env.current_idx = i
        obs = env.episodes[i]['observation']
        action, _ = model.predict(obs, deterministic=True)
        action = int(action)
        actions_taken[action] = actions_taken.get(action, 0) + 1

        reward = env._calculate_exit_reward(action, env.episodes[i])
        total_reward += reward

    print(f"Action distribution: HOLD={actions_taken[0]}, EXIT={actions_taken[1]}, TIGHTEN={actions_taken[2]}")
    print(f"Total reward: {total_reward:.2f}")
    print(f"Avg reward: {total_reward / max(n_eval, 1):.4f}")


# ============================
# MAIN
# ============================

def main():
    parser = argparse.ArgumentParser(description='RL Trainer for Trading Bot')
    parser.add_argument('--timesteps', type=int, default=RL_DEFAULT_TIMESTEPS,
                        help=f'Training timesteps (default: {RL_DEFAULT_TIMESTEPS})')
    parser.add_argument('--min-trades', type=int, default=RL_MIN_TRAINING_TRADES,
                        help=f'Minimum trades required (default: {RL_MIN_TRAINING_TRADES})')
    parser.add_argument('--entry-only', action='store_true', help='Train only entry model')
    parser.add_argument('--exit-only', action='store_true', help='Train only exit model')
    parser.add_argument('--evaluate-only', action='store_true', help='Evaluate existing models only')

    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"RL TRAINER FOR TRADING BOT")
    print(f"{'='*60}")
    print(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Data directory: {RL_DATA_DIR}")
    print(f"Model directory: {RL_MODEL_DIR}")

    # Load data
    data = load_training_data()

    trade_count = len(data.get('trades', pd.DataFrame()))
    print(f"\nTotal trades: {trade_count}")

    if trade_count < args.min_trades:
        print(f"\nInsufficient data: {trade_count} trades < {args.min_trades} minimum")
        print(f"Continue running the bot to collect more trade data.")
        print(f"Data is logged automatically to: {RL_DATA_DIR}")
        sys.exit(1)

    if args.evaluate_only:
        print("\n--- Evaluate Only Mode ---")
        from stable_baselines3 import PPO

        if os.path.exists(RL_ENTRY_MODEL_PATH):
            entry_model = PPO.load(RL_ENTRY_MODEL_PATH)
            entry_obs = data.get('entry_obs', pd.DataFrame())
            env = EntryFilterEnv(data['trades'], entry_obs)
            evaluate_entry_model(entry_model, env)
        else:
            print("No entry model found")

        if os.path.exists(RL_EXIT_MODEL_PATH):
            exit_model = PPO.load(RL_EXIT_MODEL_PATH)
            exit_obs = data.get('exit_obs', pd.DataFrame())
            env = ExitFilterEnv(data['trades'], exit_obs)
            evaluate_exit_model(exit_model, env)
        else:
            print("No exit model found")

        return

    # Train models
    if not args.exit_only:
        train_entry_model(data, args.timesteps)

    if not args.entry_only:
        train_exit_model(data, args.timesteps)

    print(f"\n{'='*60}")
    print(f"TRAINING COMPLETE")
    print(f"{'='*60}")
    print(f"Models saved to: {RL_MODEL_DIR}")
    print(f"\nNext steps:")
    print(f"1. Set RL_ENABLED = True in rl_config.py")
    print(f"2. Run the bot in PAPER TRADING mode first")
    print(f"3. Monitor RL decisions in rl_decisions.log")
    print(f"4. Retrain periodically as more data accumulates")


if __name__ == '__main__':
    main()
