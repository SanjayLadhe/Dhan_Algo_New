"""
RL Agent
========
Wrapper around stable-baselines3 PPO model for entry/exit filtering.
Handles model loading, inference, and graceful fallback.
"""

import os
import pickle
import numpy as np
from rl_config import (
    RL_ENTRY_MODEL_PATH, RL_EXIT_MODEL_PATH,
    RL_ENTRY_SCALER_PATH, RL_EXIT_SCALER_PATH,
    RL_CONFIDENCE_THRESHOLD, RL_FALLBACK_TO_RULES,
    ACTION_SKIP, ACTION_TAKE, ACTION_TAKE_REDUCED,
    ACTION_HOLD, ACTION_EXIT, ACTION_TIGHTEN,
    NUM_ENTRY_ACTIONS, NUM_EXIT_ACTIONS
)


class RLEntryAgent:
    """
    RL agent for filtering entry signals.
    Loads a pre-trained PPO model and decides whether to TAKE, SKIP, or TAKE_REDUCED.
    """

    def __init__(self, model_path=None, scaler_path=None):
        """
        Initialize the entry agent.

        Args:
            model_path: Path to the trained PPO model zip file
            scaler_path: Path to the fitted scaler pickle file
        """
        self.model_path = model_path or RL_ENTRY_MODEL_PATH
        self.scaler_path = scaler_path or RL_ENTRY_SCALER_PATH
        self.model = None
        self.scaler = None
        self._load_model()

    def _load_model(self):
        """Load the PPO model and scaler from disk."""
        try:
            if os.path.exists(self.model_path):
                from stable_baselines3 import PPO
                self.model = PPO.load(self.model_path)
                print(f"[RL Entry Agent] Model loaded from {self.model_path}")
            else:
                print(f"[RL Entry Agent] No model found at {self.model_path} - will use fallback")

            if os.path.exists(self.scaler_path):
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                print(f"[RL Entry Agent] Scaler loaded from {self.scaler_path}")

        except Exception as e:
            print(f"[RL Entry Agent] Error loading model: {e}")
            self.model = None

    def is_available(self):
        """Check if the model is loaded and ready for inference."""
        return self.model is not None

    def should_enter(self, observation):
        """
        Decide whether to enter a trade.

        Args:
            observation: np.ndarray observation vector from rl_state_builder

        Returns:
            tuple: (action: int, confidence: float)
                action: ACTION_SKIP (0), ACTION_TAKE (1), ACTION_TAKE_REDUCED (2)
                confidence: float in [0, 1]
        """
        if not self.is_available():
            return ACTION_TAKE, 0.0  # Fallback: always take

        try:
            obs = self._preprocess(observation)
            action, _states = self.model.predict(obs, deterministic=True)
            action = int(action)

            # Get action probabilities for confidence
            confidence = self._get_confidence(obs, action)

            # Clamp action to valid range
            if action < 0 or action >= NUM_ENTRY_ACTIONS:
                action = ACTION_TAKE

            return action, confidence

        except Exception as e:
            print(f"[RL Entry Agent] Prediction error: {e}")
            return ACTION_TAKE, 0.0

    def _preprocess(self, observation):
        """Apply scaler if available, ensure correct shape."""
        obs = np.array(observation, dtype=np.float32).flatten()

        if self.scaler is not None:
            obs = self.scaler.transform(obs.reshape(1, -1)).flatten()

        return obs.astype(np.float32)

    def _get_confidence(self, observation, action):
        """
        Get the confidence (probability) of the chosen action.

        Args:
            observation: preprocessed observation
            action: chosen action index

        Returns:
            float: confidence in [0, 1]
        """
        try:
            import torch
            obs_tensor = torch.FloatTensor(observation).unsqueeze(0)

            with torch.no_grad():
                distribution = self.model.policy.get_distribution(obs_tensor)
                probs = distribution.distribution.probs.numpy().flatten()

            return float(probs[action])
        except Exception:
            return 0.5  # Default medium confidence


class RLExitAgent:
    """
    RL agent for filtering exit signals (RSI/LongStop exits only).
    Decides whether to HOLD, EXIT, or TIGHTEN stop loss.
    """

    def __init__(self, model_path=None, scaler_path=None):
        """
        Initialize the exit agent.

        Args:
            model_path: Path to the trained PPO model zip file
            scaler_path: Path to the fitted scaler pickle file
        """
        self.model_path = model_path or RL_EXIT_MODEL_PATH
        self.scaler_path = scaler_path or RL_EXIT_SCALER_PATH
        self.model = None
        self.scaler = None
        self._load_model()

    def _load_model(self):
        """Load the PPO model and scaler from disk."""
        try:
            if os.path.exists(self.model_path):
                from stable_baselines3 import PPO
                self.model = PPO.load(self.model_path)
                print(f"[RL Exit Agent] Model loaded from {self.model_path}")
            else:
                print(f"[RL Exit Agent] No model found at {self.model_path} - will use fallback")

            if os.path.exists(self.scaler_path):
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                print(f"[RL Exit Agent] Scaler loaded from {self.scaler_path}")

        except Exception as e:
            print(f"[RL Exit Agent] Error loading model: {e}")
            self.model = None

    def is_available(self):
        """Check if the model is loaded and ready for inference."""
        return self.model is not None

    def should_exit(self, observation):
        """
        Decide whether to exit a trade.

        Args:
            observation: np.ndarray observation vector from rl_state_builder

        Returns:
            tuple: (action: int, confidence: float)
                action: ACTION_HOLD (0), ACTION_EXIT (1), ACTION_TIGHTEN (2)
                confidence: float in [0, 1]
        """
        if not self.is_available():
            return ACTION_EXIT, 0.0  # Fallback: agree with rule-based exit

        try:
            obs = self._preprocess(observation)
            action, _states = self.model.predict(obs, deterministic=True)
            action = int(action)

            confidence = self._get_confidence(obs, action)

            if action < 0 or action >= NUM_EXIT_ACTIONS:
                action = ACTION_EXIT

            return action, confidence

        except Exception as e:
            print(f"[RL Exit Agent] Prediction error: {e}")
            return ACTION_EXIT, 0.0

    def _preprocess(self, observation):
        """Apply scaler if available, ensure correct shape."""
        obs = np.array(observation, dtype=np.float32).flatten()

        if self.scaler is not None:
            obs = self.scaler.transform(obs.reshape(1, -1)).flatten()

        return obs.astype(np.float32)

    def _get_confidence(self, observation, action):
        """Get the confidence (probability) of the chosen action."""
        try:
            import torch
            obs_tensor = torch.FloatTensor(observation).unsqueeze(0)

            with torch.no_grad():
                distribution = self.model.policy.get_distribution(obs_tensor)
                probs = distribution.distribution.probs.numpy().flatten()

            return float(probs[action])
        except Exception:
            return 0.5
