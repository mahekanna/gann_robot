# interface/terminal_ui.py
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Static, Input, DataTable
from textual.screen import Screen
import asyncio
from datetime import datetime
from autologin import breeze_auto_login
from dotenv import load_dotenv
import os

import sys
from pathlib import Path
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from autologin import breeze_auto_login

class LoginScreen(Screen):
    """ICICI Login Screen"""
    def compose(self) -> ComposeResult:
        yield Container(
            Static("ICICI Direct Login", id="login-title"),
            Static("Status: Not Connected", id="login-status"),
            Button("Connect to ICICI", id="connect-btn", variant="primary"),
            Button("Test Connection", id="test-btn"),
            Button("Continue to Trading", id="continue-btn", disabled=True),
            id="login-container"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "connect-btn":
            self.connect_to_icici()
        elif event.button.id == "test-btn":
            self.test_connection()
        elif event.button.id == "continue-btn":
            self.app.push_screen("trading")

    def connect_to_icici(self):
        """Connect to ICICI"""
        try:
            load_dotenv()
            breeze = breeze_auto_login(
                os.getenv('ICICI_API_KEY'),
                os.getenv('ICICI_API_SECRET'),
                os.getenv('ICICI_TOTP_SECRET')
            )
            if breeze:
                self.app.breeze = breeze
                self.query_one("#login-status").update("Status: Connected")
                self.query_one("#continue-btn").disabled = False
            else:
                self.query_one("#login-status").update("Status: Connection Failed")
        except Exception as e:
            self.query_one("#login-status").update(f"Error: {str(e)}")

    def test_connection(self):
        """Test ICICI Connection"""
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
    """Main Trading Screen"""
    def compose(self) -> ComposeResult:
        yield Container(
            Header(show_clock=True),
            Horizontal(
                # Left Panel - Mode Selection
                Vertical(
                    Static("Trading Modes", id="modes-title"),
                    Button("Paper Trading", id="paper-mode"),
                    Button("Live Trading", id="live-mode"),
                    Button("Backtesting", id="backtest-mode"),
                    id="mode-panel"
                ),
                # Right Panel - Content
                Vertical(
                    Static("Trading Panel", id="panel-title"),
                    self.trading_panel(),
                    id="content-panel"
                )
            ),
            Footer()
        )

    def trading_panel(self) -> ComposeResult:
        """Create trading panel based on mode"""
        yield Container(
            Input(placeholder="Enter Symbol (e.g., SBIN)", id="symbol-input"),
            Horizontal(
                Button("BUY", id="buy-btn", variant="success"),
                Button("SELL", id="sell-btn", variant="error"),
            ),
            Static("Positions", id="positions-title"),
            DataTable(id="positions-table"),
            Static("Orders", id="orders-title"),
            DataTable(id="orders-table")
        )

    def on_mount(self) -> None:
        """Initialize tables"""
        positions_table = self.query_one("#positions-table")
        positions_table.add_columns("Symbol", "Side", "Quantity", "Price", "P&L")

        orders_table = self.query_one("#orders-table")
        orders_table.add_columns("Time", "Symbol", "Side", "Quantity", "Status")

class BacktestScreen(Screen):
    """Backtesting Screen"""
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Backtesting Configuration", id="backtest-title"),
            Input(placeholder="Symbol", id="symbol-input"),
            Input(placeholder="Start Date (YYYY-MM-DD)", id="start-date"),
            Input(placeholder="End Date (YYYY-MM-DD)", id="end-date"),
            Button("Run Backtest", id="run-backtest"),
            Static("Results", id="results-title"),
            DataTable(id="results-table")
        )

class GannTradingApp(App):
    """Main Trading Application"""
    # Replace CSS_PATH with STYLES
    STYLES = """
    Screen {
        align: center middle;
    }

    #login-container {
        width: 60;
        height: 20;
        border: solid green;
        padding: 1;
    }

    #mode-panel {
        width: 30;
        height: 100%;
        border: solid blue;
    }

    #content-panel {
        width: 100;
        height: 100%;
        border: solid green;
    }

    Button {
        width: 100%;
        margin: 1;
    }

    DataTable {
        height: 1fr;
        margin: 1;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("b", "toggle_backtest", "Backtest"),
        ("t", "toggle_trading", "Trading"),
        ("r", "refresh", "Refresh")
    ]

    def on_mount(self) -> None:
        """Start with login screen"""
        self.push_screen(LoginScreen())

    def action_toggle_backtest(self) -> None:
        """Switch to backtest screen"""
        self.push_screen(BacktestScreen())

    def action_toggle_trading(self) -> None:
        """Switch to trading screen"""
        self.push_screen(TradingScreen())

if __name__ == "__main__":
    app = GannTradingApp()
    app.run()