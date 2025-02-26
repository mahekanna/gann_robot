# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 23:06:51 2025

@author: mahes
"""

# interface/app/components/position_table.py
from textual.widgets import DataTable
from textual.app import ComposeResult
import asyncio

class PositionTable(DataTable):
    """Position display table"""
    
    def on_mount(self) -> None:
        """Initialize table"""
        self.add_columns(
            "Symbol", "Side", "Quantity", "Entry Price", "Current", "P&L", "Status"
        )
        self.cursor_type = "row"
        self.start_update_timer()

    def start_update_timer(self) -> None:
        """Start auto-update timer"""
        self.set_interval(1.0, self.update_positions)

    async def update_positions(self) -> None:
        """Update position data"""
        try:
            if hasattr(self.app, 'trading_engine'):
                positions = self.app.trading_engine.get_positions()
                self.clear()
                
                for pos in positions:
                    self.add_row(
                        pos['symbol'],
                        pos['side'],
                        str(pos['quantity']),
                        f"₹{pos['entry_price']:.2f}",
                        f"₹{pos['current_price']:.2f}",
                        f"₹{pos['pnl']:.2f}",
                        pos['status']
                    )
        except Exception as e:
            self.app.notify(f"Error updating positions: {str(e)}", severity="error")