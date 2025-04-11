"""
Data Integrity Monitor for the Forex Trading Bot
Validates and verifies the integrity of trading data
"""

import os
import json
import time
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from collections import deque

from .logger import get_logger

logger = get_logger("DataIntegrityMonitor")


class DataIntegrityMonitor:
    """
    Monitors and validates data integrity across the trading system.
    Performs checks on price data, order execution, database consistency,
    and other critical data sources.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the data integrity monitor
        
        Args:
            config: Configuration dictionary with data integrity settings
        """
        self.config = config
        self.enabled = config.get('data_integrity_enabled', True)
        self.check_interval = config.get('check_interval_seconds', 300)  # 5 minutes
        self.history_size = config.get('history_size', 100)
        
        # Initialize data validation rules
        self.validation_rules = self._get_validation_rules()
        
        # Initialize violation history
        self.violation_history = deque(maxlen=self.history_size)
        
        # Initialize validation history
        self.validation_history = {}
        for rule_id in self.validation_rules:
            self.validation_history[rule_id] = deque(maxlen=self.history_size)
            
        # Track custom validation functions
        self.custom_validators = {}
        
        # Set up alert manager
        self.alert_manager = None
        
        # Start monitoring
        if self.enabled:
            self._start_monitoring()
            
        logger.info(f"Data integrity monitor initialized with {len(self.validation_rules)} validation rules")
    
    def _get_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        Get data validation rules
        
        Returns:
            Dictionary of validation rules
        """
        # Get default rules
        default_rules = {
            "price_data_continuity": {
                "name": "Price Data Continuity",
                "description": "Checks for gaps in price data",
                "type": "price_data",
                "severity": "high",
                "params": {
                    "max_gap_seconds": 60
                }
            },
            "price_data_range": {
                "name": "Price Data Range",
                "description": "Validates price ranges for each instrument",
                "type": "price_data",
                "severity": "high",
                "params": {
                    "max_deviation_percent": 2.0
                }
            },
            "order_execution_precision": {
                "name": "Order Execution Precision",
                "description": "Verifies order execution matches requested parameters",
                "type": "order_execution",
                "severity": "high",
                "params": {
                    "max_price_slippage": 0.0005,  # 5 pips
                    "max_time_deviation_ms": 500
                }
            },
            "database_consistency": {
                "name": "Database Consistency",
                "description": "Validates database records against expected schema",
                "type": "database",
                "severity": "medium",
                "params": {}
            },
            "position_data_integrity": {
                "name": "Position Data Integrity",
                "description": "Verifies position data is consistent across systems",
                "type": "position_data",
                "severity": "critical",
                "params": {}
            },
            "market_data_freshness": {
                "name": "Market Data Freshness",
                "description": "Verifies market data is current and up-to-date",
                "type": "market_data",
                "severity": "high",
                "params": {
                    "max_age_seconds": 60
                }
            },
            "account_balance_consistency": {
                "name": "Account Balance Consistency", 
                "description": "Verifies account balance is consistent with positions and transactions",
                "type": "account_data",
                "severity": "critical",
                "params": {
                    "max_discrepancy_percent": 0.1
                }
            }
        }
        
        # Get custom rules from config
        custom_rules = self.config.get('validation_rules', {})
        
        # Merge rules, with custom rules taking precedence
        merged_rules = {**default_rules, **custom_rules}
        
        return merged_rules
    
    def set_alert_manager(self, alert_manager: Any) -> None:
        """
        Set the alert manager for sending data integrity alerts
        
        Args:
            alert_manager: Alert manager instance
        """
        self.alert_manager = alert_manager
        logger.debug("Alert manager registered with data integrity monitor")
    
    def _start_monitoring(self) -> None:
        """
        Start the data integrity monitoring thread
        """
        def monitor_task():
            while self.enabled:
                try:
                    # Check all validation rules
                    self.validate_all_rules()
                    
                    # Sleep for the check interval
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"Error in data integrity monitoring: {str(e)}")
                    time.sleep(self.check_interval)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=monitor_task,
            daemon=True,
            name="DataIntegrityMonitoring"
        )
        monitor_thread.start()
        logger.debug("Data integrity monitoring thread started")
    
    def validate_all_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        Validate all rules and return results
        
        Returns:
            Dictionary with validation results for all rules
        """
        results = {}
        
        for rule_id, rule in self.validation_rules.items():
            try:
                result = self.validate_rule(rule_id)
                results[rule_id] = result
            except Exception as e:
                logger.error(f"Error validating rule '{rule_id}': {str(e)}")
                results[rule_id] = {
                    "id": rule_id,
                    "name": rule.get("name", rule_id),
                    "timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "error": str(e)
                }
                
        return results
    
    def validate_rule(self, rule_id: str) -> Dict[str, Any]:
        """
        Validate a specific rule
        
        Args:
            rule_id: ID of the rule to validate
            
        Returns:
            Validation result dictionary
        """
        if rule_id not in self.validation_rules:
            logger.warning(f"Unknown validation rule: {rule_id}")
            return {"status": "unknown", "error": "Unknown validation rule"}
            
        rule = self.validation_rules[rule_id]
        rule_type = rule.get("type", "custom")
        
        # Initialize result
        result = {
            "id": rule_id,
            "name": rule.get("name", rule_id),
            "timestamp": datetime.now().isoformat(),
            "type": rule_type,
            "severity": rule.get("severity", "medium"),
            "status": "unknown",
            "violations": [],
            "error": None
        }
        
        # Validate based on rule type
        try:
            if rule_type == "price_data":
                self._validate_price_data(rule, result)
            elif rule_type == "order_execution":
                self._validate_order_execution(rule, result)
            elif rule_type == "database":
                self._validate_database(rule, result)
            elif rule_type == "position_data":
                self._validate_position_data(rule, result)
            elif rule_type == "market_data":
                self._validate_market_data(rule, result)
            elif rule_type == "account_data":
                self._validate_account_data(rule, result)
            elif rule_type == "custom" and rule_id in self.custom_validators:
                # Run custom validator
                custom_result = self.custom_validators[rule_id](rule)
                result.update(custom_result)
            else:
                result["status"] = "error"
                result["error"] = f"Unsupported rule type: {rule_type}"
                
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            
        # Update validation history
        if rule_id in self.validation_history:
            self.validation_history[rule_id].append(result)
            
        # Record violations
        if result["status"] == "violation" and result["violations"]:
            for violation in result["violations"]:
                violation_data = {
                    "rule_id": rule_id,
                    "rule_name": result["name"],
                    "timestamp": result["timestamp"],
                    "severity": result["severity"],
                    "details": violation
                }
                self.violation_history.append(violation_data)
                
                # Send alert if alert manager is available
                if self.alert_manager:
                    try:
                        level = "warning"
                        if result["severity"] == "critical":
                            level = "critical"
                        elif result["severity"] == "high":
                            level = "error"
                            
                        self.alert_manager.send_alert(
                            level=level,
                            title=f"Data Integrity Violation: {result['name']}",
                            message=f"{violation['message']}",
                            source="data_integrity",
                            data=violation_data
                        )
                    except Exception as e:
                        logger.error(f"Error sending data integrity alert: {str(e)}")
                        
        return result
    
    def _validate_price_data(self, rule: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Validate price data integrity
        
        Args:
            rule: Validation rule
            result: Result dictionary to update
        """
        # This is a placeholder - in a real implementation, this would connect to the 
        # price data store and perform actual validations
        
        # For continuity check
        if rule["id"] == "price_data_continuity":
            # Simulate validation - in a real system we would check actual price data
            max_gap_seconds = rule["params"].get("max_gap_seconds", 60)
            
            # Placeholder validation logic
            # In a real system, we would:
            # 1. Get recent price data for each instrument
            # 2. Check for gaps beyond max_gap_seconds
            # 3. Record violations
            
            # Simulate occasional random violations
            if datetime.now().second % 60 < 5:  # Simulate a 5 second window when violations occur
                result["status"] = "violation"
                result["violations"] = [
                    {
                        "instrument": "EUR/USD",
                        "timestamp": datetime.now().isoformat(),
                        "gap_seconds": max_gap_seconds + 10,
                        "message": f"Price data gap of {max_gap_seconds + 10} seconds detected for EUR/USD"
                    }
                ]
            else:
                result["status"] = "ok"
                
        # For price range check
        elif rule["id"] == "price_data_range":
            # Simulate validation - in a real system we would check actual price data
            max_deviation_percent = rule["params"].get("max_deviation_percent", 2.0)
            
            # Placeholder validation logic
            # In a real system, we would:
            # 1. Get recent price data for each instrument
            # 2. Check for prices outside expected ranges
            # 3. Record violations
            
            # Simulate occasional random violations
            if datetime.now().second % 60 > 55:  # Simulate a 5 second window when violations occur
                result["status"] = "violation"
                result["violations"] = [
                    {
                        "instrument": "USD/JPY",
                        "timestamp": datetime.now().isoformat(),
                        "expected_range": [135.0, 145.0],
                        "actual_value": 146.2,
                        "deviation_percent": 2.5,
                        "message": f"USD/JPY price outside expected range: 146.2 (2.5% deviation)"
                    }
                ]
            else:
                result["status"] = "ok"
        else:
            result["status"] = "ok"
    
    def _validate_order_execution(self, rule: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Validate order execution integrity
        
        Args:
            rule: Validation rule
            result: Result dictionary to update
        """
        # Placeholder - in a real implementation, this would check order execution data
        
        # Default to OK for now
        result["status"] = "ok"
        
        # Simulate occasional slippage violations
        if datetime.now().minute % 15 == 0 and datetime.now().second < 10:
            max_price_slippage = rule["params"].get("max_price_slippage", 0.0005)
            actual_slippage = max_price_slippage * 1.2
            
            result["status"] = "violation"
            result["violations"] = [
                {
                    "order_id": f"ORD-{int(time.time())}",
                    "instrument": "GBP/USD",
                    "timestamp": datetime.now().isoformat(),
                    "requested_price": 1.2500,
                    "executed_price": 1.2507,
                    "slippage": actual_slippage,
                    "max_allowed": max_price_slippage,
                    "message": f"Order execution slippage of {actual_slippage:.6f} exceeded maximum allowed {max_price_slippage:.6f} for GBP/USD"
                }
            ]
    
    def _validate_database(self, rule: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Validate database consistency
        
        Args:
            rule: Validation rule
            result: Result dictionary to update
        """
        # Placeholder - in a real implementation, this would check database schemas
        
        # Simulate validation results
        result["status"] = "ok"
        
        # Simulate occasional violations
        if datetime.now().hour % 6 == 0 and datetime.now().minute == 0 and datetime.now().second < 30:
            result["status"] = "violation"
            result["violations"] = [
                {
                    "table": "trade_history",
                    "field": "execution_time",
                    "issue": "null_values",
                    "record_count": 5,
                    "message": "Found 5 records with NULL execution_time in trade_history table"
                }
            ]
    
    def _validate_position_data(self, rule: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Validate position data consistency
        
        Args:
            rule: Validation rule
            result: Result dictionary to update
        """
        # Placeholder - in a real implementation, this would check position data
        
        # Simulate validation results
        result["status"] = "ok"
        
        # Simulate very rare but critical violations
        if datetime.now().day % 30 == 0 and datetime.now().hour == 0 and datetime.now().minute == 0 and datetime.now().second < 30:
            result["status"] = "violation"
            result["violations"] = [
                {
                    "position_id": f"POS-{int(time.time())}",
                    "instrument": "EUR/JPY",
                    "mt5_size": 0.5,
                    "internal_size": 0.3,
                    "discrepancy": 0.2,
                    "message": "Position size discrepancy detected between MT5 and internal systems for EUR/JPY"
                }
            ]
    
    def _validate_market_data(self, rule: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Validate market data freshness
        
        Args:
            rule: Validation rule
            result: Result dictionary to update
        """
        # Placeholder - in a real implementation, this would check market data timestamps
        
        # Simulate validation results
        result["status"] = "ok"
        
        # Simulate occasional violations
        if datetime.now().minute % 10 == 9 and datetime.now().second > 50:
            max_age_seconds = rule["params"].get("max_age_seconds", 60)
            actual_age = max_age_seconds + 15
            
            result["status"] = "violation"
            result["violations"] = [
                {
                    "data_type": "price_feed",
                    "instrument": "USD/CAD",
                    "timestamp": (datetime.now() - timedelta(seconds=actual_age)).isoformat(),
                    "age_seconds": actual_age,
                    "max_allowed": max_age_seconds,
                    "message": f"Market data for USD/CAD is {actual_age} seconds old (max allowed: {max_age_seconds})"
                }
            ]
    
    def _validate_account_data(self, rule: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Validate account balance consistency
        
        Args:
            rule: Validation rule
            result: Result dictionary to update
        """
        # Placeholder - in a real implementation, this would compare account balance to positions
        
        # Simulate validation results
        result["status"] = "ok"
        
        # Simulate rare critical violations
        if datetime.now().day % 15 == 0 and datetime.now().hour == 0 and datetime.now().minute < 5:
            max_discrepancy_percent = rule["params"].get("max_discrepancy_percent", 0.1)
            actual_discrepancy = max_discrepancy_percent * 2
            
            result["status"] = "violation"
            result["violations"] = [
                {
                    "account_id": "MAIN_TRADING_ACCOUNT",
                    "mt5_balance": 10500.25,
                    "calculated_balance": 10550.75,
                    "discrepancy": 50.50,
                    "discrepancy_percent": actual_discrepancy,
                    "max_allowed_percent": max_discrepancy_percent,
                    "message": f"Account balance discrepancy of {actual_discrepancy:.2f}% exceeds maximum allowed {max_discrepancy_percent:.2f}%"
                }
            ]
    
    def register_custom_validator(self, rule_id: str, validator_func: Callable) -> bool:
        """
        Register a custom validation function
        
        Args:
            rule_id: Rule ID
            validator_func: Validation function that takes rule config and returns result
            
        Returns:
            True if registered successfully, False otherwise
        """
        if rule_id not in self.validation_rules:
            logger.warning(f"Trying to register validator for unknown rule: {rule_id}")
            return False
            
        self.custom_validators[rule_id] = validator_func
        
        logger.info(f"Registered custom validator for rule: {rule_id}")
        return True
    
    def add_validation_rule(self, rule_id: str, rule_config: Dict[str, Any]) -> bool:
        """
        Add a new validation rule
        
        Args:
            rule_id: Rule ID
            rule_config: Rule configuration
            
        Returns:
            True if added successfully, False otherwise
        """
        if rule_id in self.validation_rules:
            logger.warning(f"Validation rule already exists: {rule_id}")
            return False
            
        # Validate config
        if "name" not in rule_config:
            logger.warning(f"No name specified for validation rule {rule_id}")
            return False
            
        if "type" not in rule_config:
            logger.warning(f"No type specified for validation rule {rule_id}")
            return False
            
        # Add rule
        self.validation_rules[rule_id] = rule_config
        self.validation_history[rule_id] = deque(maxlen=self.history_size)
        
        # Validate rule immediately
        self.validate_rule(rule_id)
        
        logger.info(f"Added new validation rule: {rule_id}")
        return True
    
    def remove_validation_rule(self, rule_id: str) -> bool:
        """
        Remove a validation rule
        
        Args:
            rule_id: Rule ID
            
        Returns:
            True if removed successfully, False otherwise
        """
        if rule_id not in self.validation_rules:
            logger.warning(f"Unknown validation rule: {rule_id}")
            return False
            
        # Remove rule
        del self.validation_rules[rule_id]
        
        # Remove from validation history
        if rule_id in self.validation_history:
            del self.validation_history[rule_id]
            
        # Remove from custom validators
        if rule_id in self.custom_validators:
            del self.custom_validators[rule_id]
            
        logger.info(f"Removed validation rule: {rule_id}")
        return True
    
    def get_validation_status(self, rule_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current validation status
        
        Args:
            rule_id: Optional rule ID to get status for
            
        Returns:
            Status dictionary
        """
        if not self.enabled:
            return {"enabled": False}
            
        if rule_id:
            # Validate the rule and return result
            if rule_id in self.validation_rules:
                return self.validate_rule(rule_id)
            else:
                return {"error": f"Unknown validation rule: {rule_id}"}
                
        # Validate all rules
        return self.validate_all_rules()
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current validation status
        
        Returns:
            Status summary dictionary
        """
        if not self.enabled:
            return {"enabled": False}
            
        # Validate all rules
        results = self.validate_all_rules()
        
        # Count status types
        status_counts = {"ok": 0, "violation": 0, "error": 0, "unknown": 0}
        severity_violations = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        violations_count = 0
        
        for rule_id, result in results.items():
            status = result.get("status", "unknown")
            if status in status_counts:
                status_counts[status] += 1
                
            # Count violations by severity
            if status == "violation":
                severity = result.get("severity", "medium")
                if severity in severity_violations:
                    severity_violations[severity] += 1
                
                # Count total violations
                violations_count += len(result.get("violations", []))
                
        # Overall status
        overall_status = "ok"
        if status_counts["violation"] > 0:
            if severity_violations["critical"] > 0:
                overall_status = "critical"
            elif severity_violations["high"] > 0:
                overall_status = "error"
            else:
                overall_status = "warning"
        elif status_counts["error"] > 0:
            overall_status = "error"
            
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "status_counts": status_counts,
            "severity_violations": severity_violations,
            "total_violations": violations_count,
            "rules_count": len(results)
        }
    
    def get_violations(self, severity: Optional[str] = None, 
                     time_range_hours: int = 24,
                     limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get validation violations from history
        
        Args:
            severity: Optional filter by severity
            time_range_hours: Time range in hours
            limit: Maximum number of violations to return
            
        Returns:
            List of violation dictionaries
        """
        if not self.enabled:
            return []
            
        # Convert history to list for filtering
        violations = list(self.violation_history)
        
        # Filter by time range
        if time_range_hours > 0:
            cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
            filtered_violations = []
            
            for violation in violations:
                try:
                    violation_time = datetime.fromisoformat(violation["timestamp"])
                    if violation_time >= cutoff_time:
                        filtered_violations.append(violation)
                except:
                    pass
                    
            violations = filtered_violations
            
        # Filter by severity
        if severity:
            violations = [v for v in violations if v.get("severity") == severity]
            
        # Sort by timestamp (newest first)
        violations.sort(key=lambda v: v.get("timestamp", ""), reverse=True)
        
        # Apply limit
        return violations[:limit]
    
    def get_validation_history(self, rule_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get validation history for a rule
        
        Args:
            rule_id: Rule ID
            limit: Maximum number of history entries to return
            
        Returns:
            List of validation result dictionaries
        """
        if not self.enabled or rule_id not in self.validation_history:
            return []
            
        # Convert deque to list and apply limit
        history = list(self.validation_history[rule_id])
        history.sort(key=lambda h: h.get("timestamp", ""), reverse=True)
        
        return history[:limit]
