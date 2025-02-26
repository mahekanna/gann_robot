# -*- coding: utf-8 -*-
"""
Created on Fri Feb 21 17:10:26 2025

@author: mahes
"""

# core/monitoring/trading_monitor.py

import logging
import pandas as pd
from typing import Dict, List
from datetime import datetime, date
import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from ..utils.logger import setup_logger

logger = setup_logger('trading_monitor')

class TradingMonitor:
    def __init__(self, strategy_manager, config: Dict):
        """Initialize trading monitor"""
        self.strategy_manager = strategy_manager
        self.config = config
        
        # Setup directories
        self.report_dir = Path("reports")
        self.report_dir.mkdir(exist_ok=True)
        
        # Initialize trackers
        self.performance_data = []
        self.daily_summaries = []
        self.alerts = []
        
        # Alert thresholds
        self.alert_thresholds = {
            'drawdown_alert': config.get('drawdown_alert', 0.02),  # 2%
            'profit_alert': config.get('profit_alert', 0.02),     # 2%
            'loss_alert': config.get('loss_alert', 0.01)         # 1%
        }
        
    def update(self):
        """Update monitoring data"""
        try:
            # Get current status
            status = self.strategy_manager.get_status()
            
            # Get performance metrics
            metrics = self._collect_metrics()
            
            # Check for alerts
            self._check_alerts(metrics)
            
            # Record data
            self.performance_data.append({
                'timestamp': datetime.now(),
                'status': status,
                'metrics': metrics
            })
            
            # Log status periodically
            self._log_status(status, metrics)
            
        except Exception as e:
            logger.error(f"Error updating monitor: {e}")

    def _collect_metrics(self) -> Dict:
        """Collect performance metrics"""
        metrics = {}
        
        for strategy_id, strategy in self.strategy_manager.strategies.items():
            strategy_metrics = strategy.get_metrics()
            metrics[strategy_id] = {
                'daily_pnl': strategy_metrics['daily_pnl'],
                'total_trades': strategy_metrics['total_trades'],
                'win_rate': strategy_metrics['win_rate'],
                'active_positions': len(strategy.positions),
                'max_drawdown': strategy_metrics['max_drawdown']
            }
            
        return metrics

    def _check_alerts(self, metrics: Dict):
        """Check for alert conditions"""
        try:
            for strategy_id, strategy_metrics in metrics.items():
                # Check drawdown
                if strategy_metrics['max_drawdown'] >= self.alert_thresholds['drawdown_alert']:
                    self._add_alert(
                        strategy_id,
                        'High Drawdown',
                        f"Drawdown of {strategy_metrics['max_drawdown']:.2%} exceeded threshold"
                    )
                
                # Check profit/loss
                daily_pnl_pct = strategy_metrics['daily_pnl'] / self.config['initial_capital']
                if daily_pnl_pct <= -self.alert_thresholds['loss_alert']:
                    self._add_alert(
                        strategy_id,
                        'Loss Alert',
                        f"Daily loss of {daily_pnl_pct:.2%} exceeded threshold"
                    )
                elif daily_pnl_pct >= self.alert_thresholds['profit_alert']:
                    self._add_alert(
                        strategy_id,
                        'Profit Target',
                        f"Daily profit of {daily_pnl_pct:.2%} reached target"
                    )
                    
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")

    def _add_alert(self, strategy_id: str, alert_type: str, message: str):
        """Add new alert"""
        alert = {
            'timestamp': datetime.now(),
            'strategy_id': strategy_id,
            'type': alert_type,
            'message': message
        }
        
        self.alerts.append(alert)
        logger.warning(f"Alert: {alert_type} - {message}")

    def generate_daily_report(self) -> Dict:
        """Generate daily performance report"""
        try:
            today = date.today()
            
            # Collect daily data
            daily_data = {
                'date': today,
                'strategies': {},
                'total_pnl': 0,
                'total_trades': 0,
                'winning_trades': 0
            }
            
            for strategy_id, strategy in self.strategy_manager.strategies.items():
                metrics = strategy.get_metrics()
                daily_data['strategies'][strategy_id] = metrics
                daily_data['total_pnl'] += metrics['daily_pnl']
                daily_data['total_trades'] += metrics['total_trades']
                daily_data['winning_trades'] += metrics['winning_trades']
            
            # Calculate overall metrics
            if daily_data['total_trades'] > 0:
                daily_data['win_rate'] = daily_data['winning_trades'] / daily_data['total_trades']
            else:
                daily_data['win_rate'] = 0
                
            # Save report
            self._save_daily_report(daily_data)
            
            return daily_data
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return {}

    def _save_daily_report(self, report_data: Dict):
        """Save daily report to file"""
        try:
            report_file = self.report_dir / f"daily_report_{date.today()}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=4, default=str)
                
            logger.info(f"Daily report saved: {report_file}")
            
        except Exception as e:
            logger.error(f"Error saving daily report: {e}")

    def generate_performance_charts(self):
        """Generate performance visualization charts"""
        try:
            # Convert performance data to DataFrame
            df = pd.DataFrame(self.performance_data)
            
            # Create PnL chart
            plt.figure(figsize=(12, 6))
            for strategy_id in self.strategy_manager.strategies.keys():
                pnl_data = [d['metrics'][strategy_id]['daily_pnl'] 
                           for d in self.performance_data]
                plt.plot(df['timestamp'], pnl_data, label=strategy_id)
            
            plt.title('Daily PnL Performance')
            plt.xlabel('Time')
            plt.ylabel('PnL')
            plt.legend()
            plt.grid(True)
            
            # Save chart
            chart_file = self.report_dir / f"performance_chart_{date.today()}.png"
            plt.savefig(chart_file)
            plt.close()
            
            logger.info(f"Performance chart saved: {chart_file}")
            
        except Exception as e:
            logger.error(f"Error generating performance charts: {e}")

    # core/monitoring/trading_monitor.py (continued)

    def _log_status(self, status: Dict, metrics: Dict):
        """Log current trading status"""
        try:
            logger.info("\n=== Trading Status Update ===")
            logger.info(f"Time: {datetime.now()}")
            logger.info(f"System State: {status['state']}")
            logger.info(f"Active Strategies: {status['active_strategies']}")
            logger.info(f"Total Positions: {status['total_positions']}")
            logger.info(f"Total P&L: {status['total_pnl']:.2f}")
            
            # Log individual strategy metrics
            logger.info("\nStrategy Performance:")
            for strategy_id, strategy_metrics in metrics.items():
                logger.info(f"\n{strategy_id}:")
                logger.info(f"  Daily P&L: {strategy_metrics['daily_pnl']:.2f}")
                logger.info(f"  Win Rate: {strategy_metrics['win_rate']:.2%}")
                logger.info(f"  Active Positions: {strategy_metrics['active_positions']}")
                logger.info(f"  Max Drawdown: {strategy_metrics['max_drawdown']:.2%}")
            
            # Log alerts if any
            if self.alerts:
                logger.info("\nActive Alerts:")
                for alert in self.alerts[-5:]:  # Show last 5 alerts
                    logger.info(f"  {alert['type']}: {alert['message']}")
            
            logger.info("============================\n")
            
        except Exception as e:
            logger.error(f"Error logging status: {e}")

    def generate_trade_analysis(self) -> Dict:
        """Generate detailed trade analysis"""
        try:
            analysis = {
                'overall': {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_pnl': 0,
                    'max_drawdown': 0,
                    'sharpe_ratio': 0,
                    'win_rate': 0
                },
                'by_strategy': {}
            }
            
            # Analyze each strategy
            for strategy_id, strategy in self.strategy_manager.strategies.items():
                trades = strategy.trades
                metrics = strategy.get_metrics()
                
                strategy_analysis = {
                    'total_trades': len(trades),
                    'winning_trades': metrics['winning_trades'],
                    'losing_trades': metrics['losing_trades'],
                    'total_pnl': metrics['daily_pnl'],
                    'max_drawdown': metrics['max_drawdown'],
                    'win_rate': metrics['win_rate'],
                    'avg_profit': metrics.get('avg_profit', 0),
                    'avg_loss': metrics.get('avg_loss', 0),
                    'profit_factor': metrics.get('profit_factor', 0)
                }
                
                analysis['by_strategy'][strategy_id] = strategy_analysis
                
                # Update overall metrics
                analysis['overall']['total_trades'] += strategy_analysis['total_trades']
                analysis['overall']['winning_trades'] += strategy_analysis['winning_trades']
                analysis['overall']['losing_trades'] += strategy_analysis['losing_trades']
                analysis['overall']['total_pnl'] += strategy_analysis['total_pnl']
                
            # Calculate overall ratios
            if analysis['overall']['total_trades'] > 0:
                analysis['overall']['win_rate'] = (
                    analysis['overall']['winning_trades'] / 
                    analysis['overall']['total_trades']
                )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error generating trade analysis: {e}")
            return {}

    def export_trade_data(self):
        """Export trade data to CSV"""
        try:
            # Collect all trades
            all_trades = []
            for strategy_id, strategy in self.strategy_manager.strategies.items():
                for trade in strategy.trades:
                    trade_data = {
                        'strategy': strategy_id,
                        'symbol': trade['symbol'],
                        'entry_time': trade['entry_time'],
                        'exit_time': trade['exit_time'],
                        'entry_price': trade['entry_price'],
                        'exit_price': trade['exit_price'],
                        'quantity': trade['quantity'],
                        'pnl': trade['pnl'],
                        'exit_reason': trade.get('reason', 'unknown')
                    }
                    all_trades.append(trade_data)
            
            # Convert to DataFrame and save
            if all_trades:
                df = pd.DataFrame(all_trades)
                csv_file = self.report_dir / f"trades_{date.today()}.csv"
                df.to_csv(csv_file, index=False)
                logger.info(f"Trade data exported to: {csv_file}")
                
        except Exception as e:
            logger.error(f"Error exporting trade data: {e}")

    def monitor_risk_limits(self) -> bool:
        """Monitor risk limits and generate alerts"""
        try:
            for strategy_id, strategy in self.strategy_manager.strategies.items():
                risk_metrics = strategy.risk_manager.get_risk_metrics()
                
                # Check daily loss limit
                if risk_metrics['daily_pnl'] <= -self.config['max_daily_loss']:
                    self._add_alert(
                        strategy_id,
                        'Risk Limit Breach',
                        'Daily loss limit reached'
                    )
                    return False
                
                # Check drawdown limit
                if risk_metrics['max_drawdown'] >= self.config['max_drawdown']:
                    self._add_alert(
                        strategy_id,
                        'Risk Limit Breach',
                        'Maximum drawdown limit reached'
                    )
                    return False
                
                # Check position limits
                if len(strategy.positions) >= self.config['max_positions']:
                    self._add_alert(
                        strategy_id,
                        'Position Limit',
                        'Maximum positions limit reached'
                    )
                
            return True
            
        except Exception as e:
            logger.error(f"Error monitoring risk limits: {e}")
            return False

    def cleanup_old_data(self, days: int = 30):
        """Cleanup old monitoring data"""
        try:
            cutoff_date = date.today() - pd.Timedelta(days=days)
            
            # Cleanup old reports
            for file in self.report_dir.glob("*.json"):
                file_date = date.fromisoformat(file.stem.split('_')[-1])
                if file_date < cutoff_date:
                    file.unlink()
            
            # Cleanup old performance data
            self.performance_data = [
                data for data in self.performance_data
                if data['timestamp'].date() >= cutoff_date
            ]
            
            # Cleanup old alerts
            self.alerts = [
                alert for alert in self.alerts
                if alert['timestamp'].date() >= cutoff_date
            ]
            
            logger.info(f"Cleaned up monitoring data older than {cutoff_date}")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")

    def save_state(self):
        """Save monitoring state to file"""
        try:
            state = {
                'performance_data': self.performance_data,
                'daily_summaries': self.daily_summaries,
                'alerts': self.alerts
            }
            
            state_file = self.report_dir / "monitor_state.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, default=str, indent=4)
                
            logger.info("Monitoring state saved")
            
        except Exception as e:
            logger.error(f"Error saving monitor state: {e}")

    def load_state(self):
        """Load monitoring state from file"""
        try:
            state_file = self.report_dir / "monitor_state.json"
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    
                self.performance_data = state['performance_data']
                self.daily_summaries = state['daily_summaries']
                self.alerts = state['alerts']
                
                logger.info("Monitoring state loaded")
                
        except Exception as e:
            logger.error(f"Error loading monitor state: {e}")