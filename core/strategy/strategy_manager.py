# core/strategy/strategy_manager.py

import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, time
from enum import Enum
from ..utils.logger import setup_logger

logger = setup_logger('strategy_manager')

class StrategyState(Enum):
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

class StrategyManager:
    def __init__(self, broker, config: Dict):
        """Initialize strategy manager"""
        self.broker = broker
        self.config = config
        self.strategies = {}
        self.state = StrategyState.INITIALIZED
        self.last_check_time = None
        self.check_interval = 1  # seconds
        
    async def initialize(self) -> bool:
        """Initialize strategy manager and all strategies"""
        try:
            # Connect to broker
            if not self.broker.connect():
                logger.error("Failed to connect to broker")
                return False
            
            # Initialize each strategy
            for strategy_id, strategy in self.strategies.items():
                if not await self._initialize_strategy(strategy_id):
                    return False
            
            self.state = StrategyState.INITIALIZED
            logger.info("Strategy manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing strategy manager: {e}")
            self.state = StrategyState.ERROR
            return False

    async def _initialize_strategy(self, strategy_id: str) -> bool:
        """Initialize single strategy"""
        try:
            strategy = self.strategies[strategy_id]
            if not strategy.initialize():
                logger.error(f"Failed to initialize strategy {strategy_id}")
                return False
            return True
            
        except Exception as e:
            logger.error(f"Error initializing strategy {strategy_id}: {e}")
            return False

    def add_strategy(self, strategy_id: str, strategy) -> bool:
        """Add new strategy"""
        try:
            if strategy_id in self.strategies:
                logger.error(f"Strategy {strategy_id} already exists")
                return False
                
            self.strategies[strategy_id] = strategy
            logger.info(f"Added strategy {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding strategy: {e}")
            return False

    async def start(self):
        """Start all strategies"""
        try:
            if self.state != StrategyState.INITIALIZED:
                logger.error("Strategy manager not initialized")
                return
                
            logger.info("Starting strategy manager...")
            
            # Start market data monitoring
            await self._start_market_monitor()
            
            # Start strategies
            for strategy_id, strategy in self.strategies.items():
                strategy.start()
                
            self.state = StrategyState.RUNNING
            logger.info("Strategy manager running")
            
            # Start main loop
            await self._run_loop()
            
        except Exception as e:
            logger.error(f"Error starting strategy manager: {e}")
            self.state = StrategyState.ERROR

    async def _start_market_monitor(self):
        """Start market data monitoring"""
        try:
            # Get all symbols from all strategies
            symbols = set()
            for strategy in self.strategies.values():
                symbols.update(strategy.symbols)
                
            # Initialize market data
            for symbol in symbols:
                _ = await self.broker.get_live_quote(symbol)
                
        except Exception as e:
            logger.error(f"Error starting market monitor: {e}")

    async def _run_loop(self):
        """Main execution loop"""
        try:
            while self.state == StrategyState.RUNNING:
                current_time = datetime.now()
                
                # Check market hours
                if not self.broker.is_market_open():
                    await self._handle_market_closed()
                    continue
                
                # Check square off time
                if self._should_square_off():
                    await self._square_off_all()
                    break
                
                # Process each strategy
                for strategy_id, strategy in self.strategies.items():
                    if strategy.is_running:
                        await self._process_strategy(strategy_id)
                
                # Sleep for interval
                await asyncio.sleep(self.check_interval)
                
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.state = StrategyState.ERROR
        finally:
            await self.stop()

    async def _process_strategy(self, strategy_id: str):
        """Process single strategy"""
        try:
            strategy = self.strategies[strategy_id]
            
            # Update market data
            strategy.process_market_data()
            
            # Log status periodically
            if self._should_log_status():
                self._log_strategy_status(strategy_id)
                
        except Exception as e:
            logger.error(f"Error processing strategy {strategy_id}: {e}")

    def _should_square_off(self) -> bool:
        """Check if should square off positions"""
        current_time = datetime.now().time()
        square_off_time = time(
            hour=self.config['square_off_hour'],
            minute=self.config['square_off_minute']
        )
        return current_time >= square_off_time

    async def _square_off_all(self):
        """Square off all positions"""
        try:
            logger.info("Squaring off all positions...")
            
            for strategy_id, strategy in self.strategies.items():
                if strategy.is_running:
                    strategy.stop()
                    
            self.state = StrategyState.STOPPED
            logger.info("All positions squared off")
            
        except Exception as e:
            logger.error(f"Error squaring off positions: {e}")

    async def _handle_market_closed(self):
        """Handle market closed state"""
        try:
            if self.state == StrategyState.RUNNING:
                logger.info("Market is closed")
                await self._square_off_all()
                
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Error handling market closed: {e}")

    def _should_log_status(self) -> bool:
        """Check if should log status"""
        if not self.last_check_time:
            self.last_check_time = datetime.now()
            return True
            
        time_diff = (datetime.now() - self.last_check_time).seconds
        if time_diff >= self.config['status_log_interval']:
            self.last_check_time = datetime.now()
            return True
            
        return False

    def _log_strategy_status(self, strategy_id: str):
        """Log strategy status"""
        try:
            strategy = self.strategies[strategy_id]
            metrics = strategy.get_metrics()
            
            logger.info(f"\n=== Strategy {strategy_id} Status ===")
            logger.info(f"State: {strategy.is_running}")
            logger.info(f"Active Positions: {len(strategy.positions)}")
            logger.info(f"Daily P&L: {metrics['daily_pnl']}")
            logger.info(f"Total Trades: {metrics['total_trades']}")
            logger.info("===============================\n")
            
        except Exception as e:
            logger.error(f"Error logging strategy status: {e}")

    async def stop(self):
        """Stop all strategies"""
        try:
            logger.info("Stopping strategy manager...")
            
            # Stop all strategies
            for strategy_id, strategy in self.strategies.items():
                if strategy.is_running:
                    strategy.stop()
                    
            self.state = StrategyState.STOPPED
            logger.info("Strategy manager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping strategy manager: {e}")
            self.state = StrategyState.ERROR

    def get_status(self) -> Dict:
        """Get overall status"""
        try:
            active_strategies = sum(1 for s in self.strategies.values() 
                                  if s.is_running)
            total_positions = sum(len(s.positions) for s in self.strategies.values())
            total_pnl = sum(s.daily_pnl for s in self.strategies.values())
            
            return {
                'state': self.state.value,
                'active_strategies': active_strategies,
                'total_strategies': len(self.strategies),
                'total_positions': total_positions,
                'total_pnl': total_pnl,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {}