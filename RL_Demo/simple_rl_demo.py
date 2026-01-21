"""
Simple RL Trading Demo - Easy to Understand
============================================
This demo shows how RL learns to trade using dummy data.
Run this file to see the complete workflow.

Requirements:
pip install numpy pandas torch matplotlib
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

print("="*80)
print("🤖 SIMPLE RL TRADING DEMO - STEP BY STEP EXPLANATION")
print("="*80)
print()

# ============================================================================
# STEP 1: CREATE DUMMY TRADING DATA
# ============================================================================
print("STEP 1: Creating Dummy Trading Data...")
print("-" * 80)

def generate_dummy_data(days=30):
    """
    Generate dummy stock price data that looks realistic
    """
    np.random.seed(42)

    # Generate 30 days of 1-minute data (each day = 375 minutes from 9:15 to 15:15)
    total_minutes = days * 375

    # Starting price
    price = 100.0
    prices = []
    volumes = []

    # Create trending + noise data
    for i in range(total_minutes):
        # Add trend (slowly increasing)
        trend = 0.001
        # Add random noise
        noise = np.random.randn() * 0.5
        # Price change
        price_change = price * (trend + noise / 100)
        price = max(price + price_change, 50)  # Don't go below 50

        prices.append(price)
        volumes.append(random.randint(1000, 10000))

    # Create DataFrame
    df = pd.DataFrame({
        'close': prices,
        'volume': volumes,
    })

    # Calculate technical indicators (simplified)
    df['rsi'] = calculate_simple_rsi(df['close'], period=14)
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['price_change'] = df['close'].pct_change()

    # Fill NaN values
    df.fillna(method='bfill', inplace=True)

    return df

def calculate_simple_rsi(prices, period=14):
    """Simple RSI calculation"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Generate data
