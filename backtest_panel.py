# -*- coding: utf-8 -*-
"""
Created on Sun Feb 23 21:04:41 2025

@author: mahes
"""

# terminal_modules/backtest_panel.py

from textual.app import App
from textual.widgets import Header, Footer, Static, Button, DataTable, Input, DatePicker, OptionList
from textual.containers import Container, Grid
from typing import Dict
import pandas as pd
from datetime import datetime, timedelta

class BacktestPanel(Container):
    """Backtesting control panel"""
    def compose(self):
        yield Static("=== Backtesting Configuration ===", id="backtest-header")
        
        with Grid(id="backtest-inputs"):
            yield Input(placeholder="Symbol (e.g., SBIN)", id="symbol-input")
            yield Input(placeholder="Quantity", id="quantity-input")
            yield DatePicker("Start Date", id="start-date")
            yield DatePicker("End Date", id="end-date")
            yield OptionList(
                "Timeframe",
                ["1min", "5min", "15min", "30min", "60min"],
                id="timeframe-select"
            )
        
        yield Button("Run Backtest", id="run-backtest", variant="primary")
        yield Button("Optimize Parameters", id="optimize-params")
        
        yield Static("=== Results ===", id="results-header")
        yield DataTable(id="results-table")
        
        # Charts will be displayed here
        yield Static(id="charts-display")

    def on_mount(self):
        """Initialize backtest panel"""
        results_table = self.query_one("#results-table")
        results_table.add_columns(
            "Metric", "Value"
        )

    async def run_backtest(self):
        """Execute backtest with current parameters"""
        try:
            # Get input values
            symbol = self.query_one("#symbol-input").value
            quantity = int(self.query_one("#quantity-input").value)
            start_date = self.query_one("#start-date").value
            end_date = self.query_one("#end-date").value
            timeframe = self.query_one("#timeframe-select").value

            # Run backtest
            results = await self.app.trading_engine.run_backtest(
                symbol=symbol,
                quantity=quantity,
                start_date=start_date,
                end_date=end_date,
                timeframe=timeframe
            )

            # Update results display
            self.update_results(results)

        except Exception as e:
            self.app.notify(f"Backtest error: {str(e)}", severity="error")

    def update_results(self, results: Dict):
        """Update results display"""
        table = self.query_one("#results-table")
        table.clear()
        
        # Add metrics to table
        table.add_row("Total Returns", f"₹{results['total_returns']:.2f}")
        table.add_row("Win Rate", f"{results['win_rate']:.2%}")
        table.add_row("Profit Factor", f"{results['profit_factor']:.2f}")
        table.add_row("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")
        table.add_row("Max Drawdown", f"{results['max_drawdown']:.2%}")
        table.add_row("Total Trades", str(results['total_trades']))

# terminal_modules/paper_trading_panel.py

class PaperTradingPanel(Container):
    """Paper trading control panel"""
    def compose(self):
        yield Static("=== Paper Trading Control ===", id="paper-header")
        
        with Grid(id="paper-controls"):
            yield Static("Account Balance: ", id="balance-display")
            yield Static("Open P&L: ", id="pnl-display")
            yield Static("Positions: ", id="positions-count")
        
        with Grid(id="order-entry"):
            yield Input(placeholder="Symbol", id="symbol-input")
            yield Input(placeholder="Quantity", id="quantity-input")
            yield OptionList(
                "Order Type",
                ["MARKET", "LIMIT"],
                id="order-type"
            )
            yield Input(placeholder="Price (for LIMIT)", id="price-input")
            yield Button("BUY", id="buy-button", variant="success")
            yield Button("SELL", id="sell-button", variant="error")
        
        yield Static("=== Open Positions ===", id="positions-header")
        yield DataTable(id="positions-table")
        
        yield Static("=== Order History ===", id="orders-header")
        yield DataTable(id="orders-table")

    def on_mount(self):
        """Initialize paper trading panel"""
        # Setup positions table
        positions_table = self.query_one("#positions-table")
        positions_table.add_columns(
            "Symbol", "Side", "Quantity", "Entry", "Current", "P&L"
        )
        
        # Setup orders table
        orders_table = self.query_one("#orders-table")
        orders_table.add_columns(
            "Time", "Symbol", "Side", "Type", "Quantity", "Price", "Status"
        )
        
        # Start auto-refresh
        self.set_interval(1.0, self.refresh_data)

    async def refresh_data(self):
        """Refresh display data"""
        try:
            # Update account info
            account = self.app.trading_engine.get_paper_account()
            self.query_one("#balance-display").update(
                f"Account Balance: ₹{account['balance']:.2f}"
            )
            self.query_one("#pnl-display").update(
                f"Open P&L: ₹{account['open_pnl']:.2f}"
            )
            
            # Update positions
            positions = self.app.trading_engine.get_paper_positions()
            positions_table = self.query_one("#positions-table")
            positions_table.clear()
            
            for pos in positions:
                positions_table.add_row(
                    pos['symbol'],
                    pos['side'],
                    str(pos['quantity']),
                    f"₹{pos['entry_price']:.2f}",
                    f"₹{pos['current_price']:.2f}",
                    f"₹{pos['pnl']:.2f}"
                )
                
            # Update orders
            orders = self.app.trading_engine.get_paper_orders()
            orders_table = self.query_one("#orders-table")
            orders_table.clear()
            
            for order in orders:
                orders_table.add_row(
                    order['time'].strftime("%H:%M:%S"),
                    order['symbol'],
                    order['side'],
                    order['type'],
                    str(order['quantity']),
                    f"₹{order['price']:.2f}",
                    order['status']
                )

        except Exception as e:
            self.app.notify(f"Error refreshing data: {str(e)}", severity="error")

    async def place_order(self, side: str):
        """Place paper trading order"""
        try:
            symbol = self.query_one("#symbol-input").value
            quantity = int(self.query_one("#quantity-input").value)
            order_type = self.query_one("#order-type").value
            price = float(self.query_one("#price-input").value or 0)

            order = await self.app.trading_engine.place_paper_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price
            )

            if order:
                self.app.notify(f"{side} order placed successfully")
            else:
                self.app.notify("Order placement failed", severity="error")

        except Exception as e:
            self.app.notify(f"Order error: {str(e)}", severity="error")

# terminal_ui.py (updated)

class TradingTerminal(App):
    def __init__(self, trading_engine):
        super().__init__()
        self.trading_engine = trading_engine
        self.current_mode = "paper"  # or "backtest"

    def compose(self):
        yield Header(show_clock=True)
        
        with Container(id="mode-selector"):
            yield Button("Paper Trading", id="paper-mode")
            yield Button("Backtesting", id="backtest-mode")
        
        # Main content area - will switch between paper and backtest
        yield Container(id="main-content")
        
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        """Handle mode switching"""
        if event.button.id == "paper-mode":
            self.switch_to_paper()
        elif event.button.id == "backtest-mode":
            self.switch_to_backtest()

    def switch_to_paper(self):
        """Switch to paper trading mode"""
        main_content = self.query_one("#main-content")
        main_content.remove_children()
        main_content.mount(PaperTradingPanel())
        self.current_mode = "paper"

    def switch_to_backtest(self):
        """Switch to backtesting mode"""
        main_content = self.query_one("#main-content")
        main_content.remove_children()
        main_content.mount(BacktestPanel())
        self.current_mode = "backtest"