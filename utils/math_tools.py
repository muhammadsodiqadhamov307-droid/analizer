import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

def calculate_vwap(df: pd.DataFrame) -> float:
    """
    Calculates Volume Weighted Average Price (VWAP).
    Formula: Sum(Price * Volume) / Sum(Volume)
    """
    if df.empty:
        return 0.0
    
    # Ensure columns exist (assuming 'price' and 'amount' from ccxt trades)
    if 'price' not in df.columns or 'amount' not in df.columns:
        return 0.0
        
    v = df['amount'].values
    p = df['price'].values
    
    return np.sum(p * v) / np.sum(v)

def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    Calculates Relative Strength Index (RSI).
    """
    if len(prices) < period + 1:
        return 50.0  # Default neutral if not enough data
        
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    
    if down == 0:
        return 100.0
        
    rs = up / down
    rsi = 100.0 - (100.0 / (1.0 + rs))
    
    # Smooth updates (Wilder's Smoothing usually used, but simple scalar for now)
    # For a simple bot, this scalar RSI is often sufficient. 
    # Can expand to full series if needed.
    
    return rsi

def calculate_imbalance_ratio(bids: List[List[float]], asks: List[List[float]], depth: int = 10) -> float:
    """
    Calculates Volume Imbalance Ratio.
    Ratio = Total Ask Volume / Total Bid Volume (for sell wall detection).
    Returns ratio. > 3.0 implies heavy sell pressure (Sell Wall).
    < 0.33 implies heavy buy pressure (Buy Wall).
    """
    # ccxt order book format: [[price, amount], ...]
    if not bids or not asks:
        return 1.0
        
    bid_vol = sum(b[1] for b in bids[:depth])
    ask_vol = sum(a[1] for a in asks[:depth])
    
    if bid_vol == 0:
        return 999.0 # Max sell pressure
        
    return ask_vol / bid_vol

def calculate_ofi(current_book: Dict, previous_book: Dict) -> float:
    """
    Calculates Order Flow Imbalance (OFI).
    Formula: Delta OFI = (BidVol_t - BidVol_{t-1}) - (AskVol_t - AskVol_{t-1})
    
    This requires the 'top of book' or aggregate volume at best bid/ask.
    For simplicity, we uses total volume of the top 5 levels to capture 'intent'.
    """
    if not previous_book or not current_book:
        return 0.0
        
    depth = 5
    
    cur_bid_vol = sum(b[1] for b in current_book['bids'][:depth])
    cur_ask_vol = sum(a[1] for a in current_book['asks'][:depth])
    
    prev_bid_vol = sum(b[1] for b in previous_book['bids'][:depth])
    prev_ask_vol = sum(a[1] for a in previous_book['asks'][:depth])
    
    delta_bid = cur_bid_vol - prev_bid_vol
    delta_ask = cur_ask_vol - prev_ask_vol
    
    return delta_bid - delta_ask

def calculate_dxy_correlation(gold_prices: List[float], dxy_prices: List[float]) -> float:
    """
    Calculates the Pearson correlation between Gold and DXY.
    -1.0 means perfect inverse (Healthy Gold move).
    +1.0 means moving together (Institutional Trap/Danger).
    """
    if not gold_prices or not dxy_prices or len(gold_prices) != len(dxy_prices):
        return 0.0
        
    try:
        series_gold = pd.Series(gold_prices)
        series_dxy = pd.Series(dxy_prices)
        correlation = series_gold.corr(series_dxy)
        return round(correlation, 3) if not pd.isna(correlation) else 0.0
    except Exception as e:
        print(f"Correlation Error: {e}")
        return 0.0

