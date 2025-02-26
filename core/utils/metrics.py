# core/utils/metrics.py

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class PerformanceMetrics:
    @staticmethod
    def calculate_returns(prices: List[float]) -> List[float]:
        """Calculate returns series"""
        return [((prices[i] - prices[i-1]) / prices[i-1]) 
                for i in range(1, len(prices))]

    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], 
                             risk_free_rate: float = 0.03) -> float:
        """Calculate Sharpe ratio"""
        if not returns:
            return 0.0
        excess_returns = np.array(returns) - (risk_free_rate / 252)
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)

    @staticmethod
    def calculate_max_drawdown(prices: List[float]) -> float:
        """Calculate maximum drawdown"""
        cummax = np.maximum.accumulate(prices)
        drawdown = (cummax - prices) / cummax
        return np.max(drawdown)

    @staticmethod
    def calculate_win_rate(trades: List[Dict]) -> float:
        """Calculate win rate"""
        if not trades:
            return 0.0
        winning_trades = sum(1 for trade in trades if trade['pnl'] > 0)
        return winning_trades / len(trades)

    @staticmethod
    def calculate_profit_factor(trades: List[Dict]) -> float:
        """Calculate profit factor"""
        gross_profit = sum(trade['pnl'] for trade in trades if trade['pnl'] > 0)
        gross_loss = abs(sum(trade['pnl'] for trade in trades if trade['pnl'] < 0))
        return gross_profit / gross_loss if gross_loss != 0 else 0

    @staticmethod
    def calculate_average_trade(trades: List[Dict]) -> Dict:
        """Calculate average trade metrics"""
        if not trades:
            return {'avg_profit': 0, 'avg_loss': 0, 'avg_duration': 0}
            
        profits = [t['pnl'] for t in trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in trades if t['pnl'] < 0]
        
        durations = [(t['exit_time'] - t['entry_time']).total_seconds() / 60 
                    for t in trades if 'exit_time' in t and 'entry_time' in t]
        
        return {
            'avg_profit': np.mean(profits) if profits else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'avg_duration': np.mean(durations) if durations else 0
        }

    @staticmethod
    def calculate_risk_metrics(trades: List[Dict], 
                             initial_capital: float) -> Dict:
        """Calculate risk metrics"""
        if not trades:
            return {
                'max_drawdown': 0,
                'risk_reward_ratio': 0,
                'capital_utilization': 0
            }
            
        # Calculate running balance
        balance = [initial_capital]
        for trade in trades:
            balance.append(balance[-1] + trade['pnl'])
            
        max_drawdown = PerformanceMetrics.calculate_max_drawdown(balance)
        
        # Risk-reward ratio
        avg_metrics = PerformanceMetrics.calculate_average_trade(trades)
        risk_reward = abs(avg_metrics['avg_profit'] / avg_metrics['avg_loss']) if avg_metrics['avg_loss'] != 0 else 0
        
        # Capital utilization
        max_capital_used = max(trade.get('capital_used', 0) for trade in trades)
        capital_utilization = max_capital_used / initial_capital
        
        return {
            'max_drawdown': max_drawdown,
            'risk_reward_ratio': risk_reward,
            'capital_utilization': capital_utilization
        }

    @staticmethod
    def calculate_daily_metrics(trades: List[Dict]) -> pd.DataFrame:
        """Calculate daily performance metrics"""
        if not trades:
            return pd.DataFrame()
            
        # Convert trades to DataFrame
        df = pd.DataFrame(trades)
        df['date'] = pd.to_datetime(df['entry_time']).dt.date
        
        # Group by date
        daily = df.groupby('date').agg({
            'pnl': 'sum',
            'entry_time': 'count'  # Number of trades
        }).rename(columns={'entry_time': 'num_trades'})
        
        # Calculate daily returns
        daily['returns'] = daily['pnl'].pct_change()
        
        # Calculate cumulative metrics
        daily['cumulative_pnl'] = daily['pnl'].cumsum()
        daily['cumulative_trades'] = daily['num_trades'].cumsum()
        
        return daily

    @staticmethod
    def calculate_strategy_metrics(trades: List[Dict], 
                                 initial_capital: float) -> Dict:
        """Calculate comprehensive strategy metrics"""
        if not trades:
            return {}
            
        # Basic metrics
        num_trades = len(trades)
        win_rate = PerformanceMetrics.calculate_win_rate(trades)
        profit_factor = PerformanceMetrics.calculate_profit_factor(trades)
        
        # Returns
        pnl = [trade['pnl'] for trade in trades]
        returns = [pnl / initial_capital for pnl in pnl]
        sharpe = PerformanceMetrics.calculate_sharpe_ratio(returns)
        
        # Average trade metrics
        avg_metrics = PerformanceMetrics.calculate_average_trade(trades)
        
        # Risk metrics
        risk_metrics = PerformanceMetrics.calculate_risk_metrics(
            trades, 
            initial_capital
        )
        
        # Daily metrics
        daily = PerformanceMetrics.calculate_daily_metrics(trades)
        
        return {
            'total_trades': num_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'avg_profit': avg_metrics['avg_profit'],
            'avg_loss': avg_metrics['avg_loss'],
            'avg_duration': avg_metrics['avg_duration'],
            'max_drawdown': risk_metrics['max_drawdown'],
            'risk_reward_ratio': risk_metrics['risk_reward_ratio'],
            'capital_utilization': risk_metrics['capital_utilization'],
            'total_pnl': sum(pnl),
            'return_pct': (sum(pnl) / initial_capital) * 100,
            'daily_metrics': daily.to_dict()
        }