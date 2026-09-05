# Crafted Escrow - Telegram Escrow Bot

A production-ready Telegram escrow bot built with Python 3.11+, aiogram 3.x, and SQLite.

## Features

- 🔐 Secure escrow deals with buyer/seller agreement
- 👥 Multi-role staff system (Owner, Admin, Escrower)
- 💰 Multiple payment methods (INR, GRAM, USDT, STARS)
- 📊 Global statistics with volume tracking
- 📁 Personal deal management
- ⭐ Automatic vouch requests
- ⚠️ Dispute system
- 📝 Complete audit logging
- 📢 Broadcast system
- 🔒 Production-ready security

## Requirements

- Python 3.11+
- SQLite3
- Telegram Bot Token

## Installation

### Linux Server

```bash
# Clone repository
git clone <repository-url>
cd crafted_escrow

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your tokens
nano .env

# Run the bot
python bot.py
