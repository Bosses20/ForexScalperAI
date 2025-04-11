"""
AI Integration Module for Forex Trading Bot

This module integrates the AI Decision Module with the Market Condition Detector 
and Multi-Asset Trading systems to provide enhanced trading decisions.
"""

import logging
import time
from typing import Dict, List, Any, Optional
import threading
import json
import os
from pathlib import Path

# Import related modules
from src.strategies.ai_decision_module import AIDecisionModule
from src.market.market_condition_detector import MarketConditionDetector
from src.trading.multi_asset_integrator import MultiAssetIntegrator

# Initialize logger
logger = logging.getLogger('ai_integration')

class AIIntegration:
    """
    Integrates AI decision making with market condition detection and multi-asset trading
    to provide unified, intelligent trading decisions.
    """
    
    def __init__(self, config: Dict[str, Any], data_dir: str = 'data'):
        """
        Initialize the AI Integration module.
        
        Args:
            config: Configuration dictionary
            data_dir: Directory for storing AI data
        """
        self.config = config
        self.ai_config = config.get('ai_enhanced_trading', {})
        self.enabled = self.ai_config.get('enabled', True)
        self.update_interval = self.ai_config.get('update_interval_seconds', 300)  # 5 minutes default
        
        # Initialize the AI decision module
        self.ai_module = AIDecisionModule(config)
        
        # These will be set later when connected
        self.market_detector = None
        self.multi_asset = None
        
        # Setup data storage
        self.data_dir = data_dir
        self.ai_data_dir = os.path.join(data_dir, 'ai_data')
        self._ensure_directories()
        
        # Cache for AI decisions
        self.decision_cache = {}
        self.last_update_time = 0
        
        # Threading
        self.running = False
        self.update_thread = None
        self.lock = threading.Lock()
        
        logger.info("AI Integration module initialized")
    
    def _ensure_directories(self) -> None:
        """Ensure that necessary directories exist"""
        Path(self.ai_data_dir).mkdir(parents=True, exist_ok=True)
    
    def connect_modules(self, 
                       market_detector: MarketConditionDetector, 
                       multi_asset: MultiAssetIntegrator) -> None:
        """
        Connect the required modules for integration.
        
        Args:
            market_detector: Market condition detector instance
            multi_asset: Multi-asset trading integrator instance
        """
        self.market_detector = market_detector
        self.multi_asset = multi_asset
        logger.info("Connected market detector and multi-asset modules to AI integration")
    
    def start(self) -> None:
        """Start the AI integration background processing"""
        if self.running:
            logger.warning("AI Integration is already running")
            return
            
        if not self.enabled:
            logger.info("AI Integration is disabled in configuration")
            return
            
        if not self.market_detector or not self.multi_asset:
            logger.error("Cannot start AI Integration: Required modules not connected")
            return
            
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logger.info("AI Integration started")
    
    def stop(self) -> None:
        """Stop the AI integration background processing"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5.0)
        logger.info("AI Integration stopped")
    
    def _update_loop(self) -> None:
        """Background thread for updating AI decisions"""
        while self.running:
            try:
                # Check if it's time to update
                current_time = time.time()
                if current_time - self.last_update_time >= self.update_interval:
                    self._update_all_decisions()
                    self.last_update_time = current_time
                    
                    # Save decisions to disk periodically
                    self._save_decisions()
            except Exception as e:
                logger.error(f"Error in AI Integration update loop: {str(e)}")
                
            # Sleep for a short interval to avoid high CPU usage
            time.sleep(10)
    
    def _update_all_decisions(self) -> None:
        """Update AI decisions for all active instruments"""
        if not self.market_detector or not self.multi_asset:
            logger.warning("Cannot update decisions: Required modules not connected")
            return
            
        try:
            # Get active instruments from multi-asset integrator
            active_instruments = self.multi_asset.get_active_instruments()
            
            # Get market conditions for all active instruments
            market_conditions = {}
            for symbol in active_instruments:
                market_conditions[symbol] = self.market_detector.analyze_market_conditions(symbol)
            
            # Get multi-asset data (correlations, etc.)
            multi_asset_data = self.multi_asset.get_status()
            
            # Update decisions for each instrument
            with self.lock:
                for symbol in active_instruments:
                    symbol_market_conditions = market_conditions.get(symbol, {})
                    decision = self.ai_module.analyze_trading_opportunity(
                        symbol, symbol_market_conditions, multi_asset_data
                    )
                    self.decision_cache[symbol] = decision
                    
            logger.debug(f"Updated AI decisions for {len(active_instruments)} instruments")
            
        except Exception as e:
            logger.error(f"Error updating AI decisions: {str(e)}")
    
    def get_decision(self, symbol: str) -> Dict[str, Any]:
        """
        Get the latest AI decision for a specific symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with AI decision details
        """
        if not self.enabled:
            return {"enabled": False, "message": "AI integration is disabled"}
            
        with self.lock:
            # If we have a cached decision, return it
            if symbol in self.decision_cache:
                return self.decision_cache[symbol]
                
        # If no cached decision and modules are available, generate one on-demand
        if self.market_detector and self.multi_asset:
            try:
                market_conditions = self.market_detector.analyze_market_conditions(symbol)
                multi_asset_data = self.multi_asset.get_status()
                
                decision = self.ai_module.analyze_trading_opportunity(
                    symbol, market_conditions, multi_asset_data
                )
                
                # Cache the decision
                with self.lock:
                    self.decision_cache[symbol] = decision
                    
                return decision
            except Exception as e:
                logger.error(f"Error getting decision for {symbol}: {str(e)}")
                return {
                    "error": True,
                    "message": f"Failed to analyze {symbol}: {str(e)}",
                    "favorable_for_trading": False
                }
        else:
            return {
                "error": True,
                "message": "Required modules not connected",
                "favorable_for_trading": False
            }
    
    def get_all_decisions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all cached AI decisions.
        
        Returns:
            Dictionary mapping symbols to their AI decisions
        """
        with self.lock:
            return dict(self.decision_cache)
    
    def validate_trade(self, 
                     symbol: str, 
                     direction: str, 
                     risk_level: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a potential trade against AI recommendations.
        
        Args:
            symbol: Trading symbol
            direction: Trade direction ('buy' or 'sell')
            risk_level: Optional risk level to check against
            
        Returns:
            Dictionary with validation results
        """
        decision = self.get_decision(symbol)
        
        if "error" in decision or not decision.get("favorable_for_trading", False):
            return {
                "valid": False,
                "confidence": decision.get("confidence_score", 0.0),
                "reason": "Market conditions unfavorable for trading",
                "alternative_suggestions": self._get_alternative_suggestions()
            }
            
        # Check if any recommended strategy matches the direction
        recommended_strategies = decision.get("recommended_strategies", [])
        matching_strategy = None
        
        for strategy in recommended_strategies:
            strategy_direction = strategy.get("direction", "")
            
            if strategy_direction == "both" or strategy_direction == "neutral":
                # Neutral strategies can work in either direction
                matching_strategy = strategy
                break
            elif direction.lower() == "buy" and strategy_direction == "bullish":
                matching_strategy = strategy
                break
            elif direction.lower() == "sell" and strategy_direction == "bearish":
                matching_strategy = strategy
                break
        
        # Check risk level if specified
        risk_validated = True
        if risk_level and decision.get("risk_level") != risk_level:
            risk_validated = False
        
        # Determine validation result
        if matching_strategy and risk_validated:
            return {
                "valid": True,
                "confidence": matching_strategy.get("confidence", 0.0),
                "recommended_strategy": matching_strategy.get("name", ""),
                "risk_level": decision.get("risk_level", "medium"),
                "entry_points": decision.get("entry_points", {})
            }
        elif matching_strategy and not risk_validated:
            return {
                "valid": False,
                "confidence": matching_strategy.get("confidence", 0.0),
                "reason": f"Risk level mismatch. Trade requires {decision.get('risk_level')} risk, but {risk_level} was specified",
                "recommended_strategy": matching_strategy.get("name", "")
            }
        else:
            return {
                "valid": False,
                "confidence": decision.get("confidence_score", 0.0),
                "reason": f"No matching strategy found for {direction} direction on {symbol}",
                "suggested_direction": self._get_suggested_direction(decision)
            }
    
    def _get_suggested_direction(self, decision: Dict[str, Any]) -> str:
        """
        Extract the suggested direction from a decision.
        
        Args:
            decision: AI decision dictionary
            
        Returns:
            Suggested direction or 'neutral'
        """
        strategies = decision.get("recommended_strategies", [])
        if not strategies:
            return "neutral"
            
        # Use the highest confidence strategy
        top_strategy = strategies[0]
        direction = top_strategy.get("direction", "neutral")
        
        if direction == "bullish":
            return "buy"
        elif direction == "bearish":
            return "sell"
        else:
            return "neutral"
    
    def _get_alternative_suggestions(self) -> List[Dict[str, Any]]:
        """
        Get alternative trading suggestions from other symbols.
        
        Returns:
            List of alternative trading suggestions
        """
        alternatives = []
        
        with self.lock:
            # Find the top 3 instruments with highest confidence
            sorted_decisions = sorted(
                [(symbol, decision) for symbol, decision in self.decision_cache.items() 
                 if decision.get("favorable_for_trading", False)],
                key=lambda x: x[1].get("confidence_score", 0),
                reverse=True
            )
            
            # Take top 3
            for symbol, decision in sorted_decisions[:3]:
                direction = self._get_suggested_direction(decision)
                alternatives.append({
                    "symbol": symbol,
                    "direction": direction,
                    "confidence": decision.get("confidence_score", 0.0),
                    "risk_level": decision.get("risk_level", "medium")
                })
                
        return alternatives
    
    def _save_decisions(self) -> None:
        """Save current decisions to disk for analysis"""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.ai_data_dir, f'decisions_{timestamp}.json')
            
            with self.lock:
                decisions_copy = dict(self.decision_cache)
                
            # Add metadata
            data = {
                "timestamp": time.time(),
                "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "decisions": decisions_copy,
                "metrics": self.ai_module.get_performance_metrics()
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
                
            # Clean up old files (keep last 24 hours / 288 files at 5-minute intervals)
            self._cleanup_old_files()
            
        except Exception as e:
            logger.error(f"Error saving AI decisions: {str(e)}")
    
    def _cleanup_old_files(self) -> None:
        """Clean up old decision files to prevent disk space issues"""
        try:
            files = list(Path(self.ai_data_dir).glob('decisions_*.json'))
            files.sort()
            
            # Keep only the latest 288 files (24 hours at 5-minute intervals)
            max_files = self.ai_config.get('max_saved_decisions', 288)
            
            if len(files) > max_files:
                files_to_delete = files[:-max_files]
                for file in files_to_delete:
                    os.remove(file)
                    
        except Exception as e:
            logger.error(f"Error cleaning up AI decision files: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the AI integration module.
        
        Returns:
            Dictionary with status information
        """
        return {
            "enabled": self.enabled,
            "running": self.running,
            "connected_modules": {
                "market_detector": self.market_detector is not None,
                "multi_asset": self.multi_asset is not None
            },
            "decisions_cached": len(self.decision_cache),
            "last_update_time": time.strftime("%Y-%m-%d %H:%M:%S", 
                                             time.localtime(self.last_update_time)),
            "update_interval_seconds": self.update_interval,
            "performance_metrics": self.ai_module.get_performance_metrics() if self.ai_module else {}
        }
