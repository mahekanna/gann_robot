# core/brokers/icici_breeze.py

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from breeze_connect import BreezeConnect
from .base_broker import BaseBroker, OrderResponse, PositionData
from ..utils.logger import setup_logger
from autologin import breeze_auto_login

logger = setup_logger('icici_breeze')

class ICICIBreezeError(Exception):
    """Custom exception for ICICI Breeze specific errors"""
    pass

class ICICIBreeze(BaseBroker):
    def __init__(self, api_key: str, api_secret: str, totp_secret: str, breeze_instance=None):
        """Initialize ICICI Breeze broker"""
        self.api_key = api_key
        self.api_secret = api_secret
        self.totp_secret = totp_secret
        self.breeze = breeze_instance  # Can accept an existing instance 
        self._connected = True if breeze_instance else False
        self.last_error_time = None
        self.error_cooldown = 300  # 5 minutes
        
    def connect(self) -> bool:
        """Connect to ICICI Breeze using autologin"""
        try:
            # If we already have a breeze instance, just verify it
            if self.breeze and self._connected:
                try:
                    # Test connection with a simple API call
                    _ = self.get_profile()
                    logger.info("Using existing ICICI Breeze connection")
                    return True
                except:
                    logger.warning("Existing Breeze connection failed, reconnecting...")
                    self._connected = False
            
            # Use autologin for new connection
            self.breeze = breeze_auto_login(
                self.api_key,
                self.api_secret,
                self.totp_secret
            )
            
            if self.breeze:
                self._connected = True
                logger.info("Successfully connected to ICICI Breeze")
                return True
                
            logger.error("Failed to connect to ICICI Breeze")
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to ICICI Breeze: {e}")
            raise ICICIBreezeError(f"Connection failed: {str(e)}")
            
    def is_connected(self) -> bool:
        """Check connection status"""
        if not self._connected or not self.breeze:
            return False
            
        try:
            # Test connection with a simple API call
            _ = self.get_profile()
            return True
        except:
            self._connected = False
            return False
            
    def _ensure_connection(self) -> bool:
        """Ensure we have an active connection"""
        if not self.is_connected():
            return self.connect()
        return True
        
    def get_live_quote(self, symbol: str, exchange: str = "NSE") -> Optional[Dict]:
        """Get live market quote"""
        if not self._ensure_connection():
            raise ICICIBreezeError("Not connected to broker")
            
        try:
            response = self.breeze.get_quotes(
                stock_code=symbol,
                exchange_code=exchange,
                expiry="",
                product_type="cash",
                right="",
                strike_price=""
            )
            
            if response and isinstance(response, dict):
                success_data = response.get('Success', [])
                if success_data and len(success_data) > 0:
                    quote_data = success_data[0]
                    return {
                        'symbol': symbol,
                        'ltp': float(quote_data.get('ltp', 0)),
                        'open': float(quote_data.get('open', 0)),
                        'high': float(quote_data.get('high', 0)),
                        'low': float(quote_data.get('low', 0)),
                        'close': float(quote_data.get('close', 0)),
                        'volume': int(quote_data.get('volume', 0)),
                        'timestamp': datetime.now()
                    }
            return None
            
        except Exception as e:
            self._log_error(f"Error getting quote for {symbol}: {e}")
            raise ICICIBreezeError(f"Quote fetch failed: {str(e)}")

    def place_order(self, 
                   symbol: str,
                   quantity: int,
                   side: str,
                   product_type: str,
                   order_type: str,
                   price: float = 0.0,
                   trigger_price: float = 0.0) -> OrderResponse:
        """Place new order"""
        if not self._ensure_connection():
            raise ICICIBreezeError("Not connected to broker")
            
        try:
            # Validate order parameters
            self.validate_order_params(
                symbol, quantity, side, product_type, order_type, price
            )
            
            # Convert product type to ICICI format
            product_code = self._get_product_code(product_type)
            
            # Convert order type to ICICI format
            order_code = self._get_order_type_code(order_type)
            
            # Convert side to ICICI format (B/S)
            action = "B" if side == "BUY" else "S"
            
            response = self.breeze.place_order(
                stock_code=symbol,
                exchange_code="NSE",
                product=product_code,
                action=action,
                quantity=str(quantity),
                order_type=order_code,
                price=str(price) if price > 0 else "0",
                validity="DAY",
                disclosed_quantity="0",
                trigger_price=str(trigger_price) if trigger_price > 0 else "0",
                retention="DAY",
                remarks="API Order"
            )
            
            if response and isinstance(response, dict):
                success = response.get('Success', [])
                if success and len(success) > 0:
                    order_id = success[0].get('order_id')
                    return OrderResponse(
                        order_id=order_id,
                        status='success',
                        message='Order placed successfully',
                        details=success[0]
                    )
            
            return OrderResponse(
                order_id='',
                status='error',
                message=f"Order failed: {response}",
                details=response
            )
            
        except Exception as e:
            self._log_error(f"Error placing order: {e}")
            raise ICICIBreezeError(f"Order placement failed: {str(e)}")

    def _get_product_code(self, product_type: str) -> str:
        """Convert generic product type to ICICI specific code"""
        product_mapping = {
            "INTRADAY": "I",
            "DELIVERY": "C",
            "CNC": "C",
            "MARGIN": "M"
        }
        return product_mapping.get(product_type.upper(), "I")  # Default to Intraday

    def _get_order_type_code(self, order_type: str) -> str:
        """Convert generic order type to ICICI specific code"""
        order_mapping = {
            "MARKET": "MKT",
            "LIMIT": "L",
            "SL": "SL",
            "SL-M": "SL-M"
        }
        return order_mapping.get(order_type.upper(), "MKT")  # Default to Market

    def modify_order(self,
                    order_id: str,
                    new_quantity: Optional[int] = None,
                    new_price: Optional[float] = None,
                    new_trigger_price: Optional[float] = None) -> OrderResponse:
        """Modify existing order"""
        if not self._ensure_connection():
            raise ICICIBreezeError("Not connected to broker")
            
        try:
            response = self.breeze.modify_order(
                order_id=order_id,
                quantity=str(new_quantity) if new_quantity else None,
                price=str(new_price) if new_price else None,
                trigger_price=str(new_trigger_price) if new_trigger_price else None,
                validity="DAY",
                disclosed_quantity="0",
                retention="DAY"
            )
            
            if response and isinstance(response, dict):
                success = response.get('Success', [])
                if success and len(success) > 0:
                    return OrderResponse(
                        order_id=order_id,
                        status='success',
                        message='Order modified successfully',
                        details=success[0]
                    )
            
            return OrderResponse(
                order_id=order_id,
                status='error',
                message=f"Modification failed: {response}",
                details=response
            )
            
        except Exception as e:
            self._log_error(f"Error modifying order: {e}")
            raise ICICIBreezeError(f"Order modification failed: {str(e)}")

    def get_positions(self) -> List[PositionData]:
        """Get current positions"""
        if not self._ensure_connection():
            raise ICICIBreezeError("Not connected to broker")
            
        try:
            response = self.breeze.get_portfolio_positions()
            
            positions = []
            if response and isinstance(response, dict):
                success_data = response.get('Success', [])
                for pos in success_data:
                    positions.append(PositionData(
                        symbol=pos['stock_code'],
                        quantity=int(pos['quantity']),
                        average_price=float(pos['average_price']),
                        current_price=float(pos['last_price']),
                        pnl=float(pos['pnl']),
                        product_type=pos['product'],
                        exchange=pos['exchange_code']
                    ))
            return positions
            
        except Exception as e:
            self._log_error(f"Error getting positions: {e}")
            raise ICICIBreezeError(f"Position fetch failed: {str(e)}")

    def _log_error(self, error_msg: str):
        """Log error with cooldown"""
        current_time = datetime.now()
        if (self.last_error_time is None or 
            (current_time - self.last_error_time).seconds > self.error_cooldown):
            logger.error(error_msg)
            self.last_error_time = current_time
            
    def get_historical_data(self,
                          symbol: str,
                          start_time: datetime,
                          end_time: datetime,
                          interval: str,
                          exchange: str = "NSE") -> Optional[List[Dict]]:
        """Get historical data"""
        if not self._ensure_connection():
            raise ICICIBreezeError("Not connected to broker")
            
        try:
            response = self.breeze.get_historical_data(
                interval=interval,
                from_date=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                to_date=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                stock_code=symbol,
                exchange_code=exchange,
                product_type="cash"
            )
            
            if response and isinstance(response, dict):
                data = response.get('Success', [])
                if data:
                    return self.format_historical_data(data)
            return None
            
        except Exception as e:
            self._log_error(f"Error getting historical data: {e}")
            raise ICICIBreezeError(f"Historical data fetch failed: {str(e)}")

    def get_option_chain(self,
                        symbol: str,
                        expiry: datetime) -> Optional[Dict]:
        """Get option chain data"""
        if not self._ensure_connection():
            raise ICICIBreezeError("Not connected to broker")
            
        try:
            response = self.breeze.get_option_chain_quotes(
                stock_code=symbol,
                exchange_code="NFO",
                expiry=expiry.strftime("%d-%m-%Y"),
                right="CE,PE",
                strike_price=""
            )
            
            if response and isinstance(response, dict):
                return response.get('Success', [])
            return None
            
        except Exception as e:
            self._log_error(f"Error getting option chain: {e}")
            raise ICICIBreezeError(f"Option chain fetch failed: {str(e)}")

    def get_profile(self) -> Dict:
        """Get trading profile/account information"""
        if not self._ensure_connection():
            raise ICICIBreezeError("Not connected to broker")
            
        try:
            response = self.breeze.get_customer_details()
            
            if response and isinstance(response, dict):
                return response.get('Success', [{}])[0]
            return {}
            
        except Exception as e:
            self._log_error(f"Error getting profile: {e}")
            raise ICICIBreezeError(f"Profile fetch failed: {str(e)}")

    def get_margins(self) -> Dict:
        """Get margin information"""
        if not self._ensure_connection():
            raise ICICIBreezeError("Not connected to broker")
            
        try:
            response = self.breeze.get_margin()
            
            if response and isinstance(response, dict):
                margins = response.get('Success', [{}])[0]
                return {
                    'total': float(margins.get('total', 0)),
                    'used': float(margins.get('utilized', 0)),
                    'available': float(margins.get('available', 0))
                }
            return {}
            
        except Exception as e:
            self._log_error(f"Error getting margins: {e}")
            raise ICICIBreezeError(f"Margin fetch failed: {str(e)}")

    def get_funds(self) -> Dict:
        """Get funds information"""
        return self.get_margins()  # Same as margins for ICICI

    def is_market_open(self) -> bool:
        """Check if market is open"""
        current_time = datetime.now()
        
        # Check if it's a weekday
        if current_time.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
            return False
        
        # Market hours: 9:15 AM to 3:30 PM IST
        market_start = current_time.replace(hour=9, minute=15, second=0, microsecond=0)
        market_end = current_time.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return market_start <= current_time <= market_end

    def get_exchange_status(self, exchange: str = "NSE") -> Dict:
        """Get exchange status"""
        if not self._ensure_connection():
            raise ICICIBreezeError("Not connected to broker")
            
        try:
            # ICICI doesn't provide direct exchange status
            # Using market hours as proxy
            is_open = self.is_market_open()
            
            return {
                'exchange': exchange,
                'status': 'open' if is_open else 'closed',
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self._log_error(f"Error getting exchange status: {e}")
            raise ICICIBreezeError(f"Exchange status fetch failed: {str(e)}")

def get_trade_book(self) -> List[Dict]:
    """Get trade book"""
    if not self._ensure_connection():
        raise ICICIBreezeError("Not connected to broker")
        
    try:
        response = self.breeze.get_trade_list()
        
        if response and isinstance(response, dict):
            trades = response.get('Success', [])
            formatted_trades = []
            
            for trade in trades:
                formatted_trades.append({
                    'trade_id': trade.get('trade_id'),
                    'order_id': trade.get('order_id'),
                    'symbol': trade.get('stock_code'),
                    'exchange': trade.get('exchange_code'),
                    'quantity': int(trade.get('quantity', 0)),
                    'price': float(trade.get('price', 0)),
                    'trade_time': trade.get('trade_time'),
                    'side': trade.get('action'),
                    'product': trade.get('product')
                })
                
            return formatted_trades
        return []
        
    except Exception as e:
        self._log_error(f"Error getting trade book: {e}")
        raise ICICIBreezeError(f"Trade book fetch failed: {str(e)}")

def get_holdings(self) -> List[Dict]:
    """Get holdings information"""
    if not self._ensure_connection():
        raise ICICIBreezeError("Not connected to broker")
        
    try:
        response = self.breeze.get_portfolio_holdings()
        
        if response and isinstance(response, dict):
            holdings = response.get('Success', [])
            formatted_holdings = []
            
            for holding in holdings:
                formatted_holdings.append({
                    'symbol': holding.get('stock_code'),
                    'exchange': holding.get('exchange_code'),
                    'quantity': int(holding.get('quantity', 0)),
                    'average_price': float(holding.get('average_price', 0)),
                    'last_price': float(holding.get('last_price', 0)),
                    'pnl': float(holding.get('pnl', 0)),
                    'product': holding.get('product')
                })
                
            return formatted_holdings
        return []
        
    except Exception as e:
        self._log_error(f"Error getting holdings: {e}")
        raise ICICIBreezeError(f"Holdings fetch failed: {str(e)}")

def cancel_order(self, order_id: str) -> OrderResponse:
    """Cancel an order"""
    if not self._ensure_connection():
        raise ICICIBreezeError("Not connected to broker")
        
    try:
        response = self.breeze.cancel_order(order_id=order_id)
        
        if response and isinstance(response, dict):
            success = response.get('Success', [])
            if success and len(success) > 0:
                return OrderResponse(
                    order_id=order_id,
                    status='success',
                    message='Order cancelled successfully',
                    details=success[0]
                )
        
        return OrderResponse(
            order_id=order_id,
            status='error',
            message=f"Cancellation failed: {response}",
            details=response
        )
        
    except Exception as e:
        self._log_error(f"Error cancelling order: {e}")
        raise ICICIBreezeError(f"Order cancellation failed: {str(e)}")

def get_option_expiries(self, symbol: str) -> List[datetime]:
    """Get available option expiry dates"""
    if not self._ensure_connection():
        raise ICICIBreezeError("Not connected to broker")
        
    try:
        response = self.breeze.get_option_chain_quotes(
            stock_code=symbol,
            exchange_code="NFO",
            expiry="",  # Empty for all expiries
            right="CE",  # Doesn't matter for expiry list
            strike_price=""
        )
        
        if response and isinstance(response, dict):
            expiries = set()
            for data in response.get('Success', []):
                expiry_str = data.get('expiry')
                if expiry_str:
                    try:
                        expiry_date = datetime.strptime(expiry_str, "%d-%m-%Y")
                        expiries.add(expiry_date)
                    except:
                        continue
            
            return sorted(list(expiries))
        return []
        
    except Exception as e:
        self._log_error(f"Error getting option expiries: {e}")
        raise ICICIBreezeError(f"Option expiry fetch failed: {str(e)}")

def get_option_strikes(self, 
                     symbol: str, 
                     expiry: datetime) -> List[float]:
    """Get available option strikes"""
    if not self._ensure_connection():
        raise ICICIBreezeError("Not connected to broker")
        
    try:
        response = self.breeze.get_option_chain_quotes(
            stock_code=symbol,
            exchange_code="NFO",
            expiry=expiry.strftime("%d-%m-%Y"),
            right="CE",  # Get only calls (strikes will be same for puts)
            strike_price=""
        )
        
        if response and isinstance(response, dict):
            strikes = set()
            for data in response.get('Success', []):
                strike = data.get('strike_price')
                if strike:
                    try:
                        strikes.add(float(strike))
                    except:
                        continue
            
            return sorted(list(strikes))
        return []
        
    except Exception as e:
        self._log_error(f"Error getting option strikes: {e}")
        raise ICICIBreezeError(f"Option strike fetch failed: {str(e)}")

def get_instrument_limits(self, symbol: str) -> Dict:
    """Get trading limits for an instrument"""
    if not self._ensure_connection():
        raise ICICIBreezeError("Not connected to broker")
        
    try:
        response = self.breeze.get_limits(
            exchange_code="NSE",
            stock_code=symbol
        )
        
        if response and isinstance(response, dict):
            limits = response.get('Success', [{}])[0]
            return {
                'max_quantity': int(limits.get('max_quantity', 0)),
                'lot_size': int(limits.get('lot_size', 1)),
                'tick_size': float(limits.get('tick_size', 0.05)),
                'freeze_quantity': int(limits.get('freeze_quantity', 0))
            }
        return {}
        
    except Exception as e:
        self._log_error(f"Error getting instrument limits: {e}")
        raise ICICIBreezeError(f"Limits fetch failed: {str(e)}")

def get_market_depth(self, symbol: str) -> Dict:
    """Get market depth (order book)"""
    if not self._ensure_connection():
        raise ICICIBreezeError("Not connected to broker")
        
    try:
        response = self.breeze.get_quotes(
            stock_code=symbol,
            exchange_code="NSE",
            expiry="",
            product_type="cash",
            right="",
            strike_price=""
        )
        
        if response and isinstance(response, dict):
            depth = response.get('Success', [{}])[0]
            return {
                'bids': [
                    {
                        'quantity': int(depth.get(f'best_bid_qty{i}', 0)),
                        'price': float(depth.get(f'best_bid_price{i}', 0))
                    }
                    for i in range(1, 6)  # Top 5 bids
                ],
                'asks': [
                    {
                        'quantity': int(depth.get(f'best_ask_qty{i}', 0)),
                        'price': float(depth.get(f'best_ask_price{i}', 0))
                    }
                    for i in range(1, 6)  # Top 5 asks
                ]
            }
        return {'bids': [], 'asks': []}
        
    except Exception as e:
        self._log_error(f"Error getting market depth: {e}")
        raise ICICIBreezeError(f"Market depth fetch failed: {str(e)}")

def get_daily_limits(self) -> Dict:
    """Get daily trading limits"""
    return {
        'cash': self.get_margins(),
        'intraday_margin': 5.0,  # Example: 5x leverage for intraday
        'max_orders': 200  # Example: max 200 orders per day
    }

def _get_exchange_segment(self, exchange: str, product_type: str = "cash") -> str:
    """Get exchange segment code"""
    segments = {
        ("NSE", "cash"): "NSE",
        ("NSE", "futures"): "NFO",
        ("NSE", "options"): "NFO",
        ("BSE", "cash"): "BSE",
        ("BSE", "futures"): "BFO",
        ("BSE", "options"): "BFO"
    }
    return segments.get((exchange.upper(), product_type.lower()), "NSE")

def cleanup(self):
    """Cleanup resources"""
    self._connected = False
    self.breeze = None
    logger.info("ICICI Breeze resources cleaned up")