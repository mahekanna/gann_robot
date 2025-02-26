# core/engine/session_manager.py

import logging
from datetime import datetime, time, timedelta
from typing import Dict, Optional
import asyncio
from enum import Enum

from ..utils.logger import setup_logger

logger = setup_logger('session_manager')

class SessionState(Enum):
    WAITING = "WAITING"
    STARTING = "STARTING"
    ACTIVE = "ACTIVE"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    ERROR = "ERROR"

class SessionManager:
    def __init__(self, config: Dict):
        """Initialize session manager"""
        self.config = config
        self.state = SessionState.CLOSED
        
        # Parse trading hours
        self.market_start = self._parse_time(config['trading_hours']['start'])
        self.market_end = self._parse_time(config['trading_hours']['end'])
        self.square_off_time = self._parse_time(config['trading_hours']['square_off'])
        
        # Session tracking
        self.session_id = None
        self.session_start = None
        self.last_check_time = None
        self.check_interval = config.get('session_check_interval', 60)  # seconds
        
        # Performance tracking
        self.daily_stats = {}
        
    def _parse_time(self, time_str: str) -> time:
        """Parse time string to time object"""
        return datetime.strptime(time_str, "%H:%M").time()

    async def initialize(self) -> bool:
        """Initialize session manager"""
        try:
            # Start in waiting state
            self.state = SessionState.WAITING
            
            # Start session monitor
            asyncio.create_task(self._monitor_session())
            
            logger.info("Session manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing session manager: {e}")
            self.state = SessionState.ERROR
            return False

    async def _monitor_session(self):
        """Monitor trading session"""
        while True:
            try:
                current_time = datetime.now().time()
                
                if self.state == SessionState.WAITING:
                    # Check for session start
                    if self._should_start_session(current_time):
                        await self._start_session()
                        
                elif self.state == SessionState.ACTIVE:
                    # Check for session end
                    if self._should_end_session(current_time):
                        await self._end_session()
                        
                # Sleep for interval
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring session: {e}")
                await asyncio.sleep(5)

    def _should_start_session(self, current_time: time) -> bool:
        """Check if session should start"""
        if not self._is_trading_day():
            return False
            
        return current_time >= self.market_start and current_time < self.market_end

    def _should_end_session(self, current_time: time) -> bool:
        """Check if session should end"""
        return current_time >= self.square_off_time

    def _is_trading_day(self) -> bool:
        """Check if current day is a trading day"""
        current_date = datetime.now().date()
        
        # Check weekday (0 = Monday, 6 = Sunday)
        if current_date.weekday() >= 5:
            return False
            
        # Check holidays
        holidays = self.config.get('market_holidays', [])
        if current_date.strftime("%Y-%m-%d") in holidays:
            return False
            
        return True

    async def _start_session(self):
        """Start new trading session"""
        try:
            logger.info("Starting new trading session")
            self.state = SessionState.STARTING
            
            # Generate session ID
            self.session_id = datetime.now().strftime("%Y%m%d")
            self.session_start = datetime.now()
            
            # Initialize session stats
            self.daily_stats = {
                'session_id': self.session_id,
                'start_time': self.session_start,
                'trades': 0,
                'errors': 0,
                'pnl': 0.0
            }
            
            self.state = SessionState.ACTIVE
            logger.info(f"Trading session {self.session_id} started")
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            self.state = SessionState.ERROR

    async def _end_session(self):
        """End current trading session"""
        try:
            logger.info("Ending trading session")
            self.state = SessionState.CLOSING
            
            # Save session stats
            self.daily_stats['end_time'] = datetime.now()
            self.daily_stats['duration'] = (
                self.daily_stats['end_time'] - self.daily_stats['start_time']
            ).total_seconds() / 3600  # hours
            
            await self._save_session_stats()
            
            # Reset session
            self.session_id = None
            self.session_start = None
            
            self.state = SessionState.WAITING
            logger.info("Trading session ended")
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            self.state = SessionState.ERROR

    async def _save_session_stats(self):
        """Save session statistics"""
        try:
            # Save to database or file
            stats_file = f"logs/sessions/session_{self.session_id}.json"
            
            import json
            with open(stats_file, 'w') as f:
                json.dump(self.daily_stats, f, indent=4, default=str)
                
            logger.info(f"Session stats saved to {stats_file}")
            
        except Exception as e:
            logger.error(f"Error saving session stats: {e}")

    def is_active_session(self) -> bool:
        """Check if session is active"""
        return self.state == SessionState.ACTIVE

    def update_session_stats(self, stats_update: Dict):
        """Update session statistics"""
        try:
            if self.state != SessionState.ACTIVE:
                return
                
            # Update stats
            self.daily_stats['trades'] += stats_update.get('trades', 0)
            self.daily_stats['errors'] += stats_update.get('errors', 0)
            self.daily_stats['pnl'] += stats_update.get('pnl', 0.0)
            
        except Exception as e:
            logger.error(f"Error updating session stats: {e}")

    def get_session_info(self) -> Dict:
        """Get current session information"""
        return {
            'session_id': self.session_id,
            'state': self.state.value,
            'start_time': self.session_start,
            'stats': self.daily_stats
        }

    def get_next_session_start(self) -> datetime:
        """Get next session start time"""
        current_date = datetime.now().date()
        next_date = current_date
        
        while True:
            next_date += timedelta(days=1)
            if self._is_trading_day():
                break
                
        return datetime.combine(next_date, self.market_start)

    async def stop(self):
        """Stop session manager"""
        try:
            if self.state == SessionState.ACTIVE:
                await self._end_session()
                
            logger.info("Session manager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping session manager: {e}")