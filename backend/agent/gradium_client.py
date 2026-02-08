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
        
        # Default voice settings
        self.default_voice_id = "YTpq7expH9539ERJ"  # Emma - pleasant female US voice
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
            voice_id: Voice ID to use (defaults to Emma)
            output_format: Audio format ("wav", "pcm", "opus")
            stream: If True, returns async generator for streaming audio
        
        Returns:
            Audio bytes or async generator of audio chunks
        """
        voice = voice_id or self.default_voice_id
        
        setup = {
            "model_name": self.default_model,
            "voice_id": voice,
            "output_format": output_format
        }
        
        if stream:
            # Return streaming audio
            return self._stream_tts(text, setup)
        else:
            # Return complete audio
            result = await self.client.tts(setup=setup, text=text)
            return result.raw_data
    
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
            language: Language code ("en", "fr", "de", "es", "pt")
        
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
        
        async for message in stream._stream:
            # Process different message types
            if message.get("type") == "text":
                yield {
                    "type": "text",
                    "text": message.get("text", ""),
                    "start_s": message.get("start_s", 0.0),
                    "stream_id": message.get("stream_id")
                }
            elif message.get("type") == "step":
                # VAD (Voice Activity Detection)
                vad_info = message.get("vad", [])
                inactivity_prob = vad_info[2].get("inactivity_prob", 0.0) if len(vad_info) > 2 else 0.0
                yield {
                    "type": "step",
                    "vad": vad_info,
                    "inactivity_prob": inactivity_prob,
                    "step_idx": message.get("step_idx", 0),
                    "step_duration_s": message.get("step_duration_s", 0.08),
                    "total_duration_s": message.get("total_duration_s", 0.0)
                }
            elif message.get("type") == "end_text":
                yield {
                    "type": "end_text",
                    "stop_s": message.get("stop_s", 0.0),
                    "stream_id": message.get("stream_id")
                }
            elif message.get("type") == "end_of_stream":
                yield {
                    "type": "end_of_stream"
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