data = generate_dummy_data(days=30)
print(f"✅ Generated {len(data)} data points (30 days of trading)")
print(f"   Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
print(f"   Sample data:")
print(data.head(10))
print()

# ============================================================================
# STEP 2: CREATE SIMPLE TRADING ENVIRONMENT
# ============================================================================
print("\nSTEP 2: Creating Simple Trading Environment...")
print("-" * 80)

class SimpleTradingEnvironment:
    """
    A simple trading environment where an agent can:
    - BUY (go long)
    - SELL (close position)
    - HOLD (do nothing)
    """

    def __init__(self, data, initial_balance=10000):
        self.data = data.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.reset()

    def reset(self):
        """Reset environment to start"""
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0  # 0 = no position, 1 = holding position
        self.entry_price = 0
        self.total_profit = 0
        self.trades_made = 0
        self.winning_trades = 0
        self.history = []
        return self._get_state()

    def _get_state(self):
        """
        Get current state as a simple array of features
        State includes:
        - Current price (normalized)
        - RSI
        - Price vs SMA
        - Recent price change
        - Position status
        """
        if self.current_step >= len(self.data):
            return np.zeros(5)

        row = self.data.iloc[self.current_step]

        state = np.array([
            row['close'] / 100,  # Normalized price
            row['rsi'] / 100,    # Normalized RSI
            (row['close'] - row['sma_20']) / row['sma_20'] if row['sma_20'] > 0 else 0,  # Price vs SMA
            row['price_change'],  # Recent change
            self.position,        # Current position
        ])

        return state

    def step(self, action):
        """
        Take an action and return (next_state, reward, done, info)

        Actions:
        0 = HOLD (do nothing)
        1 = BUY (enter position)
        2 = SELL (exit position)
        """
        current_price = self.data.iloc[self.current_step]['close']
        reward = 0

        # Execute action
        if action == 1 and self.position == 0:  # BUY
            self.position = 1
            self.entry_price = current_price
            reward = -0.1  # Small penalty for taking action (transaction cost)

        elif action == 2 and self.position == 1:  # SELL
            exit_price = current_price
            profit = exit_price - self.entry_price
            profit_pct = (profit / self.entry_price) * 100

            # Reward based on profit
            reward = profit_pct  # Reward is the % profit/loss

            self.total_profit += profit
            self.trades_made += 1
            if profit > 0:
                self.winning_trades += 1

            self.position = 0
            self.entry_price = 0

        # Small penalty for holding too long
        if self.position == 1:
            reward -= 0.01

        # Move to next step
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1

        # Get next state
        next_state = self._get_state()

        # Info
        info = {
            'balance': self.balance,
            'total_profit': self.total_profit,
            'trades': self.trades_made,
            'position': self.position,
        }

        return next_state, reward, done, info

print("✅ Trading Environment Created!")
print("   Actions: 0=HOLD, 1=BUY, 2=SELL")
print("   State: 5 features (price, RSI, SMA, change, position)")
print("   Reward: Based on profit %")
print()

# ============================================================================
# STEP 3: CREATE SIMPLE RL AGENT (DQN)
# ============================================================================
print("\nSTEP 3: Creating RL Agent (Deep Q-Network)...")
print("-" * 80)

class SimpleQNetwork(nn.Module):
    """
    Simple neural network that learns Q-values for each action
    """
    def __init__(self, state_size, action_size):
        super(SimpleQNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, action_size)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

class DQNAgent:
    """
    Simple DQN Agent that learns to trade
    """
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size

        # Hyperparameters
        self.gamma = 0.95  # Discount factor
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001

        # Neural network
        self.model = SimpleQNetwork(state_size, action_size)
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        self.criterion = nn.MSELoss()

        # Memory for experience replay
        self.memory = deque(maxlen=2000)
        self.batch_size = 32

    def remember(self, state, action, reward, next_state, done):
        """Store experience in memory"""
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state, training=True):
        """
        Choose action using epsilon-greedy policy
        """
        if training and np.random.rand() <= self.epsilon:
            # Explore: random action
            return random.randrange(self.action_size)

        # Exploit: use neural network
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            q_values = self.model(state_tensor)
        return q_values.argmax().item()

    def replay(self):
        """
        Train the neural network using experiences from memory
        """
        if len(self.memory) < self.batch_size:
            return 0

        # Sample random batch from memory
        batch = random.sample(self.memory, self.batch_size)

        total_loss = 0
        for state, action, reward, next_state, done in batch:
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            next_state_tensor = torch.FloatTensor(next_state).unsqueeze(0)

            # Current Q value
            current_q = self.model(state_tensor)[0][action]

            # Target Q value
            if done:
                target_q = reward
            else:
                next_q = self.model(next_state_tensor).max().item()
                target_q = reward + self.gamma * next_q

            # Calculate loss
            target_q_tensor = torch.FloatTensor([target_q])
            loss = self.criterion(current_q.unsqueeze(0), target_q_tensor)

            # Backpropagation
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

        # Decay exploration
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        return total_loss / self.batch_size

print("✅ RL Agent Created!")
print("   Type: Deep Q-Network (DQN)")
print("   Neural Network: 5 -> 64 -> 64 -> 3")
print("   Exploration: Starts at 100%, decays to 1%")
print()

# ============================================================================
# STEP 4: TRAIN THE RL AGENT
# ============================================================================
print("\nSTEP 4: Training RL Agent...")
print("-" * 80)
print("This will take 1-2 minutes. Watch the agent learn!")
print()

# Initialize
env = SimpleTradingEnvironment(data)
agent = DQNAgent(state_size=5, action_size=3)

# Training parameters
episodes = 100  # Train for 100 episodes
episode_rewards = []
episode_profits = []
episode_trades = []

print("Training Progress:")
print("Episode | Reward | Profit | Trades | Epsilon | Loss")
print("-" * 70)

for episode in range(episodes):
    state = env.reset()
    total_reward = 0
    total_loss = 0
    steps = 0

    # Run one episode
    while True:
        # Agent chooses action
        action = agent.act(state, training=True)

        # Execute action in environment
        next_state, reward, done, info = env.step(action)

        # Remember experience
        agent.remember(state, action, reward, next_state, done)

        # Train agent
        loss = agent.replay()
        total_loss += loss

        # Update
        state = next_state
        total_reward += reward
        steps += 1

        if done:
            break

    # Record metrics
    episode_rewards.append(total_reward)
    episode_profits.append(info['total_profit'])
    episode_trades.append(info['trades'])

    # Print progress every 10 episodes
    if (episode + 1) % 10 == 0:
        avg_loss = total_loss / steps if steps > 0 else 0
        print(f"{episode+1:4d}    | {total_reward:6.2f} | ${info['total_profit']:7.2f} | "
              f"{info['trades']:4d}   | {agent.epsilon:.3f}  | {avg_loss:.4f}")

