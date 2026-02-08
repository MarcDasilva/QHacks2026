"""
Gradium TTS and STT client wrapper.
"""

import os
import gradium
from typing import AsyncGenerator, Optional


class GradiumVoiceClient:
    """Client for Gradium Text-to-Speech and Speech-to-Text services."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gradium client.
        
        Args:
            api_key: Gradium API key. If not provided, uses GRADIUM_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GRADIUM_API_KEY")
        if not self.api_key:
            raise ValueError("GRADIUM_API_KEY not found in environment variables")
        
        self.client = gradium.client.GradiumClient(api_key=self.api_key)

        # Default voice: Jack (male, British). Same as Gradium sample:
        #   result = await client.tts(setup={"model_name": "default", "voice_id": "m86j6D7UZpGzHsNu", "output_format": "wav"}, text="Hello, world!")
        self.default_voice_id = "m86j6D7UZpGzHsNu"
        self.default_model = "default"
    
    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_format: str = "wav",
        stream: bool = False
    ) -> bytes | AsyncGenerator[bytes, None]:
        """
        Convert text to speech.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use (defaults to Jack)
            output_format: Audio format ("wav", "pcm", "opus")
            stream: If True, returns async generator for streaming audio
        
        Returns:
            Audio bytes or async generator of audio chunks
        """
        voice = voice_id or self.default_voice_id

        setup = {
            "model_name": self.default_model,
            "voice_id": voice,
            "output_format": output_format,
        }

        if stream:
            # Return streaming audio
            return self._stream_tts(text, setup)
        else:
            # Return complete audio
            result = await self.client.tts(setup=setup, text=text)
            return result.raw_data

    async def text_to_speech_with_timestamps(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_format: str = "wav",
    ) -> tuple[bytes, list[dict]]:
        """
        TTS and word-level timestamps for subtitle sync.
        Returns (audio_bytes, timestamps) where timestamps is list of {"text": str, "start_s": float, "stop_s": float}.
        """
        voice = voice_id or self.default_voice_id
        setup = {
            "model_name": self.default_model,
            "voice_id": voice,
            "output_format": output_format,
        }
        result = await self.client.tts(setup=setup, text=text)
        timestamps = []
        if getattr(result, "text_with_timestamps", None):
            for item in result.text_with_timestamps:
                timestamps.append({
                    "text": getattr(item, "text", str(item)) if not isinstance(item, dict) else item.get("text", ""),
                    "start_s": getattr(item, "start_s", 0.0) if not isinstance(item, dict) else item.get("start_s", 0.0),
                    "stop_s": getattr(item, "stop_s", 0.0) if not isinstance(item, dict) else item.get("stop_s", 0.0),
                })
        return result.raw_data, timestamps

    async def _stream_tts(self, text: str, setup: dict) -> AsyncGenerator[bytes, None]:
        """
        Stream TTS audio chunks.
        
        Args:
            text: Text to synthesize
            setup: Gradium setup configuration
        
        Yields:
            Audio chunks as bytes
        """
        stream = await self.client.tts_stream(setup=setup, text=text)
        
        async for audio_chunk in stream.iter_bytes():
            yield audio_chunk
    
    async def speech_to_text(
        self,
        audio_generator: AsyncGenerator[bytes, None],
        input_format: str = "pcm",
        language: str = "en"
    ) -> AsyncGenerator[dict, None]:
        """
        Convert speech to text with streaming.
        
        Args:
            audio_generator: Async generator yielding audio chunks
            input_format: Input audio format ("pcm", "wav", "opus")
            language: Language code - defaults to "en" for English ("en", "fr", "de", "es", "pt")
        
        Yields:
            Dictionary with transcription results and VAD info:
            {
                "type": "text" | "step" | "end_text",
                "text": str (for type="text"),
                "start_s": float (for type="text"),
                "vad": list (for type="step"),
                "inactivity_prob": float (for type="step"),
                ...
            }
        """
        setup = {
            "model_name": self.default_model,
            "input_format": input_format,
            "json_config": {"language": language}
        }
        
        stream = await self.client.stt_stream(setup, audio_generator)

        # Consume _stream and yield text messages; log raw API response for debugging
        async for message in stream._stream:
            print(f"[STT] Gradium API raw: {message}")
            if message.get("type") == "text":
                text = message.get("text", "")
                if text:
                    yield {
                        "type": "text",
                        "text": text,
                        "start_s": message.get("start_s", 0.0),
                        "stream_id": message.get("stream_id"),
                    }
    
    async def get_available_voices(self, include_catalog: bool = True) -> list[dict]:
        """
        Get list of available voices.
        
        Args:
            include_catalog: Whether to include catalog voices
        
        Returns:
            List of voice dictionaries with uid, name, description, etc.
        """
        voices = await gradium.voices.get(self.client)
        return voices
