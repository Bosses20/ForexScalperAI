#!/bin/bash
# Forex Trading Bot Backup Script
# This script performs regular backups of the trading bot data and configurations

# Configuration
APP_DIR="/opt/forex-trading-bot"
BACKUP_DIR="/var/backups/forex-trading-bot"
S3_BUCKET="s3://trading-bot-backups"  # If using S3 for offsite backups
RETENTION_DAYS=30
DATE=$(date +%Y%m%d-%H%M%S)
LOG_FILE="/var/log/forex-trading-bot-backup.log"

# Ensure backup directory exists
mkdir -p $BACKUP_DIR

# Log function
log() {
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $1" | tee -a $LOG_FILE
}

log "Starting backup process..."

# Create temporary directory for backup
TEMP_DIR=$(mktemp -d)
log "Created temporary directory: $TEMP_DIR"

# Backup configuration files
log "Backing up configuration files..."
mkdir -p $TEMP_DIR/config
cp -r $APP_DIR/config/* $TEMP_DIR/config/

# Backup trading data
log "Backing up trading data..."
mkdir -p $TEMP_DIR/data
cp -r $APP_DIR/data/* $TEMP_DIR/data/

# Backup database (if applicable)
if [ -d "$APP_DIR/database" ]; then
    log "Backing up database..."
    mkdir -p $TEMP_DIR/database
    cp -r $APP_DIR/database/* $TEMP_DIR/database/
fi

# Create the backup archive
BACKUP_FILE="$BACKUP_DIR/forex-trading-bot-backup-$DATE.tar.gz"
log "Creating backup archive: $BACKUP_FILE"
tar -czf $BACKUP_FILE -C $TEMP_DIR .

# Calculate checksum
sha256sum $BACKUP_FILE > $BACKUP_FILE.sha256
log "Created checksum file: $BACKUP_FILE.sha256"

# Upload to S3 (if configured)
if command -v aws &> /dev/null; then
    log "Uploading backup to S3..."
    aws s3 cp $BACKUP_FILE $S3_BUCKET/
    aws s3 cp $BACKUP_FILE.sha256 $S3_BUCKET/
    log "S3 upload completed."
else
    log "AWS CLI not found, skipping S3 upload."
fi

# Clean up temporary directory
rm -rf $TEMP_DIR
log "Cleaned up temporary directory."

# Remove old backups based on retention policy
log "Cleaning up old backups (keeping backups from the last $RETENTION_DAYS days)..."
find $BACKUP_DIR -name "forex-trading-bot-backup-*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "forex-trading-bot-backup-*.tar.gz.sha256" -type f -mtime +$RETENTION_DAYS -delete

# Verify the backup
log "Verifying the latest backup..."
if tar -tzf $BACKUP_FILE &> /dev/null; then
    log "Backup verification successful."
else
    log "ERROR: Backup verification failed!"
    exit 1
fi

log "Backup process completed successfully."

# Send notification (optional)
if [ -f "$APP_DIR/scripts/notify.sh" ]; then
    $APP_DIR/scripts/notify.sh "Forex Trading Bot backup completed successfully."
fi

exit 0
