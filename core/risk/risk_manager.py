# core/risk/risk_manager.py

import logging
from typing import Dict, Optional, List
from datetime import datetime, time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

@dataclass
class RiskLimits:
    max_capital_per_trade: float
    max_loss_per_trade: float
    max_daily_loss: float
    max_positions: int
    max_capital_used: float
    intraday_square_off_time: time

class RiskMetrics:
    def __init__(self):
        self.daily_pnl = 0
        self.max_drawdown = 0
        self.peak_capital = 0
        self.current_drawdown = 0
        self.num_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.capital_used = 0
        self.risk_level = RiskLevel.NORMAL

class RiskManager:
    def __init__(self, config: Dict):
        """Initialize risk manager"""
        self.config = config
        self.limits = RiskLimits(
            max_capital_per_trade=config['max_capital_per_trade'],
            max_loss_per_trade=config['max_loss_per_trade'],
            max_daily_loss=config['max_daily_loss'],
            max_positions=config['max_positions'],
            max_capital_used=config['max_capital_used'],
            intraday_square_off_time=config['square_off_time']
        )
        
        self.metrics = RiskMetrics()
        self.positions = {}
        self.daily_trades = []
        self.last_check_time = None
        self.check_interval = 60  # seconds

    def initialize(self) -> bool:
        """Initialize risk manager"""
        try:
            # Reset daily tracking
            self.reset_daily_metrics()
            logger.info("Risk manager initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing risk manager: {e}")
            return False

    def can_take_trade(self, signal) -> bool:
        """Check if new trade can be taken"""
        try:
            # Check risk level
            if self.metrics.risk_level == RiskLevel.CRITICAL:
                logger.warning("No new trades - Critical risk level")
                return False

            # Check number of positions
            if len(self.positions) >= self.limits.max_positions:
                logger.warning("Maximum positions limit reached")
                return False

            # Check capital availability
            required_capital = self.calculate_required_capital(signal)
            if not self.check_capital_availability(required_capital):
                logger.warning("Insufficient capital for trade")
                return False

            # Check daily loss limit
            if self.metrics.daily_pnl <= -self.limits.max_daily_loss:
                logger.warning("Daily loss limit reached")
                return False

            # Check time restrictions
            if not self.check_time_restrictions():
                logger.warning("Outside trading hours")
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking trade possibility: {e}")
            return False

    def calculate_position_size(self, 
                              symbol: str,
                              price: float,
                              stop_loss: float) -> int:
        """Calculate position size based on risk"""
        try:
            risk_per_unit = abs(price - stop_loss)
            if risk_per_unit <= 0:
                return 0

            # Calculate based on risk per trade
            risk_based_qty = int(self.limits.max_loss_per_trade / risk_per_unit)

            # Calculate based on capital per trade
            capital_based_qty = int(self.limits.max_capital_per_trade / price)

            # Get minimum of both
            quantity = min(risk_based_qty, capital_based_qty)

            # Round to lot size if applicable
            lot_size = self.get_lot_size(symbol)
            if lot_size > 1:
                quantity = (quantity // lot_size) * lot_size

            return quantity

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0

    def update_position(self, 
                       symbol: str,
                       current_price: float,
                       position: Dict):
        """Update position risk metrics"""
        try:
            # Calculate P&L
            pnl = self.calculate_pnl(position, current_price)
            
            # Update position metrics
            position['current_price'] = current_price
            position['pnl'] = pnl
            
            # Update daily P&L
            old_pnl = self.positions.get(symbol, {}).get('pnl', 0)
            pnl_change = pnl - old_pnl
            self.metrics.daily_pnl += pnl_change
            
            # Update drawdown
            self._update_drawdown()
            
            # Update risk level
            self._update_risk_level()
            
            # Store position
            self.positions[symbol] = position

        except Exception as e:
            logger.error(f"Error updating position: {e}")

    def check_exit_conditions(self, position: Dict) -> bool:
        """Check if position should be exited based on risk"""
        try:
            # Check stop loss
            if position['pnl'] <= -self.limits.max_loss_per_trade:
                logger.warning(f"Max loss per trade hit for {position['symbol']}")
                return True

            # Check daily loss limit
            if self.metrics.daily_pnl <= -self.limits.max_daily_loss:
                logger.warning("Daily loss limit hit")
                return True

            # Check square off time
            current_time = datetime.now().time()
            if current_time >= self.limits.intraday_square_off_time:
                logger.info("Square off time reached")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return False

    def _update_drawdown(self):
        """Update drawdown calculations"""
        try:
            # Update peak capital
            if self.metrics.daily_pnl > self.metrics.peak_capital:
                self.metrics.peak_capital = self.metrics.daily_pnl

            # Calculate current drawdown
            self.metrics.current_drawdown = self.metrics.peak_capital - self.metrics.daily_pnl

            # Update max drawdown
            if self.metrics.current_drawdown > self.metrics.max_drawdown:
                self.metrics.max_drawdown = self.metrics.current_drawdown

        except Exception as e:
            logger.error(f"Error updating drawdown: {e}")

    def _update_risk_level(self):
        """Update risk level based on metrics"""
        try:
            daily_loss_limit = self.limits.max_daily_loss
            drawdown_limit = daily_loss_limit * 1.5  # 150% of daily loss limit

            if self.metrics.daily_pnl <= -daily_loss_limit or \
               self.metrics.max_drawdown >= drawdown_limit:
                self.metrics.risk_level = RiskLevel.CRITICAL
            elif self.metrics.daily_pnl <= -daily_loss_limit * 0.7:  # 70% of loss limit
                self.metrics.risk_level = RiskLevel.WARNING
            else:
                self.metrics.risk_level = RiskLevel.NORMAL

        except Exception as e:
            logger.error(f"Error updating risk level: {e}")

    def calculate_required_capital(self, signal) -> float:
        """Calculate required capital for trade"""
        return signal.entry_price * signal.quantity

    def check_capital_availability(self, required_capital: float) -> bool:
        """Check if sufficient capital is available"""
        return (self.metrics.capital_used + required_capital) <= self.limits.max_capital_used

    def check_time_restrictions(self) -> bool:
        """Check if within trading hours"""
        current_time = datetime.now().time()
        return current_time < self.limits.intraday_square_off_time

    def get_lot_size(self, symbol: str) -> int:
        """Get lot size for symbol"""
        # This should be implemented based on exchange data
        return 1

    def calculate_pnl(self, position: Dict, current_price: float) -> float:
        """Calculate position P&L"""
        try:
            quantity = position['quantity']
            entry_price = position['entry_price']
            
            if position['side'] == 'BUY':
                return (current_price - entry_price) * quantity
            else:
                return (entry_price - current_price) * quantity
                
        except Exception as e:
            logger.error(f"Error calculating P&L: {e}")
            return 0

    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics"""
        return {
            'daily_pnl': self.metrics.daily_pnl,
            'max_drawdown': self.metrics.max_drawdown,
            'current_drawdown': self.metrics.current_drawdown,
            'num_trades': self.metrics.num_trades,
            'winning_trades': self.metrics.winning_trades,
            'losing_trades': self.metrics.losing_trades,
            'capital_used': self.metrics.capital_used,
            'risk_level': self.metrics.risk_level.value,
            'win_rate': self.metrics.winning_trades / self.metrics.num_trades 
                       if self.metrics.num_trades > 0 else 0
        }

    def reset_daily_metrics(self):
        """Reset daily tracking metrics"""
        self.metrics = RiskMetrics()
        self.positions.clear()
        self.daily_trades.clear()
        self.last_check_time = None
        logger.info("Daily metrics reset")

    def log_risk_status(self):
        """Log current risk status"""
        metrics = self.get_risk_metrics()
        logger.info("\n=== Risk Status ===")
        logger.info(f"Risk Level: {metrics['risk_level']}")
        logger.info(f"Daily P&L: {metrics['daily_pnl']}")
        logger.info(f"Max Drawdown: {metrics['max_drawdown']}")
        logger.info(f"Active Positions: {len(self.positions)}")
        logger.info(f"Capital Used: {metrics['capital_used']}")
        logger.info("==================\n")