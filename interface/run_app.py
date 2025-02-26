# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 06:36:00 2025

@author: mahes
"""

#!/usr/bin/env python3
import os
import sys
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.containers import Container
from rich.console import Console
import asyncio

# Ensure we're running in a terminal
if sys.platform == 'win32':
    os.system('cls')
else:
    os.system('clear')

console = Console()

def launch_trading_app():
    """Launch the trading application"""
    try:
        # Clear terminal and show welcome message
        console.print("[bold green]Launching GANN Trading System...[/bold green]")
        
        # Import and run app
        from interface.app.trading_app import GannTradingApp
        app = GannTradingApp()
        app.run(fullscreen=True)

    except KeyboardInterrupt:
        console.print("\n[yellow]Trading system shutdown by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error starting trading system: {e}[/red]")
        raise

if __name__ == "__main__":
    launch_trading_app()