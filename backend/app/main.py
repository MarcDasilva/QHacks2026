"""
FastAPI backend for CRM Analytics Agent with streaming support
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
import json
import asyncio
from typing import AsyncGenerator
import sys
from pathlib import Path
import base64

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.agent import CRMAnalyticsAgent
from agent.gemini_client import GeminiAgent
from agent.gradium_client import GradiumVoiceClient

app = FastAPI(title="CRM Analytics API")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent (will use GEMINI_API_KEY from .env)
try:
    agent = CRMAnalyticsAgent()
except Exception as e:
    print(f"Warning: Could not initialize agent: {e}")
    agent = None

# Initialize Gradium voice client (will use GRADIUM_API_KEY from .env)
try:
    gradium_client = GradiumVoiceClient()
    print("✅ Gradium voice client initialized")
except Exception as e:
    print(f"Warning: Could not initialize Gradium client: {e}")
    gradium_client = None


class ChatRequest(BaseModel):
    message: str
    mode: str = "auto"  # "auto", "deep_analysis", or "chat"


class ChatMessage(BaseModel):
    type: str  # "thought", "plan", "data", "navigation", "answer", "error"
    content: str
    data: dict = None


async def stream_simple_chat(user_question: str) -> AsyncGenerator[str, None]:
    """
    Stream simple chatbot responses (no data analysis)
    """
    try:
        yield f"data: {json.dumps({'type': 'start', 'content': 'Thinking...'})}\n\n"
        await asyncio.sleep(0.1)
        
        # Get simple chat response
        response = agent.gemini_agent.simple_chat(user_question)
        
        # Send response as a chat message (not analysis)
        yield f"data: {json.dumps({'type': 'chat', 'content': response})}\n\n"
        
        # Send completion signal
        yield f"data: {json.dumps({'type': 'complete', 'content': 'Done'})}\n\n"
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
        yield f"data: {json.dumps({'type': 'complete', 'content': 'Stream ended'})}\n\n"


async def stream_agent_response(user_question: str) -> AsyncGenerator[str, None]:
    """
    Stream agent responses as Server-Sent Events
    Yields messages in SSE format
    """
    try:
        # Send initial acknowledgment
        yield f"data: {json.dumps({'type': 'start', 'content': 'Processing your question...'})}\n\n"
        await asyncio.sleep(0.1)
        
        # STAGE 1: Planning
        yield f"data: {json.dumps({'type': 'thought', 'content': '🤔 Analyzing your question and planning which data to use...'})}\n\n"
        await asyncio.sleep(0.5)
        
        # Get catalog and frequency preview
        catalog_summary = agent.catalog_summary
        frequency_preview = agent._get_frequency_preview()
        
        # Generate plan
        plan = agent.gemini_agent.plan_stage(
            user_question=user_question,
            catalog_summary=catalog_summary,
            frequency_data_preview=frequency_preview
        )
        
        # Send plan to frontend
        yield f"data: {json.dumps({'type': 'plan', 'content': 'Selected data products:', 'data': {'plan': plan}})}\n\n"
        await asyncio.sleep(0.3)
        
        # STAGE 2: Fetch data
        product_ids = [item["product"] for item in plan]
        
        for item in plan:
            product_name = item["product"]
            yield f"data: {json.dumps({'type': 'thought', 'content': f'📊 Loading {product_name}...'})}\n\n"
            await asyncio.sleep(0.2)
        
        # Determine which navigation is needed
        navigation_mapping = {
            "frequency_over_time": "/dashboard/analytics/frequency",
            "backlog_ranked_list": "/dashboard/analytics/backlog",
            "backlog_distribution": "/dashboard/analytics/backlog",
            "priority_quadrant": "/dashboard/analytics/priority-quadrant",
            "geographic_hot_spots": "/dashboard/analytics/geographic",
            "time_to_close": "/dashboard/analytics/population",
        }
        
        # Navigate to relevant pages
        navigated_pages = set()
        for product_id in product_ids:
            for key, url in navigation_mapping.items():
                if key in product_id:
                    if url not in navigated_pages:
                        yield f"data: {json.dumps({'type': 'navigation', 'content': f'Navigating to {key} view', 'data': {'url': url}})}\n\n"
                        navigated_pages.add(url)
                        await asyncio.sleep(0.5)
        
        # Load data
        fetched_data_summaries = agent.data_loader.load_multiple_summaries(product_ids)
        
        if not fetched_data_summaries:
            # Fall back to loading raw data
            yield f"data: {json.dumps({'type': 'thought', 'content': 'Loading raw data (no summaries available)...'})}\n\n"
            await asyncio.sleep(0.2)
            fetched_data_summaries = agent.data_loader.load_multiple_products(product_ids)
        
        # STAGE 3: Analysis
        yield f"data: {json.dumps({'type': 'thought', 'content': '🧠 Analyzing data and generating insights...'})}\n\n"
        await asyncio.sleep(0.5)
        
        # Generate final answer
        answer_data = agent.gemini_agent.analysis_stage(
            user_question=user_question,
            access_log=plan,
            fetched_data=fetched_data_summaries
        )
        
        # Send final answer
        yield f"data: {json.dumps({'type': 'answer', 'content': answer_data['answer'], 'data': {'rationale': answer_data.get('rationale', []), 'key_metrics': answer_data.get('key_metrics', [])}})}\n\n"
        
        # Send completion signal
        yield f"data: {json.dumps({'type': 'complete', 'content': 'Analysis complete'})}\n\n"
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
        # Ensure stream closes even after error
        yield f"data: {json.dumps({'type': 'complete', 'content': 'Stream ended'})}\n\n"


@app.get("/")
async def root():
    return {"message": "CRM Analytics API", "status": "running"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent_initialized": agent is not None,
        "gradium_initialized": gradium_client is not None
    }


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat responses using Server-Sent Events
    Supports two modes: deep_analysis and chat
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized. Check GEMINI_API_KEY in .env")
    
    # Determine mode
    mode = request.mode
    if mode == "auto":
        # Check if "analysis" keyword is in the message
        mode = "deep_analysis" if "analysis" in request.message.lower() else "chat"
    
    # Select appropriate stream handler
    if mode == "deep_analysis":
        stream_func = stream_agent_response(request.message)
    else:
        stream_func = stream_simple_chat(request.message)
    
    return StreamingResponse(
        stream_func,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Non-streaming chat endpoint (for testing)
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    try:
        result = agent.query(request.message, verbose=False)
        return {
            "answer": result["answer"],
            "plan": result["plan"],
            "key_metrics": result.get("key_metrics", []),
            "rationale": result.get("rationale", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TTSRequest(BaseModel):
    text: str
    voice_id: str = "YTpq7expH9539ERJ"  # Default to Emma voice
    output_format: str = "wav"


@app.post("/api/voice/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech using Gradium TTS
    Returns audio file as WAV
    """
    if not gradium_client:
        raise HTTPException(status_code=500, detail="Gradium client not initialized. Check GRADIUM_API_KEY in .env")
    
    try:
        # Generate audio
        audio_bytes = await gradium_client.text_to_speech(
            text=request.text,
            voice_id=request.voice_id,
            output_format=request.output_format
        )
        
        # Determine content type
        content_type_mapping = {
            "wav": "audio/wav",
            "pcm": "audio/pcm",
            "opus": "audio/ogg"
        }
        content_type = content_type_mapping.get(request.output_format, "audio/wav")
        
        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.output_format}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@app.post("/api/voice/tts/stream")
