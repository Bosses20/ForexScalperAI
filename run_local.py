#!/usr/bin/env python
"""
Local Execution Runner for Forex Trading Bot

This script launches the Forex Trading Bot in local execution mode,
optimized for running on mobile devices and laptops without a VPS.

It starts both the trading bot and the local API server in separate processes,
allowing for communication between the mobile app and the local bot.

Usage:
    python run_local.py [--config CONFIG_PATH] [--local-config LOCAL_CONFIG_PATH]
"""

import os
import sys
import time
import argparse
import threading
import subprocess
import signal
import logging
from pathlib import Path

# Set up project root
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "local_run.log")
    ]
)
logger = logging.getLogger("local_runner")

# Ensure logs directory exists
(PROJECT_ROOT / "logs").mkdir(exist_ok=True)

# Import local modules
try:
    from src.core.local_executor import LocalExecutor
    from src.api.local_api import start_local_api
    from src.utils.config_utils import load_config
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    print(f"Error: Failed to import required modules: {e}")
    sys.exit(1)

def run_api_server(host, port, config_path, local_config_path, stop_event):
    """Run the local API server in a separate thread"""
    logger.info(f"Starting local API server on {host}:{port}")
    
    try:
        from src.api.local_api import start_local_api
        import threading
        
        # Run API server in a thread
        api_thread = threading.Thread(
            target=start_local_api,
            args=(host, port, config_path, local_config_path),
            daemon=True
        )
        api_thread.start()
        
        # Wait for stop event
        while not stop_event.is_set():
            time.sleep(1)
            
        logger.info("API server stopping...")
    
    except Exception as e:
        logger.error(f"Error in API server: {e}")

def print_startup_banner():
    """Print a fancy startup banner"""
    print("\n" + "=" * 60)
    print("  FOREX TRADING BOT - LOCAL EXECUTION MODE")
    print("=" * 60)
    print("  Running bot locally on your device")
    print("  Mobile app can connect via the local API")
    print("-" * 60)
    

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run Forex Trading Bot in local execution mode")
    parser.add_argument("--config", type=str, default="config/mt5_config.yaml", help="Path to MT5 config")
    parser.add_argument("--local-config", type=str, default="config/local_execution.yaml", help="Path to local execution config")
    parser.add_argument("--api-only", action="store_true", help="Run only the API server without the trading bot")
    parser.add_argument("--bot-only", action="store_true", help="Run only the trading bot without the API server")
    
    args = parser.parse_args()
    
    # Resolve config paths
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
        
    local_config_path = Path(args.local_config)
    if not local_config_path.is_absolute():
        local_config_path = PROJECT_ROOT / local_config_path
    
    # Check if config files exist
    if not config_path.exists():
        logger.error(f"MT5 config file not found: {config_path}")
        print(f"Error: MT5 config file not found: {config_path}")
        return 1
        
    if not local_config_path.exists():
        logger.error(f"Local execution config file not found: {local_config_path}")
        print(f"Error: Local execution config file not found: {local_config_path}")
        return 1
    
    print_startup_banner()
    
    # Load local configuration
    try:
        local_config = load_config(str(local_config_path))
        api_config = local_config.get("execution", {}).get("local_api", {})
        api_host = api_config.get("host", "127.0.0.1")
        api_port = api_config.get("port", 8000)
        api_enabled = api_config.get("enabled", True) and not args.bot_only
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        print(f"Error loading configuration: {e}")
        return 1
    
    # Create stop event for graceful shutdown
    stop_event = threading.Event()
    
    # Initialize components
    executor = None
    api_thread = None
    
    # Setup signal handlers for graceful shutdown
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        stop_event.set()
        if executor and executor.running:
            executor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        # Start API server if enabled
        if api_enabled and not args.bot_only:
            logger.info("Starting local API server")
            print(f"Starting local API server at http://{api_host}:{api_port}")
            
            api_thread = threading.Thread(
                target=run_api_server,
                args=(api_host, api_port, str(config_path), str(local_config_path), stop_event),
                daemon=True
            )
            api_thread.start()
            
            # Give API server time to start
            time.sleep(2)
            
            # Print access info
            print(f"Mobile app can connect to: http://{api_host}:{api_port}")
            print(f"WebSocket endpoint: ws://{api_host}:{api_port}/ws")
            print("-" * 60)
        
        # Start local executor if not in API-only mode
        if not args.api_only:
            logger.info("Starting trading bot in local execution mode")
            print("Starting trading bot in local execution mode...")
            
            executor = LocalExecutor(str(config_path), str(local_config_path))
            if executor.start():
                print("Trading bot started successfully!")
                print("-" * 60)
                print("Press Ctrl+C to stop")
                
                # Main loop
                try:
                    while not stop_event.is_set():
                        time.sleep(5)
                        status = executor.get_status()
                        
                        # Print occasional status updates
                        if int(time.time()) % 60 == 0:  # Every minute
                            # Format an informative status message
                            status_msg = (
                                f"Status: {'Running' if status['running'] else 'Stopped'}, "
                                f"{'Paused' if status['paused'] else 'Active'} | "
                                f"CPU: {status['resource_usage']['cpu_percent']:.1f}%, "
                                f"Mem: {status['resource_usage']['memory_mb']:.1f} MB | "
                                f"Network: {status['network_status']} | "
                                f"Trades: {status['trades_executed']}"
                            )
                            print(status_msg)
                
                except KeyboardInterrupt:
                    print("\nShutting down...")
                finally:
                    if executor.running:
                        executor.stop()
            else:
                logger.error("Failed to start trading bot")
                print("Error: Failed to start trading bot")
                return 1
        
        # If only running API, wait for Ctrl+C
        elif args.api_only and api_thread:
            print("Running in API-only mode. Press Ctrl+C to stop.")
            try:
                while api_thread.is_alive():
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down API server...")
    
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        return 1
    
    finally:
        # Clean shutdown
        stop_event.set()
        
        if executor and executor.running:
            executor.stop()
            print("Trading bot stopped")
        
        if api_thread and api_thread.is_alive():
            # API thread should exit when stop_event is set
            api_thread.join(timeout=5)
            print("API server stopped")
    
    print("\nLocal execution ended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
