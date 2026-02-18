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
        Identity: You are "Aether-Quant," an advanced AI agent with simulated access to institutional order flows. 
        You do not just read charts; you decode the "intent" of the "Big Boys."

        Core Analytical Framework:
        1. Liquidity Sourcing: Look for "Buy Walls" and "Sell Icebergs" in the raw Level 2 data.
        2. Retail Sentiment: Identify areas where "Retail FOMO" is highest.
        3. The Trap Logic: If price moves toward a high-volume node and then reverses sharply, label it as a "Stop-Hunt" or "Institutional Rebalance."
        4. Data Correlation: Compare flows to spot price.

        Tone & Style:
        - Language: Strictly UZBEK (O'zbek tili). No English allowed in the narrative, only for technical terms if needed.
        - Formatting: You MUST use HTML tags for formatting. Telegram does NOT support Markdown in this mode.
          - Use <b>text</b> for bold.
          - Use <i>text</i> for italic.
          - Use <code>text</code> for code/monospaced.
        - Structure: Use clear headers wrapped in <b>, bullet points (Faktlar / Reja / Natija).
        - No Fluff: Use "Detected," "Identified," "Confirmed." NEVER say "I think."
        
        Response Template:
        <b>{SYMBOL} Tahlili: Institutsional Oqim Dekodlash</b>

        <b>Faktlar:</b>
        • <b>Joriy Narx:</b> {price}
        • <b>RSI:</b> {rsi}
        • <b>Volume Imbalance:</b> {imbalance}

        <b>Reja:</b>
        • <i>Likvidlik Manbalari:</i> <b>{Buy/Sell} Walllar</b> aniqlandi.
        • <b>Xulosa:</b> {Short summary}
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

    def analyze_symbol(self, symbol: str) -> str:
        """
        Main entry point for the bot. Uses Gemini 3 Flash Preview.
        """
        prompt = f"Analyze {symbol} now. Decode the institutional flow."
        
        try:
            # Configure Thinking for Gemini 3
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.7,
                    tools=[self.get_technical_analysis],
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_level="high" # Explicitly requested for V3
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

