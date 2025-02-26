# core/data/historical_data.py

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import json
import h5py
import numpy as np

from ..utils.logger import setup_logger

logger = setup_logger('historical_data')

class HistoricalDataManager:
    def __init__(self, config: Dict):
        """Initialize historical data manager"""
        self.config = config
        
        # Set up data directories
        self.data_dir = Path(config.get('data_dir', 'data/historical'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage
        self.storage_type = config.get('storage_type', 'hdf5')  # or 'csv'
        self.compression = config.get('compression', 'gzip')
        
        # Cache settings
        self.cache_enabled = config.get('cache_enabled', True)
        self.cache = {}
        self.cache_size = config.get('cache_size', 1000)  # number of dataframes to cache
        
    def store_data(self, 
                   symbol: str,
                   timeframe: str,
                   data: pd.DataFrame) -> bool:
        """Store historical data"""
        try:
            # Ensure data is properly formatted
            if not self._validate_data(data):
                logger.error("Invalid data format")
                return False
            
            # Generate filename
            filename = self._generate_filename(symbol, timeframe)
            
            if self.storage_type == 'hdf5':
                return self._store_hdf5(filename, data)
            else:
                return self._store_csv(filename, data)
            
        except Exception as e:
            logger.error(f"Error storing data: {e}")
            return False

    def _store_hdf5(self, filename: Path, data: pd.DataFrame) -> bool:
        """Store data in HDF5 format"""
        try:
            with h5py.File(filename.with_suffix('.h5'), 'a') as f:
                # Store metadata
                meta = {
                    'columns': data.columns.tolist(),
                    'last_update': datetime.now().isoformat()
                }
                if 'metadata' in f:
                    del f['metadata']
                f.create_dataset('metadata', data=json.dumps(meta))
                
                # Store data
                if 'data' in f:
                    del f['data']
                f.create_dataset('data', 
                               data=data.values,
                               compression=self.compression)
                
            return True
            
        except Exception as e:
            logger.error(f"Error storing HDF5 data: {e}")
            return False

    def _store_csv(self, filename: Path, data: pd.DataFrame) -> bool:
        """Store data in CSV format"""
        try:
            data.to_csv(filename.with_suffix('.csv'))
            return True
            
        except Exception as e:
            logger.error(f"Error storing CSV data: {e}")
            return False

    def get_data(self,
                 symbol: str,
                 timeframe: str,
                 start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """Get historical data"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{timeframe}"
            if self.cache_enabled and cache_key in self.cache:
                data = self.cache[cache_key]
                return self._filter_date_range(data, start_date, end_date)
            
            # Generate filename
            filename = self._generate_filename(symbol, timeframe)
            
            # Load data
            if self.storage_type == 'hdf5':
                data = self._load_hdf5(filename)
            else:
                data = self._load_csv(filename)
                
            if data is None:
                return None
                
            # Update cache
            if self.cache_enabled:
                self._update_cache(cache_key, data)
                
            return self._filter_date_range(data, start_date, end_date)
            
        except Exception as e:
            logger.error(f"Error getting data: {e}")
            return None

    def _load_hdf5(self, filename: Path) -> Optional[pd.DataFrame]:
        """Load data from HDF5 file"""
        try:
            filepath = filename.with_suffix('.h5')
            if not filepath.exists():
                return None
                
            with h5py.File(filepath, 'r') as f:
                # Load metadata
                meta = json.loads(f['metadata'][()])
                columns = meta['columns']
                
                # Load data
                data = f['data'][()]
                
                # Create DataFrame
                df = pd.DataFrame(data, columns=columns)
                df.index = pd.to_datetime(df['timestamp'])
                
                return df
                
        except Exception as e:
            logger.error(f"Error loading HDF5 data: {e}")
            return None

    def _load_csv(self, filename: Path) -> Optional[pd.DataFrame]:
        """Load data from CSV file"""
        try:
            filepath = filename.with_suffix('.csv')
            if not filepath.exists():
                return None
                
            df = pd.read_csv(filepath)
            df.index = pd.to_datetime(df['timestamp'])
            return df
            
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            return None

    def _filter_date_range(self,
                          data: pd.DataFrame,
                          start_date: Optional[datetime],
                          end_date: Optional[datetime]) -> pd.DataFrame:
        """Filter data for date range"""
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        return data

    def _update_cache(self, key: str, data: pd.DataFrame):
        """Update cache with new data"""
        self.cache[key] = data
        
        # Remove oldest entries if cache is too large
        if len(self.cache) > self.cache_size:
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k].index[-1])
            del self.cache[oldest_key]

    def _generate_filename(self, symbol: str, timeframe: str) -> Path:
        """Generate filename for data storage"""
        return self.data_dir / f"{symbol}_{timeframe}"

    def _validate_data(self, data: pd.DataFrame) -> bool:
        """Validate data format"""
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        return all(col in data.columns for col in required_columns)

    def update_data(self,
                    symbol: str,
                    timeframe: str,
                    new_data: pd.DataFrame) -> bool:
        """Update historical data with new data"""
        try:
            # Get existing data
            existing_data = self.get_data(symbol, timeframe)
            
            if existing_data is None:
                # No existing data, store new data
                return self.store_data(symbol, timeframe, new_data)
            
            # Combine data
            combined_data = pd.concat([existing_data, new_data])
            combined_data = combined_data[~combined_data.index.duplicated(keep='last')]
            combined_data.sort_index(inplace=True)
            
            # Store updated data
            return self.store_data(symbol, timeframe, combined_data)
            
        except Exception as e:
            logger.error(f"Error updating data: {e}")
            return False

    

    def get_data_info(self, symbol: str, timeframe: str) -> Dict:
        """Get information about stored data"""
        try:
            data = self.get_data(symbol, timeframe)
            if data is None:
                return {}
                
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'start_date': data.index.min(),
                'end_date': data.index.max(),
                'rows': len(data),
                'file_size': self._get_file_size(symbol, timeframe),
                'last_updated': self._get_last_update_time(symbol, timeframe)
            }
            
        except Exception as e:
            logger.error(f"Error getting data info: {e}")
            return {}

    def _get_file_size(self, symbol: str, timeframe: str) -> int:
        """Get file size in bytes"""
        try:
            filename = self._generate_filename(symbol, timeframe)
            if self.storage_type == 'hdf5':
                path = filename.with_suffix('.h5')
            else:
                path = filename.with_suffix('.csv')
                
            return path.stat().st_size if path.exists() else 0
            
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return 0

    def _get_last_update_time(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """Get last update time of data file"""
        try:
            filename = self._generate_filename(symbol, timeframe)
            if self.storage_type == 'hdf5':
                path = filename.with_suffix('.h5')
            else:
                path = filename.with_suffix('.csv')
                
            return datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else None
            
        except Exception as e:
            logger.error(f"Error getting last update time: {e}")
            return None

    def cleanup_old_data(self, days: int = 30):
        """Cleanup data older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get all data files
            if self.storage_type == 'hdf5':
                files = self.data_dir.glob('*.h5')
            else:
                files = self.data_dir.glob('*.csv')
                
            for file in files:
                # Check last modification time
                if datetime.fromtimestamp(file.stat().st_mtime) < cutoff_date:
                    file.unlink()
                    logger.info(f"Deleted old data file: {file}")
                    
            # Clear cache
            self.cache.clear()
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")

    def get_all_symbols(self) -> List[str]:
        """Get list of all symbols with stored data"""
        try:
            symbols = set()
            pattern = '*.h5' if self.storage_type == 'hdf5' else '*.csv'
            
            for file in self.data_dir.glob(pattern):
                # Extract symbol from filename
                symbol = file.stem.split('_')[0]
                symbols.add(symbol)
                
            return sorted(list(symbols))
            
        except Exception as e:
            logger.error(f"Error getting symbols list: {e}")
            return []

    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        try:
            total_size = 0
            file_count = 0
            symbol_count = len(self.get_all_symbols())
            
            pattern = '*.h5' if self.storage_type == 'hdf5' else '*.csv'
            for file in self.data_dir.glob(pattern):
                total_size += file.stat().st_size
                file_count += 1
                
            return {
                'storage_type': self.storage_type,
                'total_size_mb': total_size / (1024 * 1024),
                'file_count': file_count,
                'symbol_count': symbol_count,
                'cache_size': len(self.cache),
                'cache_enabled': self.cache_enabled
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}

    def verify_data_integrity(self, symbol: str, timeframe: str) -> bool:
        """Verify data integrity"""
        try:
            data = self.get_data(symbol, timeframe)
            if data is None:
                return False
                
            # Check for missing values
            if data.isnull().any().any():
                logger.warning(f"Missing values found in {symbol} {timeframe} data")
                return False
                
            # Check for duplicate timestamps
            if data.index.duplicated().any():
                logger.warning(f"Duplicate timestamps found in {symbol} {timeframe} data")
                return False
                
            # Check for gaps in data
            expected_periods = pd.date_range(data.index.min(), 
                                          data.index.max(), 
                                          freq=timeframe)
            if len(expected_periods) != len(data):
                logger.warning(f"Data gaps found in {symbol} {timeframe} data")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error verifying data integrity: {e}")
            return False

    def repair_data(self, symbol: str, timeframe: str) -> bool:
        """Attempt to repair data issues"""
        try:
            data = self.get_data(symbol, timeframe)
            if data is None:
                return False
                
            # Remove duplicates
            data = data[~data.index.duplicated(keep='first')]
            
            # Sort by timestamp
            data.sort_index(inplace=True)
            
            # Forward fill missing values
            data.fillna(method='ffill', inplace=True)
            
            # Store repaired data
            return self.store_data(symbol, timeframe, data)
            
        except Exception as e:
            logger.error(f"Error repairing data: {e}")
            return False

    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Clear cache
            self.cache.clear()
            
            logger.info("Historical data manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")