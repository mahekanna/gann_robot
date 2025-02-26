# core/strategy/base_strategy.py

from abc import ABC, abstractmethod
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SignalType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT = "EXIT"
    NO_SIGNAL = "NO_SIGNAL"

@dataclass
class Signal:
    type: SignalType
    symbol: str
    entry_price: float
    stop_loss: float
    targets: List[float]
    quantity: int
    timestamp: datetime
    expiry: Optional[datetime] = None
    option_data: Optional[Dict] = None
    metadata: Optional[Dict] = None

class BaseStrategy(ABC):
    def __init__(self, 
                 broker, 
                 market_data,
                 risk_manager,
                 config: Dict):
        """Initialize base strategy"""
        self.broker = broker
        self.market_data = market_data
        self.risk_manager = risk_manager
        self.config = config
        
        # Strategy state
        self.is_running = False
        self.symbols = []
        self.positions = {}
        self.last_signals = {}
        self.last_candle_time = {}
        
        # Performance tracking
        self.trades = []
        self.daily_pnl = 0
        self.metrics = {}

    @abstractmethod
    def generate_signal(self, symbol: str) -> Optional[Signal]:
        """Generate trading signal - to be implemented by specific strategy"""
        pass

    @abstractmethod
    def validate_signal(self, signal: Signal) -> bool:
        """Validate signal - to be implemented by specific strategy"""
        pass

    def initialize(self) -> bool:
        """Initialize strategy"""
        try:
            # Connect to broker
            if not self.broker.connect():
                logger.error("Failed to connect to broker")
                return False
            
            # Validate symbols
            if not self.symbols:
                logger.error("No symbols configured")
                return False
            
            # Initialize risk manager
            if not self.risk_manager.initialize():
                logger.error("Failed to initialize risk manager")
                return False
            
            logger.info("Strategy initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing strategy: {e}")
            return False

    def start(self):
        """Start strategy"""
        try:
            if not self.initialize():
                return
                
            self.is_running = True
            logger.info("Strategy started")
            
        except Exception as e:
            logger.error(f"Error starting strategy: {e}")
            self.stop()

    def stop(self):
        """Stop strategy"""
        try:
            self.is_running = False
            self.cleanup()
            logger.info("Strategy stopped")
            
        except Exception as e:
            logger.error(f"Error stopping strategy: {e}")

    def process_market_data(self):
        """Process market data for all symbols"""
        try:
            for symbol in self.symbols:
                # Get market data
                quote = self.market_data.get_live_quote(symbol)
                if not quote:
                    continue
                
                # Check for new candle
                if self._is_new_candle(symbol):
                    candle = self.market_data.get_latest_candle(
                        symbol, 
                        self.config['candle_interval']
                    )
                    if candle:
                        self._process_new_candle(symbol, candle)
                
                # Generate and process signals
                self._process_symbol(symbol, quote)
                
        except Exception as e:
            logger.error(f"Error processing market data: {e}")

    def _process_symbol(self, symbol: str, quote):
        """Process single symbol"""
        try:
            # Check active positions
            if symbol in self.positions:
                self._monitor_position(symbol, quote)
                return
            
            # Generate new signal
            signal = self.generate_signal(symbol)
            if not signal:
                return
                
            # Validate signal
            if not self.validate_signal(signal):
                return
                
            # Check risk limits
            if not self.risk_manager.can_take_trade(signal):
                return
                
            # Execute signal
            self._execute_signal(signal)
            
        except Exception as e:
            logger.error(f"Error processing symbol {symbol}: {e}")

    def _monitor_position(self, symbol: str, quote):
        """Monitor active position"""
        try:
            position = self.positions[symbol]
            
            # Update position P&L
            self._update_position_pnl(position, quote)
            
            # Check exit conditions
            if self._check_exit_conditions(position, quote):
                self._exit_position(position, quote, "Exit signal")
                
        except Exception as e:
            logger.error(f"Error monitoring position for {symbol}: {e}")

    def _execute_signal(self, signal: Signal) -> bool:
        """Execute trading signal"""
        try:
            # Place order
            response = self.broker.place_order(
                symbol=signal.symbol,
                quantity=signal.quantity,
                side="BUY" if signal.type == SignalType.LONG else "SELL",
                product_type=self.config['product_type'],
                order_type="MARKET",
                price=signal.entry_price
            )
            
            if response.status != 'success':
                logger.error(f"Order failed: {response.message}")
                return False
            
            # Track position
            self.positions[signal.symbol] = {
                'signal': signal,
                'order_id': response.order_id,
                'entry_time': datetime.now(),
                'entry_price': signal.entry_price,
                'quantity': signal.quantity,
                'pnl': 0
            }
            
            # Record signal
            self.last_signals[signal.symbol] = signal
            
            logger.info(f"Executed signal for {signal.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return False

    def _exit_position(self, position: Dict, quote, reason: str) -> bool:
        """Exit position"""
        try:
            response = self.broker.place_order(
                symbol=position['signal'].symbol,
                quantity=position['quantity'],
                side="SELL" if position['signal'].type == SignalType.LONG else "BUY",
                product_type=self.config['product_type'],
                order_type="MARKET"
            )
            
            if response.status != 'success':
                logger.error(f"Exit order failed: {response.message}")
                return False
            
            # Record trade
            self.trades.append({
                'symbol': position['signal'].symbol,
                'entry_time': position['entry_time'],
                'exit_time': datetime.now(),
                'entry_price': position['entry_price'],
                'exit_price': quote.ltp,
                'quantity': position['quantity'],
                'pnl': position['pnl'],
                'reason': reason
            })
            
            # Update daily P&L
            self.daily_pnl += position['pnl']
            
            # Remove position
            del self.positions[position['signal'].symbol]
            
            logger.info(f"Exited position for {position['signal'].symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error exiting position: {e}")
            return False

    def _is_new_candle(self, symbol: str) -> bool:
        """Check if we have a new candle"""
        if symbol not in self.last_candle_time:
            return True
            
        current_time = datetime.now()
        last_time = self.last_candle_time[symbol]
        
        minutes_diff = (current_time - last_time).total_seconds() / 60
        return minutes_diff >= self.config['candle_interval']

    def _process_new_candle(self, symbol: str, candle):
        """Process new candle data"""
        self.last_candle_time[symbol] = candle.timestamp
        # Specific strategy can override this method

    @abstractmethod
    def _update_position_pnl(self, position: Dict, quote):
        """Update position P&L - to be implemented by specific strategy"""
        pass

    @abstractmethod
    def _check_exit_conditions(self, position: Dict, quote) -> bool:
        """Check exit conditions - to be implemented by specific strategy"""
        pass

    def cleanup(self):
        """Cleanup strategy"""
        try:
            # Close all positions
            for symbol in list(self.positions.keys()):
                quote = self.market_data.get_live_quote(symbol)
                if quote:
                    self._exit_position(
                        self.positions[symbol], 
                        quote, 
                        "Strategy stopped"
                    )
            
            # Reset state
            self.positions.clear()
            self.last_signals.clear()
            
            logger.info("Strategy cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in strategy cleanup: {e}")