async def text_to_speech_stream(request: TTSRequest):
    """
    Convert text to speech using Gradium TTS with streaming
    Returns audio chunks as they're generated
    """
    if not gradium_client:
        raise HTTPException(status_code=500, detail="Gradium client not initialized. Check GRADIUM_API_KEY in .env")
    
    try:
        async def generate_audio():
            audio_stream = await gradium_client.text_to_speech(
                text=request.text,
                voice_id=request.voice_id,
                output_format=request.output_format,
                stream=True
            )
            
            async for chunk in audio_stream:
                yield chunk
        
        # Determine content type
        content_type_mapping = {
            "wav": "audio/wav",
            "pcm": "audio/pcm",
            "opus": "audio/ogg"
        }
        content_type = content_type_mapping.get(request.output_format, "audio/wav")
        
        return StreamingResponse(
            generate_audio(),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.output_format}",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS streaming error: {str(e)}")


class STTRequest(BaseModel):
    audio_data: str  # Base64 encoded audio
    input_format: str = "webm"  # "webm", "wav", "pcm", or "opus"


class STTStreamChunk(BaseModel):
    audio_chunk: str  # Base64 encoded audio chunk
    is_final: bool = False  # True when recording is complete
    input_format: str = "wav"


# Global storage for streaming STT sessions
active_stt_sessions = {}


