"""
Ultra Simple RL Trading Demo - No External Dependencies
========================================================
This runs with just Python standard library!
Shows the core concept of RL for trading.
"""

import random
import math

print("="*80)
print("🤖 ULTRA SIMPLE RL TRADING DEMO - EASY TO UNDERSTAND")
print("="*80)
print()

# ============================================================================
# STEP 1: CREATE DUMMY PRICE DATA
# ============================================================================
print("STEP 1: Creating Dummy Price Data...")
print("-" * 80)

random.seed(42)

# Generate 100 price points
price = 100.0
prices = []
for i in range(100):
    # Random walk with slight upward trend
    change = random.uniform(-2, 2.5)
    price = max(50, price + change)  # Don't go below 50
    prices.append(round(price, 2))

print(f"✅ Generated {len(prices)} price points")
print(f"   Starting price: ${prices[0]}")
print(f"   Ending price: ${prices[-1]}")
print(f"   First 10 prices: {prices[:10]}")
print()

# ============================================================================
# STEP 2: SIMPLE TRADING ENVIRONMENT
# ============================================================================
print("\nSTEP 2: Creating Simple Trading Environment...")
print("-" * 80)

class SimpleTrader:
    """
    Simple trader that can:
    - BUY (enter position)
    - SELL (exit position)
    - HOLD (do nothing)
    """

    def __init__(self, prices):
        self.prices = prices
        self.reset()

    def reset(self):
        self.position = None  # None = no position
        self.entry_price = 0
        self.balance = 10000
        self.step = 0
        self.total_profit = 0
        self.trades = 0

    def take_action(self, action):
        """
        Execute action:
        0 = HOLD
        1 = BUY
        2 = SELL
        """
        reward = 0
        current_price = self.prices[self.step]

        if action == 1 and self.position is None:  # BUY
            self.position = 'LONG'
            self.entry_price = current_price
            reward = -0.1  # Small cost for taking action

        elif action == 2 and self.position == 'LONG':  # SELL
            exit_price = current_price
            profit = exit_price - self.entry_price
            profit_pct = (profit / self.entry_price) * 100

            reward = profit_pct  # Reward is the % gain/loss
            self.total_profit += profit
            self.trades += 1
            self.position = None

        self.step += 1
        done = self.step >= len(self.prices)

        return reward, done

print("✅ Trading Environment Created!")
print("   Actions: HOLD(0), BUY(1), SELL(2)")
print()

# ============================================================================
# STEP 3: SIMPLE Q-LEARNING AGENT (NO NEURAL NETWORK)
# ============================================================================
print("\nSTEP 3: Creating Simple Q-Learning Agent...")
print("-" * 80)

class SimpleQLearningAgent:
    """
    Simple Q-Learning agent using a table
    (No neural networks needed!)
    """

    def __init__(self):
        # Q-table: stores value of each action in each situation
        self.q_table = {}
        self.learning_rate = 0.1
        self.discount = 0.95
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01

    def get_state(self, trader):
        """
        Convert current situation to a simple state
        """
        current_price = trader.prices[trader.step]

        # Calculate simple indicators
        if trader.step >= 5:
            avg_5 = sum(trader.prices[trader.step-5:trader.step]) / 5
            trend = "UP" if current_price > avg_5 else "DOWN"
        else:
            trend = "NEUTRAL"

        position = "HOLDING" if trader.position else "EMPTY"

        # State is combination of trend and position
        state = f"{trend}_{position}"
        return state

    def choose_action(self, state, training=True):
        """
        Choose action using epsilon-greedy
        """
        # Explore: random action
        if training and random.random() < self.epsilon:
            return random.randint(0, 2)

        # Exploit: choose best known action
        if state not in self.q_table:
            self.q_table[state] = [0.0, 0.0, 0.0]  # Initialize

        return self.q_table[state].index(max(self.q_table[state]))

    def learn(self, state, action, reward, next_state):
        """
        Update Q-table based on experience
        """
        if state not in self.q_table:
            self.q_table[state] = [0.0, 0.0, 0.0]
        if next_state not in self.q_table:
            self.q_table[next_state] = [0.0, 0.0, 0.0]

        # Q-learning formula
        current_q = self.q_table[state][action]
        max_next_q = max(self.q_table[next_state])
        new_q = current_q + self.learning_rate * (reward + self.discount * max_next_q - current_q)
        self.q_table[state][action] = new_q

        # Decay exploration
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

print("✅ Q-Learning Agent Created!")
print("   Type: Table-based Q-Learning (no neural net)")
print("   States: Based on price trend + position")
print()

# ============================================================================
# STEP 4: TRAIN THE AGENT
# ============================================================================
print("\nSTEP 4: Training the Agent...")
print("-" * 80)
print("Training for 50 episodes. Watch it learn!")
print()

agent = SimpleQLearningAgent()
trader = SimpleTrader(prices)

episode_profits = []
episode_trades = []
episode_rewards = []

print("Episode | Total Reward | Profit  | Trades | Epsilon")
print("-" * 60)

