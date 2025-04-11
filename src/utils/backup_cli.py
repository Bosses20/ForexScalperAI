#!/usr/bin/env python3
"""
Command Line Interface for Forex Trading Bot Backup Management
Provides utilities for creating backups, restoring from backups,
and listing available backups.
"""

import os
import sys
import argparse
import yaml
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

# Add the parent directory to the path so we can import the src module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.backup_manager import BackupManager
from src.monitoring.alert_manager import AlertManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '../../logs/backup_cli.log'))
    ]
)

logger = logging.getLogger('backup_cli')


def load_config() -> Dict[str, Any]:
    """Load configuration from the config file"""
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../config/backup_config.yaml'))
    
    # If config doesn't exist, create a default one
    if not os.path.exists(config_path):
        logger.warning(f"Configuration file not found at {config_path}. Creating default configuration.")
        default_config = {
            'app_dir': os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')),
            'backup_dir': os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backups')),
            'backup_retention_days': 30,
            'backup_frequency': 'daily',
            'use_s3_backup': False,
            's3_bucket': 's3://trading-bot-backups',
            's3_region': 'us-east-1',
            'backup_components': {
                'config': True,
                'data': True,
                'database': True,
                'logs': False  # Default to not backing up logs to save space
            }
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Write default config
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
    
    # Load the config
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        sys.exit(1)


def create_backup(args: argparse.Namespace) -> None:
    """Create a new backup"""
    config = load_config()
    
    # Initialize alert manager if needed
    alert_manager = None
    if args.notify:
        try:
            from src.monitoring.alert_manager import AlertManager
            alert_manager = AlertManager(config.get('alerts', {}))
        except Exception as e:
            logger.warning(f"Failed to initialize alert manager: {str(e)}")
    
    # Initialize backup manager
    backup_manager = BackupManager(config, alert_manager=alert_manager)
    
    # Perform backup
    success, message = backup_manager.perform_backup()
    
    if success:
        logger.info(f"Backup completed successfully: {message}")
        print(f"✅ {message}")
        sys.exit(0)
    else:
        logger.error(f"Backup failed: {message}")
        print(f"❌ {message}")
        sys.exit(1)


def restore_backup(args: argparse.Namespace) -> None:
    """Restore from a backup"""
    config = load_config()
    
    # Initialize alert manager if needed
    alert_manager = None
    if args.notify:
        try:
            from src.monitoring.alert_manager import AlertManager
            alert_manager = AlertManager(config.get('alerts', {}))
        except Exception as e:
            logger.warning(f"Failed to initialize alert manager: {str(e)}")
    
    # Initialize backup manager
    backup_manager = BackupManager(config, alert_manager=alert_manager)
    
    # List available backups
    backups = backup_manager.list_backups()
    
    if not backups:
        logger.error("No backups found.")
        print("❌ No backups available to restore from.")
        sys.exit(1)
    
    # Get the backup to restore
    backup_to_restore = None
    
    if args.backup_id:
        # Find backup by ID
        for backup in backups:
            if args.backup_id in backup['filename']:
                backup_to_restore = backup
                break
                
        if not backup_to_restore:
            logger.error(f"Backup with ID {args.backup_id} not found.")
            print(f"❌ Backup with ID {args.backup_id} not found.")
            sys.exit(1)
    else:
        # Use latest backup
        backup_to_restore = backups[0]  # Backups are sorted newest first
    
    # Confirm restoration if not forced
    if not args.force:
        print("\n⚠️  WARNING: This will overwrite current data with data from the backup.")
        print(f"    Backup: {backup_to_restore['filename']}")
        print(f"    Created: {backup_to_restore['created_at']}")
        print(f"    Size: {backup_to_restore['size_mb']} MB")
        print(f"    Components: {', '.join(backup_to_restore['components'])}")
        
        confirmation = input("\nAre you sure you want to proceed? (yes/no): ")
        if confirmation.lower() not in ['yes', 'y']:
            print("Restoration cancelled.")
            sys.exit(0)
    
    # Get components to restore
    components = args.components.split(',') if args.components else None
    
    # Perform the restoration
    success, message = backup_manager.restore_backup(
        backup_to_restore['path'],
        components=components
    )
    
    if success:
        logger.info(f"Restore completed successfully: {message}")
        print(f"✅ {message}")
        sys.exit(0)
    else:
        logger.error(f"Restore failed: {message}")
        print(f"❌ {message}")
        sys.exit(1)


def list_backups(args: argparse.Namespace) -> None:
    """List available backups"""
    config = load_config()
    
    # Initialize backup manager
    backup_manager = BackupManager(config)
    
    # Get list of backups
    backups = backup_manager.list_backups()
    
    if not backups:
        print("No backups found.")
        return
    
    # Display backups
    print(f"\nFound {len(backups)} backups:\n")
    print(f"{'ID':<20} {'Created':<25} {'Size':<10} {'Components':<30}")
    print("-" * 85)
    
    for backup in backups:
        # Extract backup ID from filename
        backup_id = backup['filename'].replace('forex-trading-bot-backup-', '').replace('.tar.gz', '')
        
        # Format date
        created_date = backup['created_at'].split('T')[0]
        created_time = backup['created_at'].split('T')[1].split('.')[0] if 'T' in backup['created_at'] else ''
        created = f"{created_date} {created_time}"
        
        # Format size
        size = f"{backup['size_mb']} MB"
        
        # Format components (limit to first 3 for display)
        components = backup['components']
        if len(components) > 3:
            components_str = f"{', '.join(components[:3])}... (+{len(components)-3})"
        else:
            components_str = ', '.join(components)
        
        print(f"{backup_id:<20} {created:<25} {size:<10} {components_str:<30}")
    
    print("\nTo restore a backup, run: python backup_cli.py restore --backup-id=<ID>")
    print("To view metadata for a specific backup, add --verbose to the list command.")


def verify_backups(args: argparse.Namespace) -> None:
    """Verify backup integrity"""
    config = load_config()
    
    # Initialize backup manager
    backup_manager = BackupManager(config)
    
    # Get list of backups
    backups = backup_manager.list_backups()
    
    if not backups:
        print("No backups found to verify.")
        return
    
    # Verify all or specific backup
    if args.backup_id:
        # Find specific backup
        backup_to_verify = None
        for backup in backups:
            if args.backup_id in backup['filename']:
                backup_to_verify = backup
                break
                
        if not backup_to_verify:
            logger.error(f"Backup with ID {args.backup_id} not found.")
            print(f"❌ Backup with ID {args.backup_id} not found.")
            sys.exit(1)
            
        backups_to_verify = [backup_to_verify]
    else:
        # Verify all backups
        backups_to_verify = backups
    
    # Verify each backup
    print(f"\nVerifying {len(backups_to_verify)} backup(s)...\n")
    
    all_valid = True
    for backup in backups_to_verify:
        backup_id = backup['filename'].replace('forex-trading-bot-backup-', '').replace('.tar.gz', '')
        print(f"Verifying backup {backup_id}... ", end='')
        
        is_valid = backup_manager._verify_backup(backup['path'])
        
        if is_valid:
            print("✅ Valid")
        else:
            print("❌ Invalid or corrupted")
            all_valid = False
    
    if all_valid:
        print("\nAll backups verified successfully!")
    else:
        print("\n⚠️ One or more backups failed verification. Consider recreating them.")


def main() -> None:
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(description="Forex Trading Bot Backup Management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create a new backup')
    backup_parser.add_argument('--notify', action='store_true', help='Send notifications when backup completes')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from a backup')
    restore_parser.add_argument('--backup-id', help='ID of the backup to restore (default: latest)')
    restore_parser.add_argument('--components', help='Comma-separated list of components to restore')
    restore_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    restore_parser.add_argument('--notify', action='store_true', help='Send notifications when restore completes')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available backups')
    list_parser.add_argument('--verbose', action='store_true', help='Show detailed backup information')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify backup integrity')
    verify_parser.add_argument('--backup-id', help='ID of specific backup to verify (default: all)')
    
    args = parser.parse_args()
    
    if args.command == 'backup':
        create_backup(args)
    elif args.command == 'restore':
        restore_backup(args)
    elif args.command == 'list':
        list_backups(args)
    elif args.command == 'verify':
        verify_backups(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
