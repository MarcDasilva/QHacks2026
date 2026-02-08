"""
FastAPI backend for CRM Analytics Agent with streaming support
"""

from pathlib import Path
import sys
import os
import ssl

# Ensure backend root is on path
_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

# Use certifi CA bundle for SSL (fixes CERTIFICATE_VERIFY_FAILED on macOS with Python from python.org)
# Set before any import that uses aiohttp/ssl (Gradium uses aiohttp which creates SSL context at import time).
import certifi
_cert_file = certifi.where()
os.environ["SSL_CERT_FILE"] = _cert_file
os.environ["REQUESTS_CA_BUNDLE"] = _cert_file
_orig_create_default_context = ssl.create_default_context
def _ssl_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=None, capath=None, cadata=None):
    if cafile is None and capath is None and cadata is None:
        return _orig_create_default_context(purpose=purpose, cafile=_cert_file, capath=capath, cadata=cadata)
    return _orig_create_default_context(purpose=purpose, cafile=cafile, capath=capath, cadata=cadata)
ssl.create_default_context = _ssl_default_context
ssl._create_default_https_context = lambda: _ssl_default_context()

from dotenv import load_dotenv
_env_file = _backend_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    load_dotenv()  # fallback to cwd

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from datetime import datetime

# Optional: report generator (reportlab + reporting package)
# backend root is already on sys.path; reportlab must be installed (pip install reportlab)
_report_generator_error: str | None = None
try:
    from reporting.report_generator import ReportGenerator
except Exception as e:
    import logging
    _report_generator_error = str(e)
    logging.getLogger("uvicorn.error").warning(
        "Report generator unavailable (install reportlab?): %s", _report_generator_error
    )
    ReportGenerator = None  # type: ignore[misc, assignment]
import json
import asyncio
from typing import AsyncGenerator
import base64

from agent.agent import CRMAnalyticsAgent
from agent.gemini_client import GeminiAgent

# Optional: cluster predictor (needs DATABASE_URL + sentence-transformers)
try:
    from app.ai.cluster_predictor import (
        get_cluster_labels,
        predict_cluster as sync_predict_cluster,
    )
except Exception:
    sync_predict_cluster = None  # type: ignore[misc, assignment]
    get_cluster_labels = None  # type: ignore[misc, assignment]

try:
    from app.db.connection import get_conn
except Exception:
    get_conn = None  # type: ignore[misc, assignment]

# Optional: Gradium voice (TTS/STT); app runs without it if package unavailable
try:
    from agent.gradium_client import GradiumVoiceClient
except ImportError:
    GradiumVoiceClient = None  # type: ignore[misc, assignment]

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
agent = None
try:
    if not os.getenv("GEMINI_API_KEY"):
        print("Warning: GEMINI_API_KEY not set. Add it to backend/.env to enable chat.")
    else:
        agent = CRMAnalyticsAgent()
        print("✅ Agent (Gemini) initialized")
except Exception as e:
    print(f"Warning: Could not initialize agent: {e}")
    agent = None

# Initialize Gradium voice client (will use GRADIUM_API_KEY from .env)
gradium_client = None
if GradiumVoiceClient is not None:
    try:
        gradium_client = GradiumVoiceClient()
        print("✅ Gradium voice client initialized")
    except Exception as e:
        print(f"Warning: Could not initialize Gradium client: {e}")
else:
    print("Gradium not installed; voice endpoints disabled. pip install gradium when available.")

# True after the user has entered analysis mode at least once (used to gate the "deep research" message in chat)
_has_entered_analysis_mode = False


class ChatRequest(BaseModel):
    message: str
    mode: str = "auto"  # "auto", "deep_analysis", or "chat"


class ChatMessage(BaseModel):
    type: str  # "thought", "plan", "data", "navigation", "answer", "error"
    content: str
    data: dict = None


