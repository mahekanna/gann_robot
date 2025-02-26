# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 01:24:14 2025

@author: mahes
"""

# terminal_ui.py (in project root)
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio
import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import your existing autologin
from autologin import breeze_auto_login, load_session_key

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print application header"""
    print("\n")
    print("=" * 60)
    print("             GANN TRADING SYSTEM             ")
    print("=" * 60)
    print("\n")

def main_menu():
    """Display main menu"""
    clear_screen()
    print_header()
    print("1. Connect to ICICI Breeze")
    print("2. Run Backtest")
    print("3. Paper Trading")
    print("4. Live Trading")
    print("5. Exit")
    print("\n")
    
    choice = input("Enter your choice (1-5): ")
    
    if choice == "1":
        connect_to_icici()
    elif choice == "2":
        run_backtest()
    elif choice == "3":
        paper_trading()
    elif choice == "4":
        live_trading()
    elif choice == "5":
        sys.exit(0)
    else:
        print("Invalid choice. Please try again.")
        input("\nPress Enter to continue...")
    
    main_menu()  # Return to main menu

def connect_to_icici():
    """Connect to ICICI Breeze API"""
    clear_screen()
    print_header()
    print("CONNECT TO ICICI BREEZE")
    print("-" * 60)
    
    # Load credentials
    load_dotenv()
    api_key = os.getenv('ICICI_API_KEY')
    api_secret = os.getenv('ICICI_API_SECRET')
    totp_secret = os.getenv('ICICI_TOTP_SECRET')
    
    if not api_key or not api_secret or not totp_secret:
        print("Error: API credentials not found in .env file")
        print("Please ensure ICICI_API_KEY, ICICI_API_SECRET, and ICICI_TOTP_SECRET are set")
        input("\nPress Enter to continue...")
        return

    # First check if we have an existing valid session
    session_key, generated_at = load_session_key()
    if session_key and generated_at:
        time_difference = datetime.datetime.now() - generated_at
        if time_difference < datetime.timedelta(hours=24):
            print(f"\nFound existing session from {generated_at}")
            print(f"Session age: {time_difference}")
            use_existing = input("\nUse existing session? (y/n): ").lower()
            
            if use_existing == 'y':
                try:
                    print("\nConnecting using saved session...")
                    from breeze_connect import BreezeConnect
                    
                    breeze = BreezeConnect(api_key=api_key)
                    breeze.generate_session(api_secret=api_secret, session_token=session_key)
                    
                    print("\nSuccessfully connected to ICICI Breeze!")
                    # Store breeze instance for later use
                    global_state['breeze'] = breeze
                    input("\nPress Enter to continue...")
                    return
                except Exception as e:
                    print(f"\nError using saved session: {e}")
                    print("Proceeding to create a new session.")
    
    # If we get here, we need to create a new session
    print("\nUsing auto-login to connect to ICICI Breeze...")
    
    try:
        # Use the autologin function
        breeze = breeze_auto_login(api_key, api_secret, totp_secret)
        
        if breeze:
            print("\nSuccessfully connected to ICICI Breeze!")
            # Store breeze instance for later use
            global_state['breeze'] = breeze
        else:
            print("\nFailed to connect to ICICI Breeze.")
    except Exception as e:
        print(f"\nError connecting to ICICI Breeze: {e}")
    
    input("\nPress Enter to continue...")

