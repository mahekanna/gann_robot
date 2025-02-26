# database/models.py

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class TradeType(enum.Enum):
    EQUITY = "EQUITY"
    OPTION = "OPTION"
    FUTURE = "FUTURE"

class Trade(Base):
    """Model for storing trade information"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    trade_type = Column(Enum(TradeType), nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime)
    pnl = Column(Float)
    status = Column(String)
    strategy = Column(String, nullable=False)
    
    # Relationships
    orders = relationship("Order", back_populates="trade")
    positions = relationship("Position", back_populates="trade")

class Order(Base):
    """Model for storing order information"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey('trades.id'))
    order_id = Column(String, unique=True)
    symbol = Column(String, nullable=False)
    order_type = Column(String, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float)
    trigger_price = Column(Float)
    status = Column(Enum(OrderStatus), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    filled_quantity = Column(Integer, default=0)
    average_price = Column(Float)
    remarks = Column(String)
    
    # Relationships
    trade = relationship("Trade", back_populates="orders")

class Position(Base):
    """Model for storing position information"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey('trades.id'))
    symbol = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float)
    pnl = Column(Float)
    last_update = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    trade = relationship("Trade", back_populates="positions")

class MarketData(Base):
    """Model for storing market data"""
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    vwap = Column(Float)
    number_of_trades = Column(Integer)

class OptionData(Base):
    """Model for storing options data"""
    __tablename__ = 'option_data'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    expiry = Column(DateTime, nullable=False)
    strike = Column(Float, nullable=False)
    option_type = Column(String, nullable=False)  # CE or PE
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    oi = Column(Integer)  # Open Interest
    iv = Column(Float)   # Implied Volatility

class DailyStats(Base):
    """Model for storing daily statistics"""
    __tablename__ = 'daily_stats'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    gross_profit = Column(Float, default=0)
    gross_loss = Column(Float, default=0)
    net_pnl = Column(Float, default=0)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    strategy = Column(String, nullable=False)

class StrategyState(Base):
    """Model for storing strategy state"""
    __tablename__ = 'strategy_state'
    
    id = Column(Integer, primary_key=True)
    strategy_name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    state = Column(String, nullable=False)
    last_update = Column(DateTime, nullable=False)
    parameters = Column(String)  # JSON string of parameters
    active_positions = Column(Integer, default=0)
    daily_pnl = Column(Float, default=0)
    is_active = Column(Boolean, default=True)

class SystemLog(Base):
    """Model for storing system logs"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    level = Column(String, nullable=False)
    component = Column(String, nullable=False)
    message = Column(String, nullable=False)
    details = Column(String)  # Additional JSON details

class Error(Base):
    """Model for storing errors"""
    __tablename__ = 'errors'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    component = Column(String, nullable=False)
    error_type = Column(String, nullable=False)
    message = Column(String, nullable=False)
    stack_trace = Column(String)
    resolved = Column(Boolean, default=False)
    resolution_time = Column(DateTime)
    resolution_notes = Column(String)