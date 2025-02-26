# core/brokers/paper_broker.py

import logging
from datetime import datetime
from typing import Dict, Optional, List
from .base_broker import BaseBroker, OrderResponse, PositionData
from ..utils.logger import setup_logger

logger = setup_logger('paper_broker')

class PaperBroker(BaseBroker):
    def __init__(self, live_broker, config: Dict):
        """
        Initialize paper trading broker
        Uses live broker for market data but simulates executions
        """
        self.live_broker = live_broker  # For market data
        self.config = config
        self.positions = {}
        self.orders = {}
        self.trades = []
        self.order_counter = 1
        
        # Paper trading settings
        self.initial_capital = config.get('paper_capital', 100000)
        self.available_capital = self.initial_capital
        self.used_capital = 0
        self.total_pnl = 0
        
        # Simulation settings
        self.slippage = config.get('slippage_percent', 0.05)  # 0.05% slippage
        self.transaction_cost = config.get('transaction_cost', 0.0003)  # 0.03% cost
        
    def connect(self) -> bool:
        """Connect is always successful for paper trading"""
        return True
        
    def is_connected(self) -> bool:
        """Always connected in paper trading"""
        return True
        
    def get_live_quote(self, symbol: str, exchange: str = "NSE") -> Optional[Dict]:
        """Get live quote from live broker"""
        return self.live_broker.get_live_quote(symbol, exchange)
        
    def place_order(self, 
                   symbol: str,
                   quantity: int,
                   side: str,
                   product_type: str,
                   order_type: str,
                   price: float = 0.0,
                   trigger_price: float = 0.0) -> OrderResponse:
        """Simulate order placement"""
        try:
            # Get current market price
            quote = self.get_live_quote(symbol)
            if not quote:
                return OrderResponse(
                    order_id="",
                    status='error',
                    message='Unable to get market price',
                    details={}
                )
            
            current_price = quote['ltp']
            
            # Apply slippage
            executed_price = self._apply_slippage(current_price, side)
            
            # Calculate transaction costs
            transaction_cost = executed_price * quantity * self.transaction_cost
            
            # Check capital availability for buy orders
            if side == "BUY":
                required_capital = (executed_price * quantity) + transaction_cost
                if required_capital > self.available_capital:
                    return OrderResponse(
                        order_id="",
                        status='error',
                        message='Insufficient capital',
                        details={'required': required_capital, 'available': self.available_capital}
                    )
            
            # Generate order id
            order_id = f"PAPER_ORD_{self.order_counter:06d}"
            self.order_counter += 1
            
            # Create order
            order = {
                'order_id': order_id,
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'product_type': product_type,
                'order_type': order_type,
                'price': executed_price,
                'status': 'COMPLETE',
                'timestamp': datetime.now(),
                'transaction_cost': transaction_cost
            }
            
            # Store order
            self.orders[order_id] = order
            
            # Update position
            self._update_position(order)
            
            # Update capital
            if side == "BUY":
                self.available_capital -= (executed_price * quantity + transaction_cost)
                self.used_capital += executed_price * quantity
            else:
                self.available_capital += (executed_price * quantity - transaction_cost)
                self.used_capital -= executed_price * quantity
            
            return OrderResponse(
                order_id=order_id,
                status='success',
                message='Order executed',
                details=order
            )
            
        except Exception as e:
            logger.error(f"Error placing paper order: {e}")
            return OrderResponse(
                order_id="",
                status='error',
                message=str(e),
                details={}
            )

    def _apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to price"""
        slippage_factor = 1 + (self.slippage/100 if side == "BUY" else -self.slippage/100)
        return price * slippage_factor

    def _update_position(self, order: Dict):
        """Update positions after order execution"""
        symbol = order['symbol']
        quantity = order['quantity']
        price = order['price']
        side = order['side']
        
        if symbol not in self.positions:
            self.positions[symbol] = PositionData(
                symbol=symbol,
                quantity=0,
                average_price=0,
                current_price=price,
                pnl=0,
                product_type=order['product_type'],
                exchange="NSE"
            )
        
        position = self.positions[symbol]
        
        if side == "BUY":
            # Calculate new average price
            new_quantity = position.quantity + quantity
            position.average_price = ((position.quantity * position.average_price) + 
                                    (quantity * price)) / new_quantity
            position.quantity = new_quantity
        else:
            # Update quantity and calculate P&L
            position.quantity -= quantity
            trade_pnl = (price - position.average_price) * quantity
            self.total_pnl += trade_pnl
            
            # Record trade
            self.trades.append({
                'symbol': symbol,
                'entry_price': position.average_price,
                'exit_price': price,
                'quantity': quantity,
                'pnl': trade_pnl,
                'timestamp': datetime.now()
            })
            
            # Remove position if fully closed
            if position.quantity == 0:
                del self.positions[symbol]

    def get_positions(self) -> List[PositionData]:
        """Get current positions"""
        return list(self.positions.values())

    def get_portfolio_value(self) -> Dict:
        """Get current portfolio value"""
        return {
            'initial_capital': self.initial_capital,
            'available_capital': self.available_capital,
            'used_capital': self.used_capital,
            'total_pnl': self.total_pnl,
            'current_value': self.initial_capital + self.total_pnl,
            'num_positions': len(self.positions)
        }

    def get_order_history(self) -> List[Dict]:
        """Get order history"""
        return list(self.orders.values())

    def get_trade_history(self) -> List[Dict]:
        """Get trade history"""
        return self.trades

    def reset(self):
        """Reset paper trading account"""
        self.positions.clear()
        self.orders.clear()
        self.trades.clear()
        self.available_capital = self.initial_capital
        self.used_capital = 0
        self.total_pnl = 0
        self.order_counter = 1
        logger.info("Paper trading account reset")