"""Test Gradium API key validity."""
import os
import asyncio
from dotenv import load_dotenv
import gradium

async def test_key():
    load_dotenv()
    api_key = os.getenv("GRADIUM_API_KEY")
    
    print(f"API Key: {api_key[:20]}...")
    
    try:
        client = gradium.client.GradiumClient(api_key=api_key)
        print("✅ Client created successfully")
        
        # Test TTS (simpler than STT)
        setup = {
            "model_name": "default",
            "voice_id": "YTpq7expH9539ERJ",  # Emma
            "output_format": "wav"
        }
        
        print("Testing TTS...")
        result = await client.tts(setup=setup, text="Hello world")
        print(f"✅ TTS succeeded! Audio data size: {len(result.raw_data)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_key())
    exit(0 if success else 1)
