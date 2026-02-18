# Aether-Quant Telegram Bot

An advanced Institutional Order Flow Analysis bot powered by Gemini 1.5/3 Flash and real-time market data.

## Features
- **Institutional Detection**: Identifies "Buy Walls" and "Sell Icebergs" using Order Book analysis.
- **Gemini Brain**: Simulates an "Insider" persona (Aether-Quant) to decode market moves.
- **Real-Time Data**: Fetches Level 2 Order Book and Tape data via `ccxt` (Binance).
- **Deep Dive Reports**: Generates detailed "Faktlar / Reja / Natija" reports.
- **Alert Mode**: Monitors for Volume Imbalance > 3.0.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: This might take a few minutes)*

2.  **Configure Environment**:
    - Rename `.env.example` to `.env` (or create `.env`)
    - Add your API Keys:
        - `TELEGRAM_BOT_TOKEN`
        - `GEMINI_API_KEY`
        - `TRADING_SYMBOL` (e.g., BTC/USDT)

3.  **Run the Bot**:
    ```bash
    python main.py
    ```

## Commands
- `/start`: Initialize the bot.
- `/analyze [symbol]`: Quick "Server Decode" report.
- `/deep_dive [symbol]`: Full institutional breakdown.
- `/monitor`: Toggle background monitoring for Order Flow Imbalance.

## Architecture
- `main.py`: Telegram Bot interface.
- `engine/data_fetcher.py`: Connects to Binance public API.
- `engine/gemini_brain.py`: AI Logic with Function Calling.
- `utils/math_tools.py`: VWAP, RSI, OFI, and Imbalance calculations.