@app.post("/api/voice/stt/stream")
async def speech_to_text_stream(request: STTStreamChunk):
    """
    Stream speech-to-text with real-time transcription
    Client sends audio chunks as they're recorded
    Returns SSE stream with partial transcripts
    """
    if not gradium_client:
        raise HTTPException(status_code=500, detail="Gradium client not initialized. Check GRADIUM_API_KEY in .env")
    
    session_id = request.audio_chunk[:20]  # Use first 20 chars as session ID
    
    async def generate_transcription():
        try:
            # Decode audio chunk
            audio_data = base64.b64decode(request.audio_chunk)
            print(f"🎤 STT stream chunk: format={request.input_format}, size={len(audio_data)} bytes, final={request.is_final}")
            
            # Create async generator for this chunk
            async def audio_generator():
                chunk_size = 3840 if request.input_format == "pcm" else len(audio_data)
                for i in range(0, len(audio_data), chunk_size):
                    yield audio_data[i:i + chunk_size]
            
            # Process STT stream
            async for message in gradium_client.speech_to_text(
                audio_generator=audio_generator(),
                input_format=request.input_format,
                language="en"
            ):
                if message["type"] == "text":
                    text = message.get("text", "")
                    print(f"📝 Stream transcript: {text}")
                    yield f"data: {json.dumps({'type': 'transcript', 'text': text, 'is_final': request.is_final})}\n\n"
            
            if request.is_final:
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                
        except Exception as e:
            print(f"❌ STT stream error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_transcription(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/voice/stt")
async def speech_to_text(request: STTRequest):
    """
    Convert speech to text using Gradium STT
    Accepts base64-encoded audio data
    """
    if not gradium_client:
        raise HTTPException(status_code=500, detail="Gradium client not initialized. Check GRADIUM_API_KEY in .env")
    
    try:
        # Decode base64 audio data
        audio_data = base64.b64decode(request.audio_data)
        print(f"🎤 STT request: format={request.input_format}, size={len(audio_data)} bytes")
        
        # Map input format (Gradium accepts pcm, wav, opus)
        input_format = request.input_format
        if input_format == "webm":
            input_format = "opus"  # WebM uses Opus codec
        
        # Create async generator for audio chunks
        async def audio_generator():
            # For PCM: 1920 samples per chunk (80ms at 24kHz)
            # 1920 samples * 2 bytes/sample = 3840 bytes per chunk
            chunk_size = 3840 if input_format == "pcm" else len(audio_data)
            
            for i in range(0, len(audio_data), chunk_size):
                yield audio_data[i:i + chunk_size]
        
        # Process STT
        transcription_parts = []
        final_transcript = ""
        
        print(f"🔄 Starting Gradium STT stream...")
        async for message in gradium_client.speech_to_text(
            audio_generator=audio_generator(),
            input_format=input_format,
            language="en"
        ):
            if message["type"] == "text":
                transcription_parts.append(message["text"])
                final_transcript = " ".join(transcription_parts)
                print(f"📝 Transcription chunk: {message['text']}")
        
        print(f"✅ STT complete: {final_transcript}")
        return {
            "transcript": final_transcript,
            "success": True
        }
    
    except Exception as e:
        print(f"❌ STT error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"STT error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
