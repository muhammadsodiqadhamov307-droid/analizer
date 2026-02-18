import requests
import pandas as pd
from typing import Dict, List, Optional
import time

class MarketConnector:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://data-api.binance.vision/api/v3"
        # Note: This base URL is specific to Crypto/Binance.
        # For Forex, we would need a different provider later.
        self.headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        print(f"DEBUG: Initialized MarketConnector with Direct HTTP to {self.base_url}")

    def get_market_context(self, symbol):
        """
        Determines if the symbol is Crypto or Forex and returns the analytical context.
        """
        if "/" in symbol and ("EUR" in symbol or "USD" in symbol or "JPY" in symbol or "GBP" in symbol) and "USDT" not in symbol: 
            return "Forex Mode: Prioritize Session Time (London/NY) & Tick Velocity. Look for Stop Hunts around News."
        else: 
            return "Crypto Mode: Prioritize Open Interest, Funding Rates, and On-Chain Whale Movements."

    def _get(self, endpoint: str, params: Dict = None):
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"HTTP Error {endpoint}: {e}")
            return None

    def _format_symbol(self, symbol: str) -> str:
        # Convert BTC/USDT to BTCUSDT
        return symbol.replace('/', '').upper()

    def get_price(self, symbol: str) -> float:
        symbol_fmt = self._format_symbol(symbol)
        data = self._get("ticker/price", params={'symbol': symbol_fmt})
        if data:
            return float(data['price'])
        return 0.0

    def get_order_book(self, symbol: str, limit: int = 50) -> Dict:
        """
        Fetches the Order Book (Level 2 Data) from data-api.
        """
        symbol_fmt = self._format_symbol(symbol)
        data = self._get("depth", params={'symbol': symbol_fmt, 'limit': limit})
        
        if not data:
            return {'bids': [], 'asks': [], 'timestamp': None}

        # Binance response: {'lastUpdateId': ..., 'bids': [['price', 'qty'], ...], ...}
        return {
            'bids': [[float(p), float(q)] for p, q in data.get('bids', [])],
            'asks': [[float(p), float(q)] for p, q in data.get('asks', [])],
            'timestamp': int(time.time() * 1000) # data-api depth doesn't always have timestamp, use current
        }

    def get_recent_trades(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """
        Fetches recent trades (Tape Data).
        """
        symbol_fmt = self._format_symbol(symbol)
        data = self._get("trades", params={'symbol': symbol_fmt, 'limit': limit})
        
        if not data:
            return pd.DataFrame()

        # Binance trade format: {'id':..., 'price': '...', 'qty': '...', 'time': ..., 'isBuyerMaker': ...}
        formatted_trades = []
        for t in data:
            formatted_trades.append({
                'timestamp': t['time'],
                'symbol': symbol,
                'side': 'sell' if t['isBuyerMaker'] else 'buy', # isBuyerMaker=True means seller was maker (buyer was taker -> buy side?) Wait.
                # If isBuyerMaker is True, the maker was a buyer. The Taker was a Seller. So it's a SELL trade.
                # If isBuyerMaker is False, the maker was a seller. The Taker was a Buyer. So it's a BUY trade.
                'price': float(t['price']),
                'amount': float(t['qty'])
            })
            
        df = pd.DataFrame(formatted_trades)
        if not df.empty:
            df = df[['timestamp', 'symbol', 'side', 'price', 'amount']]
        return df

    def get_market_snapshot(self, symbol: str) -> Dict:
        """
        Combines Price, Order Book, and Tape into a single snapshot.
        """
        price = self.get_price(symbol)
        book = self.get_order_book(symbol)
        trades = self.get_recent_trades(symbol)
        
        if price == 0.0 and not book['bids']:
            return {'error': 'Could not fetch market data'}

        return {
            'symbol': symbol,
            'price': price,
            'order_book': book,
            'recent_trades': trades.to_dict('records') if not trades.empty else []
        }

