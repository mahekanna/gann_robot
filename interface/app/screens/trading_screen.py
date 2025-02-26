# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 23:05:42 2025

@author: mahes
"""

# interface/app/screens/trading_screen.py
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static
from textual.app import ComposeResult
from ..components.position_table import PositionTable
from ..components.order_panel import OrderPanel

class TradingScreen(Screen):
    """Main Trading Screen"""

    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Container(
            Header(show_clock=True),
            Horizontal(
                # Left sidebar
                Vertical(
                    OrderPanel(),
                    id="sidebar"
                ),
                # Main content
                Vertical(
                    Static("Positions", id="positions-title"),
                    PositionTable(),
                    id="main-content"
                ),
                id="trading-layout"
            ),
            Footer()
        )

    def on_mount(self) -> None:
        """Called when screen is mounted"""
        self.update_timer = self.set_interval(1.0, self.update_data)

    async def update_data(self) -> None:
        """Update trading data"""
        if hasattr(self.app, 'trading_engine'):
            await self.query_one(PositionTable).update_positions()