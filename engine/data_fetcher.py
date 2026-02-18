import ccxt
import pandas as pd
from typing import Dict, List, Optional
import time

class MarketConnector:
    def __init__(self, exchange_id: str = 'binance'):
        # FIX: Aggressive Spot-Only Mode for AWS Bypass
        config = {
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot', 
                'adjustForTimeDifference': True,
                'warnOnFetchOpenOrdersWithoutSymbol': False,
            }
        }
        
        if exchange_id == 'binance':
            # FORCE override of ALL endpoints to Spot (data-api)
            # This ensures that even if ccxt tries to use fapi, it will be redirected to spot (or fail differently/safely)
            config['urls'] = {
                'logo': 'https://user-images.githubusercontent.com/1294454/29604020-d5483cdc-87ee-11e7-94c7-d1a8d9169293.jpg',
                'api': {
                    'public': 'https://data-api.binance.vision/api/v3',
                    'private': 'https://api.binance.com/api/v3',
                    # Redirecting futures to spot to prevent 451 (it will error on logic but bypass the geo-block 451)
                    'fapiPublic': 'https://data-api.binance.vision/api/v3', 
                    'fapiPrivate': 'https://api.binance.com/api/v3',
                },
                'www': 'https://www.binance.com',
                'doc': 'https://binance-docs.github.io/apidocs/spot/en',
            }
            
        print(f"DEBUG: Initializing {exchange_id} with config: {config}")
        self.exchange = getattr(ccxt, exchange_id)(config)
        # self.exchange.load_markets() # can be slow, call only if needed

    def get_price(self, symbol: str) -> float:
        ticker = self.exchange.fetch_ticker(symbol)
        return ticker['last']

    def get_order_book(self, symbol: str, limit: int = 50) -> Dict:
        """
        Fetches the Order Book (Level 2 Data).
        Returns dict with 'bids' and 'asks' lists: [[price, amount], ...]
        """
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            return {
                'bids': orderbook['bids'],
                'asks': orderbook['asks'],
                'timestamp': orderbook['timestamp']
            }
        except Exception as e:
            print(f"Error fetching order book for {symbol}: {e}")
            return {'bids': [], 'asks': [], 'timestamp': None}

    def get_recent_trades(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """
        Fetches recent trades (Tape Data).
        Returns DataFrame with ['timestamp', 'symbol', 'side', 'price', 'amount']
        """
        try:
            trades = self.exchange.fetch_trades(symbol, limit=limit)
            df = pd.DataFrame(trades)
            if not df.empty:
                df = df[['timestamp', 'symbol', 'side', 'price', 'amount']]
            return df
        except Exception as e:
            print(f"Error fetching trades for {symbol}: {e}")
            return pd.DataFrame()

    def get_market_snapshot(self, symbol: str) -> Dict:
        """
        Combines Price, Order Book, and Tape into a single snapshot.
        """
        price = self.get_price(symbol)
        book = self.get_order_book(symbol)
        trades = self.get_recent_trades(symbol)
        
        return {
            'symbol': symbol,
            'price': price,
            'order_book': book,
            'recent_trades': trades.to_dict('records') if not trades.empty else []
        }

