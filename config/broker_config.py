from dataclasses import dataclass
from typing import Dict, List
from datetime import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class BrokerConfig:
    """Broker configuration settings"""
    
    # API Credentials
    api_key: str = os.getenv('ICICI_API_KEY', '')
    api_secret: str = os.getenv('ICICI_API_SECRET', '')
    totp_secret: str = os.getenv('ICICI_TOTP_SECRET', '')
    
    # Broker Type
    broker_type: str = "ICICI"            # ICICI or PAPER
    is_paper_trading: bool = False        # Paper trading mode
    
    # Default Parameters
    default_exchange: str = "NSE"         # Default exchange
    default_product: str = "I"            # Default product type (I=Intraday, C=CNC)
    default_validity: str = "DAY"         # Default order validity
    
    # Order Settings
    allow_pending_orders: bool = True     # Allow pending orders
    max_pending_orders: int = 10          # Maximum pending orders
    order_timeout: int = 5                # Order timeout in seconds
    retry_attempts: int = 3               # Number of retry attempts
    
    # Market Hours
    market_start: time = time(9, 15)      # Market start time
    market_end: time = time(15, 30)       # Market end time
    pre_market_start: time = time(9, 0)   # Pre-market start
    post_market_end: time = time(15, 45)  # Post-market end
    
    # Connection Settings
    connection_timeout: int = 5           # Connection timeout in seconds
    keepalive_interval: int = 60          # Keepalive interval in seconds
    reconnect_attempts: int = 3           # Reconnection attempts
    reconnect_delay: int = 5              # Delay between reconnections
    
    # Rate Limits
    max_orders_per_second: int = 10       # Maximum orders per second
    max_modifications_per_second: int = 5  # Maximum modifications per second
    max_cancellations_per_second: int = 5 # Maximum cancellations per second
    
    # Session Settings
    session_reset_time: time = time(0, 0) # Session reset time
    session_expiry_hours: int = 24        # Session expiry in hours
    
    # Paper Trading Settings
    paper_capital: float = 100000.0       # Initial paper trading capital
    paper_leverage: float = 1.0           # Paper trading leverage
    paper_commission: float = 0.0003      # Paper trading commission (0.03%)
    paper_slippage: float = 0.0002       # Paper trading slippage (0.02%)
    
    # Lot Size Settings
    use_exchange_lots: bool = True        # Use exchange lot sizes
    default_lot_size: int = 1             # Default lot size if not using exchange
    
    # Order Type Mapping
    order_type_mapping: Dict = {
        'MARKET': 'MKT',
        'LIMIT': 'L',
        'STOP_LOSS': 'SL',
        'STOP_LOSS_MARKET': 'SL-M'
    }
    
    # Product Type Mapping
    product_type_mapping: Dict = {
        'INTRADAY': 'I',
        'DELIVERY': 'C',
        'MARGIN': 'M'
    }
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'BrokerConfig':
        """Create BrokerConfig from dictionary"""
        # Convert time strings to time objects
        time_fields = [
            'market_start', 'market_end',
            'pre_market_start', 'post_market_end',
            'session_reset_time'
        ]
        
        for field in time_fields:
            if field in config_dict:
                time_str = config_dict[field]
                hour, minute = map(int, time_str.split(':'))
                config_dict[field] = time(hour, minute)
        
        return cls(**config_dict)
    
    def to_dict(self) -> Dict:
        """Convert BrokerConfig to dictionary"""
        config_dict = {}
        for key, value in self.__dict__.items():
            if isinstance(value, time):
                config_dict[key] = value.strftime('%H:%M')
            else:
                config_dict[key] = value
        return config_dict
    
    def validate(self) -> List[str]:
        """Validate broker configuration"""
        errors = []
        
        # Validate credentials
        if not self.api_key:
            errors.append("API key is required")
        if not self.api_secret:
            errors.append("API secret is required")
        if not self.totp_secret:
            errors.append("TOTP secret is required")
            
        # Validate broker type
        if self.broker_type not in ["ICICI", "PAPER"]:
            errors.append("Invalid broker type")
            
        # Validate exchange and product
        if self.default_exchange not in ["NSE", "BSE", "NFO"]:
            errors.append("Invalid default exchange")
        if self.default_product not in ["I", "C", "M"]:
            errors.append("Invalid default product")
            
        # Validate numeric limits
        if self.max_pending_orders <= 0:
            errors.append("max_pending_orders must be positive")
        if self.order_timeout <= 0:
            errors.append("order_timeout must be positive")
        if self.retry_attempts <= 0:
            errors.append("retry_attempts must be positive")
            
        # Validate connection settings
        if self.connection_timeout <= 0:
            errors.append("connection_timeout must be positive")
        if self.keepalive_interval <= 0:
            errors.append("keepalive_interval must be positive")
        if self.reconnect_attempts <= 0:
            errors.append("reconnect_attempts must be positive")
        if self.reconnect_delay <= 0:
            errors.append("reconnect_delay must be positive")
            
        # Validate rate limits
        if self.max_orders_per_second <= 0:
            errors.append("max_orders_per_second must be positive")
        if self.max_modifications_per_second <= 0:
            errors.append("max_modifications_per_second must be positive")
        if self.max_cancellations_per_second <= 0:
            errors.append("max_cancellations_per_second must be positive")
            
        # Validate session settings
        if self.session_expiry_hours <= 0:
            errors.append("session_expiry_hours must be positive")
            
        # Validate paper trading settings
        if self.paper_capital <= 0:
            errors.append("paper_capital must be positive")