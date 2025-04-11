# Forex Trading Bot Troubleshooting Guide

This guide provides systematic approaches to identifying and resolving common issues with the Forex Trading Bot system.

## Table of Contents

1. [System Status Check](#system-status-check)
2. [Connectivity Issues](#connectivity-issues)
3. [Trading System Issues](#trading-system-issues)
4. [Database Issues](#database-issues)
5. [Performance Issues](#performance-issues)
6. [Security Incidents](#security-incidents)
7. [Log Analysis](#log-analysis)
8. [Common Error Codes](#common-error-codes)
9. [Support Escalation](#support-escalation)

## System Status Check

### Quick System Verification

Run the following command to check the status of all system components:

```bash
sudo systemctl status forex-trading-bot forex-api-server mt5-connector trading-database
```

### Diagnostic Script

For a comprehensive system check, run the diagnostic script:

```bash
cd /opt/forex-trading-bot/scripts
./system_diagnostics.sh
```

This script checks:
- All service statuses
- System resource usage
- Network connectivity
- Database health
- MT5 connection status
- API endpoint health

### Health Checking Endpoints

The API provides health check endpoints:

- System Status: `GET /v1/health/system`
- MT5 Connectivity: `GET /v1/health/mt5`
- Database Status: `GET /v1/health/database`
- Trading Engine Status: `GET /v1/health/trading-engine`

Example:
```bash
curl -H "X-API-Key: your_api_key" http://localhost:8000/v1/health/system
```

## Connectivity Issues

### MetaTrader 5 Connection Problems

#### Symptoms:
- Trading bot logs show "Unable to connect to MT5"
- No data being received from MT5
- Trades not being executed

#### Troubleshooting Steps:

1. **Verify MT5 Terminal Status**
   ```bash
   ps aux | grep terminal.exe
   ```

2. **Check MT5 Logs**
   ```bash
   cat /var/log/forex-trading-bot/mt5_connector.log
   ```

3. **Test MT5 Connectivity**
   ```bash
   cd /opt/forex-trading-bot/tools
   python test_mt5_connection.py
   ```

4. **Common Solutions**:
   - Restart MT5 terminal:
     ```bash
     supervisorctl restart mt5_terminal
     ```
   - Check credentials in `config/mt5_config.yaml`
   - Verify MT5 is allowed in the firewall:
     ```bash
     sudo ufw status
     ```
   - Check broker server status

### API Connection Issues

#### Symptoms:
- 502 Bad Gateway errors
- Clients unable to connect to API
- Timeout errors

#### Troubleshooting Steps:

1. **Check API Server Status**
   ```bash
   systemctl status forex-api-server
   ```

2. **Verify NGINX Configuration**
   ```bash
   sudo nginx -t
   ```

3. **Check API Logs**
   ```bash
   tail -n 100 /var/log/forex-trading-bot/api_server.log
   ```

4. **Test API Locally**
   ```bash
   curl -v http://localhost:8000/v1/health/system
   ```

5. **Common Solutions**:
   - Restart API service:
     ```bash
     supervisorctl restart forex-api-server
     ```
   - Check NGINX configuration:
     ```bash
     cat /etc/nginx/sites-enabled/forex-trading-bot
     ```
   - Verify port and firewall settings:
     ```bash
     sudo netstat -tulpn | grep 8000
     sudo ufw status
     ```

### Database Connection Issues

#### Symptoms:
- Error logs showing database connection failures
- API returns 500 errors on data requests
- Trading bot not recording trades

#### Troubleshooting Steps:

1. **Check Database Service Status**
   ```bash
   systemctl status postgresql
   ```

2. **Verify Database Logs**
   ```bash
   tail -n 100 /var/log/postgresql/postgresql-13-main.log
   ```

3. **Test Database Connection**
   ```bash
   cd /opt/forex-trading-bot/tools
   python test_db_connection.py
   ```

4. **Common Solutions**:
   - Restart PostgreSQL:
     ```bash
     sudo systemctl restart postgresql
     ```
   - Check database credentials:
     ```bash
     cat /opt/forex-trading-bot/config/database_config.yaml
     ```
   - Verify database user permissions:
     ```bash
     sudo -u postgres psql -c "\du"
     ```
   - Check database disk space:
     ```bash
     df -h /var/lib/postgresql
     ```

## Trading System Issues

### Bot Not Executing Trades

#### Symptoms:
- Bot identifies trading signals but doesn't execute trades
- No error messages in logs
- Account shows sufficient balance

#### Troubleshooting Steps:

1. **Check Trading Permission Settings**
   ```bash
   cat /opt/forex-trading-bot/config/trading_config.yaml | grep enabled
   ```

2. **Verify Risk Management Limits**
   ```bash
   cd /opt/forex-trading-bot/tools
   python check_risk_limits.py
   ```

3. **Check for Circuit Breakers**
   ```bash
   cat /opt/forex-trading-bot/data/circuit_breakers.json
   ```

4. **Verify MT5 Trading Permissions**
   - Log into MT5 and check account permissions
   - Verify AutoTrading is enabled in MT5

5. **Common Solutions**:
   - Reset circuit breakers:
     ```bash
     cd /opt/forex-trading-bot/scripts
     ./reset_circuit_breakers.sh
     ```
   - Check account status:
     ```bash
     python check_account_status.py
     ```
   - Increase log verbosity for debugging:
     ```bash
     sed -i 's/INFO/DEBUG/g' /opt/forex-trading-bot/config/logging_config.yaml
     supervisorctl restart forex-trading-bot
     ```

### Incorrect Trading Behavior

#### Symptoms:
- Bot opens positions with wrong lot sizes
- Stop losses or take profits incorrectly placed
- Wrong currency pairs being traded

#### Troubleshooting Steps:

1. **Check Strategy Configuration**
   ```bash
   cat /opt/forex-trading-bot/config/trading_config.yaml
   ```

2. **Verify Position Sizing Calculation**
   ```bash
   cd /opt/forex-trading-bot/tools
   python test_position_sizing.py
   ```

3. **Check for Recent Configuration Changes**
   ```bash
   cd /opt/forex-trading-bot
   git diff HEAD~10 HEAD -- config/
   ```

4. **Common Solutions**:
   - Restore configuration from backup:
     ```bash
     cp /var/backups/forex-trading-bot/config_backup_latest.tar.gz /tmp/
     cd /tmp
     tar xzf config_backup_latest.tar.gz
     cp -r config/* /opt/forex-trading-bot/config/
     ```
   - Validate configuration files:
     ```bash
     cd /opt/forex-trading-bot/tools
     python validate_config.py
     ```

### Strategy Not Generating Signals

#### Symptoms:
- No trading signals being generated
- Bot running but inactive
- No errors in logs

#### Troubleshooting Steps:

1. **Check Market Data Reception**
   ```bash
   cd /opt/forex-trading-bot/tools
   python check_market_data.py
   ```

2. **Verify Strategy Settings**
   ```bash
   cat /opt/forex-trading-bot/config/trading_config.yaml | grep -A 20 strategies
   ```

3. **Review Market Condition Filters**
   ```bash
   cat /opt/forex-trading-bot/logs/market_conditions.log
   ```

4. **Common Solutions**:
   - Adjust strategy parameters:
     ```bash
     vi /opt/forex-trading-bot/config/trading_config.yaml
     ```
   - Disable market condition filtering temporarily:
     ```bash
     sed -i 's/use_market_condition_filter: true/use_market_condition_filter: false/g' /opt/forex-trading-bot/config/trading_config.yaml
     ```
   - Check symbol configuration:
     ```bash
     cat /opt/forex-trading-bot/config/mt5_config.yaml | grep -A 50 symbols
     ```

## Database Issues

### Database Corruption

#### Symptoms:
- SQL errors in logs
- Inconsistent query results
- Bot crashing when accessing certain data

#### Troubleshooting Steps:

1. **Run Database Check**
   ```bash
   sudo -u postgres vacuumdb --analyze --verbose trading_bot_db
   ```

2. **Check Database Logs**
   ```bash
   tail -n 200 /var/log/postgresql/postgresql-13-main.log
   ```

3. **Backup Current Database**
   ```bash
   cd /opt/forex-trading-bot/scripts
   ./backup_database.sh emergency_backup
   ```

4. **Common Solutions**:
   - Restore from last backup:
     ```bash
     cd /opt/forex-trading-bot/scripts
     ./restore_database.sh --latest
     ```
   - Repair database:
     ```bash
     sudo -u postgres psql trading_bot_db -c "REINDEX DATABASE trading_bot_db;"
     ```
   - Check disk health:
     ```bash
     sudo smartctl -a /dev/sda
     ```

### Database Performance Issues

#### Symptoms:
- Slow query responses
- High CPU usage by database
- Timeouts when accessing trade history

#### Troubleshooting Steps:

1. **Check Database Statistics**
   ```bash
   sudo -u postgres psql trading_bot_db -c "SELECT * FROM pg_stat_activity;"
   ```

2. **Identify Slow Queries**
   ```bash
   tail -n 1000 /var/log/postgresql/postgresql-13-main.log | grep -i "duration:"
   ```

3. **Check Index Health**
   ```bash
   sudo -u postgres psql trading_bot_db -c "\di+"
   ```

4. **Common Solutions**:
   - Vacuum the database:
     ```bash
     sudo -u postgres vacuumdb --analyze --verbose trading_bot_db
     ```
   - Optimize database configuration:
     ```bash
     vi /etc/postgresql/13/main/postgresql.conf
     ```
   - Add missing indexes:
     ```bash
     cd /opt/forex-trading-bot/scripts
     ./optimize_database.sh
     ```

## Performance Issues

### High CPU Usage

#### Symptoms:
- System load consistently high
- Bot operations slow
- CPU usage above 80% for extended periods

#### Troubleshooting Steps:

1. **Identify Resource-Intensive Processes**
   ```bash
   top -c
   ```

2. **Check System Load History**
   ```bash
   sar -u 1 10
   ```

3. **Profile Python Processes**
   ```bash
   cd /opt/forex-trading-bot/tools
   python profile_bot.py
   ```

4. **Common Solutions**:
   - Reduce number of monitored symbols:
     ```bash
     vi /opt/forex-trading-bot/config/mt5_config.yaml
     ```
   - Increase timeframe intervals:
     ```bash
     vi /opt/forex-trading-bot/config/trading_config.yaml
     ```
   - Disable resource-intensive strategies:
     ```bash
     vi /opt/forex-trading-bot/config/trading_config.yaml
     ```
   - Check for and kill orphaned processes:
     ```bash
     ps aux | grep python | grep -v grep
     ```

### Memory Leaks

#### Symptoms:
- Increasing memory usage over time
- Bot slows down after running for days
- Eventually crashes due to OOM (Out of Memory)

#### Troubleshooting Steps:

1. **Monitor Memory Usage**
   ```bash
   watch -n 5 'ps -o pid,user,%mem,command ax | sort -b -k3 -r | head -n 20'
   ```

2. **Check for Python Memory Leaks**
   ```bash
   cd /opt/forex-trading-bot/tools
   python memory_profiler.py
   ```

3. **Analyze Memory Usage Patterns**
   ```bash
   cd /opt/forex-trading-bot/tools
   python analyze_memory.py --days 7
   ```

4. **Common Solutions**:
   - Implement scheduled restarts:
     ```bash
     crontab -e
     # Add: 0 3 * * * supervisorctl restart forex-trading-bot
     ```
   - Check for and fix memory leaks:
     ```bash
     cd /opt/forex-trading-bot
     grep -r "append" --include="*.py" .
     ```
   - Update memory-intensive libraries:
     ```bash
     pip list --outdated
     pip install --upgrade pandas numpy
     ```

### Slow API Responses

#### Symptoms:
- API endpoints taking >1s to respond
- Timeout errors from clients
- Dashboard loading slowly

#### Troubleshooting Steps:

1. **Profile API Endpoints**
   ```bash
   cd /opt/forex-trading-bot/tools
   python profile_api.py
   ```

2. **Check API Server Load**
   ```bash
   cat /var/log/forex-trading-bot/api_server.log | grep "response_time"
   ```

3. **Check Database Query Performance**
   ```bash
   sudo -u postgres psql trading_bot_db -c "SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 20;"
   ```

4. **Common Solutions**:
   - Optimize slow endpoints:
     ```bash
     vi /opt/forex-trading-bot/src/api/endpoints/performance.py
     ```
   - Add caching:
     ```bash
     vi /opt/forex-trading-bot/src/api/middleware/cache.py
     ```
   - Implement pagination:
     ```bash
     vi /opt/forex-trading-bot/src/api/endpoints/trades.py
     ```
   - Scale API server:
     ```bash
     vi /etc/supervisor/conf.d/forex-trading-bot.conf
     # Increase numprocs
     ```

## Security Incidents

### Unauthorized Access Attempts

#### Symptoms:
- Unusual login attempts in logs
- Failed authentication attempts
- Unexpected IP addresses in access logs

#### Troubleshooting Steps:

1. **Check Authentication Logs**
   ```bash
   grep "authentication failure" /var/log/auth.log
   ```

2. **Review API Access Logs**
   ```bash
   cat /var/log/nginx/access.log | grep 401
   ```

3. **Check for Brute Force Attempts**
   ```bash
   cat /var/log/fail2ban.log
   ```

4. **Common Solutions**:
   - Block suspicious IPs:
     ```bash
     sudo ufw deny from [SUSPICIOUS_IP]
     ```
   - Reset API keys:
     ```bash
     cd /opt/forex-trading-bot/scripts
     ./reset_api_keys.sh
     ```
   - Enable additional security measures:
     ```bash
     cd /opt/forex-trading-bot/scripts
     ./enhance_security.sh
     ```
   - Update firewall rules:
     ```bash
     sudo ufw status
     sudo ufw deny from xxx.xxx.xxx.0/24
     ```

### Unusual Trading Activity

#### Symptoms:
- Unexplained trades
- Trades outside configured parameters
- Higher trading frequency than expected

#### Troubleshooting Steps:

1. **Review Recent Trading Logs**
   ```bash
   cat /var/log/forex-trading-bot/trading.log | grep "OPEN_POSITION"
   ```

2. **Check for Unauthorized API Access**
   ```bash
   cat /var/log/forex-trading-bot/api_server.log | grep "API_KEY" | sort | uniq -c
   ```

3. **Verify Strategy Configuration**
   ```bash
   cd /opt/forex-trading-bot
   git diff -- config/trading_config.yaml
   ```

4. **Common Solutions**:
   - Temporarily halt trading:
     ```bash
     cd /opt/forex-trading-bot/scripts
     ./emergency_stop.sh
     ```
   - Close all open positions:
     ```bash
     cd /opt/forex-trading-bot/scripts
     ./close_all_positions.sh
     ```
   - Reset all API keys:
     ```bash
     cd /opt/forex-trading-bot/scripts
     ./reset_all_api_keys.sh
     ```
   - Enable additional trading validation:
     ```bash
     vi /opt/forex-trading-bot/config/security_config.yaml
     # Set enforce_strict_validation: true
     ```

## Log Analysis

### Critical Log Patterns

The following log patterns indicate serious issues:

#### MT5 Connection Errors
```
ERROR - Failed to connect to MT5: Login timeout
ERROR - MT5 connection lost during trading operation
CRITICAL - Unable to retrieve account information from MT5
```

#### Trading Errors
```
ERROR - Order execution failed: [Error Code]
ERROR - Stop loss placement failed for order [Order ID]
CRITICAL - Risk management check failed: Maximum drawdown exceeded
WARNING - Circuit breaker activated: [Reason]
```

#### API Server Errors
```
ERROR - Database connection failed in API endpoint [Endpoint]
ERROR - Authentication failed: Invalid API key [Key ID]
WARNING - Rate limit exceeded for API key [Key ID]
CRITICAL - API server out of memory
```

#### Database Errors
```
ERROR - Database query failed: [SQL Error]
ERROR - Database connection timeout
CRITICAL - Database disk full
WARNING - Slow query detected: [Query]
```

### Log Analysis Tools

Use these tools to analyze the trading bot logs:

1. **Quick Error Summary**
   ```bash
   grep -i "error\|critical\|warning" /var/log/forex-trading-bot/*.log | sort -k1,1 | uniq -c
   ```

2. **Analyze Trading Patterns**
   ```bash
   cd /opt/forex-trading-bot/tools
   python analyze_trading_logs.py --days 7
   ```

3. **Check Errors by Time Period**
   ```bash
   cd /opt/forex-trading-bot/tools
   python error_analysis.py --start "2023-01-01" --end "2023-01-07"
   ```

4. **Custom Log Analysis**
   ```bash
   cd /opt/forex-trading-bot/tools
   python custom_log_analysis.py --pattern "your pattern" --log trading.log
   ```

## Common Error Codes

### MT5 Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| 10004 | Requote | Increase maximum deviation or use market orders |
| 10006 | Order rejected | Check account status and trading permissions |
| 10007 | Order modification denied | Check if position still exists |
| 10010 | Price has changed | Update price and retry |
| 10013 | Invalid stops | Check broker minimum stop distance |
| 10014 | Invalid trade parameters | Verify lot size, take profit, and stop loss values |
| 10018 | Market closed | Wait for market to open or switch to different pair |

### System Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| ERR_CONNECTION_MT5 | Unable to connect to MT5 | Check MT5 status and credentials |
| ERR_DATA_RETRIEVAL | Cannot retrieve market data | Verify symbol configuration and permissions |
| ERR_POSITION_OPEN | Failed to open position | Check logs for specific MT5 error code |
| ERR_RISK_EXCEEDED | Risk parameters exceeded | Verify risk settings or adjust position size |
| ERR_CIRCUIT_BREAKER | Circuit breaker activated | Check trading logs for reason |
| ERR_DATABASE_CONN | Database connection error | Check database status |
| ERR_API_AUTH | API authentication failure | Verify API key and permissions |

## Support Escalation

### When to Escalate

Escalate to the support team when:

1. Critical system components remain down after basic troubleshooting
2. Data loss or corruption is detected
3. Unauthorized access is confirmed
4. Trading anomalies cannot be explained or resolved
5. Performance issues persist after optimization attempts

### Escalation Process

1. **Prepare Support Information**
   ```bash
   cd /opt/forex-trading-bot/scripts
   ./collect_support_info.sh
   ```
   This creates a support package at `/tmp/forex_bot_support_YYYY-MM-DD.zip`

2. **Contact Support Channels**

   - **Email**: support@forextradingbot.com
   - **Emergency Phone**: +1-XXX-XXX-XXXX
   - **Support Portal**: https://support.forextradingbot.com

3. **Information to Provide**

   - System ID (found in `/opt/forex-trading-bot/system_id.txt`)
   - Error messages and relevant log snippets
   - Steps already taken to resolve the issue
   - Changes made prior to the issue occurring
   - Support package generated above

---

## Quick Reference

### Common Maintenance Commands

```bash
# Restart all services
supervisorctl restart all

# View logs in real-time
tail -f /var/log/forex-trading-bot/trading.log

# Check system status
cd /opt/forex-trading-bot/scripts
./system_status.sh

# Backup configuration
cd /opt/forex-trading-bot/scripts
./backup_config.sh

# Update the trading bot
cd /opt/forex-trading-bot
git pull
pip install -r requirements.txt
supervisorctl restart forex-trading-bot
```

### Emergency Commands

```bash
# Stop all trading immediately
cd /opt/forex-trading-bot/scripts
./emergency_stop.sh

# Close all open positions
cd /opt/forex-trading-bot/scripts
./close_all_positions.sh

# Reset API keys (in case of compromise)
cd /opt/forex-trading-bot/scripts
./reset_api_keys.sh

# Restore from backup
cd /opt/forex-trading-bot/scripts
./restore_from_backup.sh --latest
```

---

**Last Updated**: YYYY-MM-DD  
**Document Owner**: [Name], [Role]
