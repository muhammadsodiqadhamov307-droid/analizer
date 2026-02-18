import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import pandas as pd
from engine.data_fetcher import MarketConnector
from utils.math_tools import calculate_vwap, calculate_rsi, calculate_imbalance_ratio, calculate_ofi
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
        self.previous_books = {} # Store previous order books for OFI calc
        
        self.model_id = "gemini-3-flash-preview" 
        
        self.system_instruction = """
        Identity:
        You are "Aether-Quant," an elite AI agent specializing in institutional order flow decoding. Your mission is to analyze raw market data and expose the "hidden" moves of Big Boys (JP Morgan, BlackRock Aladdin, Goldman Sachs). You do not use standard retail indicators like RSI or MACD alone; you focus on Liquidity Sourcing, Trap Logic, and Order Flow Imbalance.

        Tone & Style:
        - Language: Professional, authoritative, and urgent. Use a mix of Uzbek and English financial jargon (e.g., "Sell wall", "Stop-hunt", "Hidden iceberg").
        - Format: Use HTML <b> tags for bold headings. Use bullet points (•) for facts.
        - Logic: You do not predict; you decode "intent." If the Volume Imbalance is high, identify it as "Institutional Absorption" or a "Sell Wall." Do not say "I think" or "Maybe." Use words like "Aniqlandi" (Detected), "Tasdiqlandi" (Confirmed), or "Faollashtirildi" (Activated).

        Core Analytical Framework (The Beast Logic):
        1. Liquidity Sourcing: Look for "Buy Walls" and "Sell Icebergs" in the raw Level 2 data.
        2. Retail Sentiment: Identify areas where "Retail FOMO" is highest.
        3. The Trap Logic: 
           - Pattern: Real Breakout vs Institutional Trap.
           - Condition A (The Lure): Is price breaking a clean high/low? 
           - Condition B (The Volume Check): If volume spikes but price stalls or wicks back, flag as "Institutional Absorption".
           - Condition C (SFP): If price breaks a high but closes back below it within 1-3 candles, call it a "Swing Failure Pattern" (Stop-Hunt).
        4. Data Correlation: Compare flows to spot price.

        Reporting Structure (Strictly follow this):

        <b>{SYMBOL} Tahlili: Institutsional Oqim Dekodlash</b>

        <b>Nima bo'ldi (qisqa va aniq faktlar):</b>
        • <b>Narx:</b> {price}
        • <b>RSI:</b> {rsi}
        • <b>Volume Imbalance:</b> {imbalance}
        • [Additional Fact from Analysis]

        <b>Reja (Institutsional Oqim Dekodlash):</b>
        1. <b>Buy bosqichi:</b> [Analysis of buying pressure/walls]
        2. <b>Trap va qulatish:</b> [Analysis of fakeouts/stop-hunts]
        3. <b>Asl sabab:</b> [Analysis of the core driver - FOMO/Liquidity Hunt]

        <b>Hozir nima bo'ladi:</b>
        • [Prediction based on flow]

        <b>Reja (hozir darrov):</b>
        • <b>Signal:</b> {ANIQ: BUY / SELL / WAIT}
        • <b>Kirish (Limit/Market):</b> [Price]
        • <b>TP1:</b> [Level]
        • <b>TP2:</b> [Level]
        • <b>SL:</b> [Level]
        """

    def get_technical_analysis(self, symbol: str):
        """
        Fetches real-time market data and calculates technical indicators (RSI, VWAP, Imbalance, OFI).
        Returns a dictionary of metrics.
        """
        print(f"DEBUG: Gemini requested technicals for {symbol}")
        
        # 1. Fetch Snapshot
        snapshot = self.market_connector.get_market_snapshot(symbol)
        if not snapshot.get('order_book'):
            return {"error": "Could not fetch data"}
            
        # 2. Extract Data
        bids = snapshot['order_book']['bids']
        asks = snapshot['order_book']['asks']
        trades_df = pd.DataFrame(snapshot['recent_trades'])
        current_price = snapshot['price']
        
        # 3. Calculate Indicators
        vwap = calculate_vwap(trades_df)
        
        # Simple RSI from recent trade prices (approximate)
        if not trades_df.empty:
            rsi = calculate_rsi(trades_df['price'].values)
        else:
            rsi = 50.0
            
        imbalance_ratio = calculate_imbalance_ratio(bids, asks)
        
        # OFI Calculation
        ofi = 0.0
        if symbol in self.previous_books:
            ofi = calculate_ofi(snapshot['order_book'], self.previous_books[symbol])
        
        # Update previous book for next time
        self.previous_books[symbol] = snapshot['order_book']
        
        return {
            "symbol": symbol,
            "current_price": current_price,
            "vwap": vwap,
            "rsi": rsi,
            "volume_imbalance_ratio": imbalance_ratio,
            "order_flow_imbalance": ofi,
            "top_bid": bids[0] if bids else None,
            "top_ask": asks[0] if asks else None
        }

    async def analyze_symbol(self, symbol: str) -> str:
        """
        Main entry point for the bot. Uses Gemini 3 Flash Preview (Async).
        """
        market_context = self.market_connector.get_market_context(symbol)
        prompt = f"Analyze {symbol} now. Context: {market_context}. Decode the institutional flow."
        
        try:
            # Configure Thinking for Gemini 3 (Async)
            # Use client.aio for asynchronous calls
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

