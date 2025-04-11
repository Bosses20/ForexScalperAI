"""
Security Hardening module for Forex Trading Bot
Implements security policies, rate limiting, IP restrictions, and protections against common attacks
"""

import ipaddress
import json
import logging
import os
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps
from threading import Lock
from typing import Dict, List, Optional, Set, Tuple, Union, Callable

import geoip2.database
import geoip2.errors
import requests
from loguru import logger

from src.monitoring.alert_manager import AlertManager
from src.utils.security import verify_jwt_token


class SecurityHardening:
    """
    Security hardening features for the Forex Trading Bot
    Provides centralized security policy enforcement
    """
    
    def __init__(self, config: dict, alert_manager: Optional[AlertManager] = None):
        """
        Initialize security hardening module
        
        Args:
            config: Configuration dictionary
            alert_manager: Optional alert manager for security notifications
        """
        self.config = config
        self.alert_manager = alert_manager
        
        # Rate limiting
        self.rate_limits = config.get("rate_limits", {
            "default": {"limit": 100, "window": 60},  # Default: 100 requests per minute
            "login": {"limit": 5, "window": 60},      # Login: 5 attempts per minute
            "api_access": {"limit": 50, "window": 60}  # API: 50 requests per minute
        })
        self.rate_limit_store = defaultdict(lambda: defaultdict(deque))
        self.rate_limit_lock = Lock()
        
        # IP restrictions
        self.ip_whitelist = set(config.get("ip_whitelist", []))
        self.ip_blacklist = set(config.get("ip_blacklist", []))
        self.allowed_countries = set(config.get("allowed_countries", []))
        self.blocked_countries = set(config.get("blocked_countries", []))
        
        # GeoIP database path
        self.geoip_db_path = config.get("geoip_db_path", "data/GeoLite2-Country.mmdb")
        self.geoip_enabled = os.path.exists(self.geoip_db_path)
        self.geoip_reader = None
        
        if self.geoip_enabled:
            try:
                self.geoip_reader = geoip2.database.Reader(self.geoip_db_path)
                logger.info(f"GeoIP database loaded from {self.geoip_db_path}")
            except Exception as e:
                logger.error(f"Failed to load GeoIP database: {str(e)}")
                self.geoip_enabled = False
        
        # Security settings
        self.enable_xss_protection = config.get("enable_xss_protection", True)
        self.enable_csrf_protection = config.get("enable_csrf_protection", True)
        self.enable_clickjacking_protection = config.get("enable_clickjacking_protection", True)
        self.enable_content_security_policy = config.get("enable_content_security_policy", True)
        
        # CSRF token store
        self.csrf_tokens = {}
        self.csrf_token_expiry = config.get("csrf_token_expiry", 3600)  # 1 hour default
        
        # Security audit log
        self.audit_log_file = config.get("security_audit_log", "logs/security_audit.log")
        self.audit_logger = self._setup_audit_logger()
        
        # Bad behavior detection
        self.failed_auth_attempts = defaultdict(lambda: {"count": 0, "last_attempt": None})
        self.suspicious_patterns = {
            "sql_injection": r"(\b(?:union|select|insert|update|delete|drop|alter)\b.*\b(?:from|table|database|where)\b)",
            "xss": r"(<script>|<\/script>|javascript:|\balert\s*\(|\beval\s*\()",
            "path_traversal": r"(\.\.\/|\.\.\\)",
            "command_injection": r"(;|\||\`|\$\(|\&\&|\|\|)"
        }
        
        # Temporary bans
        self.temporary_bans = {}  # IP -> expiry timestamp
        
        logger.info("Security hardening module initialized")
        
    def _setup_audit_logger(self):
        """
        Set up a dedicated logger for security audit events
        
        Returns:
            Logger instance for security auditing
        """
        # Ensure directory exists
        log_dir = os.path.dirname(self.audit_log_file)
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a audit logger
        audit_logger = logging.getLogger("security.audit")
        audit_logger.setLevel(logging.INFO)
        
        # Create a file handler
        handler = logging.FileHandler(self.audit_log_file)
        
        # Create a formatter with timestamp
        formatter = logging.Formatter(
            '%(asctime)s [SECURITY] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add the handler to the logger
        audit_logger.addHandler(handler)
        
        return audit_logger
        
    def audit_log(self, event_type: str, message: str, severity: str = "INFO", ip_address: Optional[str] = None,
                  user_id: Optional[str] = None, additional_data: Optional[dict] = None):
        """
        Log a security audit event
        
        Args:
            event_type: Type of security event
            message: Description of the event
            severity: Severity level (INFO, WARNING, ERROR, CRITICAL)
            ip_address: IP address associated with the event
            user_id: User ID associated with the event
            additional_data: Additional data to include in the log
        """
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "message": message,
            "severity": severity
        }
        
        if ip_address:
            event_data["ip_address"] = ip_address
            
        if user_id:
            event_data["user_id"] = user_id
            
        if additional_data:
            event_data["data"] = additional_data
            
        log_message = json.dumps(event_data)
        
        if severity == "INFO":
            self.audit_logger.info(log_message)
        elif severity == "WARNING":
            self.audit_logger.warning(log_message)
            if self.alert_manager:
                self.alert_manager.send_alert("medium", "Security Warning", message)
        elif severity == "ERROR":
            self.audit_logger.error(log_message)
            if self.alert_manager:
                self.alert_manager.send_alert("high", "Security Error", message)
        elif severity == "CRITICAL":
            self.audit_logger.critical(log_message)
            if self.alert_manager:
                self.alert_manager.send_alert("critical", "Security Critical", message, 
                                             include_data=True, data=event_data)
        
    def check_rate_limit(self, key: str, category: str = "default") -> Tuple[bool, int]:
        """
        Check if a rate limit has been exceeded
        
        Args:
            key: Unique identifier (IP, user ID, etc.)
            category: Rate limit category
            
        Returns:
            Tuple of (is_allowed, retry_after)
        """
        with self.rate_limit_lock:
            # Get rate limit settings
            limit_settings = self.rate_limits.get(category, self.rate_limits["default"])
            limit = limit_settings["limit"]
            window = limit_settings["window"]
            
            current_time = time.time()
            request_history = self.rate_limit_store[category][key]
            
            # Remove expired entries
            cutoff_time = current_time - window
            while request_history and request_history[0] < cutoff_time:
                request_history.popleft()
            
            # Check if we've hit the limit
            if len(request_history) >= limit:
                # Calculate retry-after time
                retry_after = int(request_history[0] - cutoff_time)
                return False, retry_after
            
            # Add current request timestamp
            request_history.append(current_time)
            return True, 0
            
    def is_ip_allowed(self, ip_address: str) -> bool:
        """
        Check if an IP address is allowed based on whitelists/blacklists
        
        Args:
            ip_address: IP address to check
            
        Returns:
            True if the IP is allowed, False otherwise
        """
        # Check for temporary ban
        if ip_address in self.temporary_bans:
            ban_expiry = self.temporary_bans[ip_address]
            if time.time() < ban_expiry:
                return False
            else:
                # Ban expired, remove it
                del self.temporary_bans[ip_address]
        
        # Check blacklist first (deny has priority)
        for cidr in self.ip_blacklist:
            try:
                if ipaddress.ip_address(ip_address) in ipaddress.ip_network(cidr, strict=False):
                    self.audit_log(
                        "ip_blocked", 
                        f"IP {ip_address} blocked (blacklisted)", 
                        "WARNING", 
                        ip_address
                    )
                    return False
            except Exception:
                # Invalid IP format or CIDR notation
                continue
                
        # If whitelist exists and is not empty, only IPs in whitelist are allowed
        if self.ip_whitelist:
            for cidr in self.ip_whitelist:
                try:
                    if ipaddress.ip_address(ip_address) in ipaddress.ip_network(cidr, strict=False):
                        return True
                except Exception:
                    # Invalid IP format or CIDR notation
                    continue
                    
            # IP not in whitelist
            self.audit_log(
                "ip_blocked", 
                f"IP {ip_address} blocked (not in whitelist)", 
                "WARNING", 
                ip_address
            )
            return False
        
        # If no explicit whitelist, check country restrictions
        if self.allowed_countries or self.blocked_countries:
            country_code = self.get_ip_country(ip_address)
            
            if country_code:
                # Check if country is blocked
                if country_code in self.blocked_countries:
                    self.audit_log(
                        "country_blocked", 
                        f"IP {ip_address} from {country_code} blocked (country blacklisted)", 
                        "WARNING", 
                        ip_address,
                        additional_data={"country": country_code}
                    )
                    return False
                
                # If allowed countries specified, check if country is allowed
                if self.allowed_countries and country_code not in self.allowed_countries:
                    self.audit_log(
                        "country_blocked", 
                        f"IP {ip_address} from {country_code} blocked (country not in whitelist)", 
                        "WARNING", 
                        ip_address,
                        additional_data={"country": country_code}
                    )
                    return False
        
        # Default to allowed if not explicitly denied
        return True
        
    def get_ip_country(self, ip_address: str) -> Optional[str]:
        """
        Get the country code for an IP address
        
        Args:
            ip_address: IP address to lookup
            
        Returns:
            Two-letter country code or None if not found
        """
        if not self.geoip_enabled or not self.geoip_reader:
            return None
            
        try:
            response = self.geoip_reader.country(ip_address)
            return response.country.iso_code
        except geoip2.errors.AddressNotFoundError:
            return None
        except Exception as e:
            logger.error(f"GeoIP lookup error for {ip_address}: {str(e)}")
            return None
            
    def temporary_ban(self, ip_address: str, ban_duration: int = 3600) -> None:
        """
        Temporarily ban an IP address
        
        Args:
            ip_address: IP address to ban
            ban_duration: Ban duration in seconds (default: 1 hour)
        """
        ban_expiry = time.time() + ban_duration
        self.temporary_bans[ip_address] = ban_expiry
        
        self.audit_log(
            "temporary_ban", 
            f"IP {ip_address} temporarily banned for {ban_duration} seconds", 
            "WARNING", 
            ip_address,
            additional_data={"duration": ban_duration, "expiry": datetime.fromtimestamp(ban_expiry).isoformat()}
        )
        
    def generate_csrf_token(self, session_id: str) -> str:
        """
        Generate a CSRF token for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            CSRF token
        """
        import secrets
        
        # Generate a random token
        token = secrets.token_hex(32)
        
        # Store token with expiry
        expiry = time.time() + self.csrf_token_expiry
        self.csrf_tokens[session_id] = {"token": token, "expiry": expiry}
        
        return token
        
    def verify_csrf_token(self, session_id: str, token: str) -> bool:
        """
        Verify a CSRF token for a session
        
        Args:
            session_id: Session identifier
            token: CSRF token to verify
            
        Returns:
            True if token is valid, False otherwise
        """
        # Check if token exists for session
        if session_id not in self.csrf_tokens:
            return False
            
        token_data = self.csrf_tokens[session_id]
        
        # Check if token has expired
        if time.time() > token_data["expiry"]:
            # Remove expired token
            del self.csrf_tokens[session_id]
            return False
            
        # Validate token
        return token == token_data["token"]
        
    def clean_expired_csrf_tokens(self) -> None:
        """
        Remove expired CSRF tokens
        """
        current_time = time.time()
        expired_tokens = [
            session_id for session_id, token_data in self.csrf_tokens.items()
            if current_time > token_data["expiry"]
        ]
        
        for session_id in expired_tokens:
            del self.csrf_tokens[session_id]
            
    def detect_attack_patterns(self, data: str) -> List[str]:
        """
        Detect potential attack patterns in string data
        
        Args:
            data: String data to analyze
            
        Returns:
            List of detected attack types
        """
        detected_attacks = []
        
        for attack_type, pattern in self.suspicious_patterns.items():
            if re.search(pattern, data, re.IGNORECASE):
                detected_attacks.append(attack_type)
                
        return detected_attacks
        
    def track_failed_auth(self, identifier: str) -> Tuple[int, bool]:
        """
        Track failed authentication attempts
        
        Args:
            identifier: User identifier (username, IP, etc.)
            
        Returns:
            Tuple of (failure count, should lock)
        """
        max_failures = self.config.get("max_auth_failures", 5)
        lockout_duration = self.config.get("auth_lockout_duration", 1800)  # 30 minutes
        
        current_time = time.time()
        auth_data = self.failed_auth_attempts[identifier]
        
        # Check if previous failures have expired (reset after 24 hours)
        if auth_data["last_attempt"] and current_time - auth_data["last_attempt"] > 86400:
            auth_data["count"] = 0
        
        # Increment failure count
        auth_data["count"] += 1
        auth_data["last_attempt"] = current_time
        
        # Check if account should be locked
        should_lock = auth_data["count"] >= max_failures
        
        if should_lock:
            self.audit_log(
                "account_lockout", 
                f"Account {identifier} locked after {auth_data['count']} failed authentication attempts",
                "WARNING",
                user_id=identifier,
                additional_data={"failures": auth_data["count"], "lockout_duration": lockout_duration}
            )
        
        return auth_data["count"], should_lock
        
    def reset_auth_failures(self, identifier: str) -> None:
        """
        Reset authentication failures after successful login
        
        Args:
            identifier: User identifier (username, IP, etc.)
        """
        if identifier in self.failed_auth_attempts:
            del self.failed_auth_attempts[identifier]
            
    def secure_headers(self) -> Dict[str, str]:
        """
        Generate secure HTTP headers for API responses
        
        Returns:
            Dictionary of security headers
        """
        headers = {}
        
        if self.enable_xss_protection:
            headers["X-XSS-Protection"] = "1; mode=block"
            
        if self.enable_clickjacking_protection:
            headers["X-Frame-Options"] = "DENY"
            
        headers["X-Content-Type-Options"] = "nosniff"
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        if self.enable_content_security_policy:
            headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
            
        return headers
        
    def secure_request(self, func: Callable) -> Callable:
        """
        Decorator for securing API requests with various security checks
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function
        """
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Get client IP
            ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
            
            # Check if IP is allowed
            if not self.is_ip_allowed(ip_address):
                self.audit_log(
                    "access_denied", 
                    f"Access denied for IP {ip_address}",
                    "WARNING",
                    ip_address
                )
                return {"error": "Access denied"}, 403
                
            # Check rate limits
            is_allowed, retry_after = self.check_rate_limit(ip_address, "api_access")
            if not is_allowed:
                self.audit_log(
                    "rate_limit", 
                    f"Rate limit exceeded for IP {ip_address}",
                    "WARNING",
                    ip_address,
                    additional_data={"retry_after": retry_after}
                )
                return {"error": "Rate limit exceeded", "retry_after": retry_after}, 429
                
            # Check for attack patterns in GET/POST data
            data_to_check = []
            
            # Check query parameters
            if hasattr(request, "args"):
                for key, value in request.args.items():
                    data_to_check.append(f"{key}={value}")
                    
            # Check form data
            if hasattr(request, "form"):
                for key, value in request.form.items():
                    data_to_check.append(f"{key}={value}")
                    
            # Check JSON data
            if hasattr(request, "json") and request.json:
                data_to_check.append(json.dumps(request.json))
                
            # Join all data for scanning
            all_data = " ".join(data_to_check)
            
            # Detect attack patterns
            attacks = self.detect_attack_patterns(all_data)
            if attacks:
                self.audit_log(
                    "attack_detected", 
                    f"Potential attack detected from IP {ip_address}: {', '.join(attacks)}",
                    "ERROR",
                    ip_address,
                    additional_data={"attack_types": attacks}
                )
                
                # Ban IP for serious attacks
                if any(attack in ["sql_injection", "command_injection"] for attack in attacks):
                    self.temporary_ban(ip_address)
                    
                return {"error": "Invalid request"}, 400
                
            # Add security headers to response
            response = func(request, *args, **kwargs)
            
            # If response is a tuple (data, status_code), add headers to data portion
            if isinstance(response, tuple) and len(response) >= 2:
                data, status_code = response[0], response[1]
                headers = {}
                
                # If more than 2 elements and 3rd is headers, use those
                if len(response) > 2 and isinstance(response[2], dict):
                    headers = response[2]
                    
                # Add security headers
                for header, value in self.secure_headers().items():
                    headers[header] = value
                    
                # Return updated response
                return data, status_code, headers
            
            return response
            
        return wrapper
        
    def jwt_auth_required(self, func: Callable) -> Callable:
        """
        Decorator for requiring JWT authentication
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function
        """
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Get JWT token from Authorization header
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return {"error": "Missing or invalid authorization header"}, 401
                
            token = auth_header.split(" ")[1]
            
            try:
                # Verify JWT token
                token_data = verify_jwt_token(token)
                
                # Add user data to request
                request.user = token_data
                
                # Reset failed authentication attempts
                self.reset_auth_failures(token_data.get("sub", ""))
                
            except Exception as e:
                return {"error": "Invalid or expired token"}, 401
                
            return func(request, *args, **kwargs)
            
        return wrapper
        
    def get_audit_logs(self, event_type: Optional[str] = None, 
                     severity: Optional[str] = None,
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     ip_address: Optional[str] = None,
                     user_id: Optional[str] = None,
                     limit: int = 100) -> List[Dict]:
        """
        Retrieve security audit logs with optional filtering
        
        Args:
            event_type: Filter by event type
            severity: Filter by severity level
            start_time: Filter by start time
            end_time: Filter by end time
            ip_address: Filter by IP address
            user_id: Filter by user ID
            limit: Maximum number of records to return
            
        Returns:
            List of audit log entries
        """
        logs = []
        
        try:
            with open(self.audit_log_file, 'r') as f:
                for line in f:
                    try:
                        # Extract JSON part from log line
                        json_str = line.strip().split('[SECURITY]')[1].strip()
                        log_entry = json.loads(json_str)
                        
                        # Apply filters
                        if event_type and log_entry.get("event_type") != event_type:
                            continue
                            
                        if severity and log_entry.get("severity") != severity:
                            continue
                            
                        if start_time:
                            log_time = datetime.fromisoformat(log_entry.get("timestamp", ""))
                            if log_time < start_time:
                                continue
                                
                        if end_time:
                            log_time = datetime.fromisoformat(log_entry.get("timestamp", ""))
                            if log_time > end_time:
                                continue
                                
                        if ip_address and log_entry.get("ip_address") != ip_address:
                            continue
                            
                        if user_id and log_entry.get("user_id") != user_id:
                            continue
                            
                        logs.append(log_entry)
                        
                        if len(logs) >= limit:
                            break
                            
                    except Exception:
                        # Skip malformed log entries
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading audit log file: {str(e)}")
            
        return logs
        
    def generate_security_report(self) -> Dict:
        """
        Generate a comprehensive security report
        
        Returns:
            Dictionary with security statistics and metrics
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "metrics": {},
            "recent_events": []
        }
        
        # Collect security metrics
        try:
            # Count of events by type
            event_counts = defaultdict(int)
            severity_counts = defaultdict(int)
            blocked_ips = set()
            blocked_countries = set()
            
            # Get events from last 24 hours
            end_time = datetime.now()
            start_time = end_time - timedelta(days=1)
            
            recent_events = self.get_audit_logs(
                start_time=start_time, 
                end_time=end_time,
                limit=1000
            )
            
            for event in recent_events:
                event_type = event.get("event_type", "unknown")
                severity = event.get("severity", "INFO")
                ip = event.get("ip_address")
                
                event_counts[event_type] += 1
                severity_counts[severity] += 1
                
                # Track blocked IPs and countries
                if event_type == "ip_blocked" and ip:
                    blocked_ips.add(ip)
                    
                if event_type == "country_blocked" and "data" in event:
                    country = event["data"].get("country")
                    if country:
                        blocked_countries.add(country)
                        
            report["metrics"]["event_counts"] = dict(event_counts)
            report["metrics"]["severity_counts"] = dict(severity_counts)
            report["metrics"]["unique_blocked_ips"] = len(blocked_ips)
            report["metrics"]["unique_blocked_countries"] = len(blocked_countries)
            
            # Add recent critical events
            critical_events = [
                event for event in recent_events 
                if event.get("severity") in ["ERROR", "CRITICAL"]
            ]
            report["recent_events"] = sorted(
                critical_events,
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )[:10]  # Top 10 most recent critical events
            
        except Exception as e:
            logger.error(f"Error generating security report: {str(e)}")
            
        return report
