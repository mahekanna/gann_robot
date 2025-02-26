import os
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

from ..core.utils.validators import Validators

class Settings:
    """Global settings management"""
    
    def __init__(self):
        self.config_dir = Path('config')
        self.loaded_configs = {}
        self.last_reload = {}
        self.reload_interval = 300  # 5 minutes
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
    def load_config(self, config_name: str) -> Dict:
        """Load configuration file"""
        try:
            config_path = self.config_dir / f"{config_name}.json"
            
            # Check if reload needed
            current_time = datetime.now()
            last_load_time = self.last_reload.get(config_name)
            
            if (config_name in self.loaded_configs and last_load_time and 
                (current_time - last_load_time).seconds < self.reload_interval):
                return self.loaded_configs[config_name]
            
            # Load and validate config
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Validate based on config type
            errors = []
            if config_name == 'trading_config':
                errors = Validators.validate_config(config)
            elif config_name == 'risk_config':
                errors = self._validate_risk_config(config)
            elif config_name == 'broker_config':
                errors = self._validate_broker_config(config)
            
            if errors:
                error_msg = f"Configuration validation failed: {', '.join(errors)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Store config
            self.loaded_configs[config_name] = config
            self.last_reload[config_name] = current_time
            
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading config {config_name}: {e}")
            raise
    
    def _validate_risk_config(self, config: Dict) -> List[str]:
        """Validate risk configuration"""
        errors = []
        
        required_fields = [
            'max_daily_loss',
            'max_loss_per_trade',
            'max_drawdown',
            'position_size_risk',
            'max_positions',
            'max_open_orders'
        ]
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required risk field: {field}")
        
        if 'max_daily_loss' in config and config['max_daily_loss'] <= 0:
            errors.append("Invalid max daily loss")
        
        if 'max_drawdown' in config and not 0 < config['max_drawdown'] < 1:
            errors.append("Invalid max drawdown")
        
        if 'position_size_risk' in config and not 0 < config['position_size_risk'] < 1:
            errors.append("Invalid position size risk")
        
        return errors
    
    def _validate_broker_config(self, config: Dict) -> List[str]:
        """Validate broker configuration"""
        errors = []
        
        required_fields = [
            'api_key',
            'api_secret',
            'totp_secret',
            'broker_type',
            'default_exchange',
            'default_product'
        ]
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required broker field: {field}")
        
        if 'broker_type' in config and config['broker_type'] not in ['ICICI', 'PAPER']:
            errors.append("Invalid broker type")
        
        if 'default_exchange' in config and not Validators.validate_exchange(config['default_exchange']):
            errors.append("Invalid default exchange")
        
        if 'default_product' in config and not Validators.validate_product_type(config['default_product']):
            errors.append("Invalid default product type")
        
        return errors
    
    def get_trading_config(self) -> Dict:
        """Get trading configuration"""
        return self.load_config('trading_config')
    
    def get_risk_config(self) -> Dict:
        """Get risk configuration"""
        return self.load_config('risk_config')
    
    def get_broker_config(self) -> Dict:
        """Get broker configuration"""
        return self.load_config('broker_config')
    
    def reload_all(self):
        """Force reload all configurations"""
        self.loaded_configs.clear()
        self.last_reload.clear()
        
        self.get_trading_config()
        self.get_risk_config()
        self.get_broker_config()
    
    def save_config(self, config_name: str, config: Dict):
        """Save configuration to file"""
        try:
            config_path = self.config_dir / f"{config_name}.json"
            
            # Validate before saving
            errors = []
            if config_name == 'trading_config':
                errors = Validators.validate_config(config)
            elif config_name == 'risk_config':
                errors = self._validate_risk_config(config)
            elif config_name == 'broker_config':
                errors = self._validate_broker_config(config)
            
            if errors:
                error_msg = f"Configuration validation failed: {', '.join(errors)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Save config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            # Force reload
            if config_name in self.loaded_configs:
                del self.loaded_configs[config_name]
                if config_name in self.last_reload:
                    del self.last_reload[config_name]
            
        except Exception as e:
            self.logger.error(f"Error saving config {config_name}: {e}")
            raise

# Global settings instance
settings = Settings()