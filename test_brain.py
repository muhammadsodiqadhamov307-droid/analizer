import asyncio
from engine.gemini_brain import GeminiAnalyzer
from dotenv import load_dotenv
import os

# Mock the environment for testing if not set
if not os.getenv("GEMINI_API_KEY"):
    print("WARNING: GEMINI_API_KEY not set in environment. Test may fail.")

async def test_brain():
    print("Initializing GeminiAnalyzer...")
    try:
        brain = GeminiAnalyzer()
        print("Analyzer initialized.")
        
        symbol = "BTC/USDT"
        print(f"Requesting analysis for {symbol}...")
        
        # Test direct analysis which should trigger tool usage
        response = brain.analyze_symbol(symbol)
        
        print("\n--- Gemini Response ---")
        print(response)
        print("-----------------------")
        
    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_brain())