async def stream_analysis_ack(user_question: str) -> AsyncGenerator[str, None]:
    """
    When user asks for analysis: return short ack from Gemini, then frontend shifts to cluster dashboard.
    APIs are called as normal; response is just "Awesome, lets do it" then complete.
    """
    try:
        yield f"data: {json.dumps({'type': 'start', 'content': 'Thinking...'})}\n\n"
        await asyncio.sleep(0.1)
        yield f"data: {json.dumps({'type': 'chat', 'content': 'Awesome, lets do it'})}\n\n"
        yield f"data: {json.dumps({'type': 'complete', 'content': 'Done'})}\n\n"
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
        yield f"data: {json.dumps({'type': 'complete', 'content': 'Stream ended'})}\n\n"


async def stream_simple_chat(user_question: str) -> AsyncGenerator[str, None]:
    """
    Stream simple chatbot responses (no data analysis).
    When user follows up after "what are you interested in?", run cluster predictor
    and emit parent/child cluster so the frontend can highlight that cluster.
    Only says the "deep research" message if the user has already entered analysis mode at least once.
    """
    try:
        yield f"data: {json.dumps({'type': 'start', 'content': 'Thinking...'})}\n\n"
        await asyncio.sleep(0.1)

        # Only say the "deep research" message if user has previously entered analysis mode
        if _has_entered_analysis_mode:
            response = (
                "That's a great idea, I'm going to enter deep research and generate "
                "a report based on my findings."
            )
            yield f"data: {json.dumps({'type': 'chat', 'content': response})}\n\n"
            yield f"data: {json.dumps({'type': 'glow_on'})}\n\n"

        # Only run BERT/sentence-transformers cluster predictor when user has entered analysis mode
        if _has_entered_analysis_mode and sync_predict_cluster and user_question.strip():
            try:
                # Use Gemini to extract search keywords from the user message before embedding search
                search_query = user_question.strip()
                if agent and agent.gemini_agent:
                    search_query = await asyncio.to_thread(
                        agent.gemini_agent.extract_search_keywords,
                        user_question.strip(),
                        "matching against municipal service request cluster labels (e.g. Facility Booking, City Hall Room Booking)",
                    )
                result = await asyncio.to_thread(
                    sync_predict_cluster,
                    search_query,
                )
                yield f"data: {json.dumps({'type': 'cluster_prediction', 'data': {'parent_cluster_id': result['parent_cluster_id'], 'child_cluster_id': result['child_cluster_id'], 'parent_similarity': result['parent_similarity'], 'child_similarity': result['child_similarity']}})}\n\n"
                # Short message: which cluster we opened, record count, then that we're investigating
                parent_id = result.get("parent_cluster_id")
                child_id = result.get("child_cluster_id")
                record_count = result.get("record_count", 0)
                parent_label = result.get("parent_label") or (f"cluster {parent_id}" if parent_id is not None else None)
                child_label = result.get("child_label") or (f"sub-cluster {child_id}" if child_id is not None else None)
                count_phrase = f" — {record_count} record{'s' if record_count != 1 else ''} found"
                if parent_label and child_label:
                    msg = f"I've opened \"{parent_label}\" (sub-cluster \"{child_label}\"){count_phrase}. I'm going to further investigate these records for context."
                elif parent_label:
                    msg = f"I've opened \"{parent_label}\"{count_phrase}. I'm going to further investigate these records for context."
                else:
                    msg = f"I've opened the cluster view{count_phrase}. I'm going to further investigate these records for context."
                yield f"data: {json.dumps({'type': 'chat', 'content': msg})}\n\n"
            except Exception as pred_err:
                import logging
                logging.getLogger("uvicorn.error").warning("Cluster prediction failed: %s", pred_err)
        elif not _has_entered_analysis_mode and agent and user_question.strip():
            # Regular LLM call (no BERT load) when analysis mode not yet entered
            try:
                response_text = await asyncio.to_thread(
                    agent.gemini_agent.simple_chat,
                    user_question.strip(),
                )
                if response_text:
                    yield f"data: {json.dumps({'type': 'chat', 'content': response_text})}\n\n"
            except Exception as chat_err:
                import logging
                logging.getLogger("uvicorn.error").warning("Simple chat failed: %s", chat_err)

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
        navigated_view_names = []
        key_to_display = {
            "frequency_over_time": "Frequency",
            "backlog_ranked_list": "Backlog",
            "backlog_distribution": "Backlog",
            "priority_quadrant": "Priority Quadrant",
            "geographic_hot_spots": "Geographic Hot Spots",
            "time_to_close": "Time to Close",
        }
        for product_id in product_ids:
            for key, url in navigation_mapping.items():
                if key in product_id:
                    if url not in navigated_pages:
                        yield f"data: {json.dumps({'type': 'navigation', 'content': f'Navigating to {key} view', 'data': {'url': url}})}\n\n"
                        navigated_pages.add(url)
                        display_name = key_to_display.get(key, key.replace("_", " ").title())
                        if display_name not in navigated_view_names:
                            navigated_view_names.append(display_name)
                        await asyncio.sleep(0.5)

        # After navigation: discuss where we went and that we're investigating
        if navigated_view_names:
            views_str = " and ".join(navigated_view_names)
            yield f"data: {json.dumps({'type': 'chat', 'content': f'I\'ve opened the {views_str} view. I\'m going to further investigate my records.'})}\n\n"
            await asyncio.sleep(0.2)
        
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
        import logging
        logging.getLogger("uvicorn.error").warning("POST /api/chat/stream: Agent not initialized. Set GEMINI_API_KEY in backend/.env")
        raise HTTPException(status_code=500, detail="Agent not initialized. Check GEMINI_API_KEY in backend/.env")
    
    # Determine mode
    mode = request.mode
    if mode == "auto":
        # Check if "analysis" keyword is in the message
        mode = "deep_analysis" if "analysis" in request.message.lower() else "chat"
    
    # Select appropriate stream handler (analysis returns short ack; frontend then shows cluster dashboard)
    if mode == "deep_analysis":
        global _has_entered_analysis_mode
        _has_entered_analysis_mode = True
        stream_func = stream_analysis_ack(request.message)
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


