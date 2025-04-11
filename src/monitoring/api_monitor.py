"""
API monitoring for the Forex Trading Bot
Tracks API usage, rate limits, and performance metrics
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple, Any
from collections import deque, defaultdict
import threading
import json
import os
from loguru import logger


class APIMonitor:
    """
    Monitors API usage, rate limits, and performance metrics for the bot's API endpoints
    and external broker APIs
    """
    
    def __init__(self, config: dict):
        """
        Initialize the API monitor
        
        Args:
            config: Configuration dictionary with API monitoring settings
        """
        self.config = config
        self.log_file = config.get('api_log_file', 'data/logs/api_usage.log')
        self.enabled = config.get('api_monitoring_enabled', True)
        self.rate_limit_buffer = config.get('rate_limit_buffer', 0.1)  # 10% buffer
        self.alert_threshold = config.get('rate_limit_alert_threshold', 0.8)  # 80% of limit
        
        # Initialize API tracking
        self.api_calls = {}
        self.rate_limits = {}
        self.rate_windows = {}
        self.errors = defaultdict(list)
        self.last_save_time = time.time()
        self.save_interval = config.get('save_interval', 300)  # 5 minutes
        
        # Locks for thread safety
        self.api_lock = threading.RLock()
        
        # Create log directory
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        logger.info("API monitor initialized")
    
    def register_api(self, api_name: str, endpoints: Dict[str, Dict], 
                     rate_limits: Dict[str, Dict]) -> None:
        """
        Register an API with its endpoints and rate limits
        
        Args:
            api_name: Name of the API
            endpoints: Dictionary of endpoint definitions
            rate_limits: Dictionary of rate limit definitions
        """
        with self.api_lock:
            # Initialize API tracking if not exists
            if api_name not in self.api_calls:
                self.api_calls[api_name] = {}
                
            # Initialize rate limits
            self.rate_limits[api_name] = rate_limits
            
            # Initialize rate windows - using sliding window approach
            self.rate_windows[api_name] = {}
            
            for limit_name, limit_info in rate_limits.items():
                window_seconds = limit_info.get('window_seconds', 60)
                
                self.rate_windows[api_name][limit_name] = {
                    'window_seconds': window_seconds,
                    'calls': deque(maxlen=1000)  # Store timestamps of API calls
                }
                
            logger.info(f"Registered API: {api_name} with {len(endpoints)} endpoints and {len(rate_limits)} rate limits")
    
    def record_api_call(self, api_name: str, endpoint: str, method: str, 
                     status_code: int, response_time: float, 
                     user_id: Optional[str] = None,
                     metadata: Optional[Dict] = None) -> bool:
        """
        Record an API call with its details
        
        Args:
            api_name: Name of the API
            endpoint: API endpoint path
            method: HTTP method
            status_code: Response status code
            response_time: Response time in milliseconds
            user_id: Optional user ID making the request
            metadata: Optional additional metadata
            
        Returns:
            Boolean indicating if the call was recorded successfully
        """
        if not self.enabled:
            return True
            
        try:
            with self.api_lock:
                timestamp = datetime.now()
                
                # Initialize API tracking if not exists
                if api_name not in self.api_calls:
                    self.api_calls[api_name] = {}
                
                # Initialize endpoint tracking if not exists
                endpoint_key = f"{method}_{endpoint}"
                if endpoint_key not in self.api_calls[api_name]:
                    self.api_calls[api_name][endpoint_key] = {
                        'count': 0,
                        'success_count': 0,
                        'error_count': 0,
                        'total_time': 0,
                        'min_time': float('inf'),
                        'max_time': 0,
                        'response_times': deque(maxlen=100),
                        'last_calls': deque(maxlen=20),
                        'status_codes': defaultdict(int)
                    }
                
                # Update metrics
                endpoint_stats = self.api_calls[api_name][endpoint_key]
                endpoint_stats['count'] += 1
                endpoint_stats['total_time'] += response_time
                endpoint_stats['min_time'] = min(endpoint_stats['min_time'], response_time)
                endpoint_stats['max_time'] = max(endpoint_stats['max_time'], response_time)
                endpoint_stats['response_times'].append(response_time)
                endpoint_stats['status_codes'][str(status_code)] += 1
                
                # Determine if successful or error
                if 200 <= status_code < 300:
                    endpoint_stats['success_count'] += 1
                else:
                    endpoint_stats['error_count'] += 1
                
                # Record last call details
                call_details = {
                    'timestamp': timestamp.isoformat(),
                    'status_code': status_code,
                    'response_time': response_time,
                    'user_id': user_id
                }
                
                # Add metadata if provided
                if metadata:
                    call_details['metadata'] = metadata
                    
                endpoint_stats['last_calls'].append(call_details)
                
                # Update rate windows
                if api_name in self.rate_windows:
                    for limit_name, window_info in self.rate_windows[api_name].items():
                        window_info['calls'].append(timestamp)
                
                # Log API call
                self._log_api_call(api_name, endpoint, method, status_code, response_time, user_id, metadata)
                
                # Check if we should save metrics
                current_time = time.time()
                if current_time - self.last_save_time >= self.save_interval:
                    self.save_metrics()
                    self.last_save_time = current_time
                
                return True
                
        except Exception as e:
            logger.error(f"Error recording API call: {str(e)}")
            return False
    
    def record_api_error(self, api_name: str, endpoint: str, method: str, 
                       error_code: str, error_message: str,
                       user_id: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> None:
        """
        Record an API error
        
        Args:
            api_name: Name of the API
            endpoint: API endpoint path
            method: HTTP method
            error_code: Error code
            error_message: Error message
            user_id: Optional user ID making the request
            metadata: Optional additional metadata
        """
        if not self.enabled:
            return
            
        timestamp = datetime.now().isoformat()
        
        # Create error record
        error_record = {
            'timestamp': timestamp,
            'api_name': api_name,
            'endpoint': endpoint,
            'method': method,
            'error_code': error_code,
            'error_message': error_message,
            'user_id': user_id
        }
        
        # Add metadata if provided
        if metadata:
            error_record['metadata'] = metadata
            
        # Add to errors dictionary
        with self.api_lock:
            error_key = f"{api_name}_{method}_{endpoint}"
            self.errors[error_key].append(error_record)
            
            # Keep only last 100 errors per endpoint
            if len(self.errors[error_key]) > 100:
                self.errors[error_key].pop(0)
                
        # Log error
        logger.error(f"API Error: {api_name} {method} {endpoint} - {error_code}: {error_message}")
    
    def check_rate_limit(self, api_name: str, limit_name: Optional[str] = None) -> Dict:
        """
        Check current rate limit usage
        
        Args:
            api_name: Name of the API
            limit_name: Optional specific rate limit to check
            
        Returns:
            Dictionary with rate limit information
        """
        with self.api_lock:
            result = {}
            
            if api_name not in self.rate_limits:
                return {'error': f"API '{api_name}' not registered"}
                
            # If limit_name specified, check only that limit
            if limit_name:
                if limit_name not in self.rate_limits[api_name]:
                    return {'error': f"Rate limit '{limit_name}' not found for API '{api_name}'"}
                    
                return self._calculate_rate_limit_usage(api_name, limit_name)
                
            # Check all rate limits for the API
            for limit_name in self.rate_limits[api_name]:
                result[limit_name] = self._calculate_rate_limit_usage(api_name, limit_name)
                
            return result
    
    def _calculate_rate_limit_usage(self, api_name: str, limit_name: str) -> Dict:
        """
        Calculate current rate limit usage
        
        Args:
            api_name: Name of the API
            limit_name: Name of the rate limit
            
        Returns:
            Dictionary with rate limit usage information
        """
        # Get rate limit information
        limit_info = self.rate_limits[api_name][limit_name]
        window_info = self.rate_windows[api_name][limit_name]
        
        # Get max calls and window seconds
        max_calls = limit_info.get('max_calls', 60)
        window_seconds = window_info.get('window_seconds', 60)
        
        # Get current time
        now = datetime.now()
        
        # Count calls within window
        window_start = now - timedelta(seconds=window_seconds)
        
        # Filter calls within window
        calls_in_window = sum(1 for call_time in window_info['calls'] if call_time >= window_start)
        
        # Calculate percentage used
        percentage_used = (calls_in_window / max_calls) * 100
        
        # Calculate remaining calls
        remaining_calls = max(0, max_calls - calls_in_window)
        
        # Calculate reset time (when oldest call will expire)
        if window_info['calls'] and calls_in_window >= max_calls:
            oldest_call = min(call for call in window_info['calls'] if call >= window_start)
            reset_seconds = (oldest_call + timedelta(seconds=window_seconds) - now).total_seconds()
        else:
            reset_seconds = 0
            
        # Determine if approaching limit
        approaching_limit = percentage_used >= (self.alert_threshold * 100)
        
        # Create result dictionary
        result = {
            'limit_name': limit_name,
            'max_calls': max_calls,
            'window_seconds': window_seconds,
            'calls_in_window': calls_in_window,
            'remaining_calls': remaining_calls,
            'percentage_used': percentage_used,
            'reset_seconds': reset_seconds,
            'approaching_limit': approaching_limit
        }
        
        return result
    
    def should_throttle(self, api_name: str, limit_name: Optional[str] = None) -> bool:
        """
        Check if API calls should be throttled based on rate limits
        
        Args:
            api_name: Name of the API
            limit_name: Optional specific rate limit to check
            
        Returns:
            True if calls should be throttled, False otherwise
        """
        if not self.enabled:
            return False
            
        with self.api_lock:
            # Check rate limits
            rate_limits = self.check_rate_limit(api_name, limit_name)
            
            # If checking specific limit
            if limit_name:
                if 'error' in rate_limits:
                    return False
                    
                # Throttle if approaching limit with buffer
                percentage_used = rate_limits.get('percentage_used', 0)
                throttle_threshold = (1 - self.rate_limit_buffer) * 100
                
                return percentage_used >= throttle_threshold
                
            # Check all limits if no specific limit specified
            for limit_info in rate_limits.values():
                if isinstance(limit_info, dict) and 'percentage_used' in limit_info:
                    percentage_used = limit_info.get('percentage_used', 0)
                    throttle_threshold = (1 - self.rate_limit_buffer) * 100
                    
                    if percentage_used >= throttle_threshold:
                        return True
                        
            return False
    
    def get_api_statistics(self, api_name: Optional[str] = None, endpoint: Optional[str] = None) -> Dict:
        """
        Get API usage statistics
        
        Args:
            api_name: Optional API name filter
            endpoint: Optional endpoint filter
            
        Returns:
            Dictionary with API usage statistics
        """
        if not self.enabled:
            return {}
            
        with self.api_lock:
            result = {}
            
            # If API name specified
            if api_name:
                if api_name not in self.api_calls:
                    return {}
                    
                # If endpoint specified, get only that endpoint
                if endpoint:
                    for endpoint_key, stats in self.api_calls[api_name].items():
                        if endpoint in endpoint_key:
                            result[endpoint_key] = self._calculate_api_stats(stats)
                else:
                    # Get all endpoints for the API
                    for endpoint_key, stats in self.api_calls[api_name].items():
                        result[endpoint_key] = self._calculate_api_stats(stats)
                        
                return {api_name: result}
                
            # Get all APIs and endpoints
            for api_name, endpoints in self.api_calls.items():
                api_result = {}
                
                for endpoint_key, stats in endpoints.items():
                    api_result[endpoint_key] = self._calculate_api_stats(stats)
                    
                result[api_name] = api_result
                
            return result
    
    def _calculate_api_stats(self, stats: Dict) -> Dict:
        """
        Calculate API statistics from raw data
        
        Args:
            stats: Raw API statistics
            
        Returns:
            Dictionary with calculated statistics
        """
        count = stats['count']
        if count == 0:
            return {
                'count': 0,
                'success_count': 0,
                'error_count': 0,
                'success_rate': 0,
                'avg_time': 0,
                'min_time': 0,
                'max_time': 0,
                'status_codes': {}
            }
            
        # Calculate statistics
        success_rate = (stats['success_count'] / count) * 100 if count > 0 else 0
        avg_time = stats['total_time'] / count if count > 0 else 0
        
        return {
            'count': count,
            'success_count': stats['success_count'],
            'error_count': stats['error_count'],
            'success_rate': success_rate,
            'avg_time': avg_time,
            'min_time': stats['min_time'],
            'max_time': stats['max_time'],
            'status_codes': dict(stats['status_codes']),
            'last_call': stats['last_calls'][-1]['timestamp'] if stats['last_calls'] else None
        }
    
    def get_errors(self, api_name: Optional[str] = None, 
                endpoint: Optional[str] = None, 
                limit: int = 100) -> List[Dict]:
        """
        Get API errors
        
        Args:
            api_name: Optional API name filter
            endpoint: Optional endpoint filter
            limit: Maximum number of errors to return
            
        Returns:
            List of error dictionaries
        """
        if not self.enabled:
            return []
            
        with self.api_lock:
            result = []
            
            for error_key, errors in self.errors.items():
                if api_name and api_name not in error_key:
                    continue
                    
                if endpoint and endpoint not in error_key:
                    continue
                    
                # Add errors to result
                result.extend(errors)
                
            # Sort by timestamp (newest first)
            result.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Apply limit
            return result[:limit]
    
    def _log_api_call(self, api_name: str, endpoint: str, method: str, 
                   status_code: int, response_time: float, 
                   user_id: Optional[str] = None,
                   metadata: Optional[Dict] = None) -> None:
        """
        Log an API call to the log file
        
        Args:
            api_name: Name of the API
            endpoint: API endpoint path
            method: HTTP method
            status_code: Response status code
            response_time: Response time in milliseconds
            user_id: Optional user ID making the request
            metadata: Optional additional metadata
        """
        try:
            # Create log record
            log_record = {
                'timestamp': datetime.now().isoformat(),
                'api_name': api_name,
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'response_time': response_time,
                'user_id': user_id
            }
            
            # Add metadata if provided
            if metadata:
                log_record['metadata'] = metadata
                
            # Write to log file
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_record) + '\n')
                
        except Exception as e:
            logger.error(f"Error logging API call: {str(e)}")
    
    def save_metrics(self) -> bool:
        """
        Save API metrics to file
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            # Create metrics file
            metrics_file = os.path.join(os.path.dirname(self.log_file), 'api_metrics.json')
            
            # Create metrics data
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'api_calls': self.get_api_statistics(),
                'rate_limits': {}
            }
            
            # Add rate limit data
            for api_name in self.rate_limits:
                metrics_data['rate_limits'][api_name] = self.check_rate_limit(api_name)
                
            # Write to file
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
                
            logger.debug(f"Saved API metrics to {metrics_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving API metrics: {str(e)}")
            return False
    
    def reset_metrics(self) -> None:
        """
        Reset all API metrics
        """
        with self.api_lock:
            self.api_calls = {}
            self.errors = defaultdict(list)
            
            # Reset rate windows
            for api_name in self.rate_windows:
                for limit_name in self.rate_windows[api_name]:
                    self.rate_windows[api_name][limit_name]['calls'].clear()
                    
            logger.info("API metrics reset")
