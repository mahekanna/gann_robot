# core/strategy/gann_strategy.py

import logging
from typing import Dict, Optional, List
from datetime import datetime
from .base_strategy import BaseStrategy, Signal, SignalType
from ..utils.logger import setup_logger

logger = setup_logger('gann_strategy')

class GannStrategy(BaseStrategy):
    def __init__(self, broker, market_data, risk_manager, config: Dict):
        """Initialize Gann strategy"""
        super().__init__(broker, market_data, risk_manager, config)
        
        # Gann specific parameters
        self.gann_config = {
            'increments': config.get('gann_increments', 
                                   [0.125, 0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25]),
            'num_values': config.get('gann_num_values', 35),
            'buffer_percentage': config.get('buffer_percentage', 0.002)
        }
        
        # Initialize trackers
        self.gann_levels = {}
        self.target_hits = {}

    def generate_signal(self, symbol: str) -> Optional[Signal]:
        """Generate Gann-based trading signal"""
        try:
            # Get latest candle
            candle = self.market_data.get_latest_candle(
                symbol,
                self.config['candle_interval']
            )
            if not candle:
                return None

            # Get current price
            quote = self.market_data.get_live_quote(symbol)
            if not quote:
                return None

            # Calculate Gann levels using previous close
            gann_levels = self.calculate_gann_levels(candle.close)
            if not gann_levels:
                return None

            # Store levels for reference
            self.gann_levels[symbol] = gann_levels

            # Check for signals
            current_price = quote.ltp

            # Long signal conditions
            if current_price >= gann_levels['buy_level']:
                return self._create_long_signal(symbol, current_price, gann_levels)

            # Short signal conditions
            elif current_price <= gann_levels['sell_level']:
                return self._create_short_signal(symbol, current_price, gann_levels)

            return None

        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return None

    def calculate_gann_levels(self, price: float) -> Optional[Dict]:
        """Calculate Gann Square of 9 levels"""
        try:
            # Your existing Gann calculation code here
            gann_values = self.gann_square_of_9(
                price,
                self.gann_config['increments'],
                self.gann_config['num_values']
            )

            buy_above, sell_below = self.find_buy_sell_levels(price, gann_values)
            if not (buy_above and sell_below):
                return None

            buy_targets, sell_targets = self.get_unique_targets_from_angles(
                buy_above[1],
                gann_values,
                self.config['num_targets']
            )

            long_sl, short_sl = self.calculate_stoploss(
                buy_above,
                sell_below,
                self.gann_config['buffer_percentage']
            )

            return {
                'gann_values': gann_values,
                'buy_level': buy_above[1],
                'sell_level': sell_below[1],
                'buy_targets': buy_targets,
                'sell_targets': sell_targets,
                'long_stoploss': long_sl,
                'short_stoploss': short_sl
            }

        except Exception as e:
            logger.error(f"Error calculating Gann levels: {e}")
            return None

    def _create_long_signal(self, 
                          symbol: str, 
                          current_price: float, 
                          gann_levels: Dict) -> Signal:
        """Create long signal"""
        try:
            # Calculate position size
            quantity = self.risk_manager.calculate_position_size(
                symbol=symbol,
                price=current_price,
                stop_loss=gann_levels['long_stoploss']
            )

            targets = [t[1] for t in gann_levels['buy_targets']]

            # Create signal
            return Signal(
                type=SignalType.LONG,
                symbol=symbol,
                entry_price=current_price,
                stop_loss=gann_levels['long_stoploss'],
                targets=targets,
                quantity=quantity,
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error creating long signal: {e}")
            return None

    def _create_short_signal(self, 
                           symbol: str, 
                           current_price: float, 
                           gann_levels: Dict) -> Signal:
        """Create short signal"""
        try:
            # For short signals, we'll only do options
            quantity = self.risk_manager.calculate_position_size(
                symbol=symbol,
                price=current_price,
                stop_loss=gann_levels['short_stoploss']
            )

            targets = [t[1] for t in gann_levels['sell_targets']]

            # Get ATM put option details
            option_data = self.get_atm_option_data(symbol, current_price, "PE")

            return Signal(
                type=SignalType.SHORT,
                symbol=symbol,
                entry_price=current_price,
                stop_loss=gann_levels['short_stoploss'],
                targets=targets,
                quantity=quantity,
                timestamp=datetime.now(),
                option_data=option_data
            )

        except Exception as e:
            logger.error(f"Error creating short signal: {e}")
            return None

    def get_atm_option_data(self, 
                           symbol: str, 
                           current_price: float, 
                           option_type: str) -> Dict:
        """Get ATM option data"""
        try:
            # Calculate ATM strike
            strike = round(current_price / 50) * 50  # For indices
            if symbol not in ["NIFTY", "BANKNIFTY"]:
                strike = round(current_price / 100) * 100  # For stocks

            # Get current expiry
            expiry = self.broker.get_option_expiries(symbol)[0]  # Nearest expiry

            return {
                'type': option_type,
                'strike': strike,
                'expiry': expiry
            }

        except Exception as e:
            logger.error(f"Error getting option data: {e}")
            return None

    def validate_signal(self, signal: Signal) -> bool:
        """Validate trading signal"""
        try:
            # Check time of day
            current_time = datetime.now().time()
            if current_time < self.config['trading_start_time'] or \
               current_time > self.config['trading_end_time']:
                return False

            # Check for existing position
            if signal.symbol in self.positions:
                return False

            # Check signal staleness
            if (datetime.now() - signal.timestamp).seconds > 60:
                return False

            # Validate price levels
            if signal.entry_price <= 0 or signal.stop_loss <= 0:
                return False

            # Validate targets
            if not signal.targets or len(signal.targets) == 0:
                return False

            # Validate option data for short signals
            if signal.type == SignalType.SHORT and not signal.option_data:
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            return False

    def _update_position_pnl(self, position: Dict, quote):
        """Update position P&L"""
        try:
            entry_price = position['entry_price']
            quantity = position['quantity']
            current_price = quote.ltp

            if position['signal'].type == SignalType.LONG:
                position['pnl'] = (current_price - entry_price) * quantity
            else:
                position['pnl'] = (entry_price - current_price) * quantity

        except Exception as e:
            logger.error(f"Error updating position P&L: {e}")

    def _check_exit_conditions(self, position: Dict, quote) -> bool:
        """Check exit conditions"""
        try:
            current_price = quote.ltp
            signal = position['signal']

            # Check stoploss
            if signal.type == SignalType.LONG:
                if current_price <= signal.stop_loss:
                    logger.info(f"Stoploss hit for {signal.symbol}")
                    return True
            else:
                if current_price >= signal.stop_loss:
                    logger.info(f"Stoploss hit for {signal.symbol}")
                    return True

            # Check targets
            position_key = f"{signal.symbol}_{signal.type.value}"
            current_target_idx = self.target_hits.get(position_key, 0)

            if current_target_idx < len(signal.targets):
                target = signal.targets[current_target_idx]
                
                if ((signal.type == SignalType.LONG and current_price >= target) or
                    (signal.type == SignalType.SHORT and current_price <= target)):
                    
                    # Update target hits
                    self.target_hits[position_key] = current_target_idx + 1
                    
                    # If last target hit, exit full position
                    if current_target_idx == len(signal.targets) - 1:
                        logger.info(f"Final target hit for {signal.symbol}")
                        return True
                    
                    # Otherwise, partial exit will be handled by position manager
                    logger.info(f"Target {current_target_idx + 1} hit for {signal.symbol}")

            return False

        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return False

    def _process_new_candle(self, symbol: str, candle):
        """Process new candle data"""
        super()._process_new_candle(symbol, candle)
        
        # Update Gann levels on new candle
        gann_levels = self.calculate_gann_levels(candle.close)
        if gann_levels:
            self.gann_levels[symbol] = gann_levels
            
            # Update stops if trailing
            if symbol in self.positions:
                self._update_trailing_stops(symbol, gann_levels)

    def _update_trailing_stops(self, symbol: str, gann_levels: Dict):
        """Update trailing stops based on new Gann levels"""
        try:
            position = self.positions[symbol]
            signal = position['signal']

            if signal.type == SignalType.LONG:
                new_stop = gann_levels['long_stoploss']
                if new_stop > signal.stop_loss:
                    signal.stop_loss = new_stop
                    logger.info(f"Updated trailing stop for {symbol} to {new_stop}")

            else:  # SHORT
                new_stop = gann_levels['short_stoploss']
                if new_stop < signal.stop_loss:
                    signal.stop_loss = new_stop
                    logger.info(f"Updated trailing stop for {symbol} to {new_stop}")

        except Exception as e:
            logger.error(f"Error updating trailing stops: {e}")