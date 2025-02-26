#!/usr/bin/env python3
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging
import json
import matplotlib.pyplot as plt
import seaborn as sns

from ..core.strategy.gann_strategy import GannStrategy
from ..core.data.historical_data import HistoricalDataManager
from ..core.utils.metrics import PerformanceMetrics
from ..core.utils.logger import setup_logger

logger = setup_logger('backtest')

class BacktestEngine:
    def __init__(self, config: Dict):
        """Initialize backtest engine"""
        self.config = config
        self.data_manager = HistoricalDataManager(config)
        self.performance_metrics = PerformanceMetrics()
        
        # Initialize tracking variables
        self.trades = []
        self.equity_curve = []
        self.positions = {}
        self.current_capital = config['initial_capital']
        self.peak_capital = self.current_capital
        self.max_drawdown = 0
        
        # Setup output directory
        self.output_dir = Path('backtest_results')
        self.output_dir.mkdir(exist_ok=True)
        
    async def run_backtest(self, 
                         symbol: str,
                         start_date: datetime,
                         end_date: datetime,
                         timeframe: str = '15min') -> Dict:
        """Run backtest for specified period"""
        try:
            logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
            
            # Load historical data
            data = await self.data_manager.get_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                timeframe=timeframe
            )
            
            if data is None or len(data) == 0:
                raise ValueError("No data available for backtesting")
            
            # Initialize strategy
            strategy = GannStrategy(self.config)
            
            # Process each candle
            for timestamp, candle in data.iterrows():
                # Update current price
                current_price = candle['close']
                
                # Process new candle
                signals = strategy.process_timeframe(candle)
                
                # Process signals
                if signals:
                    for signal in signals:
                        self._process_signal(signal, current_price, timestamp)
                
                # Update open positions
                self._update_positions(current_price, timestamp)
                
                # Update equity curve
                self._update_equity_curve(timestamp)
            
            # Close any remaining positions
            self._close_all_positions(data.iloc[-1]['close'], data.index[-1])
            
            # Generate and return results
            return self._generate_results()
            
        except Exception as e:
            logger.error(f"Error in backtest: {e}")
            raise

    def _process_signal(self, signal: Dict, price: float, timestamp: datetime):
        """Process trading signal"""
        try:
            # Calculate position size
            quantity = self._calculate_position_size(
                price,
                signal['stop_loss'],
                signal['type']
            )
            
            if quantity == 0:
                return
                
            # Check if we can take the trade
            required_capital = price * quantity
            if required_capital > self.current_capital:
                logger.warning("Insufficient capital for trade")
                return
            
            # Record the trade
            trade = {
                'entry_time': timestamp,
                'entry_price': price,
                'type': signal['type'],
                'quantity': quantity,
                'stop_loss': signal['stop_loss'],
                'targets': signal['targets']
            }
            
            # Add to positions
            self.positions[len(self.trades)] = trade
            self.trades.append(trade)
            
            # Update capital
            self.current_capital -= required_capital
            
            logger.info(f"Entered {signal['type']} position at {price}")
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")

    def _update_positions(self, current_price: float, timestamp: datetime):
        """Update open positions"""
        try:
            for trade_id, position in list(self.positions.items()):
                # Check stops
                if position['type'] == 'LONG':
                    if current_price <= position['stop_loss']:
                        self._exit_position(trade_id, current_price, timestamp, 'Stop Loss')
                        continue
                else:  # SHORT
                    if current_price >= position['stop_loss']:
                        self._exit_position(trade_id, current_price, timestamp, 'Stop Loss')
                        continue
                
                # Check targets
                for i, target in enumerate(position['targets']):
                    if position['type'] == 'LONG':
                        if current_price >= target:
                            self._take_partial_profit(trade_id, current_price, timestamp, i+1)
                    else:  # SHORT
                        if current_price <= target:
                            self._take_partial_profit(trade_id, current_price, timestamp, i+1)
                            
        except Exception as e:
            logger.error(f"Error updating positions: {e}")

    def _exit_position(self, trade_id: int, price: float, timestamp: datetime, reason: str):
        """Exit a position"""
        try:
            position = self.positions[trade_id]
            
            # Calculate P&L
            pnl = (price - position['entry_price']) * position['quantity']
            if position['type'] == 'SHORT':
                pnl = -pnl
            
            # Update trade record
            self.trades[trade_id].update({
                'exit_time': timestamp,
                'exit_price': price,
                'pnl': pnl,
                'exit_reason': reason
            })
            
            # Update capital
            self.current_capital += (price * position['quantity'] + pnl)
            
            # Update peak capital and drawdown
            if self.current_capital > self.peak_capital:
                self.peak_capital = self.current_capital
            else:
                drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
                self.max_drawdown = max(self.max_drawdown, drawdown)
            
            # Remove position
            del self.positions[trade_id]
            
            logger.info(f"Exited position at {price}, PnL: {pnl}")
            
        except Exception as e:
            logger.error(f"Error exiting position: {e}")

    def _take_partial_profit(self, trade_id: int, price: float, timestamp: datetime, target_num: int):
        """Take partial profit at target"""
        try:
            position = self.positions[trade_id]
            partial_quantity = position['quantity'] // len(position['targets'])
            
            if partial_quantity == 0:
                return
                
            # Update position
            position['quantity'] -= partial_quantity
            
            # Calculate partial P&L
            partial_pnl = (price - position['entry_price']) * partial_quantity
            if position['type'] == 'SHORT':
                partial_pnl = -partial_pnl
            
            # Record partial exit
            if 'partial_exits' not in self.trades[trade_id]:
                self.trades[trade_id]['partial_exits'] = []
                
            self.trades[trade_id]['partial_exits'].append({
                'time': timestamp,
                'price': price,
                'quantity': partial_quantity,
                'pnl': partial_pnl,
                'target_num': target_num
            })
            
            # Update capital
            self.current_capital += (price * partial_quantity + partial_pnl)
            
            logger.info(f"Partial profit taken at target {target_num}, PnL: {partial_pnl}")
            
            # If no quantity left, remove position
            if position['quantity'] == 0:
                del self.positions[trade_id]
                
        except Exception as e:
            logger.error(f"Error taking partial profit: {e}")

    def _update_equity_curve(self, timestamp: datetime):
        """Update equity curve"""
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': self.current_capital,
            'drawdown': (self.peak_capital - self.current_capital) / self.peak_capital
        })

    def _close_all_positions(self, price: float, timestamp: datetime):
        """Close all open positions"""
        for trade_id in list(self.positions.keys()):
            self._exit_position(trade_id, price, timestamp, 'Backtest End')

    def _calculate_position_size(self, price: float, stop_loss: float, trade_type: str) -> int:
        """Calculate position size based on risk"""
        try:
            risk_per_trade = self.current_capital * self.config['position_size_risk']
            risk_per_unit = abs(price - stop_loss)
            
            if risk_per_unit == 0:
                return 0
                
            quantity = int(risk_per_trade / risk_per_unit)
            
            # Adjust for lot size
            lot_size = self.config.get('lot_size', 1)
            quantity = (quantity // lot_size) * lot_size
            
            return quantity
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0

    def _generate_results(self) -> Dict:
        """Generate backtest results"""
        try:
            # Calculate metrics
            metrics = self.performance_metrics.calculate_strategy_metrics(
                self.trades,
                self.config['initial_capital']
            )
            
            # Save results
            results = {
                'trades': self.trades,
                'equity_curve': self.equity_curve,
                'metrics': metrics,
                'config': self.config
            }
            
            # Save to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = self.output_dir / f"backtest_results_{timestamp}.json"
            
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=4, default=str)
            
            # Generate plots
            self._generate_plots(timestamp)
            
            return results
            
        except Exception as e:
            logger.error(f"Error generating results: {e}")
            return {}

    def _generate_plots(self, timestamp: str):
        """Generate analysis plots"""
        try:
            # Create equity curve plot
            plt.figure(figsize=(12, 6))
            equity_df = pd.DataFrame(self.equity_curve)
            plt.plot(equity_df['timestamp'], equity_df['equity'])
            plt.title('Equity Curve')
            plt.grid(True)
            plt.savefig(self.output_dir / f"equity_curve_{timestamp}.png")
            plt.close()
            
            # Create drawdown plot
            plt.figure(figsize=(12, 6))
            plt.plot(equity_df['timestamp'], equity_df['drawdown'] * 100)
            plt.title('Drawdown (%)')
            plt.grid(True)
            plt.savefig(self.output_dir / f"drawdown_{timestamp}.png")
            plt.close()
            
            # Create monthly returns heatmap
            trade_df = pd.DataFrame([
                {
                    'date': t['entry_time'].date(),
                    'pnl': t.get('pnl', 0)
                }
                for t in self.trades if 'pnl' in t
            ])
            
            if not trade_df.empty:
                trade_df['month'] = trade_df['date'].apply(lambda x: x.strftime('%Y-%m'))
                monthly_returns = trade_df.groupby('month')['pnl'].sum()
                
                plt.figure(figsize=(12, 6))
                sns.heatmap(
                    monthly_returns.values.reshape(-1, 3),
                    annot=True,
                    fmt='.0f',
                    cmap='RdYlGn'
                )
                plt.title('Monthly Returns Heatmap')
                plt.savefig(self.output_dir / f"monthly_returns_{timestamp}.png")
                plt.close()
            
        except Exception as e:
            logger.error(f"Error generating plots: {e}")

if __name__ == "__main__":
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description='Run strategy backtest')
    
    parser.add_argument('--symbol', type=str, required=True, help='Trading symbol')
    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--timeframe', type=str, default='15min', help='Timeframe (default: 15min)')
    parser.add_argument('--config', type=str, default='config/trading_config.json', help='Config file')
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    # Run backtest
    backtest = BacktestEngine(config)
    results = backtest.run_backtest(
        symbol=args.symbol,
        start_date=datetime.strptime(args.start, '%Y-%m-%d'),
        end_date=datetime.strptime(args.end, '%Y-%m-%d'),
        timeframe=args.timeframe
    )
    
    print("\nBacktest Results:")
    print(f"Total Trades: {results['metrics']['total_trades']}")
    print(f"Win Rate: {results['metrics']['win_rate']:.2%}")
    print(f"Profit Factor: {results['metrics']['profit_factor']:.2f}")
    print(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['metrics']['max_drawdown']:.2%}")
    print(f"Total Return: {results['metrics']['return_pct']:.2f}%")