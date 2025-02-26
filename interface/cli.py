# interface/cli.py

import click
import json
from datetime import datetime
from typing import Dict

@click.group()
def cli():
    """Trading System CLI"""
    pass

@cli.command()
@click.option('--mode', default='paper', type=click.Choice(['live', 'paper']))
@click.option('--config', default='config/trading_config.json', help='Config file path')
def start(mode, config):
    """Start trading system"""
    click.echo(f"Starting trading system in {mode} mode...")
    # Initialize and start system

@cli.command()
def stop():
    """Stop trading system"""
    click.echo("Stopping trading system...")
    # Stop system

@cli.command()
@click.option('--symbol', required=True, help='Trading symbol')
def status(symbol):
    """Get trading status for symbol"""
    click.echo(f"Getting status for {symbol}...")
    # Get and display status

@cli.command()
@click.option('--date', type=click.DateTime(), default=str(datetime.now().date()))
def report(date):
    """Generate trading report"""
    click.echo(f"Generating report for {date}...")
    # Generate and display report

if __name__ == '__main__':
    cli()