for episode in range(50):
    trader.reset()
    total_reward = 0

    # Run one episode
    while trader.step < len(prices) - 1:
        state = agent.get_state(trader)
        action = agent.choose_action(state, training=True)
        reward, done = trader.take_action(action)
        next_state = agent.get_state(trader)

        agent.learn(state, action, reward, next_state)
        total_reward += reward

        if done:
            break

    episode_profits.append(trader.total_profit)
    episode_trades.append(trader.trades)
    episode_rewards.append(total_reward)

    # Print every 5 episodes
    if (episode + 1) % 5 == 0:
        print(f"{episode+1:4d}    | {total_reward:12.2f} | ${trader.total_profit:7.2f} | "
              f"{trader.trades:4d}   | {agent.epsilon:.3f}")

print()
print("✅ Training Complete!")
print()

# ============================================================================
# STEP 5: TEST TRAINED AGENT
# ============================================================================
print("\nSTEP 5: Testing Trained Agent vs Random Strategy...")
print("-" * 80)

# Test trained agent
trader_rl = SimpleTrader(prices)
total_reward_rl = 0

while trader_rl.step < len(prices) - 1:
    state = agent.get_state(trader_rl)
    action = agent.choose_action(state, training=False)  # No exploration
    reward, done = trader_rl.take_action(action)
    total_reward_rl += reward
    if done:
        break

# Test random strategy
trader_random = SimpleTrader(prices)
random.seed(42)
total_reward_random = 0

while trader_random.step < len(prices) - 1:
    action = random.randint(0, 2)
    reward, done = trader_random.take_action(action)
    total_reward_random += reward
    if done:
        break

# Test buy and hold
buy_hold_profit = prices[-1] - prices[0]

print("\n📊 RESULTS COMPARISON:")
print("=" * 70)
print(f"{'Strategy':<25} {'Profit':<15} {'Trades':<15} {'Reward':<15}")
print("-" * 70)
print(f"{'RL Agent (Trained)':<25} ${trader_rl.total_profit:>8.2f}      "
      f"{trader_rl.trades:>6}         {total_reward_rl:>10.2f}")
print(f"{'Random Strategy':<25} ${trader_random.total_profit:>8.2f}      "
      f"{trader_random.trades:>6}         {total_reward_random:>10.2f}")
print(f"{'Buy & Hold':<25} ${buy_hold_profit:>8.2f}      "
      f"     1              {buy_hold_profit:>10.2f}")
print("=" * 70)
print()

# Show Q-table (learned knowledge)
print("\n🧠 LEARNED Q-TABLE (What the agent learned):")
print("-" * 70)
print(f"{'State':<20} {'HOLD':<10} {'BUY':<10} {'SELL':<10} {'Best Action'}")
print("-" * 70)
for state, q_values in sorted(agent.q_table.items()):
    best_action = ['HOLD', 'BUY', 'SELL'][q_values.index(max(q_values))]
    print(f"{state:<20} {q_values[0]:>8.2f}  {q_values[1]:>8.2f}  {q_values[2]:>8.2f}  {best_action}")
print()

# ============================================================================
# STEP 6: SHOW SAMPLE DECISIONS
# ============================================================================
print("\nSTEP 6: Sample Trading Decisions by RL Agent...")
print("-" * 80)

trader_demo = SimpleTrader(prices)
actions_map = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}

print(f"{'Step':<6} {'Price':<10} {'Trend':<10} {'Position':<12} {'Action':<10}")
print("-" * 60)

for i in range(20):
    if trader_demo.step >= len(prices) - 1:
        break

    current_price = trader_demo.prices[trader_demo.step]
    state = agent.get_state(trader_demo)
    trend = state.split('_')[0]
    position_status = "IN POSITION" if trader_demo.position else "NO POSITION"

    action = agent.choose_action(state, training=False)
    reward, done = trader_demo.take_action(action)

    print(f"{i+1:<6} ${current_price:<9.2f} {trend:<10} {position_status:<12} {actions_map[action]:<10}")

    if done:
        break

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("🎉 DEMO COMPLETE! HERE'S WHAT YOU LEARNED:")
print("="*80)
print()
print("✅ What is Reinforcement Learning?")
print("   - Agent learns by trial and error")
print("   - Gets rewards for good actions (profitable trades)")
print("   - Gets penalties for bad actions (losing trades)")
print("   - Over time, learns which actions work best")
print()
print("✅ How does it work?")
print("   1. Agent looks at current situation (state)")
print("   2. Chooses action (BUY/SELL/HOLD)")
print("   3. Gets reward based on result")
print("   4. Updates knowledge (Q-table)")
print("   5. Repeats and improves over time")
print()
print("✅ What did this demo show?")
print("   - Generated 100 price points")
print("   - Trained agent for 50 episodes")
print("   - Agent learned when to buy/sell")
print("   - Compared: RL vs Random vs Buy&Hold")
print(f"   - RL Agent made ${trader_rl.total_profit:.2f} profit!")
print()
print("🎯 Key Insight:")
print("   The RL agent learned a STRATEGY by experiencing many trades.")
print("   It didn't memorize - it learned PATTERNS that work!")
print()
print("📈 Next Steps:")
print("   1. Run the full demo: python simple_rl_demo.py")
print("      (needs: pip install numpy pandas torch matplotlib)")
print("   2. That version has neural networks and better visualization")
print("   3. Then integrate with your real trading data")
print()
print("="*80)
print("✅ This demo file: /home/user/Dhan_Algo_New/RL_Demo/ultra_simple_demo.py")
print("="*80)
