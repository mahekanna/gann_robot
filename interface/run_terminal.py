# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 06:01:50 2025

@author: mahes
"""

# run_terminal.py
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

import nest_asyncio
nest_asyncio.apply()

from interface.terminal_ui import GannTradingApp

if __name__ == "__main__":
    app = GannTradingApp()
    app.run()