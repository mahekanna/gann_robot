# database/db_manager.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Optional
import logging
from datetime import datetime

from .models import Base, Trade, Order, Position, MarketData, DailyStats, Error

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_trade(self, trade_data: Dict) -> bool:
        session = self.Session()
        try:
            trade = Trade(**trade_data)
            session.add(trade)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving trade: {e}")
            return False
        finally:
            session.close()

    def save_order(self, order_data: Dict) -> bool:
        session = self.Session()
        try:
            order = Order(**order_data)
            session.add(order)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving order: {e}")
            return False
        finally:
            session.close()

    def update_position(self, position_data: Dict) -> bool:
        session = self.Session()
        try:
            position = session.query(Position).filter_by(
                symbol=position_data['symbol'], 
                is_active=True
            ).first()
            
            if position:
                for key, value in position_data.items():
                    setattr(position, key, value)
            else:
                position = Position(**position_data)
                session.add(position)
                
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating position: {e}")
            return False
        finally:
            session.close()

    def save_market_data(self, data: List[Dict]) -> bool:
        session = self.Session()
        try:
            for item in data:
                market_data = MarketData(**item)
                session.add(market_data)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving market data: {e}")
            return False
        finally:
            session.close()

    def update_daily_stats(self, stats: Dict) -> bool:
        session = self.Session()
        try:
            daily_stat = DailyStats(**stats)
            session.add(daily_stat)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating daily stats: {e}")
            return False
        finally:
            session.close()

    def log_error(self, error_data: Dict) -> bool:
        session = self.Session()
        try:
            error = Error(**error_data)
            session.add(error)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging error: {e}")
            return False
        finally:
            session.close()

    def cleanup_old_data(self, days: int) -> bool:
        session = self.Session()
        try:
            cutoff = datetime.now() - timedelta(days=days)
            session.query(MarketData).filter(MarketData.timestamp < cutoff).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up old data: {e}")
            return False
        finally:
            session.close()