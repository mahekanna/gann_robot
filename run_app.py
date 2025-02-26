# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 23:10:56 2025

@author: mahes
"""

# run_app.py (in project root)
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Clear terminal
os.system('cls' if os.name == 'nt' else 'clear')

from interface.app import GannTradingApp

if __name__ == "__main__":
    app = GannTradingApp()
    app.run()