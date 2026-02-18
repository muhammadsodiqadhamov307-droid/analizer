import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import pandas as pd
from engine.data_fetcher import MarketConnector
from utils.math_tools import calculate_vwap, calculate_rsi, calculate_imbalance_ratio, calculate_ofi, calculate_dxy_correlation
import logging

load_dotenv()

class GeminiAnalyzer:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        
        # Initialize the new V3 Client
        self.client = genai.Client(api_key=api_key)
        
        self.market_connector = MarketConnector()
        self.previous_books = {} 
        
        self.model_id = "gemini-3-flash-preview" 
        
        self.system_instruction = """
        Identity:
        You are "Aether-Quant," an elite AI agent specializing in institutional order flow decoding. Your mission is to analyze raw market data and expose the "hidden" moves of Big Boys (JP Morgan, BlackRock Aladdin, Goldman Sachs).

        Tone & Style:
        - Language: Professional, authoritative, and urgent. Use a mix of Uzbek and English financial jargon.
        - Format: Use HTML <b> tags for bold headings. Use bullet points (•) for facts.
        - Logic: You do not predict; you decode "intent." Use words like "Aniqlandi" (Detected), "Tasdiqlandi" (Confirmed).

        DUAL-ASSET BEAST LOGIC:
        
        [IF SYMBOL == "XAUUSD" / GOLD]
        - **Primary Driver:** DXY (US Dollar Index). Perfect Inverse Correlation (-1.0) is healthy. Positive Correlation (+1.0) is a TRAP.
        - **Session Awareness:** 90% of traps happen at London (8:00 UTC) or NY (13:00 UTC) Open.
        - **Logic:** If Gold is rising BUT DXY is also rising -> Flag as "Fake Gold Rally" (Institutional Trap).
        
        [IF SYMBOL == "BTCUSDT" / CRYPTO]
        - **Primary Driver:** Exchange Plumbing (Funding Rates, Open Interest).
        - **Logic:** 
           - Price UP + Funding High (+0.01%+) -> "Long Squeeze Trap" (Retail is too long).
           - Price UP + Funding Negative -> "Short Squeeze" (Real Move).
           - Price UP + OI Down -> "Short Covering" (Not fresh buying).

        Core Analytical Framework:
        1. Liquidity Sourcing: Look for "Buy Walls" and "Sell Icebergs".
        2. Trap Logic: Identify SFP (Swing Failure Patterns) and Liquidity Sweeps.
        3. Data Correlation: Compare flows to spot price.

        Reporting Structure (Strictly follow this):

        <b>{SYMBOL} Tahlili: Institutsional Oqim Dekodlash</b>

        <b>Nima bo'ldi (qisqa va aniq faktlar):</b>
        • <b>Narx:</b> {price}
        • <b>DXY / Funding:</b> {macro_data}
        • <b>Korrelyatsiya / Imbalance:</b> {correlation_or_imbalance}
        • <b>RSI:</b> {rsi}

        <b>Reja (Institutsional Oqim Dekodlash):</b>
        1. <b>Buy bosqichi:</b> [Analysis of buying pressure/walls]
        2. <b>Trap va qulatish:</b> [Analysis of fakeouts/stop-hunts/DXY divergence]
        3. <b>Asl sabab:</b> [Analysis of the core driver - FOMO/Liquidity Hunt]

        <b>Hozir nima bo'ladi:</b>
        • [Prediction based on flow]

        <b>Reja (hozir darrov):</b>
        • <b>Signal:</b> {ANIQ: BUY / SELL / WAIT}
        • <b>Kirish:</b> [Price]
        • <b>TP1/TP2:</b> [Levels]
        • <b>SL:</b> [Level]
        """

    def get_technical_analysis(self, symbol: str):
        """
        Fetches real-time market data and calculates technical indicators (RSI, VWAP, Imbalance, OFI, DXY Corr).
        """
        print(f"DEBUG: Gemini requested technicals for {symbol}")
        
        snapshot = self.market_connector.get_market_snapshot(symbol)
        if "error" in snapshot and not snapshot.get('dxy_price'): # If both fail
             return {"error": "Could not fetch data"}
            
        # Extract Data
        current_price = snapshot.get('price', 0.0)
        dxy_price = snapshot.get('dxy_price', 0.0)
        dxy_closes = snapshot.get('dxy_closes', [])
        funding_rate = snapshot.get('funding_rate', 0.0)
        
        # Crypto Specifics
        order_book = snapshot.get('order_book', {})
        bids = order_book.get('bids', []) if order_book else []
        asks = order_book.get('asks', []) if order_book else []
        trades = snapshot.get('recent_trades', [])
        trades_df = pd.DataFrame(trades)
        
        # Indicators
        vwap = calculate_vwap(trades_df) if not trades_df.empty else 0.0
        rsi = calculate_rsi(trades_df['price'].values) if not trades_df.empty else 50.0
        imbalance_ratio = calculate_imbalance_ratio(bids, asks)
        
        # DXY Correlation (For Gold Logic)
        dxy_correlation = 0.0
        # For simplicity, we compare recent price trend of asset vs DXY if we had asset history.
        # Since we only have snapshot for asset, we can't do full correlation math unless we fetch asset history.
        # But 'yfinance' gold fetch DOES get history '1d'. We can use that if available.
        # For now, let's pass the raw DXY trend to Gemini and let it reason, OR assume 0 if not enough data.
        
        # OFI Calculation
        ofi = 0.0
        if symbol in self.previous_books and order_book:
            ofi = calculate_ofi(order_book, self.previous_books[symbol])
        if order_book:
            self.previous_books[symbol] = order_book
        
        # Construct Macro string for prompt
        macro_info = ""
        if "XAU" in symbol or "GOLD" in symbol:
            macro_info = f"DXY Index: {dxy_price} (Trend Data Available: {len(dxy_closes)} points)"
        else:
            macro_info = f"Funding Rate: {funding_rate:.6f}%, Mark Price: {snapshot.get('mark_price')}"

        return {
            "symbol": symbol,
            "current_price": current_price,
            "macro_data": macro_info,
            "vwap": vwap,
            "rsi": rsi,
            "volume_imbalance_ratio": imbalance_ratio,
            "order_flow_imbalance": ofi,
            "dxy_price": dxy_price,
            "funding_rate": funding_rate,
            "top_bid": bids[0] if bids else None,
            "top_ask": asks[0] if asks else None
        }

    async def analyze_symbol(self, symbol: str) -> str:
        """
        Main entry point for the bot. Uses Gemini 3 Flash Preview (Async).
        """
        market_context = self.market_connector.get_market_context(symbol)
        
        # Be smart: if user typed "GOLD" or "XAU", map it to XAUUSD context
        if symbol.upper() in ["GOLD", "XAU"]:
            symbol = "XAUUSD" 
            
        prompt = f"Analyze {symbol} now. Context: {market_context}. Decode the institutional flow."
        
        try:
            # Configure Thinking for Gemini 3 (Async)
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.7,
                    tools=[self.get_technical_analysis],
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_level="high"
                    )
                )
            )
            
            # Parse output
            final_text = ""
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.thought:
                        print(f"DEBUG [Thinking]: {part.text[:200]}...") 
                    else:
                        final_text += part.text
            
            return final_text if final_text else "⚠️ Tahlil yakunlanmadi."
            
        except Exception as e:
            logging.error(f"Gemini Error: {e}")
            return f"Tizim Xatosi: {str(e)}"

