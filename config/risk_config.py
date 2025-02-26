from dataclasses import dataclass
from typing import Dict, List
from datetime import time

@dataclass
class RiskConfig:
    """Risk management configuration"""
    
    # Capital Limits
    max_capital_per_trade: float = 20000.0     # Maximum capital per trade
    max_capital_per_symbol: float = 50000.0    # Maximum capital per symbol
    max_total_exposure: float = 100000.0       # Maximum total exposure
    initial_capital: float = 100000.0          # Initial trading capital
    
    # Loss Limits
    max_daily_loss: float = 3000.0            # Maximum daily loss
    max_loss_per_trade: float = 1000.0        # Maximum loss per trade
    max_drawdown: float = 0.05                # Maximum drawdown (5%)
    
    # Position Limits
    max_positions: int = 5                    # Maximum concurrent positions
    max_positions_per_symbol: int = 2         # Maximum positions per symbol
    max_open_orders: int = 10                 # Maximum open orders
    
    # Risk Sizing
    position_size_risk: float = 0.02          # Risk per trade (2% of capital)
    leverage_allowed: bool = True             # Whether leverage is allowed
    max_leverage: float = 3.0                 # Maximum leverage allowed
    margin_buffer: float = 0.3                # Buffer for margin requirements (30%)
    
    # Time-based Risk Controls
    intraday_square_off_time: time = time(15, 15)  # Square off time for intraday
    position_holding_days: int = 1            # Maximum days to hold position
    trade_start_time: time = time(9, 15)      # Trading start time
    trade_end_time: time = time(15, 20)       # Trading end time
    
    # Options Risk Parameters
    max_option_lots: int = 3                  # Maximum option lots per position
    min_option_premium: float = 5.0           # Minimum option premium
    max_option_premium: float = 500.0         # Maximum option premium
    max_strikes_otm: int = 3                  # Maximum strikes out of the money
    
    # Strategy Risk Parameters
    trailing_stop_enabled: bool = True        # Whether to use trailing stops
    trailing_stop_trigger: float = 0.01       # Profit level to activate trailing (1%)
    trailing_stop_distance: float = 0.005     # Trailing stop distance (0.5%)
    min_risk_reward_ratio: float = 1.5        # Minimum risk-reward ratio
    
    # Market Risk Controls
    market_volatility_limit: float = 0.03     # Maximum market volatility allowed (3%)
    gap_up_limit: float = 0.05               # Maximum gap up allowed (5%)
    gap_down_limit: float = 0.05             # Maximum gap down allowed (5%)
    min_liquidity_volume: int = 100000       # Minimum volume required
    
    # Recovery Settings
    recovery_mode_enabled: bool = True        # Whether to enable recovery mode
    recovery_drawdown_trigger: float = 0.1    # Drawdown to trigger recovery (10%)
    recovery_position_size: float = 0.5       # Position size in recovery (50%)
    max_recovery_trades: int = 3              # Maximum recovery trades
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'RiskConfig':
        """Create RiskConfig from dictionary"""
        # Convert time strings to time objects
        if 'intraday_square_off_time' in config_dict:
            time_str = config_dict['intraday_square_off_time']
            hour, minute = map(int, time_str.split(':'))
            config_dict['intraday_square_off_time'] = time(hour, minute)
            
        if 'trade_start_time' in config_dict:
            time_str = config_dict['trade_start_time']
            hour, minute = map(int, time_str.split(':'))
            config_dict['trade_start_time'] = time(hour, minute)
            
        if 'trade_end_time' in config_dict:
            time_str = config_dict['trade_end_time']
            hour, minute = map(int, time_str.split(':'))
            config_dict['trade_end_time'] = time(hour, minute)
            
        return cls(**config_dict)
    
    def to_dict(self) -> Dict:
        """Convert RiskConfig to dictionary"""
        config_dict = {}
        for key, value in self.__dict__.items():
            if isinstance(value, time):
                config_dict[key] = value.strftime('%H:%M')
            else:
                config_dict[key] = value
        return config_dict
    
    def validate(self) -> List[str]:
        """Validate risk configuration"""
        errors = []
        
        # Validate capital limits
        if self.max_capital_per_trade <= 0:
            errors.append("max_capital_per_trade must be positive")
        if self.max_capital_per_symbol <= 0:
            errors.append("max_capital_per_symbol must be positive")
        if self.max_total_exposure <= 0:
            errors.append("max_total_exposure must be positive")
        if self.initial_capital <= 0:
            errors.append("initial_capital must be positive")
            
        # Validate loss limits
        if self.max_daily_loss <= 0:
            errors.append("max_daily_loss must be positive")
        if self.max_loss_per_trade <= 0:
            errors.append("max_loss_per_trade must be positive")
        if not 0 < self.max_drawdown < 1:
            errors.append("max_drawdown must be between 0 and 1")
            
        # Validate position limits
        if self.max_positions <= 0:
            errors.append("max_positions must be positive")
        if self.max_positions_per_symbol <= 0:
            errors.append("max_positions_per_symbol must be positive")
        if self.max_open_orders <= 0:
            errors.append("max_open_orders must be positive")
            
        # Validate risk sizing
        if not 0 < self.position_size_risk < 1:
            errors.append("position_size_risk must be between 0 and 1")
        if self.max_leverage <= 0:
            errors.append("max_leverage must be positive")
        if not 0 < self.margin_buffer < 1:
            errors.append("margin_buffer must be between 0 and 1")
            
        # Validate time controls
        if self.position_holding_days <= 0:
            errors.append("position_holding_days must be positive")
            
        # Validate option parameters
        if self.max_option_lots <= 0:
            errors.append("max_option_lots must be positive")
        if self.min_option_premium <= 0:
            errors.append("min_option_premium must be positive")
        if self.max_option_premium <= self.min_option_premium:
            errors.append("max_option_premium must be greater than min_option_premium")
        if self.max_strikes_otm <= 0:
            errors.append("max_strikes_otm must be positive")
            
        # Validate strategy parameters
        if not 0 < self.trailing_stop_trigger < 1:
            errors.append("trailing_stop_trigger must be between 0 and 1")
        if not 0 < self.trailing_stop_distance < 1:
            errors.append("trailing_stop_distance must be between 0 and 1")
        if self.min_risk_reward_ratio <= 1:
            errors.append("min_risk_reward_ratio must be greater than 1")
            
        # Validate market controls
        if not 0 < self.market_volatility_limit < 1:
            errors.append("market_volatility_limit must be between 0 and 1")
        if not 0 < self.gap_up_limit < 1:
            errors.append("gap_up_limit must be between 0 and 1")
        if not 0 < self.gap_down_limit < 1:
            errors.append("gap_down_limit must be between 0 and 1")
        if self.min_liquidity_volume <= 0:
            errors.append("min_liquidity_volume must be positive")
            
        # Validate recovery settings
        if not 0 < self.recovery_drawdown_trigger < 1:
            errors.append("recovery_drawdown_trigger must be between 0 and 1")
        if not 0 < self.recovery_position_size < 1:
            errors.append("recovery_position_size must be between 0 and 1")
        if self.max_recovery_trades <= 0:
            errors.append("max_recovery_trades must be positive")
            
        return errors