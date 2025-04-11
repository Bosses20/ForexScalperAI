# Forex Trading Bot Disaster Recovery Procedures

This document outlines the procedures for recovering the Forex Trading Bot system in case of failures or emergencies. These procedures should be tested regularly to ensure they work as expected.

## Table of Contents
1. [Emergency Contacts](#emergency-contacts)
2. [Recovery Time Objectives](#recovery-time-objectives)
3. [Backup Systems](#backup-systems)
4. [Failure Scenarios and Recovery Procedures](#failure-scenarios-and-recovery-procedures)
5. [Testing and Maintenance](#testing-and-maintenance)

## Emergency Contacts

| Role | Contact Person | Email | Phone |
|------|----------------|-------|-------|
| System Administrator | [Name] | admin@example.com | +1-XXX-XXX-XXXX |
| Trading Manager | [Name] | trading@example.com | +1-XXX-XXX-XXXX |
| MT5 Support | [Name] | mt5support@example.com | +1-XXX-XXX-XXXX |
| Cloud Provider Support | [Provider] | support@provider.com | +1-XXX-XXX-XXXX |

## Recovery Time Objectives

| System Component | Recovery Time Objective (RTO) | Recovery Point Objective (RPO) |
|------------------|-------------------------------|--------------------------------|
| Trading Engine | 15 minutes | 5 minutes |
| API Service | 30 minutes | 10 minutes |
| Database | 1 hour | 5 minutes |
| Mobile App | 2 hours | 1 hour |
| Monitoring System | 1 hour | N/A |

## Backup Systems

The Forex Trading Bot utilizes the following backup mechanisms:

1. **Configuration Backups**: Daily snapshots of all configuration files stored in:
   - Local backup: `/var/backups/forex-trading-bot/`
   - Offsite backup: S3 bucket `s3://trading-bot-backups/`
   - Managed by the `BackupManager` class with automatic integrity verification

2. **Database Backups**:
   - Real-time replication to standby server
   - Hourly snapshots
   - Daily full backups retained for 30 days
   - SHA-256 checksums for all backup verification

3. **Trading Data**:
   - Real-time synchronization between primary and standby systems
   - Hourly snapshots of trading state
   - Historical trade data archived daily

4. **System Images**:
   - Weekly full system images
   - Stored in cloud provider's snapshot service

## Failure Scenarios and Recovery Procedures

### 1. Primary Server Failure

**Symptoms**: 
- System monitoring alerts showing server unreachable
- Trading operations stopped
- API endpoints returning 500 errors

**Recovery Procedure**:
1. **Immediate Actions**:
   - Verify server failure via direct SSH attempts and cloud provider dashboard
   - Switch DNS to point to standby server
   - Alert trading team to pause manual operations

2. **Standby Activation**:
   ```bash
   # SSH into standby server
   ssh tradingbot@standby-server
   
   # Run activation script
   cd /opt/forex-trading-bot/scripts
   ./activate_standby.sh
   
   # Verify services are running
   supervisorctl status
   ```

3. **Verification**:
   - Confirm API endpoints respond correctly
   - Verify trading engine reconnects to MT5
   - Check database integrity
   - Monitor first few automated trades

4. **Resolution**:
   - Investigate cause of primary server failure
   - Rebuild primary server using latest system image
   - Sync data from standby to primary
   - When ready, switch back to primary

### 2. Database Corruption

**Symptoms**:
- Database-related error logs
- Inconsistent trading data
- Application errors when reading/writing data

**Recovery Procedure**:
1. **Immediate Actions**:
   - Stop trading engine to prevent further corruption
   - Alert all users of system downtime

2. **Assessment**:
   - Determine extent of corruption
   - Identify last known good backup

3. **Recovery**:
   ```bash
   # SSH into database server
   ssh dbadmin@db-server
   
   # Stop database service
   systemctl stop postgresql
   
   # Restore from last good backup using BackupManager
   python -m src.utils.restore_backup --component=database --latest
   
   # Alternatively, use the BackupManager with a specific backup ID
   python -m src.utils.restore_backup --backup-id=<backup_id>
   
   # Start database service
   systemctl start postgresql
   
   # Verify integrity
   python -m src.utils.verify_integrity --component=database
   ```

4. **Verification**:
   - Run database integrity checks
   - Verify application can connect and operate normally
   - Check for any missing data that needs manual reconciliation

### 3. MT5 Connection Loss

**Symptoms**:
- Trading engine logs showing connection errors
- No new trades being executed
- Balance/position information not updating

**Recovery Procedure**:
1. **Immediate Actions**:
   - Check MT5 terminal status on server
   - Verify network connectivity between the bot and MT5 server
   - Check MT5 broker status (possible broker downtime)

2. **Reconnection**:
   ```bash
   # SSH into trading server
   ssh tradingbot@trading-server
   
   # Restart MT5 connection service
   supervisorctl restart mt5_connector
   
   # Check logs for successful reconnection
   tail -f /var/log/forex-trading-bot/mt5_connector.log
   ```

3. **Alternative Recovery**:
   - If primary MT5 connection cannot be restored:
   ```bash
   # Switch to backup MT5 account
   cd /opt/forex-trading-bot/scripts
   ./switch_mt5_account.sh --account-id=backup
   
   # Restart services
   supervisorctl restart forex-trading-bot
   ```

4. **Verification**:
   - Confirm connection is reestablished
   - Verify account balance and positions are correct
   - Test a small trade to ensure functionality

### 4. API Service Failure

**Symptoms**:
- API endpoints returning errors
- Mobile app disconnected
- Error logs in API service

**Recovery Procedure**:
1. **Immediate Actions**:
   - Check API service status
   - Review error logs for root cause

2. **Service Restart**:
   ```bash
   # SSH into API server
   ssh tradingbot@api-server
   
   # Check service status
   supervisorctl status forex-api-server
   
   # Restart API service
   supervisorctl restart forex-api-server
   
   # Check logs for errors
   tail -f /var/log/forex-api-server.log
   ```

3. **Advanced Recovery**:
   - If restart doesn't resolve:
   ```bash
   # Check for config issues
   diff /opt/forex-trading-bot/config/api_config.yaml /opt/forex-trading-bot/config/api_config.yaml.backup
   
   # Restore config if corrupted
   cp /opt/forex-trading-bot/config/api_config.yaml.backup /opt/forex-trading-bot/config/api_config.yaml
   
   # Check dependencies
   cd /opt/forex-trading-bot
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Restart with debugging
   supervisorctl stop forex-api-server
   export DEBUG=1
   python run_api_server.py
   ```

4. **Verification**:
   - Test API endpoints with curl or Postman
   - Verify mobile app reconnects
   - Monitor error logs for recurrence

### 5. Data Breach Recovery

**Symptoms**:
- Unusual system access patterns
- Unexpected API usage
- Security monitoring alerts

**Recovery Procedure**:
1. **Immediate Actions**:
   - Isolate affected systems
   - Revoke all API keys and credentials
   - Disconnect from external services

2. **Assessment**:
   - Identify breach vector
   - Determine compromised data
   - Document timeline for regulatory reporting

3. **Recovery**:
   ```bash
   # Isolate affected servers
   ufw default deny outgoing
   ufw allow out on eth0 to 192.168.1.0/24
   
   # Rotate all credentials
   cd /opt/forex-trading-bot/scripts
   ./rotate_all_credentials.sh
   
   # Apply security patches
   apt update && apt upgrade -y
   
   # Run security scan
   lynis audit system
   ```

4. **Verification and Restoration**:
   - Verify system integrity with file checksums
   - Implement additional security controls
   - Gradually restore services with enhanced monitoring
   - Notify affected users if necessary

## Testing and Maintenance

### Scheduled Testing

| Test Type | Frequency | Responsible Team | Last Tested |
|-----------|-----------|------------------|------------|
| Server Failover | Monthly | DevOps | YYYY-MM-DD |
| Database Restore | Bi-weekly | Database Admin | YYYY-MM-DD |
| Full Disaster Recovery | Quarterly | All Teams | YYYY-MM-DD |
| Backup Integrity | Weekly | DevOps | YYYY-MM-DD |

### Test Procedure

1. **Preparation**:
   - Notify all stakeholders of planned test
   - Ensure backup systems are ready
   - Prepare rollback plan

2. **Execution**:
   - Follow the relevant recovery procedure
   - Document actual recovery time
   - Note any deviations from procedure

3. **Evaluation**:
   - Compare actual vs. target recovery time
   - Identify improvement opportunities
   - Update procedures as needed

4. **Documentation**:
   - Record test results
   - Update last tested date
   - Distribute findings to relevant teams

---

## Recovery Procedure Checklist

Use this checklist during an actual disaster recovery:

- [ ] Incident detected and validated
- [ ] Recovery team assembled
- [ ] Initial assessment completed
- [ ] Recovery strategy selected
- [ ] Stakeholders notified of outage and ETA
- [ ] Recovery procedure initiated
- [ ] Recovery progress monitored
- [ ] System functionality verified
- [ ] Services restored
- [ ] Post-incident review scheduled

---

**Last Updated**: 2025-04-11  
**Document Owner**: Forex Trading Bot Team

*Note: This document should be reviewed and updated quarterly or after any significant system changes.*
