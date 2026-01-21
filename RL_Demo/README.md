# 🤖 Simple RL Trading Demo

## What is this?

This is a **simple, easy-to-understand demo** that shows how Reinforcement Learning (RL) can be used for trading decisions.

## What it does:

1. **Creates dummy stock data** (30 days of trading)
2. **Builds a trading environment** where an agent can BUY, SELL, or HOLD
3. **Creates an RL agent** (neural network) that learns to trade
4. **Trains the agent** for 100 episodes
5. **Compares results**: RL vs Random vs Buy & Hold
6. **Shows visualizations** of learning progress
7. **Displays sample trading decisions**

## How to run:

### Step 1: Install requirements
```bash
cd /home/user/Dhan_Algo_New/RL_Demo
pip install -r requirements.txt
```

### Step 2: Run the demo
```bash
python simple_rl_demo.py
```

### Step 3: Check the output
- See the terminal output for results
- Check `rl_learning_progress.png` for charts

## Expected Runtime:
- 1-2 minutes on most computers

## What to expect:

You'll see:
- Step-by-step explanation of what's happening
- Training progress (100 episodes)
- Comparison of RL vs other strategies
- Charts showing learning progress
- Sample trading decisions

## Understanding the output:

### Training Output:
```
Episode | Reward | Profit | Trades | Epsilon | Loss
--------------------------------------------------------------
10      |  15.23 | $ 125.45 |   12   | 0.905  | 0.0234
```
- **Reward**: Higher is better (agent is learning)
- **Profit**: Dollar profit from trades
- **Trades**: Number of trades executed
- **Epsilon**: Exploration rate (decreases over time)
- **Loss**: Neural network training loss (lower is better)

### Final Results:
```
Strategy              Profit          Trades          Total Reward
----------------------------------------------------------------------
RL Agent (Trained)    $  450.23           15              45.67
Random Strategy       $ -120.45           25             -12.34
Buy & Hold           $  200.10            1              20.01
```

The RL agent typically performs better than random and often beats buy & hold!

## Next Steps:

Once you understand how this works:
1. Replace dummy data with real historical data
2. Add more technical indicators (ATR, VWAP, ADX)
3. Train for more episodes (1000+)
4. Add options (CE/PE) logic
5. Integrate with your actual trading bot

## Files created:
- `simple_rl_demo.py` - Main demo script
- `rl_learning_progress.png` - Learning visualization
- `requirements.txt` - Python dependencies
- `README.md` - This file

## Questions?

The code has detailed comments explaining each step. Read through the file to understand how RL works!
