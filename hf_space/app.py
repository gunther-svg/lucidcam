"""
LucidCam — HuggingFace Space Inference Server
==============================================
Runs decart-ai/Lucy-Edit-Dev (Wan2.2 5B, bfloat16) and exposes:

  GET  /health  → {"status": "ready"|"loading"|"error"}
  POST /infer   → multipart form: frames[] (JPEG bytes) + prompt (str)
               ← JSON: {"frames": [<base64>,...], "count": N}

The model is loaded once at startup in a background thread.
All POST /infer calls block until the model is ready.

Designed for the LucidCam RemoteProvider sliding-window pipeline:
  • Input:  16-frame chunks (0.67s @ 24fps) at 480x832 pixels
  • Output: N processed frames as base64-encoded JPEG
"""

import asyncio
import base64
import io
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from typing import List, Optional

import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("lucidcam-space")

# ── Model Configuration ───────────────────────────────────────────
MODEL_ID = "decart-ai/Lucy-Edit-Dev"

# Recommended inference resolution for Lucy-Edit-Dev (Wan2.2)
# Portrait 9:16 — works well for webcam feeds
INFER_WIDTH = 480
INFER_HEIGHT = 832

# Inference parameters
NUM_INFERENCE_STEPS = 20   # Balance of quality and speed on A10G
STRENGTH = 0.75            # How strongly to apply the edit (0 = no edit, 1 = full restyle)
GUIDANCE_SCALE = 7.0

# ── Global model state ────────────────────────────────────────────
_model_state: dict = {
    "pipeline": None,
    "loading": True,
    "error": None,
    "load_started": None,
    "load_finished": None,
}
_model_lock = threading.Lock()


# ── Model Loading ─────────────────────────────────────────────────

def _load_model_thread():
    """
    Downloads and loads decart-ai/Lucy-Edit-Dev into GPU memory.
    Called once in a background thread at startup.
    Memory target: ~10 GB VRAM at bfloat16 on the 24 GB A10G.
    """
    _model_state["load_started"] = time.monotonic()
    logger.info(f"Starting model load: {MODEL_ID}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)} — {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    try:
        from diffusers import WanVideoToVideoPipeline

        logger.info("Downloading / loading model weights (this may take several minutes on first run)...")
        pipe = WanVideoToVideoPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
        )

        # Memory optimisations for the 24 GB A10G
        pipe.enable_vae_slicing()          # reduces peak VRAM during VAE decode
        pipe.enable_attention_slicing()    # reduces peak VRAM during attention

        device = "cuda" if torch.cuda.is_available() else "cpu"
        pipe = pipe.to(device)

        with _model_lock:
            _model_state["pipeline"] = pipe
            _model_state["loading"] = False
            _model_state["load_finished"] = time.monotonic()

        load_time = _model_state["load_finished"] - _model_state["load_started"]
        logger.info(f"Model loaded successfully in {load_time:.1f}s")

        if torch.cuda.is_available():
            used = torch.cuda.memory_allocated() / 1e9
            total = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(f"VRAM usage after load: {used:.1f} / {total:.1f} GB")

    except ImportError as e:
        msg = (
            f"Could not import WanVideoToVideoPipeline from diffusers: {e}. "
            "Ensure diffusers>=0.32.0 is installed and the model is supported."
        )
        logger.error(msg)
        with _model_lock:
            _model_state["error"] = msg
            _model_state["loading"] = False

    except Exception as e:
        logger.exception(f"Failed to load model: {e}")
        with _model_lock:
            _model_state["error"] = str(e)
            _model_state["loading"] = False


# ── FastAPI Lifespan ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Kick off model loading in the background immediately on startup."""
    thread = threading.Thread(target=_load_model_thread, daemon=True, name="model-loader")
    thread.start()
    logger.info("Model load thread started.")
    yield
    logger.info("Server shutting down.")


# ── App ───────────────────────────────────────────────────────────

