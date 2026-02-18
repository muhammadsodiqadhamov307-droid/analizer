#!/bin/bash

# Update system
echo "🚀 Updating system..."
sudo apt update && sudo apt upgrade -y

# Install Python and pip
echo "🐍 Installing Python..."
sudo apt install -y python3 python3-pip python3-venv

# Create virtual environment
echo "🛠️ Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create .env instructions
if [ ! -f .env ]; then
    echo "⚠️ .env file not found! creating template..."
    cp .env.example .env 2>/dev/null || echo "TELEGRAM_BOT_TOKEN=\nGEMINI_API_KEY=\nTRADING_SYMBOL=BTC/USDT" > .env
    echo "❗ PLEASE EDIT .env FILE WITH YOUR API KEYS!"
fi

echo "✅ Setup Complete. Run 'source venv/bin/activate' then 'python main.py'"
