# -*- coding: utf-8 -*-
"""
Created on Sun Feb 23 21:02:48 2025

@author: mahes
"""

from terminal_ui import TradingTerminal
from your_trading_engine import TradingEngine

# Initialize your trading engine
engine = TradingEngine(...)

# Start terminal UI
app = TradingTerminal(engine)
app.run()