def run_backtest():
    """Run backtesting"""
    clear_screen()
    print_header()
    print("BACKTEST GANN STRATEGY")
    print("-" * 60)
    
    symbol = input("Enter symbol (e.g., SBIN): ")
    start_date = input("Enter start date (YYYY-MM-DD): ")
    end_date = input("Enter end date (YYYY-MM-DD): ")
    timeframe = input("Enter timeframe in minutes (default: 15): ") or "15"
    
    print(f"\nRunning backtest for {symbol} from {start_date} to {end_date} on {timeframe}min timeframe...")
    
    try:
        # Import packages with sys.path handling
        import sys
        from pathlib import Path
        import json
        from datetime import datetime
        
        # Add project root to Python path
        project_root = Path(__file__).parent
        sys.path.append(str(project_root))
        
        # Direct imports
        print("\nInitializing modules...")
        
        # Use subprocess to run backtest script
        import subprocess
        cmd = [
            sys.executable,
            "-m", "scripts.backtest",
            "--symbol", symbol,
            "--start", start_date,
            "--end", end_date,
            "--timeframe", timeframe
        ]
        
        print(f"\nExecuting: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\nBacktest completed successfully!")
            print("\nResults:")
            print(result.stdout)
        else:
            print("\nBacktest failed with error:")
            print(result.stderr)
        
    except Exception as e:
        print(f"\nError running backtest: {e}")
    
    input("\nPress Enter to continue...")

def paper_trading():
    """Run paper trading"""
    clear_screen()
    print_header()
    print("PAPER TRADING MODE")
    print("-" * 60)
    
    if 'breeze' not in global_state:
        print("Error: Not connected to ICICI Breeze")
        print("Please connect first (Option 1)")
        input("\nPress Enter to continue...")
        return
    
    try:
        # Import required modules
        from core.brokers.paper_broker import PaperBroker
        from core.engine.trading_engine import TradingEngine
        import json
        
        # Load config
        with open("config/trading_config.json", "r") as f:
            config = json.load(f)
            
        # Create paper broker
        print("Initializing paper broker...")
        paper_broker = PaperBroker(global_state['breeze'], config)
        
        # Initialize trading engine
        print("Starting trading engine...")
        engine = TradingEngine(
            broker=paper_broker,
            config=config
        )
        
        # Enter trading loop
        print("\nPaper trading started. Press Ctrl+C to exit.")
        print("\nCurrent positions will be displayed here.")
        print("\nWaiting for trading signals...")
        
        # Simple trading console
        while True:
            cmd = input("\nEnter command (p:positions, o:orders, b:buy, s:sell, q:quit): ")
            
            if cmd.lower() == 'q':
                break
            elif cmd.lower() == 'p':
                positions = paper_broker.get_positions()
                if positions:
                    print("\nCurrent Positions:")
                    for pos in positions:
                        print(f"{pos.symbol}: {pos.quantity} @ {pos.average_price} (P&L: {pos.pnl})")
                else:
                    print("\nNo open positions")
            elif cmd.lower() == 'o':
                orders = paper_broker.get_order_history()
                if orders:
                    print("\nRecent Orders:")
                    for order in orders[-5:]:  # Show last 5 orders
                        print(f"{order['timestamp']}: {order['side']} {order['symbol']} x{order['quantity']} @ {order['price']} - {order['status']}")
                else:
                    print("\nNo recent orders")
            elif cmd.lower() == 'b':
                symbol = input("Symbol to buy: ")
                quantity = int(input("Quantity: "))
                paper_broker.place_order(
                    symbol=symbol,
                    quantity=quantity,
                    side="BUY",
                    product_type="INTRADAY",
                    order_type="MARKET"
                )
                print(f"Buy order placed for {quantity} {symbol}")
            elif cmd.lower() == 's':
                symbol = input("Symbol to sell: ")
                quantity = int(input("Quantity: "))
                paper_broker.place_order(
                    symbol=symbol,
                    quantity=quantity,
                    side="SELL",
                    product_type="INTRADAY",
                    order_type="MARKET"
                )
                print(f"Sell order placed for {quantity} {symbol}")
            
    except KeyboardInterrupt:
        print("\nPaper trading stopped by user")
    except ModuleNotFoundError:
        print("\nError: Required modules not found")
        print("Please ensure core/brokers/paper_broker.py exists and is properly implemented")
    except Exception as e:
        print(f"\nError in paper trading: {e}")
    
    input("\nPress Enter to continue...")