print()
print("✅ Training Complete!")
print(f"   Final Exploration Rate: {agent.epsilon:.3f}")
print(f"   Total Episodes: {episodes}")
print()

# ============================================================================
# STEP 5: TEST THE TRAINED AGENT
# ============================================================================
print("\nSTEP 5: Testing Trained Agent vs Random Strategy...")
print("-" * 80)

def test_strategy(agent, env, strategy='rl'):
    """Test a strategy and return results"""
    state = env.reset()
    actions_taken = []
    rewards_list = []

    while True:
        if strategy == 'rl':
            action = agent.act(state, training=False)  # No exploration
        elif strategy == 'random':
            action = random.randint(0, 2)
        else:  # buy and hold
            action = 1 if env.position == 0 else 0

        next_state, reward, done, info = env.step(action)

        actions_taken.append(action)
        rewards_list.append(reward)
        state = next_state

        if done:
            break

    return {
        'profit': info['total_profit'],
        'trades': info['trades'],
        'total_reward': sum(rewards_list),
        'actions': actions_taken,
    }

# Test RL agent
rl_results = test_strategy(agent, env, strategy='rl')

# Test random strategy
env_random = SimpleTradingEnvironment(data)
random_results = test_strategy(agent, env_random, strategy='random')

# Test buy and hold
env_hold = SimpleTradingEnvironment(data)
hold_results = test_strategy(agent, env_hold, strategy='hold')

print("\n📊 RESULTS COMPARISON:")
print("=" * 70)
print(f"{'Strategy':<20} {'Profit':<15} {'Trades':<15} {'Total Reward':<15}")
print("-" * 70)
print(f"{'RL Agent (Trained)':<20} ${rl_results['profit']:>8.2f}      "
      f"{rl_results['trades']:>6}         {rl_results['total_reward']:>10.2f}")
print(f"{'Random Strategy':<20} ${random_results['profit']:>8.2f}      "
      f"{random_results['trades']:>6}         {random_results['total_reward']:>10.2f}")
print(f"{'Buy & Hold':<20} ${hold_results['profit']:>8.2f}      "
      f"{hold_results['trades']:>6}         {hold_results['total_reward']:>10.2f}")
print("=" * 70)
print()

# Calculate improvement
if random_results['profit'] != 0:
    improvement = ((rl_results['profit'] - random_results['profit']) / abs(random_results['profit'])) * 100
    print(f"🎯 RL Agent is {improvement:.1f}% better than Random Strategy!")
else:
    print(f"🎯 RL Agent profit: ${rl_results['profit']:.2f}")

print()

# ============================================================================
# STEP 6: VISUALIZE LEARNING PROGRESS
# ============================================================================
print("\nSTEP 6: Visualizing Learning Progress...")
print("-" * 80)

# Create visualization
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle('RL Trading Agent Learning Progress', fontsize=16, fontweight='bold')

# Plot 1: Episode Rewards
axes[0, 0].plot(episode_rewards, alpha=0.6, color='blue')
axes[0, 0].plot(pd.Series(episode_rewards).rolling(10).mean(), color='red', linewidth=2)
axes[0, 0].set_title('Episode Rewards (Learning Curve)')
axes[0, 0].set_xlabel('Episode')
axes[0, 0].set_ylabel('Total Reward')
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].legend(['Actual', '10-Episode Moving Avg'])

# Plot 2: Episode Profits
axes[0, 1].plot(episode_profits, alpha=0.6, color='green')
axes[0, 1].plot(pd.Series(episode_profits).rolling(10).mean(), color='darkgreen', linewidth=2)
axes[0, 1].set_title('Episode Profits')
axes[0, 1].set_xlabel('Episode')
axes[0, 1].set_ylabel('Total Profit ($)')
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].legend(['Actual', '10-Episode Moving Avg'])
axes[0, 1].axhline(y=0, color='red', linestyle='--', alpha=0.5)

