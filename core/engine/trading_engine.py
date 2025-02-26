# core/engine/trading_engine.py

import asyncio
import logging
from datetime import datetime, time
from typing import Dict, Optional
from enum import Enum

from ..utils.logger import setup_logger

logger = setup_logger('trading_engine')

class EngineState(Enum):
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

class TradingEngine:
    def __init__(self, 
                 broker,
                 strategy_manager,
                 risk_manager,
                 mode_manager,
                 session_manager,
                 config: Dict):
        """Initialize trading engine"""
        self.broker = broker
        self.strategy_manager = strategy_manager
        self.risk_manager = risk_manager
        self.mode_manager = mode_manager
        self.session_manager = session_manager
        self.config = config
        
        self.state = EngineState.INITIALIZING
        self.running = False
        self.last_check_time = None
        self.check_interval = config.get('engine_check_interval', 1)
        
        # Performance tracking
        self.execution_times = []
        self.error_count = 0
        self.cycle_count = 0
        
    async def initialize(self) -> bool:
        """Initialize trading engine and all components"""
        try:
            logger.info("Initializing trading engine...")
            
            # Initialize components in order
            if not await self._initialize_components():
                return False
                
            self.state = EngineState.READY
            logger.info("Trading engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing trading engine: {e}")
            self.state = EngineState.ERROR
            return False

    async def _initialize_components(self) -> bool:
        """Initialize all components in correct order"""
        try:
            # 1. Initialize session manager
            if not await self.session_manager.initialize():
                logger.error("Failed to initialize session manager")
                return False
                
            # 2. Initialize broker connection
            if not await self.broker.connect():
                logger.error("Failed to connect to broker")
                return False
                
            # 3. Initialize mode manager
            if not await self.mode_manager.initialize():
                logger.error("Failed to initialize mode manager")
                return False
                
            # 4. Initialize risk manager
            if not await self.risk_manager.initialize():
                logger.error("Failed to initialize risk manager")
                return False
                
            # 5. Initialize strategy manager
            if not await self.strategy_manager.initialize():
                logger.error("Failed to initialize strategy manager")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            return False

    async def start(self):
        """Start trading engine"""
        try:
            if self.state != EngineState.READY:
                logger.error("Engine not ready to start")
                return
                
            logger.info("Starting trading engine...")
            self.state = EngineState.RUNNING
            self.running = True
            
            # Start main loop
            await self._run_loop()
            
        except Exception as e:
            logger.error(f"Error starting trading engine: {e}")
            self.state = EngineState.ERROR

    async def _run_loop(self):
        """Main trading loop"""
        try:
            while self.running:
                cycle_start = datetime.now()
                
                try:
                    # Check trading session
                    if not self.session_manager.is_active_session():
                        await self._handle_inactive_session()
                        continue
                    
                    # Process trading cycle
                    await self._process_trading_cycle()
                    
                    # Update performance metrics
                    self._update_performance_metrics(cycle_start)
                    
                    # Sleep for interval
                    await asyncio.sleep(self.check_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in trading cycle: {e}")
                    self.error_count += 1
                    await asyncio.sleep(5)  # Longer sleep on error
                    
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}")
            self.state = EngineState.ERROR
        finally:
            await self.stop()

    async def _process_trading_cycle(self):
        """Process single trading cycle"""
        try:
            # 1. Update market data
            if not await self._update_market_data():
                return
                
            # 2. Check risk limits
            if not self.risk_manager.check_limits():
                logger.warning("Risk limits reached")
                await self.stop()
                return
                
            # 3. Process strategies
            await self.strategy_manager.process_strategies()
            
            # 4. Update positions
            await self._update_positions()
            
            # 5. Log status if needed
            self._log_status_if_needed()
            
            self.cycle_count += 1
            
        except Exception as e:
            logger.error(f"Error processing trading cycle: {e}")
            raise

    async def _update_market_data(self) -> bool:
        """Update market data for all symbols"""
        try:
            symbols = self.strategy_manager.get_active_symbols()
            
            for symbol in symbols:
                quote = await self.broker.get_live_quote(symbol)
                if not quote:
                    logger.error(f"Failed to get quote for {symbol}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
            return False

    async def _update_positions(self):
        """Update all position information"""
        try:
            positions = await self.broker.get_positions()
            
            for position in positions:
                # Update position tracking
                self.strategy_manager.update_position(position)
                
                # Update risk metrics
                self.risk_manager.update_position(position)
                
        except Exception as e:
            logger.error(f"Error updating positions: {e}")

    async def _handle_inactive_session(self):
        """Handle inactive trading session"""
        try:
            current_time = datetime.now().time()
            
            if current_time >= self.config['square_off_time']:
                # Square off all positions
                await self.strategy_manager.square_off_all()
                await self.stop()
            else:
                # Wait and check again
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"Error handling inactive session: {e}")

    def _update_performance_metrics(self, cycle_start: datetime):
        """Update engine performance metrics"""
        try:
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            self.execution_times.append(cycle_time)
            
            # Keep only last 1000 measurements
            if len(self.execution_times) > 1000:
                self.execution_times.pop(0)
                
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")

    def _log_status_if_needed(self):
        """Log engine status periodically"""
        try:
            current_time = datetime.now()
            
            if (not self.last_check_time or 
                (current_time - self.last_check_time).seconds >= self.config['status_log_interval']):
                
                self._log_status()
                self.last_check_time = current_time
                
        except Exception as e:
            logger.error(f"Error checking status log: {e}")

    def _log_status(self):
        """Log current engine status"""
        try:
            avg_execution_time = sum(self.execution_times) / len(self.execution_times) if self.execution_times else 0
            
            logger.info("\n=== Engine Status ===")
            logger.info(f"State: {self.state.value}")
            logger.info(f"Cycles: {self.cycle_count}")
            logger.info(f"Errors: {self.error_count}")
            logger.info(f"Avg Execution Time: {avg_execution_time:.3f}s")
            logger.info(f"Active Strategies: {len(self.strategy_manager.get_active_strategies())}")
            logger.info("===================\n")
            
        except Exception as e:
            logger.error(f"Error logging status: {e}")

    async def stop(self):
        """Stop trading engine"""
        try:
            logger.info("Stopping trading engine...")
            self.state = EngineState.STOPPING
            self.running = False
            
            # Stop all components
            await self.strategy_manager.stop()
            await self.session_manager.stop()
            
            self.state = EngineState.STOPPED
            logger.info("Trading engine stopped")
            
        except Exception as e:
            logger.error(f"Error stopping trading engine: {e}")
            self.state = EngineState.ERROR

    def get_status(self) -> Dict:
        """Get engine status"""
        return {
            'state': self.state.value,
            'cycles': self.cycle_count,
            'errors': self.error_count,
            'avg_execution_time': sum(self.execution_times) / len(self.execution_times) if self.execution_times else 0,
            'active_strategies': len(self.strategy_manager.get_active_strategies()),
            'timestamp': datetime.now()
        }