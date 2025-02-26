#!/usr/bin/env python3
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
import logging
from collections import defaultdict

from ..core.utils.metrics import PerformanceMetrics
from ..database.db_manager import DatabaseManager
from ..core.utils.logger import setup_logger

logger = setup_logger('analyze')

class TradingAnalyzer:
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize trading analyzer"""
        self.db_manager = db_manager
        self.metrics = PerformanceMetrics()
        
        # Setup output directory
        self.output_dir = Path('analysis_results')
        self.output_dir.mkdir(exist_ok=True)
        
        # Plot style
        plt.style.use('seaborn')
        self.colors = sns.color_palette("husl", 8)
        
    def analyze_results(self, 
                       trades: List[Dict],
                       initial_capital: float,
                       output_prefix: str = "") -> Dict:
        """Analyze trading results"""
        try:
            logger.info("Starting trading analysis...")
            
            # Calculate basic metrics
            metrics = self.metrics.calculate_strategy_metrics(trades, initial_capital)
            
            # Generate analysis plots
            self._generate_equity_curve(trades, initial_capital, output_prefix)
            self._generate_drawdown_chart(trades, initial_capital, output_prefix)
            self._generate_monthly_returns_heatmap(trades, output_prefix)
            self._generate_trade_distribution(trades, output_prefix)
            self._generate_win_loss_analysis(trades, output_prefix)
            
            # Additional analysis
            day_analysis = self._analyze_day_of_week(trades)
            time_analysis = self._analyze_time_of_day(trades)
            symbol_analysis = self._analyze_by_symbol(trades)
            
            # Combine results
            results = {
                'metrics': metrics,
                'day_analysis': day_analysis,
                'time_analysis': time_analysis,
                'symbol_analysis': symbol_analysis
            }
            
            # Save results
            self._save_analysis_results(results, output_prefix)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in analysis: {e}")
            raise

    def analyze_live_trading(self, 
                           start_date: datetime,
                           end_date: datetime) -> Dict:
        """Analyze live trading results from database"""
        try:
            if not self.db_manager:
                raise ValueError("Database manager required for live trading analysis")
            
            # Get trades from database
            trades = self._get_trades_from_db(start_date, end_date)
            
            if not trades:
                logger.warning("No trades found in the specified period")
                return {}
            
            # Get initial capital
            initial_capital = self._get_initial_capital_from_db()
            
            # Run analysis
            results = self.analyze_results(
                trades,
                initial_capital,
                output_prefix="live_"
            )
            
            # Additional live trading specific analysis
            results.update(self._analyze_live_specific_metrics(trades))
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing live trading: {e}")
            raise

    def _generate_equity_curve(self, 
                             trades: List[Dict],
                             initial_capital: float,
                             prefix: str):
        """Generate equity curve plot"""
        try:
            df = pd.DataFrame(trades)
            df['cumulative_pnl'] = df['pnl'].cumsum()
            df['equity'] = initial_capital + df['cumulative_pnl']
            
            plt.figure(figsize=(12, 6))
            plt.plot(df.index, df['equity'], color=self.colors[0], linewidth=2)
            plt.title('Equity Curve')
            plt.xlabel('Trade Number')
            plt.ylabel('Equity')
            plt.grid(True)
            
            plt.savefig(self.output_dir / f"{prefix}equity_curve.png")
            plt.close()
            
        except Exception as e:
            logger.error(f"Error generating equity curve: {e}")

    def _generate_drawdown_chart(self, 
                               trades: List[Dict],
                               initial_capital: float,
                               prefix: str):
        """Generate drawdown analysis chart"""
        try:
            df = pd.DataFrame(trades)
            df['cumulative_pnl'] = df['pnl'].cumsum()
            df['equity'] = initial_capital + df['cumulative_pnl']
            
            # Calculate drawdown
            rolling_max = df['equity'].expanding().max()
            drawdown = (df['equity'] - rolling_max) / rolling_max * 100
            
            plt.figure(figsize=(12, 6))
            plt.plot(df.index, drawdown, color=self.colors[1], linewidth=2)
            plt.title('Drawdown Analysis')
            plt.xlabel('Trade Number')
            plt.ylabel('Drawdown (%)')
            plt.grid(True)
            plt.fill_between(df.index, drawdown, 0, color=self.colors[1], alpha=0.3)
            
            plt.savefig(self.output_dir / f"{prefix}drawdown.png")
            plt.close()
            
        except Exception as e:
            logger.error(f"Error generating drawdown chart: {e}")

    def _generate_monthly_returns_heatmap(self,
                                        trades: List[Dict],
                                        prefix: str):
        """Generate monthly returns heatmap"""
        try:
            df = pd.DataFrame(trades)
            df['month'] = pd.to_datetime(df['entry_time']).dt.to_period('M')
            monthly_returns = df.groupby('month')['pnl'].sum()
            
            # Reshape data for heatmap
            monthly_matrix = monthly_returns.values.reshape(-1, 12)
            
            plt.figure(figsize=(12, 8))
            sns.heatmap(monthly_matrix,
                       annot=True,
                       fmt='.0f',
                       cmap='RdYlGn',
                       center=0)
            plt.title('Monthly Returns Heatmap')
            plt.xlabel('Month')
            plt.ylabel('Year')
            
            plt.savefig(self.output_dir / f"{prefix}monthly_heatmap.png")
            plt.close()
            
        except Exception as e:
            logger.error(f"Error generating monthly heatmap: {e}")

    def _generate_trade_distribution(self,
                                   trades: List[Dict],
                                   prefix: str):
        """Generate trade P&L distribution analysis"""
        try:
            df = pd.DataFrame(trades)
            
            plt.figure(figsize=(12, 6))
            sns.histplot(data=df, x='pnl', bins=50, kde=True)
            plt.title('Trade P&L Distribution')
            plt.xlabel('P&L')
            plt.ylabel('Frequency')
            
            plt.savefig(self.output_dir / f"{prefix}pnl_distribution.png")
            plt.close()
            
            # Generate trade duration distribution
            df['duration'] = pd.to_datetime(df['exit_time']) - pd.to_datetime(df['entry_time'])
            df['duration_minutes'] = df['duration'].dt.total_seconds() / 60
            
            plt.figure(figsize=(12, 6))
            sns.histplot(data=df, x='duration_minutes', bins=50, kde=True)
            plt.title('Trade Duration Distribution')
            plt.xlabel('Duration (minutes)')
            plt.ylabel('Frequency')
            
            plt.savefig(self.output_dir / f"{prefix}duration_distribution.png")
            plt.close()
            
        except Exception as e:
            logger.error(f"Error generating trade distribution: {e}")

    def _generate_win_loss_analysis(self,
                                  trades: List[Dict],
                                  prefix: str):
        """Generate win/loss analysis charts"""
        try:
            df = pd.DataFrame(trades)
            df['win'] = df['pnl'] > 0
            
            # Win/Loss ratio by month
            monthly_wins = df[df['win']].groupby(pd.to_datetime(df['entry_time']).dt.to_period('M')).size()
            monthly_losses = df[~df['win']].groupby(pd.to_datetime(df['entry_time']).dt.to_period('M')).size()
            
            plt.figure(figsize=(12, 6))
            monthly_wins.plot(kind='bar', color=self.colors[2], alpha=0.6, label='Wins')
            monthly_losses.plot(kind='bar', color=self.colors[3], alpha=0.6, label='Losses')
            plt.title('Monthly Win/Loss Distribution')
            plt.xlabel('Month')
            plt.ylabel('Number of Trades')
            plt.legend()
            
            plt.savefig(self.output_dir / f"{prefix}monthly_winloss.png")
            plt.close()
            
            # Average win/loss by time of day
            df['hour'] = pd.to_datetime(df['entry_time']).dt.hour
            hourly_pnl = df.groupby('hour')['pnl'].mean()
            
            plt.figure(figsize=(12, 6))
            hourly_pnl.plot(kind='bar', color=self.colors[4])
            plt.title('Average P&L by Hour')
            plt.xlabel('Hour of Day')
            plt.ylabel('Average P&L')
            
            plt.savefig(self.output_dir / f"{prefix}hourly_pnl.png")
            plt.close()
            
        except Exception as e:
            logger.error(f"Error generating win/loss analysis: {e}")

    def _analyze_day_of_week(self, trades: List[Dict]) -> Dict:
        """Analyze performance by day of week"""
        try:
            df = pd.DataFrame(trades)
            df['day'] = pd.to_datetime(df['entry_time']).dt.day_name()
            
            day_analysis = {}
            for day in df['day'].unique():
                day_trades = df[df['day'] == day]
                day_analysis[day] = {
                    'trade_count': len(day_trades),
                    'win_rate': (day_trades['pnl'] > 0).mean(),
                    'avg_pnl': day_trades['pnl'].mean(),
                    'total_pnl': day_trades['pnl'].sum()
                }
                
            return day_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing day of week: {e}")
            return {}

    def _analyze_time_of_day(self, trades: List[Dict]) -> Dict:
        """Analyze performance by time of day"""
        try:
            df = pd.DataFrame(trades)
            df['hour'] = pd.to_datetime(df['entry_time']).dt.hour
            
            time_analysis = {}
            for hour in range(24):
                hour_trades = df[df['hour'] == hour]
                if len(hour_trades) > 0:
                    time_analysis[hour] = {
                        'trade_count': len(hour_trades),
                        'win_rate': (hour_trades['pnl'] > 0).mean(),
                        'avg_pnl': hour_trades['pnl'].mean(),
                        'total_pnl': hour_trades['pnl'].sum()
                    }
                
            return time_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing time of day: {e}")
            return {}

    def _analyze_by_symbol(self, trades: List[Dict]) -> Dict:
        """Analyze performance by symbol"""
        try:
            df = pd.DataFrame(trades)
            
            symbol_analysis = {}
            for symbol in df['symbol'].unique():
                symbol_trades = df[df['symbol'] == symbol]
                symbol_analysis[symbol] = {
                    'trade_count': len(symbol_trades),
                    'win_rate': (symbol_trades['pnl'] > 0).mean(),
                    'avg_pnl': symbol_trades['pnl'].mean(),
                    'total_pnl': symbol_trades['pnl'].sum(),
                    'max_win': symbol_trades['pnl'].max(),
                    'max_loss': symbol_trades['pnl'].min(),
                    'profit_factor': abs(symbol_trades[symbol_trades['pnl'] > 0]['pnl'].sum() / 
                                      symbol_trades[symbol_trades['pnl'] < 0]['pnl'].sum())
                }
                
            return symbol_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing by symbol: {e}")
            return {}

    def _analyze_live_specific_metrics(self, trades: List[Dict]) -> Dict:
        """Additional analysis specific to live trading"""
        try:
            df = pd.DataFrame(trades)
            
            # Calculate execution metrics
            df['execution_delay'] = (pd.to_datetime(df['execution_time']) - 
                                   pd.to_datetime(df['signal_time'])).dt.total_seconds()
            
            # Calculate slippage
            df['slippage'] = abs(df['execution_price'] - df['signal_price']) / df['signal_price']
            
            live_metrics = {
                'avg_execution_delay': df['execution_delay'].mean(),
                'max_execution_delay': df['execution_delay'].max(),
                'avg_slippage': df['slippage'].mean(),
                'max_slippage': df['slippage'].max(),
                'orders_filled': len(df),
                'orders_rejected': len(df[df['status'] == 'REJECTED']),
                'partial_fills': len(df[df['filled_quantity'] < df['order_quantity']])
            }
            
            return {'live_metrics': live_metrics}
            
        except Exception as e:
            logger.error(f"Error analyzing live metrics: {e}")
            return {}

    def _get_trades_from_db(self, 
                           start_date: datetime,
                           end_date: datetime) -> List[Dict]:
        """Get trades from database"""
        try:
            trades = self.db_manager.get_trades(start_date, end_date)
            return trades
        except Exception as e:
            logger.error(f"Error getting trades from database: {e}")
            return []

    def _get_initial_capital_from_db(self) -> float:
        """Get initial capital from database"""
        try:
            return self.db_manager.get_initial_capital()
        except Exception as e:
            logger.error(f"Error getting initial capital: {e}")
            return 100000.0  # Default value

    def _save_analysis_results(self, results: Dict, prefix: str):
        """Save analysis results to file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = self.output_dir / f"{prefix}analysis_{timestamp}.json"
            
            # Convert non-serializable objects
            serializable_results = {}
            for key, value in results.items():
                if isinstance(value, dict):
                    serializable_results[key] = {
                        k: float(v) if isinstance(v, np.float64) else v
                        for k, v in value.items()
                    }
                else:
                    serializable_results[key] = value
            
            with open(filename, 'w') as f:
                json.dump(serializable_results, f, indent=4, default=str)
            
            logger.info(f"Analysis results saved to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving analysis results: {e}")

    def generate_report(self, results: Dict, output_file: str = "trading_report.html"):
        """Generate HTML report from analysis results"""
        try:
            report_template = """
            <html>
            <head>
                <title>Trading Analysis Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .section { margin: 20px 0; padding: 10px; border: 1px solid #ddd; }
                    .metric { margin: 10px 0; }
                    .positive { color: green; }
                    .negative { color: red; }
                    table { border-collapse: collapse; width: 100%; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    img { max-width: 100%; margin: 10px 0; }
                </style>
            </head>
            <body>
                <h1>Trading Analysis Report</h1>
                <div class="section">
                    <h2>Performance Metrics</h2>
                    {metrics_html}
                </div>
                
                <div class="section">
                    <h2>Trade Statistics</h2>
                    {trade_stats_html}
                </div>
                
                <div class="section">
                    <h2>Day of Week Analysis</h2>
                    {day_analysis_html}
                </div>
                
                <div class="section">
                    <h2>Time of Day Analysis</h2>
                    {time_analysis_html}
                </div>
                
                <div class="section">
                    <h2>Symbol Analysis</h2>
                    {symbol_analysis_html}
                </div>
                
                <div class="section">
                    <h2>Charts</h2>
                    {charts_html}
                </div>
            </body>
            </html>
            """
            
            # Generate HTML components
            metrics_html = self._generate_metrics_html(results['metrics'])
            trade_stats_html = self._generate_trade_stats_html(results)
            day_analysis_html = self._generate_day_analysis_html(results['day_analysis'])
            time_analysis_html = self._generate_time_analysis_html(results['time_analysis'])
            symbol_analysis_html = self._generate_symbol_analysis_html(results['symbol_analysis'])
            charts_html = self._generate_charts_html()
            
            # Fill template
            report_html = report_template.format(
                metrics_html=metrics_html,
                trade_stats_html=trade_stats_html,
                day_analysis_html=day_analysis_html,
                time_analysis_html=time_analysis_html,
                symbol_analysis_html=symbol_analysis_html,
                charts_html=charts_html
            )
            
            # Save report
            report_path = self.output_dir / output_file
            with open(report_path, 'w') as f:
                f.write(report_html)
                
            logger.info(f"Report generated: {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")

    def _generate_metrics_html(self, metrics: Dict) -> str:
        """Generate HTML for performance metrics"""
        html = "<table>"
        html += "<tr><th>Metric</th><th>Value</th></tr>"
        
        for metric, value in metrics.items():
            if isinstance(value, float):
                formatted_value = f"{value:.2f}"
                css_class = "positive" if value > 0 else "negative"
                html += f"<tr><td>{metric}</td><td class='{css_class}'>{formatted_value}</td></tr>"
            else:
                html += f"<tr><td>{metric}</td><td>{value}</td></tr>"
        
        html += "</table>"
        return html

    def _generate_trade_stats_html(self, results: Dict) -> str:
        """Generate HTML for trade statistics"""
        metrics = results['metrics']
        
        html = "<table>"
        html += "<tr><th>Statistic</th><th>Value</th></tr>"
        html += f"<tr><td>Total Trades</td><td>{metrics['total_trades']}</td></tr>"
        html += f"<tr><td>Win Rate</td><td>{metrics['win_rate']:.2%}</td></tr>"
        html += f"<tr><td>Profit Factor</td><td>{metrics['profit_factor']:.2f}</td></tr>"
        html += f"<tr><td>Average Win</td><td>${metrics['avg_profit']:.2f}</td></tr>"
        html += f"<tr><td>Average Loss</td><td>${abs(metrics['avg_loss']):.2f}</td></tr>"
        html += f"<tr><td>Max Drawdown</td><td>{metrics['max_drawdown']:.2%}</td></tr>"
        html += "</table>"
        
        return html

    def _generate_day_analysis_html(self, day_analysis: Dict) -> str:
        """Generate HTML for day of week analysis"""
        html = "<table>"
        html += "<tr><th>Day</th><th>Trades</th><th>Win Rate</th><th>Avg P&L</th><th>Total P&L</th></tr>"
        
        for day, stats in day_analysis.items():
            html += f"<tr>"
            html += f"<td>{day}</td>"
            html += f"<td>{stats['trade_count']}</td>"
            html += f"<td>{stats['win_rate']:.2%}</td>"
            html += f"<td>${stats['avg_pnl']:.2f}</td>"
            html += f"<td>${stats['total_pnl']:.2f}</td>"
            html += f"</tr>"
            
        html += "</table>"
        return html

    def _generate_time_analysis_html(self, time_analysis: Dict) -> str:
        """Generate HTML for time of day analysis"""
        html = "<table>"
        html += "<tr><th>Hour</th><th>Trades</th><th>Win Rate</th><th>Avg P&L</th><th>Total P&L</th></tr>"
        
        for hour in sorted(time_analysis.keys()):
            stats = time_analysis[hour]
            html += f"<tr>"
            html += f"<td>{hour:02d}:00</td>"
            html += f"<td>{stats['trade_count']}</td>"
            html += f"<td>{stats['win_rate']:.2%}</td>"
            html += f"<td>${stats['avg_pnl']:.2f}</td>"
            html += f"<td>${stats['total_pnl']:.2f}</td>"
            html += f"</tr>"
            
        html += "</table>"
        return html

    def _generate_symbol_analysis_html(self, symbol_analysis: Dict) -> str:
        """Generate HTML for symbol analysis"""
        html = "<table>"
        html += """<tr>
            <th>Symbol</th>
            <th>Trades</th>
            <th>Win Rate</th>
            <th>Avg P&L</th>
            <th>Total P&L</th>
            <th>Max Win</th>
            <th>Max Loss</th>
            <th>Profit Factor</th>
        </tr>"""
        
        for symbol, stats in symbol_analysis.items():
            html += f"<tr>"
            html += f"<td>{symbol}</td>"
            html += f"<td>{stats['trade_count']}</td>"
            html += f"<td>{stats['win_rate']:.2%}</td>"
            html += f"<td>${stats['avg_pnl']:.2f}</td>"
            html += f"<td>${stats['total_pnl']:.2f}</td>"
            html += f"<td>${stats['max_win']:.2f}</td>"
            html += f"<td>${abs(stats['max_loss']):.2f}</td>"
            html += f"<td>{stats['profit_factor']:.2f}</td>"
            html += f"</tr>"
            
        html += "</table>"
        return html

    def _generate_charts_html(self) -> str:
        """Generate HTML for embedded charts"""
        html = ""
        for image in self.output_dir.glob("*.png"):
            html += f"<img src='{image}' alt='{image.stem}'><br>"
        return html


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze trading results')
    
    parser.add_argument('--input', type=str, required=True,
                       help='Input file with trading results')
    parser.add_argument('--type', choices=['backtest', 'live'], default='backtest',
                       help='Type of results to analyze')
    parser.add_argument('--capital', type=float, default=100000.0,
                       help='Initial capital')
    parser.add_argument('--output', type=str, default='trading_report.html',
                       help='Output report file')
    
    args = parser.parse_args()
    
    # Load trading results
    with open(args.input, 'r') as f:
        trading_results = json.load(f)
    
    # Initialize analyzer
    analyzer = TradingAnalyzer()
    
    # Run analysis
    if args.type == 'backtest':
        results = analyzer.analyze_results(
            trades=trading_results['trades'],
            initial_capital=args.capital
        )
    else:
        results = analyzer.analyze_live_trading(
            start_date=datetime.strptime(trading_results['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(trading_results['end_date'], '%Y-%m-%d')
        )
    
    # Generate report
    analyzer.generate_report(results, args.output)
    
    print(f"\nAnalysis completed. Report saved to: {args.output}")