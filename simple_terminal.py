# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 23:57:32 2025

@author: mahes
"""

# simple_terminal.py (in project root)

import os
import sys
from textual.app import App
from textual.containers import Container
from textual.widgets import Header, Footer, Button, Static, Input, DataTable
from textual.screen import Screen
from pathlib import Path
from dotenv import load_dotenv

# This fixes the import order issue - import breeze_connect directly first
from breeze_connect import BreezeConnect

# Then import your own modules
sys.path.insert(0, str(Path(__file__).parent))
from autologin import breeze_auto_login


# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import your autologin function
from autologin import breeze_auto_login

class LoginScreen(Screen):
    """ICICI Login Screen"""
    
    def compose(self):
        yield Header(show_clock=True)
        yield Container(
            Static("ICICI Direct Login", id="login-title"),
            Static("Status: Not Connected", id="login-status"),
            Static("", id="login-url"),
            Input(placeholder="Enter Session Token", id="token-input"),
            Button("Connect to ICICI", id="connect-btn", variant="primary"),
            Button("Test Connection", id="test-btn"),
            Button("Continue to Trading", id="continue-btn", disabled=True),
            id="login-container"
        )
        yield Footer()

    def on_button_pressed(self, event):
        if event.button.id == "connect-btn":
            self.connect_to_icici()
        elif event.button.id == "test-btn":
            self.test_connection()
        elif event.button.id == "continue-btn":
            self.app.push_screen("trading")

    def connect_to_icici(self):
        try:
            load_dotenv()
            api_key = os.getenv('ICICI_API_KEY')
            api_secret = os.getenv('ICICI_API_SECRET')
            
            # Display login URL
            self.query_one("#login-url").update(f"Login URL: https://api.icicidirect.com/apiuser/login?api_key={api_key}")
            
            # Get token from input
            token = self.query_one("#token-input").value
            
            # Connect to ICICI
            breeze = breeze_auto_login(api_key, api_secret, token)
            
            if breeze:
                self.app.breeze = breeze
                self.query_one("#login-status").update("Status: Connected")
                self.query_one("#continue-btn").disabled = False
            else:
                self.query_one("#login-status").update("Status: Connection Failed")
        except Exception as e:
            self.query_one("#login-status").update(f"Error: {str(e)}")

    def test_connection(self):
        if hasattr(self.app, 'breeze'):
            try:
                quote = self.app.breeze.get_quotes(
                    stock_code="SBIN",
                    exchange_code="NSE"
                )
                self.query_one("#login-status").update("Connection Test: Success")
            except Exception as e:
                self.query_one("#login-status").update(f"Test Failed: {str(e)}")
        else:
            self.query_one("#login-status").update("Not connected yet")

class TradingScreen(Screen):
    """Trading Screen"""
    
    def compose(self):
        yield Header(show_clock=True)
        yield Static("Trading Panel", id="trading-title")
        yield Footer()

class GannTradingApp(App):
    """Main Trading Application"""
    
    TITLE = "GANN Trading System"
    
    SCREENS = {
        "login": LoginScreen,
        "trading": TradingScreen,
    }
    
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.breeze = None

    def on_mount(self):
        self.push_screen("login")

if __name__ == "__main__":
    # Clear terminal
    os.system('cls' if os.name == 'nt' else 'clear')
    
    app = GannTradingApp()
    app.run()