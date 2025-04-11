#!/bin/bash
# Forex Trading Bot Security Hardening Script
# This script implements security best practices for the trading bot server

echo "===== Forex Trading Bot Security Hardening ====="
echo "Implementing security best practices for the trading bot server..."

# Update and upgrade
echo "Step 1: Ensuring system is up-to-date..."
apt-get update && apt-get upgrade -y

# Install security packages
echo "Step 2: Installing security tools..."
apt-get install -y fail2ban ufw logwatch rkhunter lynis auditd

# Configure SSH
echo "Step 3: Hardening SSH configuration..."
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/X11Forwarding yes/X11Forwarding no/' /etc/ssh/sshd_config
systemctl restart sshd

# Configure firewall
echo "Step 4: Setting up firewall rules..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw allow 8000/tcp  # API port
ufw --force enable

# Set up fail2ban
echo "Step 5: Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF
systemctl restart fail2ban

# Set up API authentication middleware
echo "Step 6: Setting up API key authentication..."
cat > /opt/forex-trading-bot/src/api/middleware/auth.py << EOF
import time
import hmac
import hashlib
import base64
from functools import wraps
from flask import request, jsonify, current_app

def validate_api_key(api_key, secret_key, timestamp, signature):
    """Validate API key using HMAC authentication."""
    if not all([api_key, timestamp, signature]):
        return False
    
    # Check if timestamp is recent (within 5 minutes)
    if abs(int(time.time()) - int(timestamp)) > 300:
        return False
    
    # Lookup the secret key associated with the API key
    # In a real implementation, this would be retrieved from a database
    if api_key not in current_app.config['API_KEYS']:
        return False
    
    expected_secret = current_app.config['API_KEYS'][api_key]
    if expected_secret != secret_key:
        return False
    
    # Construct the message to sign
    message = f"{api_key}:{timestamp}"
    
    # Create the expected signature
    expected_signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(expected_signature, signature)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        timestamp = request.headers.get('X-Timestamp')
        signature = request.headers.get('X-Signature')
        secret_key = current_app.config['API_KEYS'].get(api_key, '')
        
        if not validate_api_key(api_key, secret_key, timestamp, signature):
            return jsonify({"error": "Unauthorized access"}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(limit=100, per=60):
    """Rate limiting decorator."""
    def decorator(f):
        requests = {}
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            
            if api_key not in requests:
                requests[api_key] = []
                
            # Remove old requests
            current_time = time.time()
            requests[api_key] = [req_time for req_time in requests[api_key] 
                               if current_time - req_time < per]
            
            # Check if rate limit exceeded
            if len(requests[api_key]) >= limit:
                return jsonify({
                    "error": "Rate limit exceeded",
                    "retry_after": per - (current_time - requests[api_key][0])
                }), 429
                
            # Add current request
            requests[api_key].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
EOF

# Configure automatic security updates
echo "Step 7: Setting up automatic security updates..."
apt-get install -y unattended-upgrades apt-listchanges
cat > /etc/apt/apt.conf.d/20auto-upgrades << EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

# Configure audit system
echo "Step 8: Setting up system auditing..."
cat > /etc/audit/rules.d/audit.rules << EOF
# Delete all previous rules
-D

# Set buffer size
-b 8192

# Monitor file access for configuration files
-w /opt/forex-trading-bot/config/ -p rwa -k config_changes

# Monitor authentication attempts
-w /var/log/auth.log -p rwa -k auth_log

# Monitor trading bot logs
-w /var/log/forex-trading-bot.log -p rwa -k trading_bot_log
-w /var/log/forex-api-server.log -p rwa -k api_server_log

# Monitor sudo commands
-w /var/log/sudo.log -p rwa -k sudo_log

# Monitor user/group changes
-w /etc/passwd -p wa -k user_modifications
-w /etc/group -p wa -k group_modifications

# Monitor network configurations
-w /etc/network/ -p wa -k network_modifications

# Monitor system startup scripts
-w /etc/init.d/ -p wa -k init_modifications
EOF
systemctl restart auditd

# Create database for storing API keys with encrypted storage
echo "Step 9: Setting up secure API key storage..."
mkdir -p /opt/forex-trading-bot/database
cat > /opt/forex-trading-bot/database/create_api_keys_table.sql << EOF
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_name VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) NOT NULL UNIQUE,
    secret_key_hash VARCHAR(255) NOT NULL,
    permissions TEXT[] NOT NULL,
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 60,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Create index on api_key for faster lookups
CREATE INDEX IF NOT EXISTS idx_api_key ON api_keys(api_key);

-- Create audit log table for API key usage
CREATE TABLE IF NOT EXISTS api_key_usage_log (
    id SERIAL PRIMARY KEY,
    api_key_id INTEGER REFERENCES api_keys(id),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    user_agent TEXT,
    request_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status_code INTEGER
);
EOF

# Run Lynis security audit
echo "Step 10: Running security audit with Lynis..."
lynis audit system --quick

echo "===== Security Hardening Complete ====="
echo "Security hardening completed successfully. Please review the following:"
echo "1. Update API keys in the database"
echo "2. Review firewall rules if needed"
echo "3. Check Lynis audit results for additional recommendations"
echo ""
echo "Remember to regularly review system logs and update security configurations."
