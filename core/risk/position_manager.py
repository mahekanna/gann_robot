# core/risk/position_manager.py

import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from ..utils.logger import setup_logger

logger = setup_logger('position_manager')

@dataclass
class Position:
    """Trading position"""
    symbol: str
    quantity: int
    entry_price: float
    entry_time: datetime
    side: str  # 'LONG' or 'SHORT'
    current_price: float = 0.0
    pnl: float = 0.0
    stops: List[float] = None
    targets: List[float] = None
    id: str = None
    is_active: bool = True

class PositionManager:
    def __init__(self, risk_manager, capital_manager, config: Dict):
        """Initialize position manager"""
        self.risk_manager = risk_manager
        self.capital_manager = capital_manager
        self.config = config
        self.positions = {}
        self.historical_positions = []
        
    def add_position(self, position: Position) -> bool:
        """Add a new position"""
        try:
            # Check if symbol already has active position
            if position.symbol in self.positions:
                logger.warning(f"Position already exists for {position.symbol}")
                return False
                
            # Validate position
            if not self._validate_position(position):
                return False
                
            # Check risk limits
            if not self.risk_manager.can_take_position(
                position.symbol, 
                position.quantity,
                position.entry_price
            ):
                logger.warning("Position exceeds risk limits")
                return False
                
            # Allocate capital
            capital_required = position.quantity * position.entry_price
            if not self.capital_manager.use_capital(position.symbol, capital_required):
                logger.warning("Insufficient capital for position")
                return False
                
            # Store position
            position.id = f"{position.symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.positions[position.symbol] = position
            
            logger.info(f"Added position: {position.side} {position.quantity} {position.symbol} @ {position.entry_price}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding position: {e}")
            return False
    
    def update_position(self, symbol: str, current_price: float) -> bool:
        """Update position with current price and P&L"""
        try:
            if symbol not in self.positions:
                return False
                
            position = self.positions[symbol]
            position.current_price = current_price
            
            # Calculate P&L
            if position.side == 'LONG':
                position.pnl = (current_price - position.entry_price) * position.quantity
            else:  # SHORT
                position.pnl = (position.entry_price - current_price) * position.quantity
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating position: {e}")
            return False
    
    def close_position(self, symbol: str, exit_price: float, exit_time: datetime, reason: str) -> Optional[Dict]:
        """Close a position"""
        try:
            if symbol not in self.positions:
                logger.warning(f"No position found for {symbol}")
                return None
                
            position = self.positions[symbol]
            
            # Calculate final P&L
            if position.side == 'LONG':
                pnl = (exit_price - position.entry_price) * position.quantity
            else:  # SHORT
                pnl = (position.entry_price - exit_price) * position.quantity
                
            # Release capital
            capital_used = position.quantity * position.entry_price
            self.capital_manager.release_capital(symbol, capital_used)
            
            # Update position
            position.current_price = exit_price
            position.pnl = pnl
            position.is_active = False
            
            # Create historical record
            historical_position = {
                'id': position.id,
                'symbol': position.symbol,
                'side': position.side,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'entry_time': position.entry_time,
                'exit_price': exit_price,
                'exit_time': exit_time,
                'pnl': pnl,
                'reason': reason
            }
            
            self.historical_positions.append(historical_position)
            
            # Remove from active positions
            del self.positions[symbol]
            
            logger.info(f"Closed position: {position.side} {position.quantity} {symbol} @ {exit_price}, P&L: {pnl}")
            return historical_position
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None
    
    def close_all_positions(self, current_prices: Dict[str, float], reason: str) -> List[Dict]:
        """Close all open positions"""
        closed_positions = []
        
        for symbol in list(self.positions.keys()):
            current_price = current_prices.get(symbol)
            if current_price:
                closed_position = self.close_position(
                    symbol,
                    current_price,
                    datetime.now(),
                    reason
                )
                if closed_position:
                    closed_positions.append(closed_position)
                    
        return closed_positions
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> List[Position]:
        """Get all active positions"""
        return list(self.positions.values())
    
    def get_position_history(self) -> List[Dict]:
        """Get historical positions"""
        return self.historical_positions
    
    def _validate_position(self, position: Position) -> bool:
        """Validate position parameters"""
        try:
            if position.quantity <= 0:
                logger.warning("Invalid quantity")
                return False
                
            if position.entry_price <= 0:
                logger.warning("Invalid entry price")
                return False
                
            if position.side not in ['LONG', 'SHORT']:
                logger.warning("Invalid side (must be LONG or SHORT)")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating position: {e}")
            return False
    
    def update_stops_and_targets(self, symbol: str, stops: List[float] = None, targets: List[float] = None) -> bool:
        """Update stops and targets for a position"""
        try:
            if symbol not in self.positions:
                return False
                
            position = self.positions[symbol]
            
            if stops:
                position.stops = stops
                
            if targets:
                position.targets = targets
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating stops and targets: {e}")
            return False
    
    def check_stops_and_targets(self, symbol: str, current_price: float) -> Optional[str]:
        """Check if current price hit stops or targets"""
        try:
            if symbol not in self.positions:
                return None
                
            position = self.positions[symbol]
            
            # Check stops
            if position.stops:
                for stop_price in position.stops:
                    if (position.side == 'LONG' and current_price <= stop_price) or \
                       (position.side == 'SHORT' and current_price >= stop_price):
                        return "STOP"
            
            # Check targets
            if position.targets:
                for target_price in position.targets:
                    if (position.side == 'LONG' and current_price >= target_price) or \
                       (position.side == 'SHORT' and current_price <= target_price):
                        return "TARGET"
                        
            return None
            
        except Exception as e:
            logger.error(f"Error checking stops and targets: {e}")
            return None