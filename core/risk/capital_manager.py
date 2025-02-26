from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass

from ..utils.logger import setup_logger

logger = setup_logger('capital_manager')

@dataclass
class CapitalAllocation:
    symbol: str
    allocated: float
    used: float
    available: float
    max_allowed: float

class CapitalManager:
    def __init__(self, config: Dict):
        """Initialize capital manager"""
        self.config = config
        self.initial_capital = config['total_capital']
        self.current_capital = self.initial_capital
        self.allocated_capital = 0
        self.used_capital = 0
        
        # Capital limits
        self.max_position_size = config.get('max_position_size', 0.1)  # 10% per position
        self.max_total_exposure = config.get('max_total_exposure', 0.8)  # 80% of capital
        
        # Track allocations
        self.allocations = {}
        self.position_exposure = {}
        
    def allocate_capital(self, symbol: str, amount: float) -> bool:
        """Allocate capital for a symbol"""
        try:
            if amount <= 0:
                logger.error("Invalid allocation amount")
                return False
                
            # Check against limits
            if not self._check_allocation_limits(amount):
                return False
                
            # Create or update allocation
            if symbol not in self.allocations:
                self.allocations[symbol] = CapitalAllocation(
                    symbol=symbol,
                    allocated=amount,
                    used=0,
                    available=amount,
                    max_allowed=self.current_capital * self.max_position_size
                )
            else:
                self.allocations[symbol].allocated += amount
                self.allocations[symbol].available += amount
                
            self.allocated_capital += amount
            return True
            
        except Exception as e:
            logger.error(f"Error allocating capital: {e}")
            return False

    def _check_allocation_limits(self, amount: float) -> bool:
        """Check if allocation is within limits"""
        # Check if enough capital available
        if amount > (self.current_capital - self.allocated_capital):
            logger.warning("Insufficient capital for allocation")
            return False
            
        # Check total exposure limit
        if (self.allocated_capital + amount) > (self.current_capital * self.max_total_exposure):
            logger.warning("Total exposure limit would be exceeded")
            return False
            
        return True

    def use_capital(self, symbol: str, amount: float) -> bool:
        """Use allocated capital for trading"""
        try:
            if symbol not in self.allocations:
                logger.error(f"No capital allocated for {symbol}")
                return False
                
            allocation = self.allocations[symbol]
            
            # Check if enough capital available
            if amount > allocation.available:
                logger.warning(f"Insufficient allocated capital for {symbol}")
                return False
                
            # Update allocation
            allocation.used += amount
            allocation.available -= amount
            self.used_capital += amount
            
            return True
            
        except Exception as e:
            logger.error(f"Error using capital: {e}")
            return False

    def release_capital(self, symbol: str, amount: float) -> bool:
        """Release used capital"""
        try:
            if symbol not in self.allocations:
                logger.error(f"No capital allocated for {symbol}")
                return False
                
            allocation = self.allocations[symbol]
            
            # Update allocation
            allocation.used -= amount
            allocation.available += amount
            self.used_capital -= amount
            
            return True
            
        except Exception as e:
            logger.error(f"Error releasing capital: {e}")
            return False

    def update_position_exposure(self, symbol: str, exposure: float):
        """Update position exposure"""
        self.position_exposure[symbol] = exposure
        
        # Check exposure limits
        total_exposure = sum(self.position_exposure.values())
        if total_exposure > (self.current_capital * self.max_total_exposure):
            logger.warning("Total exposure limit exceeded")

    def get_allocation(self, symbol: str) -> Optional[CapitalAllocation]:
        """Get capital allocation for symbol"""
        return self.allocations.get(symbol)

    def get_capital_status(self) -> Dict:
        """Get current capital status"""
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'allocated_capital': self.allocated_capital,
            'used_capital': self.used_capital,
            'available_capital': self.current_capital - self.allocated_capital,
            'total_exposure': sum(self.position_exposure.values()),
            'allocation_count': len(self.allocations),
            'timestamp': datetime.now()
        }

    def check_margin_requirements(self, margin_required: float) -> bool:
        """Check if margin requirements can be met"""
        available_margin = self.current_capital - self.used_capital
        return margin_required <= available_margin

    def adjust_for_pnl(self, pnl: float):
        """Adjust capital based on realized P&L"""
        self.current_capital += pnl
        
        # Recalculate max allowed positions
        for allocation in self.allocations.values():
            allocation.max_allowed = self.current_capital * self.max_position_size

    def reset_allocations(self):
        """Reset all allocations"""
        self.allocations.clear()
        self.position_exposure.clear()
        self.allocated_capital = 0
        self.used_capital = 0
        logger.info("Capital allocations reset")