class ClusterPredictRequest(BaseModel):
    message: str


class AnalyticsVisitRequest(BaseModel):
    parent_cluster_id: int
    child_cluster_id: int


# Product IDs that have an analytics dashboard page (from README / navigation_mapping)
ANALYTICS_PRODUCT_IDS = {
    "frequency_over_time",
    "backlog_ranked_list",
    "backlog_distribution",
    "priority_quadrant",
    "geographic_hot_spots",
    "time_to_close",
}
NAVIGATION_MAPPING = {
    "frequency_over_time": "/dashboard/analytics/frequency",
    "backlog_ranked_list": "/dashboard/analytics/backlog",
    "backlog_distribution": "/dashboard/analytics/backlog",
    "priority_quadrant": "/dashboard/analytics/priority-quadrant",
    "geographic_hot_spots": "/dashboard/analytics/geographic",
    "time_to_close": "/dashboard/analytics/population",
}
KEY_TO_DISPLAY = {
    "frequency_over_time": "Frequency",
    "backlog_ranked_list": "Backlog",
    "backlog_distribution": "Backlog",
    "priority_quadrant": "Priority Quadrant",
    "geographic_hot_spots": "Geographic Hot Spots",
    "time_to_close": "Current population",
}


@app.post("/api/chat/analytics-visit")
async def analytics_visit(request: AnalyticsVisitRequest):
    """
    After the records dialogue on the records page: pick a top CSV/data product
    related to an analytics page, and return the URL plus a short discussion
    (relationship to the analytics page or general trends).
    """
    if not agent:
        raise HTTPException(
            status_code=500,
            detail="Agent not initialized. Set GEMINI_API_KEY in backend/.env",
        )
    if get_conn is None or get_cluster_labels is None:
        raise HTTPException(
            status_code=503,
            detail="Cluster/DB not available for analytics visit.",
        )
    parent_id = request.parent_cluster_id
    child_id = request.child_cluster_id
    conn = get_conn()
    try:
        parent_label, child_label = get_cluster_labels(
            conn, parent_id, child_id or 0
        )
    finally:
        conn.close()
    parent_label = parent_label or f"cluster {parent_id}"
    child_label = child_label or f"sub-cluster {child_id}"

    # Plan: pick one analytics-linked data product for this cluster (README flow)
    frequency_preview = agent._get_frequency_preview()
    plan = await asyncio.to_thread(
        agent.gemini_agent.plan_one_analytics_product_for_cluster,
        parent_label,
        child_label,
        agent.catalog_summary,
        frequency_preview,
    )
    product_id = None
    for item in plan:
        pid = item.get("product")
        if pid and pid in ANALYTICS_PRODUCT_IDS:
            product_id = pid
            break
    if not product_id:
        product_id = "frequency_over_time"
    url = NAVIGATION_MAPPING.get(product_id, "/dashboard/analytics/frequency")
    display_name = KEY_TO_DISPLAY.get(
        product_id, product_id.replace("_", " ").title()
    )

    # Load that product's data summary for the discussion
    summaries = agent.data_loader.load_multiple_summaries([product_id])
    data_summary = (summaries or {}).get(product_id, "")
    if not data_summary:
        dfs = agent.data_loader.load_multiple_products([product_id])
        data_summary = ""
        if dfs and product_id in dfs and dfs[product_id] is not None:
            data_summary = agent.data_loader.get_data_summary(
                dfs[product_id], max_rows=30
            )

    discussion = await asyncio.to_thread(
        agent.gemini_agent.discuss_analytics_visit,
        parent_label,
        child_label,
        product_id,
        display_name,
        data_summary,
    )
    return {"url": url, "discussion": discussion}


