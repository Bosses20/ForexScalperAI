"""
AI-Enhanced Decision Making Module for Forex Trading Bot

This module integrates with the market condition detector and multi-asset integrator
to provide enhanced decision making capabilities using machine learning techniques.
"""

import logging
import numpy as np
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

# Initialize logger
logger = logging.getLogger('ai_decision_module')

class AIDecisionModule:
    """
    AI-Enhanced Decision Making Module that processes market data and enhances
    trading decisions with machine learning insights.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AI Decision Module.
        
        Args:
            config: Configuration dictionary with AI parameters
        """
        self.config = config.get('ai_enhanced_trading', {})
        self.enabled = self.config.get('enabled', True)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.65)
        self.min_data_points = self.config.get('min_data_points', 100)
        self.feature_weights = self.config.get('feature_weights', {})
        self.historical_decisions = []
        self.last_update_time = time.time()
        
        # Default weights if not specified in config
        if not self.feature_weights:
            self.feature_weights = {
                'trend_strength': 0.25,
                'volatility': 0.20,
                'momentum': 0.15,
                'liquidity': 0.10,
                'session_activity': 0.10,
                'correlation_impact': 0.10,
                'risk_profile': 0.10,
            }
            
        logger.info(f"AI Decision Module initialized with confidence threshold: {self.confidence_threshold}")
    
    def analyze_trading_opportunity(self, 
                                    symbol: str, 
                                    market_conditions: Dict[str, Any], 
                                    multi_asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a potential trading opportunity using AI-enhanced decision making.
        
        Args:
            symbol: The trading symbol to analyze
            market_conditions: Current market conditions from MarketConditionDetector
            multi_asset_data: Multi-asset trading data
            
        Returns:
            Dictionary with decision details and confidence score
        """
        if not self.enabled:
            return {"enabled": False, "message": "AI decision module is disabled"}
        
        try:
            # Extract relevant features
            features = self._extract_features(symbol, market_conditions, multi_asset_data)
            
            # Calculate weighted confidence score
            confidence_score = self._calculate_confidence(features)
            
            # Determine optimal entry points
            entry_points = self._determine_entry_points(symbol, features, market_conditions)
            
            # Evaluate risk level
            risk_level = self._evaluate_risk(features, market_conditions)
            
            # Get strategy recommendations
            recommended_strategies = self._recommend_strategies(
                symbol, features, confidence_score, risk_level, market_conditions
            )
            
            # Record this decision for learning
            self._record_decision(symbol, features, confidence_score, recommended_strategies)
            
            # Create decision result
            decision = {
                "symbol": symbol,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "confidence_score": round(confidence_score, 4),
                "risk_level": risk_level,
                "favorable_for_trading": confidence_score >= self.confidence_threshold,
                "entry_points": entry_points,
                "recommended_strategies": recommended_strategies,
                "features_analyzed": features
            }
            
            logger.debug(f"AI Decision for {symbol}: Confidence={confidence_score:.4f}, Risk={risk_level}")
            return decision
            
        except Exception as e:
            logger.error(f"Error in AI decision module: {str(e)}")
            return {
                "error": True,
                "message": f"Failed to analyze trading opportunity: {str(e)}",
                "confidence_score": 0.0,
                "favorable_for_trading": False
            }
    
    def _extract_features(self, 
                         symbol: str, 
                         market_conditions: Dict[str, Any], 
                         multi_asset_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract relevant features from market data for decision making.
        
        Args:
            symbol: Trading symbol
            market_conditions: Market condition data
            multi_asset_data: Multi-asset trading data
            
        Returns:
            Dictionary of extracted features with normalized values
        """
        features = {}
        
        # Extract trend features
        trend = market_conditions.get('trend', 'neutral')
        trend_strength = market_conditions.get('trend_strength', 0.5)
        
        if trend == 'bullish':
            features['trend_strength'] = trend_strength
        elif trend == 'bearish':
            features['trend_strength'] = -trend_strength
        else:
            features['trend_strength'] = 0.0
            
        # Extract volatility
        volatility = market_conditions.get('volatility', 'medium')
        
        if volatility == 'low':
            features['volatility'] = 0.2
        elif volatility == 'medium':
            features['volatility'] = 0.5
        elif volatility == 'high':
            features['volatility'] = 0.8
        else:
            features['volatility'] = 0.5
            
        # Extract momentum
        momentum = market_conditions.get('momentum', 0.0)
        features['momentum'] = max(-1.0, min(1.0, momentum))  # Normalize to [-1, 1]
        
        # Extract liquidity
        liquidity = market_conditions.get('liquidity', 'medium')
        
        if liquidity == 'low':
            features['liquidity'] = 0.3
        elif liquidity == 'medium':
            features['liquidity'] = 0.6
        elif liquidity == 'high':
            features['liquidity'] = 0.9
        else:
            features['liquidity'] = 0.6
        
        # Extract trading session activity
        current_session = market_conditions.get('current_session', '')
        session_activity = 0.5  # Default
        
        if current_session in ['london_open', 'ny_open', 'london_ny_overlap']:
            session_activity = 0.9  # High activity periods
        elif current_session in ['asian', 'sydney_open']:
            session_activity = 0.6  # Moderate activity
        elif current_session in ['late_ny', 'weekend']:
            session_activity = 0.2  # Low activity
            
        features['session_activity'] = session_activity
        
        # Extract correlation impact
        correlation_impact = 0.0
        correlations = multi_asset_data.get('correlations', {})
        
        # Calculate average correlation with actively traded instruments
        active_symbols = multi_asset_data.get('active_instruments', [])
        if active_symbols and symbol in correlations:
            corr_sum = 0.0
            count = 0
            for active_symbol in active_symbols:
                if active_symbol != symbol and active_symbol in correlations[symbol]:
                    corr_sum += abs(correlations[symbol][active_symbol])
                    count += 1
                    
            if count > 0:
                correlation_impact = corr_sum / count
                
        features['correlation_impact'] = correlation_impact
        
        # Extract risk profile
        risk_management = multi_asset_data.get('risk_management', {})
        max_risk = risk_management.get('max_risk_per_trade', 0.02)  # Default 2%
        
        features['risk_profile'] = max_risk * 50  # Normalize to [0, 1] assuming max is 2%
        
        return features
    
    def _calculate_confidence(self, features: Dict[str, float]) -> float:
        """
        Calculate weighted confidence score based on extracted features.
        
        Args:
            features: Dictionary of extracted features
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 0.0
        total_weight = 0.0
        
        for feature_name, feature_value in features.items():
            if feature_name in self.feature_weights:
                weight = self.feature_weights[feature_name]
                
                # Apply specific logic for certain features
                if feature_name == 'volatility':
                    # High volatility can be good or bad depending on strategy
                    # Here we assume moderate volatility is best
                    adjusted_value = 1.0 - 2.0 * abs(feature_value - 0.5)
                    confidence += weight * adjusted_value
                elif feature_name == 'correlation_impact':
                    # Lower correlation is better (less risk)
                    confidence += weight * (1.0 - feature_value)
                elif feature_name == 'trend_strength':
                    # We want strong trends in either direction
                    confidence += weight * abs(feature_value)
                elif feature_name == 'momentum':
                    # Strong momentum in either direction can be good
                    confidence += weight * abs(feature_value)
                else:
                    # For other features, higher values are generally better
                    confidence += weight * feature_value
                    
                total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            confidence /= total_weight
            
        # Apply sigmoid function to create better differentiation
        # between medium and high confidence scenarios
        confidence = 1.0 / (1.0 + np.exp(-5.0 * (confidence - 0.5)))
        
        return max(0.0, min(1.0, confidence))
    
    def _determine_entry_points(self, 
                             symbol: str, 
                             features: Dict[str, float],
                             market_conditions: Dict[str, Any]) -> Dict[str, float]:
        """
        Determine optimal entry points for trading.
        
        Args:
            symbol: Trading symbol
            features: Extracted features
            market_conditions: Current market conditions
            
        Returns:
            Dictionary with entry points and confidence levels
        """
        entry_points = {}
        
        # Get key price levels
        support_levels = market_conditions.get('support_levels', [])
        resistance_levels = market_conditions.get('resistance_levels', [])
        current_price = market_conditions.get('current_price', 0.0)
        
        if not current_price:
            return {"error": "No current price available"}
        
        # Determine entry for bullish scenario
        if features['trend_strength'] > 0.3:
            nearest_support = None
            max_distance = 0.02 * current_price  # 2% max distance
            
            for level in support_levels:
                if level < current_price and (current_price - level) < max_distance:
                    if nearest_support is None or level > nearest_support:
                        nearest_support = level
            
            if nearest_support:
                entry_price = (current_price + nearest_support) / 2
                entry_confidence = features['trend_strength'] * (1.0 - (current_price - nearest_support) / max_distance)
                entry_points["bullish"] = {
                    "price": round(entry_price, 5),
                    "confidence": round(entry_confidence, 4),
                    "type": "buy"
                }
        
        # Determine entry for bearish scenario
        if features['trend_strength'] < -0.3:
            nearest_resistance = None
            max_distance = 0.02 * current_price  # 2% max distance
            
            for level in resistance_levels:
                if level > current_price and (level - current_price) < max_distance:
                    if nearest_resistance is None or level < nearest_resistance:
                        nearest_resistance = level
            
            if nearest_resistance:
                entry_price = (current_price + nearest_resistance) / 2
                entry_confidence = abs(features['trend_strength']) * (1.0 - (nearest_resistance - current_price) / max_distance)
                entry_points["bearish"] = {
                    "price": round(entry_price, 5),
                    "confidence": round(entry_confidence, 4),
                    "type": "sell"
                }
        
        return entry_points
    
    def _evaluate_risk(self, 
                     features: Dict[str, float], 
                     market_conditions: Dict[str, Any]) -> str:
        """
        Evaluate the risk level for a potential trade.
        
        Args:
            features: Extracted features
            market_conditions: Current market conditions
            
        Returns:
            Risk level as string: "low", "medium", or "high"
        """
        # Calculate raw risk score
        risk_score = 0.0
        
        # Higher volatility means higher risk
        risk_score += features['volatility'] * 0.3
        
        # Higher trend strength means lower risk
        risk_score -= abs(features['trend_strength']) * 0.2
        
        # Higher liquidity means lower risk
        risk_score -= features['liquidity'] * 0.15
        
        # Higher correlation impact means higher risk
        risk_score += features['correlation_impact'] * 0.2
        
        # Fundamental risk from market conditions
        market_risk = market_conditions.get('market_risk', 0.5)
        risk_score += market_risk * 0.15
        
        # News events increase risk
        has_high_impact_news = market_conditions.get('has_high_impact_news', False)
        if has_high_impact_news:
            risk_score += 0.2
            
        # Normalize to [0, 1]
        risk_score = max(0.0, min(1.0, risk_score + 0.5))
        
        # Categorize risk level
        if risk_score < 0.33:
            return "low"
        elif risk_score < 0.66:
            return "medium"
        else:
            return "high"
    
    def _recommend_strategies(self, 
                            symbol: str,
                            features: Dict[str, float],
                            confidence_score: float,
                            risk_level: str,
                            market_conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Recommend appropriate trading strategies based on analysis.
        
        Args:
            symbol: Trading symbol
            features: Extracted features
            confidence_score: Overall confidence score
            risk_level: Assessed risk level
            market_conditions: Current market conditions
            
        Returns:
            List of recommended strategies with confidence levels
        """
        recommendations = []
        trend = market_conditions.get('trend', 'neutral')
        volatility = features['volatility']
        
        # Only recommend strategies if confidence is reasonable
        if confidence_score < 0.4:
            return []
            
        # Trend-following strategies
        if abs(features['trend_strength']) > 0.4:
            trend_direction = "bullish" if features['trend_strength'] > 0 else "bearish"
            trend_strategy = {
                "name": "trend_following",
                "direction": trend_direction,
                "confidence": round(min(1.0, abs(features['trend_strength']) * 1.2), 4),
                "timeframe": "medium",
                "params": {
                    "entry": "market" if confidence_score > 0.7 else "limit",
                    "stop_distance": "medium"
                }
            }
            recommendations.append(trend_strategy)
            
        # Mean reversion strategies for ranging markets
        if abs(features['trend_strength']) < 0.3 and volatility < 0.6:
            mean_reversion = {
                "name": "mean_reversion",
                "direction": "neutral",
                "confidence": round(0.8 - abs(features['trend_strength']), 4),
                "timeframe": "short",
                "params": {
                    "entry": "limit",
                    "stop_distance": "tight"
                }
            }
            recommendations.append(mean_reversion)
            
        # Breakout strategies for periods of low volatility that may expand
        if volatility < 0.4 and market_conditions.get('volatility_expanding', False):
            breakout_strategy = {
                "name": "breakout",
                "direction": "both",
                "confidence": round(0.5 + features['momentum'] * 0.5, 4),
                "timeframe": "short",
                "params": {
                    "entry": "stop",
                    "stop_distance": "wide"
                }
            }
            recommendations.append(breakout_strategy)
            
        # Momentum strategies for strong directional movements
        if abs(features['momentum']) > 0.6:
            momentum_direction = "bullish" if features['momentum'] > 0 else "bearish"
            momentum_strategy = {
                "name": "momentum",
                "direction": momentum_direction,
                "confidence": round(abs(features['momentum']), 4),
                "timeframe": "short",
                "params": {
                    "entry": "market",
                    "stop_distance": "medium"
                }
            }
            recommendations.append(momentum_strategy)
            
        # Sort recommendations by confidence
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Only return top 3 strategies
        return recommendations[:3]
    
    def _record_decision(self, 
                       symbol: str,
                       features: Dict[str, float],
                       confidence_score: float,
                       recommended_strategies: List[Dict[str, Any]]) -> None:
        """
        Record decision for future learning and optimization.
        
        Args:
            symbol: Trading symbol
            features: Extracted features
            confidence_score: Overall confidence score
            recommended_strategies: Strategies that were recommended
        """
        decision_record = {
            "timestamp": time.time(),
            "symbol": symbol,
            "features": features,
            "confidence_score": confidence_score,
            "recommended_strategies": recommended_strategies
        }
        
        self.historical_decisions.append(decision_record)
        
        # Keep only the most recent decisions to avoid memory bloat
        max_decisions = self.config.get('max_historical_decisions', 1000)
        if len(self.historical_decisions) > max_decisions:
            self.historical_decisions = self.historical_decisions[-max_decisions:]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the AI decision module.
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            "decisions_analyzed": len(self.historical_decisions),
            "average_confidence": self._calculate_average_confidence(),
            "last_update_time": self.last_update_time,
            "enabled": self.enabled,
            "confidence_threshold": self.confidence_threshold
        }
    
    def _calculate_average_confidence(self) -> float:
        """
        Calculate the average confidence score from historical decisions.
        
        Returns:
            Average confidence score
        """
        if not self.historical_decisions:
            return 0.0
            
        total = sum(d["confidence_score"] for d in self.historical_decisions)
        return total / len(self.historical_decisions)
    
    def update_feature_weights(self, new_weights: Dict[str, float]) -> None:
        """
        Update the feature weights based on performance feedback.
        
        Args:
            new_weights: Dictionary of new feature weights
        """
        if not new_weights:
            return
            
        # Validate weights
        for feature, weight in new_weights.items():
            if feature in self.feature_weights and 0.0 <= weight <= 1.0:
                self.feature_weights[feature] = weight
                
        # Normalize weights to sum to 1
        total = sum(self.feature_weights.values())
        if total > 0:
            for feature in self.feature_weights:
                self.feature_weights[feature] /= total
                
        logger.info(f"AI Decision Module feature weights updated: {self.feature_weights}")
