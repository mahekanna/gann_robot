# core/engine/mode_manager.py

import logging
from enum import Enum
from typing import Dict, Optional
from datetime import datetime

from ..brokers.icici_breeze import ICICIBreeze
from ..brokers.paper_broker import PaperBroker
from ..utils.logger import setup_logger

logger = setup_logger('mode_manager')

class TradingMode(Enum):
    LIVE = "LIVE"
    PAPER = "PAPER"
    BACKTEST = "BACKTEST"  # For future use

class ModeManager:
    def __init__(self, config: Dict):
        """Initialize mode manager"""
        self.config = config
        self.current_mode = None
        self.broker = None
        self.mode_history = []
        
    async def initialize(self) -> bool:
        """Initialize mode manager"""
        try:
            # Set initial mode
            initial_mode = TradingMode(self.config.get('initial_mode', 'PAPER').upper())
            return await self.set_mode(initial_mode)
            
        except Exception as e:
            logger.error(f"Error initializing mode manager: {e}")
            return False

    async def set_mode(self, mode: TradingMode) -> bool:
        """Set trading mode"""
        try:
            logger.info(f"Setting trading mode to {mode.value}")
            
            # Create appropriate broker
            if mode == TradingMode.LIVE:
                self.broker = ICICIBreeze(
                    api_key=self.config['api_key'],
                    api_secret=self.config['api_secret'],
                    totp_secret=self.config['totp_secret']
                )
            elif mode == TradingMode.PAPER:
                # Create live broker for market data
                live_broker = ICICIBreeze(
                    api_key=self.config['api_key'],
                    api_secret=self.config['api_secret'],
                    totp_secret=self.config['totp_secret']
                )
                # Wrap with paper broker
                self.broker = PaperBroker(live_broker, self.config)
            else:
                logger.error(f"Unsupported mode: {mode.value}")
                return False
            
            # Initialize broker
            if not await self.broker.connect():
                logger.error("Failed to initialize broker")
                return False
            
            # Update mode
            self.current_mode = mode
            self._record_mode_change(mode)
            
            logger.info(f"Successfully switched to {mode.value} mode")
            return True
            
        except Exception as e:
            logger.error(f"Error setting mode: {e}")
            return False

    def _record_mode_change(self, mode: TradingMode):
        """Record mode change in history"""
        self.mode_history.append({
            'timestamp': datetime.now(),
            'mode': mode.value,
            'reason': 'User initiated'  # Can be extended for automatic switches
        })

    def get_broker(self):
        """Get current broker instance"""
        return self.broker

    def is_live_mode(self) -> bool:
        """Check if in live mode"""
        return self.current_mode == TradingMode.LIVE

    def get_mode_history(self) -> list:
        """Get mode change history"""
        return self.mode_history

    def validate_operation(self, operation: str) -> bool:
        """Validate if operation is allowed in current mode"""
        # Define operations allowed in each mode
        mode_permissions = {
            TradingMode.LIVE: ['trade', 'modify', 'cancel', 'query'],
            TradingMode.PAPER: ['trade', 'modify', 'cancel', 'query'],
            TradingMode.BACKTEST: ['query']
        }
        
        return operation in mode_permissions.get(self.current_mode, [])

    async def cleanup(self):
        """Cleanup mode manager"""
        try:
            if self.broker:
                # Cleanup broker resources
                await self.broker.cleanup()
            
            logger.info("Mode manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in mode manager cleanup: {e}")