class ReportGenerateRequest(BaseModel):
    parent_cluster_id: int
    child_cluster_id: int
    discussion: str


@app.post("/api/report/generate")
async def report_generate(request: ReportGenerateRequest):
    """
    Generate a PDF report from cluster context and discussion.
    Expects JSON with answer, rationale, key_metrics (synthesized from discussion via Gemini).
    Returns PDF bytes so the frontend can display it.
    """
    if not agent:
        raise HTTPException(
            status_code=500,
            detail="Agent not initialized. Set GEMINI_API_KEY in backend/.env",
        )
    if ReportGenerator is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Report generator not available. Install reportlab: pip install reportlab. "
                + (f"Error: {_report_generator_error}" if _report_generator_error else "")
            ),
        )
    if get_conn is None or get_cluster_labels is None:
        raise HTTPException(
            status_code=503,
            detail="Cluster/DB not available for report context.",
        )

    parent_id = request.parent_cluster_id
    child_id = request.child_cluster_id
    discussion = (request.discussion or "").strip()

    conn = get_conn()
    try:
        parent_label, child_label = get_cluster_labels(
            conn, parent_id, child_id or 0
        )
    finally:
        conn.close()
    parent_label = parent_label or f"cluster {parent_id}"
    child_label = child_label or f"sub-cluster {child_id}"

    # Build report input: answer, rationale, key_metrics (required by ReportGenerator per README)
    report_data = await asyncio.to_thread(
        agent.gemini_agent.report_data_from_discussion,
        parent_label,
        child_label,
        discussion,
    )

    # Add products so report can render "Supporting Data Analysis" with CSV-based charts (README)
    frequency_preview = agent._get_frequency_preview()
    plan = await asyncio.to_thread(
        agent.gemini_agent.plan_one_analytics_product_for_cluster,
        parent_label,
        child_label,
        agent.catalog_summary,
        frequency_preview,
    )
    product_id = None
    for item in plan:
        pid = item.get("product")
        if pid and pid in ANALYTICS_PRODUCT_IDS:
            product_id = pid
            break
    if product_id:
        report_data["products"] = [
            {"product": product_id, "why": plan[0].get("why", "Relevant to cluster") if plan else "Relevant to cluster"}
        ]

    # Generate PDF (ReportGenerator.generate_pdf: answer, rationale, key_metrics, optional products)
    subtitle = f"Cluster: {parent_label} / {child_label} — {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    generator = ReportGenerator(
        title="CRM Analytics Report",
        subtitle=subtitle,
    )
    pdf_bytes = await asyncio.to_thread(generator.generate_pdf, report_data)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=report.pdf",
        },
    )


