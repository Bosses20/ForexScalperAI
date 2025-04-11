#!/bin/bash
# Production VPS Setup Script for Forex Trading Bot
# This script sets up a production environment on a VPS for running the trading bot

echo "===== Forex Trading Bot Production VPS Setup ====="
echo "Setting up the production environment..."

# Make sure we're updated
echo "Step 1: Updating system packages..."
apt-get update && apt-get upgrade -y

# Install dependencies
echo "Step 2: Installing required dependencies..."
apt-get install -y python3 python3-pip python3-venv git tmux nginx supervisor redis-server ufw

# Set up firewall
echo "Step 3: Configuring firewall..."
ufw allow ssh
ufw allow http
ufw allow https
ufw allow 8000  # API port
ufw --force enable

# Create a dedicated user for the trading bot
echo "Step 4: Creating dedicated user for the trading bot..."
useradd -m -s /bin/bash tradingbot
usermod -aG sudo tradingbot

# Set up the application directory
echo "Step 5: Setting up application directory..."
mkdir -p /opt/forex-trading-bot
chown tradingbot:tradingbot /opt/forex-trading-bot

# Clone the repository
echo "Step 6: Cloning repository..."
git clone https://github.com/yourusername/forex-trading-bot.git /opt/forex-trading-bot

# Set up virtual environment
echo "Step 7: Setting up Python virtual environment..."
cd /opt/forex-trading-bot
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Set up supervisor configuration
echo "Step 8: Setting up supervisor for process management..."
cat > /etc/supervisor/conf.d/forex-trading-bot.conf << EOF
[program:forex-trading-bot]
command=/opt/forex-trading-bot/venv/bin/python /opt/forex-trading-bot/run.py
directory=/opt/forex-trading-bot
user=tradingbot
autostart=true
autorestart=true
startretries=3
redirect_stderr=true
stdout_logfile=/var/log/forex-trading-bot.log
environment=PRODUCTION=1

[program:forex-api-server]
command=/opt/forex-trading-bot/venv/bin/python /opt/forex-trading-bot/run_api_server.py
directory=/opt/forex-trading-bot
user=tradingbot
autostart=true
autorestart=true
startretries=3
redirect_stderr=true
stdout_logfile=/var/log/forex-api-server.log
environment=PRODUCTION=1
EOF

# Set up NGINX as a reverse proxy
echo "Step 9: Setting up NGINX as a reverse proxy..."
cat > /etc/nginx/sites-available/forex-trading-bot << EOF
server {
    listen 80;
    server_name trading.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
ln -s /etc/nginx/sites-available/forex-trading-bot /etc/nginx/sites-enabled/

# Set up daily cron job for auto-updates
echo "Step 10: Setting up automatic updates..."
cat > /etc/cron.daily/forex-trading-bot-updates << EOF
#!/bin/bash
cd /opt/forex-trading-bot
git pull
source venv/bin/activate
pip install -r requirements.txt
supervisorctl restart forex-trading-bot forex-api-server
EOF
chmod +x /etc/cron.daily/forex-trading-bot-updates

# Reload configurations
echo "Step 11: Reloading configurations..."
supervisorctl reread
supervisorctl update
nginx -t && systemctl restart nginx

echo "===== Production VPS Setup Complete ====="
echo "Trading bot is now running and will automatically start on system boot."
echo "API server is available at http://trading.yourdomain.com"
echo ""
echo "Important next steps:"
echo "1. Update the config files in /opt/forex-trading-bot/config/"
echo "2. Set up SSL certificate with Certbot for HTTPS"
echo "3. Configure monitoring system (Prometheus/Grafana)"
echo "4. Set up backup procedures"
echo ""
echo "For more information, see the documentation in /opt/forex-trading-bot/docs/"
