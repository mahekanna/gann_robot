# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 23:07:21 2025

@author: mahes
"""

# interface/app/components/order_panel.py
from textual.widgets import Static, Input, Button
from textual.containers import Vertical
from textual.app import ComposeResult

class OrderPanel(Vertical):
    """Order entry panel"""
    
    def compose(self) -> ComposeResult:
        """Create order panel widgets"""
        yield Static("Order Entry", id="order-title")
        yield Input(placeholder="Symbol (e.g., SBIN)", id="symbol-input")
        yield Input(placeholder="Quantity", id="quantity-input")
        yield Input(placeholder="Price (optional)", id="price-input")
        yield Button("BUY", id="buy-btn", variant="success")
        yield Button("SELL", id="sell-btn", variant="error")
        yield Static("Order Status", id="order-status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle order button presses"""
        if event.button.id in ["buy-btn", "sell-btn"]:
            self.place_order(event.button.id == "buy-btn")

    async def place_order(self, is_buy: bool) -> None:
        """Place trading order"""
        try:
            symbol = self.query_one("#symbol-input").value
            quantity = int(self.query_one("#quantity-input").value)
            price = float(self.query_one("#price-input").value or 0)

            order = await self.app.trading_engine.place_order(
                symbol=symbol,
                side="BUY" if is_buy else "SELL",
                quantity=quantity,
                price=price,
                order_type="LIMIT" if price > 0 else "MARKET"
            )

            if order:
                self.query_one("#order-status").update("Order placed successfully")
                self.app.notify("Order placed successfully", severity="information")
            else:
                self.query_one("#order-status").update("Order placement failed")
                self.app.notify("Order failed", severity="error")

        except Exception as e:
            self.app.notify(f"Order error: {str(e)}", severity="error")