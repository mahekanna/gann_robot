# Gann Trading System Setup Guide

## Prerequisites

- Python 3.9 or higher
- ICICI Direct Breeze API credentials
- Virtual environment (recommended)
- Git (for version control)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gann_trading.git
cd gann_trading
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Configuration

### 1. Environment Variables

Create a `.env` file in the root directory with your ICICI Breeze credentials:

```env
ICICI_API_KEY=your_api_key
ICICI_API_SECRET=your_api_secret
ICICI_TOTP_SECRET=your_totp_secret
```

### 2. Trading Configuration

Configure your trading parameters in `config/trading_config.json`:

```json
{
    "symbols": ["SBIN", "RELIANCE", "INFY"],
    "timeframes": {
        "primary": 15,
        "secondary": 5
    },
    "trading_hours": {
        "start": "09:15",
        "end": "15:20",
        "square_off": "15:15"
    },
    "capital_allocation": {
        "total": 100000,
        "per_trade": 20000,
        "per_symbol": 50000
    }
}
```

### 3. Risk Configuration

Set up risk parameters in `config/risk_config.json`:

```json
{
    "max_daily_loss": 3000,
    "max_loss_per_trade": 1000,
    "max_drawdown": 0.05,
    "max_positions": 5,
    "position_size_risk": 0.02
}
```

## Database Setup

1. Create database directory:
```bash
mkdir data
```

2. Initialize database:
```bash
python scripts/init_db.py
```

## Directory Structure

```
gann_trading/
├── core/
│   ├── brokers/        # Broker integrations
│   ├── data/          # Data handling
│   ├── strategy/      # Trading strategies
│   └── risk/          # Risk management
├── config/            # Configuration files
├── docs/             # Documentation
├── logs/             # Log files
├── scripts/          # Utility scripts
└── tests/            # Test cases
```

## Running Tests

Run all tests:
```bash
python -m pytest tests/
```

Run specific test file:
```bash
python -m pytest tests/test_strategy.py
```

## Development Setup

### 1. IDE Configuration

For VSCode, create `.vscode/settings.json`:

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true
}
```

### 2. Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

## Production Deployment

### 1. System Requirements

- Dedicated server/VM with:
  - 4+ CPU cores
  - 8+ GB RAM
  - 100+ GB SSD storage
  - Ubuntu 20.04 LTS or higher

### 2. Service Setup

Create systemd service file `/etc/systemd/system/gann_trading.service`:

```ini
[Unit]
Description=Gann Trading System
After=network.target

[Service]
User=trading
WorkingDirectory=/opt/gann_trading
Environment=PYTHONPATH=/opt/gann_trading
ExecStart=/opt/gann_trading/venv/bin/python main.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable gann_trading
sudo systemctl start gann_trading
```

### 3. Monitoring

Set up monitoring using Prometheus and Grafana:

1. Install Prometheus:
```bash
sudo apt-get install prometheus
```

2. Configure metrics in `core/monitoring/metrics.py`

3. Add to Prometheus config:
```yaml
scrape_configs:
  - job_name: 'gann_trading'
    static_configs:
      - targets: ['localhost:8000']
```

## Logging

Logs are stored in `logs/` directory:
- `trading.log`: Main trading logs
- `error.log`: Error logs
- `access.log`: API access logs

Configure log rotation in `config/logging_config.json`.

## Troubleshooting

### Common Issues

1. Connection Issues
```python
from core.utils.connection import test_connection
test_connection()  # Tests broker connectivity
```

2. Data Issues
```python
from core.data.validator import validate_data
validate_data('path/to/data.csv')
```

3. Permission Issues
```bash
sudo chown -R trading:trading /opt/gann_trading
sudo chmod -R 755 /opt/gann_trading
```

### Support

For additional support:
1. Check the [FAQ](./faq.md)
2. File an issue on GitHub
3. Contact support at support@example.com

## Updates and Maintenance

1. Update dependencies:
```bash
pip install --upgrade -r requirements.txt
```

2. Backup data:
```bash
./scripts/backup.sh
```

3. System updates:
```bash
sudo apt update && sudo apt upgrade
```

## Security

1. Set up SSH keys:
```bash
ssh-keygen -t ed25519 -C "trading@example.com"
```

2. Configure firewall:
```bash
sudo ufw allow 22
sudo ufw allow 443
sudo ufw enable
```

3. Regular security updates:
```bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get dist-upgrade
```