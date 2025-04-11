"""
Price Prediction Model for forex trading
Implements machine learning models to predict short-term price movements
"""

import numpy as np
import pandas as pd
import os
import joblib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple
from loguru import logger
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import xgboost as xgb
import numpy as np
import time
import random

class PricePredictionModel:
    """
    Machine learning model for predicting price movements
    Supports both LSTM and XGBoost models
    """
    
    def __init__(self, model_config: dict):
        """
        Initialize the prediction model
        
        Args:
            model_config: Dictionary with model configuration
        """
        self.config = model_config
        self.models = {}
        self.scalers = {}
        self.model_type = model_config.get('model_type', 'lstm').lower()
        self.lookback_periods = model_config.get('lookback_periods', 30)
        self.prediction_horizon = model_config.get('prediction_horizon', 5)
        self.confidence_threshold = model_config.get('confidence_threshold', 0.65)
        self.retrain_interval = model_config.get('retrain_interval_hours', 24)
        self.enabled = model_config.get('enabled', True)
        
        # Directory for storing trained models
        self.model_dir = os.path.join(os.getcwd(), 'models')
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Last training timestamp for each pair
        self.last_training = {}
        
        logger.info(f"Price prediction model initialized (type: {self.model_type})")
    
    def predict(self, pair: str, data: pd.DataFrame) -> Dict:
        """
        Make a price prediction for a given pair
        
        Args:
            pair: Currency pair
            data: OHLCV DataFrame with indicators
            
        Returns:
            Dictionary with prediction details
        """
        if not self.enabled:
            return {'direction': 0, 'confidence': 0, 'price_target': None}
        
        # Check if model exists for this pair, train if needed
        if pair not in self.models or self._should_retrain(pair):
            self._train_model(pair, data)
        
        # Prepare features for prediction
        X = self._prepare_prediction_features(pair, data)
        
        # Make prediction
        try:
            if self.model_type == 'lstm':
                # LSTM prediction
                prediction = self.models[pair].predict(X)
                direction = 1 if prediction[0][0] > 0.5 else -1
                confidence = max(prediction[0][0], 1 - prediction[0][0])
                
            elif self.model_type == 'xgboost':
                # XGBoost prediction
                prediction = self.models[pair].predict_proba(X)
                direction = 1 if prediction[0][1] > 0.5 else -1
                confidence = max(prediction[0][1], 1 - prediction[0][1])
            
            else:
                logger.error(f"Unsupported model type: {self.model_type}")
                return {'direction': 0, 'confidence': 0, 'price_target': None}
            
            # Calculate price target
            current_price = data['close'].iloc[-1]
            pip_value = 0.0001 if 'JPY' not in pair else 0.01
            
            # Simple price target based on confidence and direction
            price_target = current_price + (direction * confidence * 10 * pip_value)
            
            return {
                'direction': direction,
                'confidence': float(confidence),
                'price_target': float(price_target)
            }
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return {'direction': 0, 'confidence': 0, 'price_target': None}
    
    def _should_retrain(self, pair: str) -> bool:
        """
        Check if the model should be retrained
        
        Args:
            pair: Currency pair
            
        Returns:
            True if retraining is needed
        """
        if pair not in self.last_training:
            return True
        
        hours_since_training = (datetime.now() - self.last_training[pair]).total_seconds() / 3600
        return hours_since_training >= self.retrain_interval
    
    def _train_model(self, pair: str, data: pd.DataFrame):
        """
        Train a new model for a currency pair
        
        Args:
            pair: Currency pair
            data: OHLCV DataFrame with indicators
        """
        logger.info(f"Training new {self.model_type} model for {pair}")
        
        try:
            # Prepare training data
            X, y = self._prepare_training_data(pair, data)
            
            if len(X) < 100:  # Not enough data for training
                logger.warning(f"Not enough data to train model for {pair}")
                # Create a dummy model with random weights
                self._create_dummy_model(pair)
                return
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
            
            if self.model_type == 'lstm':
                # Reshape data for LSTM [samples, time steps, features]
                _, timesteps, n_features = X_train.shape
                
                # Build LSTM model
                model = Sequential([
                    LSTM(64, activation='relu', return_sequences=True, input_shape=(timesteps, n_features)),
                    Dropout(0.2),
                    BatchNormalization(),
                    LSTM(32, activation='relu'),
                    Dropout(0.2),
                    BatchNormalization(),
                    Dense(16, activation='relu'),
                    Dense(1, activation='sigmoid')
                ])
                
                # Compile model
                model.compile(
                    optimizer=Adam(learning_rate=0.001),
                    loss='binary_crossentropy',
                    metrics=['accuracy']
                )
                
                # Define callbacks
                callbacks = [
                    EarlyStopping(patience=10, restore_best_weights=True),
                    ModelCheckpoint(
                        filepath=os.path.join(self.model_dir, f"{pair.replace('/', '_')}_lstm.h5"),
                        save_best_only=True
                    )
                ]
                
                # Train model
                model.fit(
                    X_train, y_train,
                    epochs=50,
                    batch_size=32,
                    validation_data=(X_test, y_test),
                    callbacks=callbacks,
                    verbose=0
                )
                
                self.models[pair] = model
                
            elif self.model_type == 'xgboost':
                # XGBoost requires 2D data
                X_train_2d = X_train.reshape(X_train.shape[0], -1)
                X_test_2d = X_test.reshape(X_test.shape[0], -1)
                
                # Build XGBoost model
                model = xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    objective='binary:logistic',
                    use_label_encoder=False,
                    eval_metric='logloss'
                )
                
                # Train model
                model.fit(
                    X_train_2d, y_train,
                    eval_set=[(X_test_2d, y_test)],
                    early_stopping_rounds=10,
                    verbose=0
                )
                
                # Save model
                joblib.dump(
                    model,
                    os.path.join(self.model_dir, f"{pair.replace('/', '_')}_xgb.joblib")
                )
                
                self.models[pair] = model
            
            # Update last training timestamp
            self.last_training[pair] = datetime.now()
            
            logger.info(f"Model training completed for {pair}")
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            self._create_dummy_model(pair)
    
    def _create_dummy_model(self, pair: str):
        """
        Create a dummy model when training fails
        
        Args:
            pair: Currency pair
        """
        logger.warning(f"Creating dummy model for {pair}")
        
        if self.model_type == 'lstm':
            # Simple LSTM model with random weights
            timesteps = self.lookback_periods
            n_features = 5  # Typical number of features
            
            model = Sequential([
                LSTM(8, activation='relu', return_sequences=True, input_shape=(timesteps, n_features)),
                LSTM(4, activation='relu'),
                Dense(1, activation='sigmoid')
            ])
            
            # Compile model with random weights (no training)
            model.compile(
                optimizer=Adam(learning_rate=0.001),
                loss='binary_crossentropy',
                metrics=['accuracy']
            )
            
            self.models[pair] = model
            
        elif self.model_type == 'xgboost':
            # Simple XGBoost model with minimal parameters
            model = xgb.XGBClassifier(
                n_estimators=10,
                max_depth=3,
                learning_rate=0.1,
                use_label_encoder=False,
                eval_metric='logloss'
            )
            
            self.models[pair] = model
        
        # Create a dummy scaler
        self.scalers[pair] = MinMaxScaler()
        
        # Update last training timestamp
        self.last_training[pair] = datetime.now()
    
    def _prepare_training_data(self, pair: str, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare data for model training
        
        Args:
            pair: Currency pair
            data: OHLCV DataFrame with indicators
            
        Returns:
            Tuple of (features, labels)
        """
        df = data.copy()
        
        # Select features for training
        features = ['open', 'high', 'low', 'close', 'volume']
        
        # Add indicator columns if available
        for indicator in ['rsi', 'ema_5', 'ema_8', 'bb_upper', 'bb_lower', 'bb_middle']:
            if indicator in df.columns:
                features.append(indicator)
        
        # Create a new scaler for this pair
        self.scalers[pair] = MinMaxScaler()
        
        # Scale selected features
        scaled_data = self.scalers[pair].fit_transform(df[features])
        
        # Create sequences for LSTM
        X, y = [], []
        
        for i in range(len(scaled_data) - self.lookback_periods - self.prediction_horizon):
            # Input sequence
            X.append(scaled_data[i:i + self.lookback_periods])
            
            # Target (binary classification: 1 if price goes up, 0 if down)
            future_price = df['close'].iloc[i + self.lookback_periods + self.prediction_horizon]
            current_price = df['close'].iloc[i + self.lookback_periods]
            y.append(1 if future_price > current_price else 0)
        
        return np.array(X), np.array(y)
    
    def _prepare_prediction_features(self, pair: str, data: pd.DataFrame) -> np.ndarray:
        """
        Prepare features for making a prediction
        
        Args:
            pair: Currency pair
            data: OHLCV DataFrame with indicators
            
        Returns:
            Numpy array of features
        """
        df = data.copy()
        
        # Select features for prediction
        features = ['open', 'high', 'low', 'close', 'volume']
        
        # Add indicator columns if available
        for indicator in ['rsi', 'ema_5', 'ema_8', 'bb_upper', 'bb_lower', 'bb_middle']:
            if indicator in df.columns:
                features.append(indicator)
        
        # Ensure all required features are available
        for feature in features.copy():
            if feature not in df.columns:
                features.remove(feature)
                logger.warning(f"Feature {feature} not found in data, removing from prediction features")
        
        # Create scaler if not exists
        if pair not in self.scalers:
            self.scalers[pair] = MinMaxScaler()
            self.scalers[pair].fit(df[features])
        
        # Scale the data
        scaled_data = self.scalers[pair].transform(df[features])
        
        # Get the last sequence for prediction
        sequence = scaled_data[-self.lookback_periods:]
        
        # Reshape for model
        if self.model_type == 'lstm':
            # [1, timesteps, features]
            return np.array([sequence])
        else:
            # Flatten for XGBoost [1, timesteps*features]
            return sequence.reshape(1, -1)
    
    def save_model(self, pair: str):
        """
        Save model to disk
        
        Args:
            pair: Currency pair
        """
        if pair not in self.models:
            logger.warning(f"No model to save for {pair}")
            return
        
        try:
            pair_filename = pair.replace('/', '_')
            
            if self.model_type == 'lstm':
                model_path = os.path.join(self.model_dir, f"{pair_filename}_lstm.h5")
                self.models[pair].save(model_path)
            
            elif self.model_type == 'xgboost':
                model_path = os.path.join(self.model_dir, f"{pair_filename}_xgb.joblib")
                joblib.dump(self.models[pair], model_path)
            
            # Save scaler
            scaler_path = os.path.join(self.model_dir, f"{pair_filename}_scaler.joblib")
            joblib.dump(self.scalers[pair], scaler_path)
            
            logger.info(f"Model saved for {pair}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def load_model(self, pair: str) -> bool:
        """
        Load model from disk
        
        Args:
            pair: Currency pair
            
        Returns:
            True if successful
        """
        try:
            pair_filename = pair.replace('/', '_')
            
            if self.model_type == 'lstm':
                model_path = os.path.join(self.model_dir, f"{pair_filename}_lstm.h5")
                if os.path.exists(model_path):
                    self.models[pair] = load_model(model_path)
                else:
                    return False
            
            elif self.model_type == 'xgboost':
                model_path = os.path.join(self.model_dir, f"{pair_filename}_xgb.joblib")
                if os.path.exists(model_path):
                    self.models[pair] = joblib.load(model_path)
                else:
                    return False
            
            # Load scaler
            scaler_path = os.path.join(self.model_dir, f"{pair_filename}_scaler.joblib")
            if os.path.exists(scaler_path):
                self.scalers[pair] = joblib.load(scaler_path)
            else:
                return False
            
            logger.info(f"Model loaded for {pair}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False


class ReinforcementLearningModel:
    """
    Reinforcement Learning model for optimizing trading decisions
    Implements Deep Q-Network (DQN) approach
    """
    
    def __init__(self, model_config: dict):
        """
        Initialize the reinforcement learning model
        
        Args:
            model_config: Dictionary with model configuration
        """
        self.config = model_config
        self.models = {}
        self.enabled = model_config.get('enabled', True)
        self.model_type = model_config.get('model_type', 'dqn').lower()
        self.reward_function = model_config.get('reward_function', 'profit_sharpe').lower()
        
        # DQN parameters
        self.learning_rate = 0.001
        self.discount_factor = 0.95
        self.exploration_rate = 1.0
        self.exploration_decay = 0.995
        self.min_exploration_rate = 0.01
        self.batch_size = 32
        self.memory_size = 10000
        self.replay_memory = {}
        
        # Model directory
        self.model_dir = os.path.join(os.getcwd(), 'models', 'rl')
        os.makedirs(self.model_dir, exist_ok=True)
        
        logger.info(f"Reinforcement Learning model initialized (type: {self.model_type})")
    
    def get_action(self, pair: str, state: np.ndarray) -> int:
        """
        Get the best action for the current state
        
        Args:
            pair: Currency pair
            state: Current state vector
            
        Returns:
            Action index (0: hold, 1: buy, 2: sell)
        """
        if not self.enabled:
            return 0  # Hold by default if disabled
        
        # Initialize model for this pair if needed
        if pair not in self.models:
            self._initialize_model(pair)
        
        # Exploration vs exploitation
        if np.random.random() < self.exploration_rate:
            # Explore: random action
            return np.random.randint(0, 3)  # 0: hold, 1: buy, 2: sell
        
        # Exploit: use model
        q_values = self.models[pair].predict(state.reshape(1, -1))
        return np.argmax(q_values[0])
    
    def train(self, pair: str, state: np.ndarray, action: int, reward: float, 
              next_state: np.ndarray, done: bool):
        """
        Train the RL model based on experience
        
        Args:
            pair: Currency pair
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether episode is done
        """
        if not self.enabled:
            return
        
        # Initialize model for this pair if needed
        if pair not in self.models:
            self._initialize_model(pair)
        
        # Initialize replay memory for this pair if needed
        if pair not in self.replay_memory:
            self.replay_memory[pair] = []
        
        # Add experience to replay memory
        memory = self.replay_memory[pair]
        memory.append((state, action, reward, next_state, done))
        
        # Limit memory size
        if len(memory) > self.memory_size:
            memory.pop(0)
        
        # Need enough samples for batch training
        if len(memory) < self.batch_size:
            return
        
        # Sample batch from memory
        batch = random.sample(memory, self.batch_size)
        
        # Extract batch components
        states = np.array([x[0] for x in batch])
        actions = np.array([x[1] for x in batch])
        rewards = np.array([x[2] for x in batch])
        next_states = np.array([x[3] for x in batch])
        dones = np.array([x[4] for x in batch])
        
        # Get current Q values
        current_q = self.models[pair].predict(states)
        
        # Get next Q values
        next_q = self.models[pair].predict(next_states)
        
        # Update Q values
        for i in range(self.batch_size):
            if dones[i]:
                current_q[i, actions[i]] = rewards[i]
            else:
                current_q[i, actions[i]] = rewards[i] + self.discount_factor * np.max(next_q[i])
        
        # Train model
        self.models[pair].fit(states, current_q, epochs=1, verbose=0)
        
        # Decay exploration rate
        self.exploration_rate = max(self.min_exploration_rate, 
                                   self.exploration_rate * self.exploration_decay)
    
    def _initialize_model(self, pair: str):
        """
        Initialize RL model for a pair
        
        Args:
            pair: Currency pair
        """
        logger.info(f"Initializing RL model for {pair}")
        
        # Load model if exists
        if self._load_model(pair):
            return
        
        # Create new model
        if self.model_type == 'dqn':
            # For DQN, input is the state vector, output is Q-values for each action
            input_dim = 50  # Typical state dimension, adjust as needed
            output_dim = 3  # Actions: hold, buy, sell
            
            model = Sequential([
                Dense(64, input_dim=input_dim, activation='relu'),
                Dense(32, activation='relu'),
                Dense(output_dim, activation='linear')
            ])
            
            model.compile(
                optimizer=Adam(learning_rate=self.learning_rate),
                loss='mse'
            )
            
            self.models[pair] = model
            
            # Initialize replay memory
            self.replay_memory[pair] = []
            
            logger.info(f"New RL model created for {pair}")
    
    def _load_model(self, pair: str) -> bool:
        """
        Load RL model from disk
        
        Args:
            pair: Currency pair
            
        Returns:
            True if successful
        """
        try:
            model_path = os.path.join(self.model_dir, f"{pair.replace('/', '_')}_rl.h5")
            
            if os.path.exists(model_path):
                self.models[pair] = load_model(model_path)
                logger.info(f"RL model loaded for {pair}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading RL model: {e}")
            return False
    
    def save_model(self, pair: str):
        """
        Save RL model to disk
        
        Args:
            pair: Currency pair
        """
        if pair not in self.models:
            return
        
        try:
            model_path = os.path.join(self.model_dir, f"{pair.replace('/', '_')}_rl.h5")
            self.models[pair].save(model_path)
            logger.info(f"RL model saved for {pair}")
            
        except Exception as e:
            logger.error(f"Error saving RL model: {e}")
