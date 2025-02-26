# core/data/market_data.py

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass
import asyncio

from ..utils.logger import setup_logger

logger = setup_logger('market_data')

@dataclass
class MarketQuote:
    symbol: str
    timestamp: datetime
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None
    atp: Optional[float] = None
    total_quantity: Optional[int] = None

class MarketDataHandler:
    def __init__(self, broker, config: Dict):
        """Initialize market data handler"""
        self.broker = broker
        self.config = config
        
        # Data caches
        self.quote_cache = {}
        self.candle_cache = {}
        self.last_update_time = {}
        
        # Update settings
        self.update_interval = config.get('quote_update_interval', 1)  # seconds
        self.cache_duration = config.get('cache_duration', 300)  # seconds
        self.max_retries = config.get('max_retries', 3)
        
        # Performance tracking
        self.update_times = []
        self.error_count = 0
        
    async def initialize(self) -> bool:
        """Initialize market data handler"""
        try:
            # Start data updater
            asyncio.create_task(self._run_updater())
            
            logger.info("Market data handler initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing market data handler: {e}")
            return False

    async def _run_updater(self):
        """Run continuous data updater"""
        while True:
            try:
                await self._update_market_data()
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in data updater: {e}")
                self.error_count += 1
                await asyncio.sleep(5)

    async def _update_market_data(self):
        """Update market data for all symbols"""
        try:
            update_start = datetime.now()
            
            # Get all symbols to update
            symbols = self._get_symbols_to_update()
            
            for symbol in symbols:
                try:
                    quote = await self.broker.get_live_quote(symbol)
                    if quote:
                        self._update_cache(symbol, quote)
                

                except Exception as e:
                    logger.error(f"Error updating {symbol}: {e}")
                    self.error_count += 1
            
            # Update performance metrics
            update_time = (datetime.now() - update_start).total_seconds()
            self.update_times.append(update_time)
            if len(self.update_times) > 1000:
                self.update_times.pop(0)
            
        except Exception as e:
            logger.error(f"Error in market data update: {e}")
            self.error_count += 1

    def _get_symbols_to_update(self) -> List[str]:
        """Get list of symbols that need updating"""
        current_time = datetime.now()
        return [
            symbol for symbol, last_time in self.last_update_time.items()
            if (current_time - last_time).seconds >= self.update_interval
        ]

    def _update_cache(self, symbol: str, quote_data: Dict):
        """Update cache with new quote data"""
        try:
            quote = MarketQuote(
                symbol=symbol,
                timestamp=datetime.now(),
                ltp=float(quote_data['ltp']),
                open=float(quote_data['open']),
                high=float(quote_data['high']),
                low=float(quote_data['low']),
                close=float(quote_data['close']),
                volume=int(quote_data['volume']),
                vwap=float(quote_data.get('vwap', 0)) or None,
                atp=float(quote_data.get('atp', 0)) or None,
                total_quantity=int(quote_data.get('total_quantity', 0)) or None
            )
            
            self.quote_cache[symbol] = quote
            self.last_update_time[symbol] = quote.timestamp
            
        except Exception as e:
            logger.error(f"Error updating cache for {symbol}: {e}")
            self.error_count += 1

    async def get_live_quote(self, symbol: str, max_age: int = None) -> Optional[MarketQuote]:
        """Get live quote for symbol"""
        try:
            # Check cache first
            if symbol in self.quote_cache:
                quote = self.quote_cache[symbol]
                age = (datetime.now() - quote.timestamp).seconds
                
                # Return cached quote if fresh enough
                if max_age is None or age <= max_age:
                    return quote
            
            # Get fresh quote
            for _ in range(self.max_retries):
                try:
                    quote_data = await self.broker.get_live_quote(symbol)
                    if quote_data:
                        self._update_cache(symbol, quote_data)
                        return self.quote_cache[symbol]
                except Exception as e:
                    logger.error(f"Error fetching quote for {symbol}: {e}")
                    await asyncio.sleep(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting live quote for {symbol}: {e}")
            return None

    async def get_historical_data(self,
                                symbol: str,
                                start_time: datetime,
                                end_time: datetime,
                                interval: str) -> Optional[pd.DataFrame]:
        """Get historical candle data"""
        try:
            # Generate cache key
            cache_key = f"{symbol}_{interval}_{start_time.date()}_{end_time.date()}"
            
            # Check cache
            if cache_key in self.candle_cache:
                return self.candle_cache[cache_key]
            
            # Fetch from broker
            candles = await self.broker.get_historical_data(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                interval=interval
            )
            
            if not candles:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(candles)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Cache data
            self.candle_cache[cache_key] = df
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None

    async def get_last_n_candles(self,
                                symbol: str,
                                n: int,
                                interval: str) -> Optional[pd.DataFrame]:
        """Get last N candles"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=n * int(interval))
            
            return await self.get_historical_data(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                interval=interval
            )
            
        except Exception as e:
            logger.error(f"Error getting last {n} candles for {symbol}: {e}")
            return None

    def clear_cache(self, symbol: Optional[str] = None):
        """Clear data cache"""
        try:
            if symbol:
                # Clear specific symbol
                self.quote_cache.pop(symbol, None)
                self.last_update_time.pop(symbol, None)
                
                # Clear candle cache for symbol
                keys_to_remove = [k for k in self.candle_cache.keys() 
                                if k.startswith(f"{symbol}_")]
                for key in keys_to_remove:
                    self.candle_cache.pop(key)
            else:
                # Clear all caches
                self.quote_cache.clear()
                self.last_update_time.clear()
                self.candle_cache.clear()
                
            logger.info(f"Cache cleared for {'all symbols' if symbol is None else symbol}")
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'quotes_cached': len(self.quote_cache),
            'candles_cached': len(self.candle_cache),
            'avg_update_time': sum(self.update_times) / len(self.update_times) if self.update_times else 0,
            'error_count': self.error_count,
            'timestamp': datetime.now()
        }

    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Clear all caches
            self.clear_cache()
            
            logger.info("Market data handler cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")