@app.post("/api/cluster/predict")
async def cluster_predict(request: ClusterPredictRequest):
    """
    Predict parent (level-1) and child (level-2) cluster for a text message.
    Used when user follows up after "what are you interested in?" to highlight the relevant cluster.
    """
    if not sync_predict_cluster:
        raise HTTPException(
            status_code=503,
            detail="Cluster predictor not available. Need DATABASE_URL and sentence-transformers.",
        )
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    try:
        result = await asyncio.to_thread(
            sync_predict_cluster,
            request.message.strip(),
        )
        return {
            "parent_cluster_id": result["parent_cluster_id"],
            "child_cluster_id": result["child_cluster_id"],
            "parent_similarity": result["parent_similarity"],
            "child_similarity": result["child_similarity"],
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    voice_id: str = "m86j6D7UZpGzHsNu"  # Default to Jack voice
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


@app.post("/api/voice/tts/with-timestamps")
async def text_to_speech_with_timestamps(request: TTSRequest):
    """
    TTS with word-level timestamps for subtitle sync.
    Returns JSON: { "audio_base64": str, "timestamps": [{ "text", "start_s", "stop_s" }] }
    """
    if not gradium_client:
        raise HTTPException(status_code=500, detail="Gradium client not initialized. Check GRADIUM_API_KEY in .env")
    try:
        audio_bytes, timestamps = await gradium_client.text_to_speech_with_timestamps(
            text=request.text,
            voice_id=request.voice_id,
            output_format=request.output_format,
        )
        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "timestamps": timestamps,
        }
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
    input_format: str = "wav"  # "wav", "pcm", or "opus" (Gradium; no webm)


class STTStreamChunk(BaseModel):
    audio_chunk: str  # Base64 encoded audio chunk
    is_final: bool = False  # True when recording is complete
    input_format: str = "wav"


@app.post("/api/voice/stt/stream")
async def speech_to_text_stream(request: STTStreamChunk):
    """
    Stream speech-to-text with real-time transcription
    Client sends audio chunks as they're recorded
    Returns SSE stream with partial transcripts
    """
    if not gradium_client:
        raise HTTPException(status_code=500, detail="Gradium client not initialized. Check GRADIUM_API_KEY in .env")
    
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

            # Process STT stream (English language only)
            async for message in gradium_client.speech_to_text(
                audio_generator=audio_generator(),
                input_format=request.input_format,
                language="en"  # Always use English for transcription
            ):
                print(f"[STT] Gradium message: {message}")
                if message.get("type") == "text":
                    text = message.get("text", "")
                    print(f"📝 Stream transcript: {text}")
                    sse_line = json.dumps({"type": "transcript", "text": text, "is_final": request.is_final})
                    print(f"[STT] SSE out: data: {sse_line}")
                    yield f"data: {sse_line}\n\n"

            if request.is_final:
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                print("[STT] SSE out: data: complete")

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
        
        # Gradium accepts only wav, pcm, opus
        input_format = request.input_format if request.input_format in ("wav", "pcm", "opus") else "wav"

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
        # Always transcribe in English
        async for message in gradium_client.speech_to_text(
            audio_generator=audio_generator(),
            input_format=input_format,
            language="en"  # English language enforced
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
