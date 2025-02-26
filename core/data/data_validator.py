# core/data/data_validator.py

import logging
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass

from ..utils.logger import setup_logger

logger = setup_logger('data_validator')

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict

class DataValidator:
    def __init__(self, config: Dict):
        """Initialize data validator"""
        self.config = config
        
        # Validation thresholds
        self.price_thresholds = {
            'min_price': 0.01,
            'max_price_change': 20.0,  # percentage
            'volume_min': 0,
            'gap_threshold': 0.1  # percentage
        }
        
        # Time validation settings
        self.max_timestamp_delay = 60  # seconds
        self.required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
    def validate_market_data(self, 
                           data: Union[Dict, pd.DataFrame],
                           data_type: str = 'quote') -> ValidationResult:
        """Validate market data"""
        errors = []
        warnings = []
        metadata = {}
        
        try:
            if isinstance(data, dict):
                result = self._validate_quote(data)
            else:
                result = self._validate_candles(data)
                
            errors.extend(result.errors)
            warnings.extend(result.warnings)
            metadata.update(result.metadata)
            
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error validating data: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                metadata={}
            )

    def _validate_quote(self, quote: Dict) -> ValidationResult:
        """Validate single quote data"""
        errors = []
        warnings = []
        metadata = {}
        
        try:
            # Check required fields
            required_fields = ['symbol', 'timestamp', 'ltp']
            for field in required_fields:
                if field not in quote:
                    errors.append(f"Missing required field: {field}")
            
            if errors:
                return ValidationResult(False, errors, warnings, metadata)
            
            # Validate timestamp
            timestamp_valid = self._validate_timestamp(quote['timestamp'])
            if not timestamp_valid:
                errors.append("Invalid timestamp")
            
            # Validate prices
            price_fields = ['ltp', 'open', 'high', 'low', 'close']
            for field in price_fields:
                if field in quote:
                    price_valid = self._validate_price(quote[field])
                    if not price_valid:
                        errors.append(f"Invalid price in {field}")
            
            # Check price consistency
            if all(field in quote for field in ['high', 'low', 'close']):
                if not (quote['low'] <= quote['close'] <= quote['high']):
                    errors.append("Inconsistent price levels")
            
            # Validate volume
            if 'volume' in quote and quote['volume'] < self.price_thresholds['volume_min']:
                warnings.append("Suspicious volume")
            
            # Add metadata
            metadata['timestamp_delay'] = (
                datetime.now() - pd.to_datetime(quote['timestamp'])
            ).total_seconds()
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error validating quote: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Quote validation error: {str(e)}"],
                warnings=[],
                metadata={}
            )

    def _validate_candles(self, df: pd.DataFrame) -> ValidationResult:
        """Validate candle data"""
        errors = []
        warnings = []
        metadata = {}
        
        try:
            # Check required columns
            missing_columns = set(self.required_columns) - set(df.columns)
            if missing_columns:
                errors.append(f"Missing required columns: {missing_columns}")
                return ValidationResult(False, errors, warnings, metadata)
            
            # Check for missing values
            null_counts = df.isnull().sum()
            if null_counts.any():
                for col in null_counts[null_counts > 0].index:
                    errors.append(f"Missing values in column: {col}")
            
            # Check price consistency
            price_errors = df[~(
                (df['low'] <= df['open']) & 
                (df['low'] <= df['close']) & 
                (df['high'] >= df['open']) & 
                (df['high'] >= df['close'])
            )]
            
            if not price_errors.empty:
                errors.append(f"Price consistency errors in {len(price_errors)} candles")
            
            # Check for gaps
            gaps = self._find_time_gaps(df)
            if gaps:
                warnings.append(f"Found {len(gaps)} time gaps in data")
                metadata['gaps'] = gaps
            
            # Check for price jumps
            price_jumps = self._check_price_jumps(df)
            if price_jumps:
                warnings.append(f"Found {len(price_jumps)} suspicious price jumps")
                metadata['price_jumps'] = price_jumps
            
            # Add metadata
            metadata.update({
                'start_time': df.index.min(),
                'end_time': df.index.max(),
                'candle_count': len(df),
                'null_counts': null_counts.to_dict()
            })
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error validating candles: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Candle validation error: {str(e)}"],
                warnings=[],
                metadata={}
            )

    def _validate_timestamp(self, timestamp) -> bool:
        """Validate timestamp"""
        try:
            ts = pd.to_datetime(timestamp)
            delay = (datetime.now() - ts).total_seconds()
            return delay <= self.max_timestamp_delay
            
        except Exception as e:
            logger.error(f"Error validating timestamp: {e}")
            return False

    def _validate_price(self, price: float) -> bool:
        """Validate price value"""
        try:
            return (isinstance(price, (int, float)) and 
                   price >= self.price_thresholds['min_price'])
        except Exception as e:
            logger.error(f"Error validating price: {e}")
            return False

    def _find_time_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """Find gaps in time series data"""
        try:
            gaps = []
            if len(df) < 2:
                return gaps
                
            # Calculate time differences
            time_diff = df.index.to_series().diff()
            expected_diff = pd.Timedelta(minutes=1)  # Assume 1-minute data
            
            # Find gaps
            gap_mask = time_diff > expected_diff
            if gap_mask.any():
                for i in gap_mask[gap_mask].index:
                    gaps.append({
                        'start': df.index[i-1],
                        'end': df.index[i],
                        'duration': time_diff[i]
                    })
            
            return gaps
            
        except Exception as e:
            logger.error(f"Error finding time gaps: {e}")
            return []

    # core/data/data_validator.py (continued)

    def _check_price_jumps(self, df: pd.DataFrame) -> List[Dict]:
        """Check for suspicious price jumps"""
        try:
            jumps = []
            if len(df) < 2:
                return jumps
                
            # Calculate percentage changes
            pct_changes = df['close'].pct_change().abs() * 100
            
            # Find significant jumps
            jump_threshold = self.price_thresholds['max_price_change']
            jump_mask = pct_changes > jump_threshold
            
            if jump_mask.any():
                for idx in jump_mask[jump_mask].index:
                    jumps.append({
                        'timestamp': idx,
                        'prev_price': df['close'][idx-1],
                        'curr_price': df['close'][idx],
                        'pct_change': pct_changes[idx]
                    })
            
            return jumps
            
        except Exception as e:
            logger.error(f"Error checking price jumps: {e}")
            return []

    def validate_tick_data(self, ticks: List[Dict]) -> ValidationResult:
        """Validate tick data"""
        errors = []
        warnings = []
        metadata = {'tick_count': len(ticks)}
        
        try:
            if not ticks:
                errors.append("Empty tick data")
                return ValidationResult(False, errors, warnings, metadata)
            
            # Check each tick
            for i, tick in enumerate(ticks):
                # Validate basic structure
                if not all(key in tick for key in ['price', 'quantity', 'timestamp']):
                    errors.append(f"Missing required fields in tick {i}")
                    continue
                
                # Validate price
                if not self._validate_price(tick['price']):
                    errors.append(f"Invalid price in tick {i}")
                
                # Validate quantity
                if tick['quantity'] <= 0:
                    errors.append(f"Invalid quantity in tick {i}")
                
                # Validate timestamp
                if not self._validate_timestamp(tick['timestamp']):
                    warnings.append(f"Delayed timestamp in tick {i}")
            
            # Check sequence
            timestamps = [pd.to_datetime(tick['timestamp']) for tick in ticks]
            if any(timestamps[i] > timestamps[i+1] for i in range(len(timestamps)-1)):
                errors.append("Out of sequence timestamps")
            
            metadata.update({
                'start_time': min(timestamps),
                'end_time': max(timestamps),
                'avg_tick_gap': np.mean(np.diff([t.timestamp() for t in timestamps]))
            })
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error validating tick data: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Tick validation error: {str(e)}"],
                warnings=[],
                metadata=metadata
            )

    def validate_options_data(self, data: Dict) -> ValidationResult:
        """Validate options market data"""
        errors = []
        warnings = []
        metadata = {}
        
        try:
            # Check required fields
            required_fields = ['symbol', 'strike', 'expiry', 'option_type', 'ltp']
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
            
            if errors:
                return ValidationResult(False, errors, warnings, metadata)
            
            # Validate option type
            if data['option_type'] not in ['CE', 'PE']:
                errors.append("Invalid option type")
            
            # Validate expiry
            try:
                expiry = pd.to_datetime(data['expiry'])
                if expiry < datetime.now():
                    errors.append("Expired option")
            except:
                errors.append("Invalid expiry date")
            
            # Validate strike price
            if not self._validate_price(data['strike']):
                errors.append("Invalid strike price")
            
            # Validate LTP
            if not self._validate_price(data['ltp']):
                errors.append("Invalid LTP")
            
            # Check for suspicious values
            if 'open_interest' in data and data['open_interest'] < 0:
                errors.append("Invalid open interest")
            
            if 'volume' in data and data['volume'] < 0:
                errors.append("Invalid volume")
            
            metadata.update({
                'symbol': data['symbol'],
                'strike': data['strike'],
                'option_type': data['option_type'],
                'expiry': data.get('expiry')
            })
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error validating options data: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Options validation error: {str(e)}"],
                warnings=[],
                metadata=metadata
            )

    def validate_order_data(self, order: Dict) -> ValidationResult:
        """Validate order data"""
        errors = []
        warnings = []
        metadata = {}
        
        try:
            # Check required fields
            required_fields = ['symbol', 'quantity', 'order_type', 'side']
            for field in required_fields:
                if field not in order:
                    errors.append(f"Missing required field: {field}")
            
            if errors:
                return ValidationResult(False, errors, warnings, metadata)
            
            # Validate quantity
            if not isinstance(order['quantity'], int) or order['quantity'] <= 0:
                errors.append("Invalid quantity")
            
            # Validate order type
            valid_order_types = ['MARKET', 'LIMIT', 'SL', 'SL-M']
            if order['order_type'] not in valid_order_types:
                errors.append("Invalid order type")
            
            # Validate side
            if order['side'] not in ['BUY', 'SELL']:
                errors.append("Invalid order side")
            
            # Validate price for limit orders
            if order['order_type'] in ['LIMIT', 'SL']:
                if 'price' not in order or not self._validate_price(order['price']):
                    errors.append("Invalid price for limit order")
            
            metadata.update({
                'symbol': order['symbol'],
                'order_type': order['order_type'],
                'side': order['side'],
                'quantity': order['quantity']
            })
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error validating order data: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Order validation error: {str(e)}"],
                warnings=[],
                metadata=metadata
            )