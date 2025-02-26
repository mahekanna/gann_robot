# main.py

import asyncio
import logging
import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Dict

from core.brokers.icici_breeze import ICICIBreeze
from core.brokers.paper_broker import PaperBroker
from core.strategy.gann_strategy import GannStrategy
from core.strategy.strategy_manager import StrategyManager
from core.monitoring.trading_monitor import TradingMonitor
from core.utils.logger import setup_logger
from config.config import Config

logger = setup_logger('main')

class TradingSystem:
    def __init__(self, config_path: str, mode: str):
        """Initialize trading system"""
        self.config_path = config_path
        self.mode = mode
        self.config = None
        self.broker = None
        self.strategy_manager = None
        self.monitor = None
        
    async def initialize(self) -> bool:
        """Initialize all components"""
        try:
            # Load configuration
            if not self.load_config():
                return False
            
            # Initialize broker based on mode
            if not await self.initialize_broker():
                return False
            
            # Initialize strategy manager
            if not await self.initialize_strategy_manager():
                return False
            
            # Initialize monitor
            if not self.initialize_monitor():
                return False
            
            logger.info("Trading system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing trading system: {e}")
            return False

    def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.error(f"Config file not found: {self.config_path}")
                return False
                
            with open(config_file, 'r') as f:
                self.config = json.load(f)
                
            # Validate configuration
            if not self._validate_config():
                return False
                
            logger.info("Configuration loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False

    def _validate_config(self) -> bool:
        """Validate configuration parameters"""
        required_fields = [
            'api_key', 'api_secret', 'totp_secret',
            'symbols', 'timeframes', 'risk_params',
            'trading_hours', 'capital_allocation'
        ]
        
        for field in required_fields:
            if field not in self.config:
                logger.error(f"Missing required config field: {field}")
                return False
                
        return True

    async def initialize_broker(self) -> bool:
        """Initialize broker based on mode"""
        try:
            # Create live broker instance
            live_broker = ICICIBreeze(
                api_key=self.config['api_key'],
                api_secret=self.config['api_secret'],
                totp_secret=self.config['totp_secret']
            )
            
            # For paper trading, wrap live broker
            if self.mode == 'paper':
                self.broker = PaperBroker(live_broker, self.config)
                logger.info("Paper trading broker initialized")
            else:
                self.broker = live_broker
                logger.info("Live trading broker initialized")
                
            return True
            
        except Exception as e:
            logger.error(f"Error initializing broker: {e}")
            return False

    async def initialize_strategy_manager(self) -> bool:
        """Initialize strategy manager and strategies"""
        try:
            # Create strategy manager
            self.strategy_manager = StrategyManager(self.broker, self.config)
            
            # Initialize strategies
            for symbol in self.config['symbols']:
                strategy = GannStrategy(
                    broker=self.broker,
                    symbol=symbol,
                    config=self._get_strategy_config(symbol)
                )
                
                if not self.strategy_manager.add_strategy(f"GANN_{symbol}", strategy):
                    return False
                    
            logger.info("Strategy manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing strategy manager: {e}")
            return False

    def _get_strategy_config(self, symbol: str) -> Dict:
        """Get symbol-specific strategy configuration"""
        base_config = self.config['strategy_params'].copy()
        
        # Override with symbol-specific settings if available
        if 'symbol_params' in self.config and symbol in self.config['symbol_params']:
            base_config.update(self.config['symbol_params'][symbol])
            
        return base_config

    def initialize_monitor(self) -> bool:
        """Initialize trading monitor"""
        try:
            self.monitor = TradingMonitor(
                strategy_manager=self.strategy_manager,
                config=self.config
            )
            logger.info("Trading monitor initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing monitor: {e}")
            return False

    async def run(self):
        """Main execution loop"""
        try:
            logger.info(f"Starting trading system in {self.mode} mode...")
            
            # Start strategy manager
            await self.strategy_manager.start()
            
            # Main loop
            while True:
                try:
                    # Update monitor
                    self.monitor.update()
                    
                    # Check risk limits
                    if not self.monitor.monitor_risk_limits():
                        logger.warning("Risk limits breached, stopping trading")
                        break
                    
                    # Generate reports periodically
                    await self._generate_periodic_reports()
                    
                    # Sleep interval
                    await asyncio.sleep(self.config['update_interval'])
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"Error running trading system: {e}")
        finally:
            await self.cleanup()

    async def _generate_periodic_reports(self):
        """Generate periodic reports"""
        current_time = datetime.now().time()
        
        # Daily report at end of day
        if (current_time >= self.config['trading_hours']['end'] and 
            not hasattr(self, '_daily_report_generated')):
            self.monitor.generate_daily_report()
            self.monitor.generate_performance_charts()
            self.monitor.export_trade_data()
            self._daily_report_generated = True
            
        # Reset daily report flag at start of day
        if current_time <= self.config['trading_hours']['start']:
            self._daily_report_generated = False

    async def cleanup(self):
        """Cleanup and shutdown"""
        try:
            # Stop strategy manager
            await self.strategy_manager.stop()
            
            # Save monitor state
            self.monitor.save_state()
            
            # Cleanup old data
            self.monitor.cleanup_old_data()
            
            logger.info("Trading system shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Gann Trading System')
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['live', 'paper'],
        default='paper',
        help='Trading mode (default: paper)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/trading_config.json',
        help='Path to configuration file'
    )
    
    return parser.parse_args()

async def main():
    """Main entry point"""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Create and initialize trading system
        system = TradingSystem(args.config, args.mode)
        
        if await system.initialize():
            # Run system
            await system.run()
        else:
            logger.error("Failed to initialize trading system")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    # Run main
    asyncio.run(main())