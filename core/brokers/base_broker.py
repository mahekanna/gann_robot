# core/brokers/base_broker.py

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass

@dataclass
class OrderResponse:
    order_id: str
    status: str
    message: str
    details: Dict

@dataclass
class PositionData:
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    pnl: float
    product_type: str
    exchange: str

class BaseBroker(ABC):
    """Abstract base class for broker implementations"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection with broker"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if broker connection is active"""
        pass
    
    @abstractmethod
    def get_live_quote(self, symbol: str, exchange: str = "NSE") -> Optional[Dict]:
        """Get live market quote"""
        pass
    
    @abstractmethod
    def place_order(self, 
                   symbol: str,
                   quantity: int,
                   side: str,
                   product_type: str,
                   order_type: str,
                   price: float = 0.0,
                   trigger_price: float = 0.0) -> OrderResponse:
        """Place new order"""
        pass
    
    @abstractmethod
    def modify_order(self,
                    order_id: str,
                    new_quantity: Optional[int] = None,
                    new_price: Optional[float] = None,
                    new_trigger_price: Optional[float] = None) -> OrderResponse:
        """Modify existing order"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel order"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get order status"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[PositionData]:
        """Get current positions"""
        pass
    
    @abstractmethod
    def get_historical_data(self,
                          symbol: str,
                          start_time: datetime,
                          end_time: datetime,
                          interval: str,
                          exchange: str = "NSE") -> Optional[List[Dict]]:
        """Get historical data"""
        pass
    
    @abstractmethod
    def get_option_chain(self,
                        symbol: str,
                        expiry: datetime) -> Optional[Dict]:
        """Get option chain data"""
        pass
    
    @abstractmethod
    def get_profile(self) -> Dict:
        """Get trading profile/account information"""
        pass
    
    @abstractmethod
    def get_margins(self) -> Dict:
        """Get margin information"""
        pass
    
    @abstractmethod
    def get_funds(self) -> Dict:
        """Get funds/balance information"""
        pass
    
    @abstractmethod
    def is_market_open(self) -> bool:
        """Check if market is open"""
        pass
    
    @abstractmethod
    def get_exchange_status(self, exchange: str = "NSE") -> Dict:
        """Get exchange status"""
        pass
    
    @abstractmethod
    def get_order_book(self) -> List[Dict]:
        """Get order book"""
        pass
    
    @abstractmethod
    def get_trade_book(self) -> List[Dict]:
        """Get trade book"""
        pass
    
    @abstractmethod
    def get_holdings(self) -> List[Dict]:
        """Get holdings"""
        pass
    
    def validate_order_params(self,
                            symbol: str,
                            quantity: int,
                            side: str,
                            product_type: str,
                            order_type: str,
                            price: float = 0.0) -> bool:
        """Validate order parameters"""
        try:
            # Check symbol
            if not symbol:
                raise ValueError("Symbol cannot be empty")
                
            # Check quantity
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
                
            # Check side
            valid_sides = ["BUY", "SELL"]
            if side not in valid_sides:
                raise ValueError(f"Side must be one of {valid_sides}")
                
            # Check product type
            valid_products = ["INTRADAY", "DELIVERY", "CNC"]
            if product_type not in valid_products:
                raise ValueError(f"Product type must be one of {valid_products}")
                
            # Check order type
            valid_orders = ["MARKET", "LIMIT", "SL", "SL-M"]
            if order_type not in valid_orders:
                raise ValueError(f"Order type must be one of {valid_orders}")
                
            # Check price for limit orders
            if order_type == "LIMIT" and price <= 0:
                raise ValueError("Price must be positive for limit orders")
                
            return True
            
        except Exception as e:
            raise ValueError(f"Order validation failed: {str(e)}")
    
    def format_historical_data(self, data: List[Dict]) -> List[Dict]:
        """Format historical data to standard format"""
        formatted_data = []
        
        for candle in data:
            formatted_candle = {
                'timestamp': candle.get('datetime') or candle.get('date'),
                'open': float(candle.get('open', 0)),
                'high': float(candle.get('high', 0)),
                'low': float(candle.get('low', 0)),
                'close': float(candle.get('close', 0)),
                'volume': int(candle.get('volume', 0))
            }
            formatted_data.append(formatted_candle)
            
        return formatted_data
    
    def handle_error(self, error: Exception) -> Dict:
        """Handle and format error responses"""
        return {
            'status': 'error',
            'message': str(error),
            'error_type': error.__class__.__name__,
            'timestamp': datetime.now().isoformat()
        }