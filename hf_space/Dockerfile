# -------------------------------------------------------------------
# LucidCam HF Space — Dockerfile
# Base: CUDA 12.1 + PyTorch 2.4 (matches A10G driver stack)
# Model: decart-ai/Lucy-Edit-Dev (Wan2.2 5B, bfloat16)
# API:   FastAPI on port 7860
# -------------------------------------------------------------------

FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn8-runtime

# ── System dependencies ────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ──────────────────────────────────────────────
WORKDIR /app

# ── HF cache: point to /app/hf_cache so it survives within the container
ENV HF_HOME=/app/hf_cache
ENV TRANSFORMERS_CACHE=/app/hf_cache
ENV DIFFUSERS_CACHE=/app/hf_cache

# ── Python deps (separate layer for caching) ──────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────
COPY app.py .

# ── HF Spaces: non-root user requirement ──────────────────────────
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# ── Expose port ───────────────────────────────────────────────────
EXPOSE 7860

# ── Startup ───────────────────────────────────────────────────────
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1", "--log-level", "info"]
