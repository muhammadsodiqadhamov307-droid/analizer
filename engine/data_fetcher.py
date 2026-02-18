import requests
import pandas as pd
from typing import Dict, List, Optional
import time
import yfinance as yf

class MarketConnector:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://data-api.binance.vision/api/v3"
        self.futures_url = "https://fapi.binance.com/fapi/v1" # For Funding/OI
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
        if "XAU" in symbol or "GOLD" in symbol:
            return "Gold Mode: Prioritize DXY Inverse Correlation & Central Bank Traps."
        elif "/" in symbol and ("EUR" in symbol or "USD" in symbol or "JPY" in symbol or "GBP" in symbol) and "USDT" not in symbol: 
            return "Forex Mode: Prioritize Session Time (London/NY) & Tick Velocity. Look for Stop Hunts around News."
        else: 
            return "Crypto Mode: Prioritize Open Interest, Funding Rates, and On-Chain Whale Movements."

    def _get(self, endpoint: str, params: Dict = None, base_url: str = None):
        try:
            url = f"{base_url or self.base_url}/{endpoint}"
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
        
    # --- YFINANCE METHODS (Macro/Gold) ---
    def get_dxy_data(self):
        """Fetches recent DXY (Dollar Index) prices for correlation."""
        try:
            dxy = yf.Ticker("DX-Y.NYB") # DXY ticker
            hist = dxy.history(period="5d", interval="1h") # Get last 5 days hourly
            if not hist.empty:
                return hist['Close'].tolist(), hist['Close'].iloc[-1]
            return [], 0.0
        except Exception as e:
            print(f"YFinance DXY Error: {e}")
            return [], 0.0

    def get_gold_price_yfinance(self):
        """Fetches Gold Price via YFinance (GC=F or XAUUSD=X)"""
        try:
            gold = yf.Ticker("GC=F") # Gold Futures
            hist = gold.history(period="1d")
            if not hist.empty:
                return hist['Close'].iloc[-1]
            return 0.0
        except Exception as e:
            print(f"YFinance Gold Error: {e}")
            return 0.0

    # --- CRYPTO FUTURES METHODS ---
    def get_crypto_funding_rate(self, symbol: str):
        symbol_fmt = self._format_symbol(symbol)
        data = self._get("premiumIndex", params={'symbol': symbol_fmt}, base_url=self.futures_url)
        if data:
            # lastFundingRate is string
            return float(data.get('lastFundingRate', 0.0)), float(data.get('markPrice', 0.0))
        return 0.0, 0.0

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
        Combines Price, Order Book, Tape, and Extended Data (DXY/Funding) into a single snapshot.
        """
        snapshot = {
            'symbol': symbol,
            'timestamp': int(time.time() * 1000),
            'order_book': {'bids': [], 'asks': []},
            'recent_trades': [],
            'dxy_closes': [],
            'dxy_price': 0.0,
            'funding_rate': 0.0,
            'mark_price': 0.0
        }

        # 1. Determine Asset Type & Fetch Core Data
        is_gold = "XAU" in symbol or "GOLD" in symbol
        
        if is_gold:
            # Fetch from YFinance
            price = self.get_gold_price_yfinance()
            snapshot['price'] = price
            # Order book for Gold? If using OANDA/AllTick via simple requests if key existed...
            # But we don't have key. We will skip deep order book for Gold unless we have provider.
            # We can rely on DXY correlation mainly.
        else:
            # Crypto
            price = self.get_price(symbol)
            snapshot['price'] = price
            snapshot['order_book'] = self.get_order_book(symbol)
            recent_trades_df = self.get_recent_trades(symbol)
            snapshot['recent_trades'] = recent_trades_df.to_dict('records') if not recent_trades_df.empty else []
            
            # Fetch Funding Rate (Futures)
            funding, mark = self.get_crypto_funding_rate(symbol)
            snapshot['funding_rate'] = funding
            snapshot['mark_price'] = mark

        # 2. Fetch Checks (DXY)
        dxy_closes, dxy_current = self.get_dxy_data()
        snapshot['dxy_closes'] = dxy_closes
        snapshot['dxy_price'] = dxy_current
        
        return snapshot
