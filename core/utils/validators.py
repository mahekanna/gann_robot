from typing import Dict, Any, List, Optional
from datetime import datetime, time
import re

class Validators:
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """Validate trading symbol"""
        if not symbol:
            return False
        # Basic symbol format check
        pattern = r'^[A-Z]{2,}$'
        return bool(re.match(pattern, symbol))

    @staticmethod
    def validate_price(price: float) -> bool:
        """Validate price value"""
        return isinstance(price, (int, float)) and price > 0

    @staticmethod
    def validate_quantity(quantity: int) -> bool:
        """Validate quantity"""
        return isinstance(quantity, int) and quantity > 0

    @staticmethod
    def validate_order_type(order_type: str) -> bool:
        """Validate order type"""
        valid_types = ['MARKET', 'LIMIT', 'SL', 'SL-M']
        return order_type in valid_types

    @staticmethod
    def validate_trade_action(action: str) -> bool:
        """Validate trade action"""
        return action in ['BUY', 'SELL']

    @staticmethod
    def validate_product_type(product_type: str) -> bool:
        """Validate product type"""
        valid_types = ['INTRADAY', 'DELIVERY', 'CARRYFORWARD']
        return product_type in valid_types

    @staticmethod
    def validate_exchange(exchange: str) -> bool:
        """Validate exchange"""
        valid_exchanges = ['NSE', 'BSE', 'NFO']
        return exchange in valid_exchanges

    @staticmethod
    def validate_timeframe(timeframe: int) -> bool:
        """Validate timeframe"""
        valid_timeframes = [1, 3, 5, 10, 15, 30, 60]
        return timeframe in valid_timeframes

    @staticmethod
    def validate_date(date_str: str) -> bool:
        """Validate date string format"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_time(time_str: str) -> bool:
        """Validate time string format"""
        try:
            datetime.strptime(time_str, '%H:%M')
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_expiry_date(expiry: str) -> bool:
        """Validate option expiry date"""
        try:
            expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
            return expiry_date >= datetime.now()
        except ValueError:
            return False

    @staticmethod
    def validate_strike_price(strike: float) -> bool:
        """Validate option strike price"""
        return isinstance(strike, (int, float)) and strike > 0

    @staticmethod
    def validate_option_type(option_type: str) -> bool:
        """Validate option type"""
        return option_type in ['CE', 'PE']

    @staticmethod
    def validate_trade_params(params: Dict) -> List[str]:
        """Validate all trade parameters"""
        errors = []
        
        # Required fields
        required_fields = ['symbol', 'quantity', 'order_type', 'action']
        for field in required_fields:
            if field not in params:
                errors.append(f"Missing required field: {field}")
                
        # Validate individual fields
        if 'symbol' in params and not Validators.validate_symbol(params['symbol']):
            errors.append("Invalid symbol format")
            
        if 'quantity' in params and not Validators.validate_quantity(params['quantity']):
            errors.append("Invalid quantity")
            
        if 'order_type' in params and not Validators.validate_order_type(params['order_type']):
            errors.append("Invalid order type")
            
        if 'action' in params and not Validators.validate_trade_action(params['action']):
            errors.append("Invalid trade action")
            
        if 'price' in params and not Validators.validate_price(params['price']):
            errors.append("Invalid price")
            
        if 'product_type' in params and not Validators.validate_product_type(params['product_type']):
            errors.append("Invalid product type")
            
        # Option specific validations
        if params.get('instrument_type') == 'OPT':
            if 'strike' in params and not Validators.validate_strike_price(params['strike']):
                errors.append("Invalid strike price")
                
            if 'expiry' in params and not Validators.validate_expiry_date(params['expiry']):
                errors.append("Invalid expiry date")
                
            if 'option_type' in params and not Validators.validate_option_type(params['option_type']):
                errors.append("Invalid option type")
        
        return errors

    @staticmethod
    def validate_config(config: Dict) -> List[str]:
        """Validate configuration parameters"""
        errors = []
        
        # Check required fields
        required_fields = [
            'api_key', 'api_secret', 'totp_secret',
            'symbols', 'timeframes', 'trading_hours',
            'risk_params', 'capital_allocation'
        ]
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required config field: {field}")
        
        # Validate trading hours
        if 'trading_hours' in config:
            hours = config['trading_hours']
            for key in ['start', 'end', 'square_off']:
                if key in hours and not Validators.validate_time(hours[key]):
                    errors.append(f"Invalid {key} time format")
        
        # Validate capital allocation
        if 'capital_allocation' in config:
            capital = config['capital_allocation']
            if capital.get('total', 0) <= 0:
                errors.append("Invalid total capital")
            if capital.get('per_trade', 0) <= 0:
                errors.append("Invalid per trade capital")
            if capital.get('per_symbol', 0) <= 0:
                errors.append("Invalid per symbol capital")
        
        # Validate risk parameters
        if 'risk_params' in config:
            risk = config['risk_params']
            if risk.get('max_daily_loss', 0) <= 0:
                errors.append("Invalid max daily loss")
            if risk.get('max_loss_per_trade', 0) <= 0:
                errors.append("Invalid max loss per trade")
            if not 0 < risk.get('max_drawdown', 0) < 1:
                errors.append("Invalid max drawdown")
            if risk.get('max_positions', 0) <= 0:
                errors.append("Invalid max positions")
        
        return errors

    @staticmethod
    def validate_strategy_params(params: Dict) -> List[str]:
        """Validate strategy specific parameters"""
        errors = []
        
        if 'gann_increments' in params:
            increments = params['gann_increments']
            if not all(isinstance(x, (int, float)) and x > 0 for x in increments):
                errors.append("Invalid Gann increments")
        
        if 'num_values' in params:
            if not isinstance(params['num_values'], int) or params['num_values'] <= 0:
                errors.append("Invalid number of values")
        
        if 'buffer_percentage' in params:
            buffer = params['buffer_percentage']
            if not isinstance(buffer, float) or not 0 < buffer < 1:
                errors.append("Invalid buffer percentage")
        
        if 'num_targets' in params:
            if not isinstance(params['num_targets'], int) or params['num_targets'] <= 0:
                errors.append("Invalid number of targets")
        
        if 'trailing_stop' in params:
            if not isinstance(params['trailing_stop'], float) or not 0 < params['trailing_stop'] < 1:
                errors.append("Invalid trailing stop value")
        
        return errors