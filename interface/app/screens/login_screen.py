# -*- coding: utf-8 -*-
"""
Created on Tue Feb 25 23:04:38 2025

@author: mahes
"""

# interface/app/screens/login_screen.py
from textual.screen import Screen
from textual.containers import Container
from textual.widgets import Header, Footer, Button, Static, Input, Label
from textual.app import ComposeResult
from autologin import breeze_auto_login
from dotenv import load_dotenv
import os
import asyncio

class LoginScreen(Screen):
    """ICICI Login Screen"""

    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Container(
            Header(show_clock=True),
            Container(
                Static("ICICI Direct Login", id="login-title"),
                Static("Status: Not Connected", id="login-status"),
                
                # Login URL Display
                Label("Login URL will appear here", id="login-url"),
                
                # TOTP Display and Input
                Static("", id="totp-display"),
                Input(placeholder="Enter Session Token", id="token-input", password=True),
                
                # Buttons
                Button("Start Login Process", id="start-login-btn", variant="primary"),
                Button("Submit Token", id="submit-token-btn", variant="success", disabled=True),
                Button("Test Connection", id="test-btn", disabled=True),
                Button("Continue to Trading", id="continue-btn", disabled=True),
                
                id="login-container"
            ),
            Footer()
        )

    def on_mount(self) -> None:
        """Initialize the screen"""
        self.login_url = ""
        self.totp_code = ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id
        
        if button_id == "start-login-btn":
            self.start_login_process()
        elif button_id == "submit-token-btn":
            self.submit_token()
        elif button_id == "test-btn":
            self.test_connection()
        elif button_id == "continue-btn":
            self.app.push_screen("trading")

    def start_login_process(self) -> None:
        """Start the login process"""
        try:
            # Load credentials
            load_dotenv()
            api_key = os.getenv('ICICI_API_KEY')
            
            if not api_key:
                self.notify("API credentials not found in .env file", severity="error")
                return

            # Generate and display login URL
            self.login_url = f"https://api.icicidirect.com/apiuser/login?api_key={api_key}"
            self.query_one("#login-url").update(f"Login URL: {self.login_url}")
            
            # Enable token input and submit button
            self.query_one("#token-input").disabled = False
            self.query_one("#submit-token-btn").disabled = False
            
            # Update status
            self.query_one("#login-status").update("Status: Waiting for session token")
            self.notify("Please login using the URL and enter the session token", severity="information")

        except Exception as e:
            self.notify(f"Error starting login: {str(e)}", severity="error")

    def submit_token(self) -> None:
        """Submit session token and complete login"""
        try:
            # Get token from input
            token = self.query_one("#token-input").value
            if not token:
                self.notify("Please enter the session token", severity="warning")
                return

            # Load credentials
            load_dotenv()
            api_key = os.getenv('ICICI_API_KEY')
            api_secret = os.getenv('ICICI_API_SECRET')
            
            # Initialize connection
            breeze = breeze_auto_login(
                api_key=api_key,
                api_secret=api_secret,
                session_token=token  # Pass the manually entered token
            )

            if breeze:
                # Store breeze instance
                self.app.breeze = breeze
                
                # Update UI
                self.query_one("#login-status").update("Status: Connected")
                self.query_one("#test-btn").disabled = False
                self.notify("Successfully connected to ICICI", severity="information")
                
                # Clear sensitive data
                self.query_one("#token-input").value = ""
                self.query_one("#login-url").update("Login URL: [Connected]")
            else:
                self.notify("Connection failed with provided token", severity="error")

        except Exception as e:
            self.notify(f"Error during login: {str(e)}", severity="error")

    def test_connection(self) -> None:
        """Test ICICI Connection"""
        if hasattr(self.app, 'breeze'):
            try:
                # Test with a simple quote request
                quote = self.app.breeze.get_quotes(
                    stock_code="SBIN",
                    exchange_code="NSE"
                )
                
                if quote:
                    self.notify("Connection test successful!", severity="information")
                    self.query_one("#continue-btn").disabled = False
                else:
                    self.notify("Test failed: No data received", severity="error")
                    
            except Exception as e:
                self.notify(f"Test failed: {str(e)}", severity="error")
        else:
            self.notify("Not connected yet", severity="warning")

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes"""
        if event.input.id == "token-input":
            # Enable/disable submit button based on token input
            self.query_one("#submit-token-btn").disabled = not event.value.strip()