# interface/app/__init__.py
from textual.app import App
from textual.binding import Binding
from textual.widgets import Header, Footer
from pathlib import Path
from .screens.login_screen import LoginScreen
from .screens.trading_screen import TradingScreen
from .screens.backtest_screen import BacktestScreen

class GannTradingApp(App):
    """Main Trading Application"""
    
    TITLE = "GANN Trading System"
    # Fix the CSS path to use an absolute path
    CSS_PATH = str(Path(__file__).parent / "styles" / "app.tcss")
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("b", "toggle_backtest", "Backtest"),
        Binding("t", "toggle_trading", "Trading"),
        Binding("d", "toggle_dark", "Dark Mode"),
        Binding("r", "refresh", "Refresh")
    ]

    def __init__(self):
        super().__init__()
        self.breeze = None
        self.trading_engine = None
        self.dark = True

    def on_mount(self) -> None:
        """Start with login screen"""
        self.push_screen(LoginScreen())

    def action_toggle_backtest(self) -> None:
        """Switch to backtest screen"""
        self.push_screen(BacktestScreen())

    def action_toggle_trading(self) -> None:
        """Switch to trading screen"""
        self.push_screen(TradingScreen())

    def action_toggle_dark(self) -> None:
        """Toggle dark mode"""
        self.dark = not self.dark

    def action_refresh(self) -> None:
        """Refresh current screen"""
        self.current_screen.refresh()