def live_trading():
    """Run live trading"""
    clear_screen()
    print_header()
    print("LIVE TRADING MODE")
    print("-" * 60)
    
    if 'breeze' not in global_state:
        print("Error: Not connected to ICICI Breeze")
        print("Please connect first (Option 1)")
        input("\nPress Enter to continue...")
        return
    
    print("⚠️ WARNING: You are about to start LIVE trading with real money ⚠️")
    confirmation = input("\nAre you absolutely sure? (yes/no): ")
    
    if confirmation.lower() != "yes":
        print("\nLive trading cancelled")
        input("\nPress Enter to continue...")
        return
    
    try:
        # Import required modules
        from core.brokers.icici_breeze import ICICIBreeze
        from core.engine.trading_engine import TradingEngine
        import json
        
        # Load config
        with open("config/trading_config.json", "r") as f:
            config = json.load(f)
        
        # Create live broker wrapper (reusing existing connection)
        print("Initializing live broker...")
        live_broker = ICICIBreeze(
            api_key=config['api_key'],
            api_secret=config['api_secret'],
            totp_secret=config['totp_secret'],
            breeze_instance=global_state['breeze']
        )
        
        # Initialize trading engine
        print("Starting trading engine...")
        engine = TradingEngine(
            broker=live_broker,
            config=config
        )
        
        # Enter trading loop
        print("\nLIVE TRADING STARTED - USE WITH CAUTION!")
        print("\nPositions and P&L will be displayed here.")
        print("\nActive trading signals in progress...")
        
        # Simple trading console - similar to paper trading but with warnings
        while True:
            cmd = input("\n⚠️ LIVE TRADING ⚠️ - Enter command (p:positions, o:orders, b:buy, s:sell, q:quit): ")
            
            if cmd.lower() == 'q':
                confirmation = input("Are you sure you want to quit live trading? (yes/no): ")
                if confirmation.lower() == "yes":
                    break
            
            elif cmd.lower() == 'p':
                positions = live_broker.get_positions()
                if positions:
                    print("\nLIVE Positions:")
                    for pos in positions:
                        print(f"{pos.symbol}: {pos.quantity} @ {pos.average_price} (P&L: {pos.pnl})")
                else:
                    print("\nNo open positions")
            
            elif cmd.lower() == 'o':
                orders = live_broker.get_order_book()
                if orders:
                    print("\nRecent Orders:")
                    for order in orders[-5:]:  # Show last 5 orders
                        print(f"{order.get('time')}: {order.get('action')} {order.get('stock_code')} x{order.get('quantity')} @ {order.get('price')} - {order.get('status')}")
                else:
                    print("\nNo recent orders")
            
            elif cmd.lower() == 'b':
                symbol = input("Symbol to buy: ")
                quantity = int(input("Quantity: "))
                confirm = input(f"CONFIRM LIVE BUY of {quantity} {symbol}? (yes/no): ")
                if confirm.lower() == "yes":
                    response = live_broker.place_order(
                        symbol=symbol,
                        quantity=quantity,
                        side="BUY",
                        product_type="INTRADAY",
                        order_type="MARKET"
                    )
                    print(f"Live buy order result: {response.status}")
                else:
                    print("Buy order cancelled")
            
            elif cmd.lower() == 's':
                symbol = input("Symbol to sell: ")
                quantity = int(input("Quantity: "))
                confirm = input(f"CONFIRM LIVE SELL of {quantity} {symbol}? (yes/no): ")
                if confirm.lower() == "yes":
                    response = live_broker.place_order(
                        symbol=symbol,
                        quantity=quantity,
                        side="SELL",
                        product_type="INTRADAY",
                        order_type="MARKET"
                    )
                    print(f"Live sell order result: {response.status}")
                else:
                    print("Sell order cancelled")
    
    except KeyboardInterrupt:
        print("\nLive trading stopped by user")
    except ModuleNotFoundError:
        print("\nError: Required modules not found")
        print("Please ensure core/brokers/icici_breeze.py exists and is properly implemented")
    except Exception as e:
        print(f"\nError in live trading: {e}")
    
    input("\nPress Enter to continue...")

# Global state to store connections and data
global_state = {}

if __name__ == "__main__":
    main_menu()