app = FastAPI(
    title="LucidCam Lucy-Edit Backend",
    description="Sliding-window video inference backend for LucidCam using decart-ai/Lucy-Edit-Dev",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow calls from the LucidCam desktop app (localhost) and the HF domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restricted by HF Space private setting + token auth
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────

def _jpeg_to_pil(data: bytes) -> Image.Image:
    """Decode JPEG bytes to a PIL Image in RGB mode."""
    return Image.open(io.BytesIO(data)).convert("RGB")


def _pil_to_jpeg_b64(img: Image.Image, quality: int = 85) -> str:
    """Encode a PIL Image as a base64 JPEG string."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _resize_frames(frames: List[Image.Image], width: int, height: int) -> List[Image.Image]:
    """Resize a list of PIL frames to the model's expected resolution."""
    return [f.resize((width, height), Image.LANCZOS) for f in frames]


def _run_inference(
    pipeline,
    frames: List[Image.Image],
    prompt: str,
    negative_prompt: str = "blurry, low quality, distorted, watermark",
) -> List[Image.Image]:
    """
    Run Lucy-Edit-Dev inference on a list of video frames.

    Returns a list of processed PIL Images at the same count as input.
    The pipeline (WanVideoToVideoPipeline) expects:
      - video: List[PIL.Image.Image] in RGB
      - prompt: str instruction
      - strength: float — how much to edit (0=none, 1=full)
    """
    # Resize to model's native resolution
    resized = _resize_frames(frames, INFER_WIDTH, INFER_HEIGHT)

    with torch.inference_mode():
        output = pipeline(
            video=resized,
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=NUM_INFERENCE_STEPS,
            strength=STRENGTH,
            guidance_scale=GUIDANCE_SCALE,
        )

    # output.frames is List[List[PIL.Image.Image]] — one per batch item
    processed_frames: List[Image.Image] = output.frames[0]
    return processed_frames


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/health", summary="Model readiness probe")
async def health():
    """
    Returns the current model status.
    Poll this endpoint after a cold-start until it returns 'ready'.
    """
    with _model_lock:
        if _model_state["loading"]:
            elapsed = (
                time.monotonic() - _model_state["load_started"]
                if _model_state["load_started"]
                else 0
            )
            return JSONResponse({"status": "loading", "elapsed_seconds": round(elapsed, 1)})

        if _model_state["error"]:
            return JSONResponse(
                {"status": "error", "detail": _model_state["error"]},
                status_code=500,
            )

        load_time = (
            _model_state["load_finished"] - _model_state["load_started"]
            if _model_state["load_finished"]
            else None
        )
        return JSONResponse({
            "status": "ready",
            "model": MODEL_ID,
            "load_time_seconds": round(load_time, 1) if load_time else None,
            "device": "cuda" if torch.cuda.is_available() else "cpu",
        })


@app.post("/infer", summary="Process a video frame chunk")
async def infer(
    frames: List[UploadFile] = File(
        ...,
        description="List of JPEG-encoded video frames (sliding window chunk)",
    ),
    prompt: str = Form(
        ...,
        description="Text instruction for Lucy-Edit-Dev, e.g. 'Substitute the character with an anime avatar'",
    ),
):
    """
    Accepts a chunk of consecutive video frames and a text prompt.
    Runs Lucy-Edit-Dev inference and returns the processed frames as base64 JPEG.

    This endpoint is designed for the LucidCam RemoteProvider's sliding-window pipeline.
    Expected chunk size: 8–24 frames.
    """
    # ── Guard: model must be ready ────────────────────────────────
    with _model_lock:
        if _model_state["loading"]:
            raise HTTPException(status_code=503, detail="Model is still loading. Poll /health first.")
        if _model_state["error"]:
            raise HTTPException(status_code=500, detail=f"Model error: {_model_state['error']}")
        pipeline = _model_state["pipeline"]

    if not frames:
        raise HTTPException(status_code=400, detail="No frames provided.")

    if len(frames) > 81:
        raise HTTPException(
            status_code=400,
            detail=f"Too many frames ({len(frames)}). Maximum is 81 (3 seconds at 24fps).",
        )

    # ── Decode incoming JPEG frames ───────────────────────────────
    logger.info(f"Inference request: {len(frames)} frames, prompt='{prompt[:60]}'")
    infer_start = time.monotonic()

    pil_frames: List[Image.Image] = []
    for upload in frames:
        raw = await upload.read()
        try:
            img = _jpeg_to_pil(raw)
            pil_frames.append(img)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not decode frame '{upload.filename}': {e}")

    # ── Run inference in an executor (avoids blocking the event loop) ─
    try:
        loop = asyncio.get_event_loop()
        processed_frames = await loop.run_in_executor(
            None,
            _run_inference,
            pipeline,
            pil_frames,
            prompt,
        )
    except Exception as e:
        logger.exception(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

    # ── Encode output frames as base64 JPEG ───────────────────────
    encoded: List[str] = [_pil_to_jpeg_b64(f) for f in processed_frames]

    elapsed = time.monotonic() - infer_start
    logger.info(f"Inference done: {len(encoded)} frames in {elapsed:.2f}s ({elapsed/len(encoded):.2f}s/frame)")

    return JSONResponse({
        "frames": encoded,
        "count": len(encoded),
        "inference_time_seconds": round(elapsed, 2),
        "fps_equivalent": round(len(encoded) / elapsed, 2) if elapsed > 0 else 0,
    })


# ── Dev entrypoint ────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="info")