# Plot 3: Number of Trades
axes[1, 0].plot(episode_trades, alpha=0.6, color='orange')
axes[1, 0].plot(pd.Series(episode_trades).rolling(10).mean(), color='darkorange', linewidth=2)
axes[1, 0].set_title('Number of Trades per Episode')
axes[1, 0].set_xlabel('Episode')
axes[1, 0].set_ylabel('Trades')
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].legend(['Actual', '10-Episode Moving Avg'])

# Plot 4: Strategy Comparison
strategies = ['RL Agent', 'Random', 'Buy & Hold']
profits = [rl_results['profit'], random_results['profit'], hold_results['profit']]
colors = ['green' if p > 0 else 'red' for p in profits]

axes[1, 1].bar(strategies, profits, color=colors, alpha=0.7, edgecolor='black')
axes[1, 1].set_title('Final Strategy Comparison')
axes[1, 1].set_ylabel('Total Profit ($)')
axes[1, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
axes[1, 1].grid(True, alpha=0.3, axis='y')

# Add value labels on bars
for i, (strategy, profit) in enumerate(zip(strategies, profits)):
    axes[1, 1].text(i, profit + (max(profits) * 0.02), f'${profit:.2f}',
                    ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig('/home/user/Dhan_Algo_New/RL_Demo/rl_learning_progress.png', dpi=150, bbox_inches='tight')
print("✅ Chart saved as 'rl_learning_progress.png'")
print()

# ============================================================================
# STEP 7: SHOW SAMPLE TRADING DECISIONS
# ============================================================================
print("\nSTEP 7: Sample RL Agent Trading Decisions...")
print("-" * 80)

# Reset environment and show first 20 decisions
env_demo = SimpleTradingEnvironment(data)
state = env_demo.reset()

print(f"{'Step':<6} {'Price':<10} {'RSI':<8} {'Position':<10} {'Action':<15} {'Reason':<30}")
print("-" * 90)

action_names = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}
for i in range(20):
    action = agent.act(state, training=False)

    current_price = env_demo.data.iloc[env_demo.current_step]['close']
    current_rsi = env_demo.data.iloc[env_demo.current_step]['rsi']
    position_status = "IN POSITION" if env_demo.position == 1 else "NO POSITION"

    # Explain decision
    if action == 1 and env_demo.position == 0:
        reason = "Opportunity detected"
    elif action == 2 and env_demo.position == 1:
        reason = "Exit signal"
    else:
        reason = "Waiting for setup"

    print(f"{i+1:<6} ${current_price:<9.2f} {current_rsi:<7.1f} {position_status:<10} "
          f"{action_names[action]:<15} {reason:<30}")

    next_state, reward, done, info = env_demo.step(action)
    state = next_state

    if done:
        break

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("🎉 DEMO COMPLETE! HERE'S WHAT HAPPENED:")
print("="*80)
print()
print("1️⃣  Created 30 days of dummy stock data (11,250 data points)")
print("2️⃣  Built a simple trading environment (BUY/SELL/HOLD)")
print("3️⃣  Created an RL agent with a neural network (DQN)")
print("4️⃣  Trained the agent for 100 episodes")
print("5️⃣  Tested: RL Agent vs Random vs Buy & Hold")
print("6️⃣  Visualized learning progress (see chart)")
print("7️⃣  Showed sample trading decisions")
print()
print("🧠 HOW IT WORKS:")
print("   - The RL agent learns by trial and error")
print("   - It gets rewards for profitable trades")
print("   - Over time, it learns which actions work best")
print("   - The neural network finds patterns in the data")
print()
print("📈 NEXT STEPS:")
print("   - Replace dummy data with your real historical data")
print("   - Add more features (ATR, VWAP, ADX, etc.)")
print("   - Train for more episodes (1000+)")
print("   - Add CE/PE options logic")
print("   - Integrate with your trading bot")
print()
print("="*80)
print("✅ Demo file: /home/user/Dhan_Algo_New/RL_Demo/simple_rl_demo.py")
print("✅ Chart saved: /home/user/Dhan_Algo_New/RL_Demo/rl_learning_progress.png")
print("="*80)
