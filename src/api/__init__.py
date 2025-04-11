"""
API Package

This package contains the API server for remote control of the trading bot.
"""

from pathlib import Path
import sys

# Ensure proper imports from the project
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
