# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 23:06:12 2025

@author: mahes
"""

# interface/app/screens/backtest_screen.py
from textual.screen import Screen
from textual.containers import Container
from textual.widgets import Header, Footer, Button, Static, Input, DataTable
from textual.app import ComposeResult
from datetime import datetime

class BacktestScreen(Screen):
    """Backtesting Screen"""

    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Container(
            Header(show_clock=True),
            Container(
                Static("Backtesting Configuration", id="backtest-title"),
                Input(placeholder="Symbol (e.g., SBIN)", id="symbol-input"),
                Input(placeholder="Start Date (YYYY-MM-DD)", id="start-date"),
                Input(placeholder="End Date (YYYY-MM-DD)", id="end-date"),
                Button("Run Backtest", id="run-backtest", variant="primary"),
                Static("Results", id="results-title"),
                DataTable(id="results-table"),
                id="backtest-container"
            ),
            Footer()
        )

    def on_mount(self) -> None:
        """Initialize components"""
        table = self.query_one("#results-table")
        table.add_columns(
            "Metric", "Value"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "run-backtest":
            self.run_backtest()

    async def run_backtest(self) -> None:
        """Run backtest with current parameters"""
        try:
            symbol = self.query_one("#symbol-input").value
            start = datetime.strptime(self.query_one("#start-date").value, "%Y-%m-%d")
            end = datetime.strptime(self.query_one("#end-date").value, "%Y-%m-%d")

            results = await self.app.trading_engine.run_backtest(
                symbol=symbol,
                start_date=start,
                end_date=end
            )

            self.display_results(results)
        except Exception as e:
            self.notify(f"Backtest error: {str(e)}", severity="error")