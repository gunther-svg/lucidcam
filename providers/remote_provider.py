"""
RemoteProvider — HuggingFace Space inference backend for LucidCam.
==================================================================

Architecture
------------
This provider implements a sliding-window async pipeline:

  Camera (24fps)
    │
    ▼  push_frame()
  ┌──────────────────────────────────────┐
  │  Input Ring Buffer  (maxlen = 2×chunk)│
  └──────────────────────────────────────┘
    │  when buffer ≥ chunk_size AND
    │  frames_since_last_send ≥ stride
    ▼  _inference_loop() fires a task
  ┌──────────────────────────────────────┐
  │  POST /infer  (aiohttp, async)       │ → HF Space (A10G)
  │  • sends `chunk_size` JPEG frames    │
  │  • prompt string                     │
  └──────────────────────────────────────┘
    │  returns base64 processed frames
    ▼
  ┌──────────────────────────────────────┐
  │  Output Queue  (maxlen = 5×fps)      │
  └──────────────────────────────────────┘
    │
    ▼  get_output_frame() — called at 24fps
  Virtual Camera / UI display

Latency model (A10G, 16-frame chunk, 20 steps):
  • Expected inference time: ~8–25 s per chunk
  • Output plays at steady 24fps once the first batch is ready
  • Queue depth absorbs the inference round-trip time
  • Cold-start (Space waking from sleep): additional ~30–60 s

The output virtual camera always runs at 24fps:
  • While queue is filling: last known frame is repeated (freeze)
  • Once queue has frames: frames play in sequence at 24fps
"""

import asyncio
import base64
import io
import logging
import time
from collections import deque
from typing import Optional

import aiohttp
import numpy as np
from PIL import Image

from providers.base import BaseProvider

logger = logging.getLogger("lucidcam.remote_provider")


class RemoteProvider(BaseProvider):
    """
    Sends sliding-window frame chunks to a private HF Space running
    decart-ai/Lucy-Edit-Dev, and feeds the processed frames to the
    virtual camera output at 24fps.
    """

    def __init__(
        self,
        space_url: str,
        hf_token: str,
        chunk_size: int = 16,
        stride: int = 8,
        fps: int = 24,
        infer_width: int = 480,
        infer_height: int = 832,
        jpeg_quality: int = 85,
        health_poll_interval: float = 3.0,
        infer_timeout: float = 180.0,
    ):
        """
        Args:
            space_url:           Base URL of the HF Space, e.g.
                                 "https://gunther-svg-lucidcam-lucy-backend.hf.space"
            hf_token:            HuggingFace access token for private Space auth.
            chunk_size:          Number of frames per inference request (default 16 ≈ 0.67s).
            stride:              Send a new batch every N new frames (default 8 ≈ 0.33s).
            fps:                 Target output FPS (default 24).
            infer_width:         Frame width sent to the model (default 480).
            infer_height:        Frame height sent to the model (default 832).
            jpeg_quality:        JPEG quality for frame encoding (default 85).
            health_poll_interval: Seconds between /health polls during warm-up.
            infer_timeout:       Max seconds to wait for a single /infer response.
        """
        self.space_url = space_url.rstrip("/")
        self.hf_token = hf_token
        self.chunk_size = chunk_size
        self.stride = stride
        self.fps = fps
        self.infer_width = infer_width
        self.infer_height = infer_height
        self.jpeg_quality = jpeg_quality
        self.health_poll_interval = health_poll_interval
        self.infer_timeout = infer_timeout

        # Current text prompt (updated via set_prompt())
        self._prompt: str = (
            "Substitute the character in the video with an anime-style character "
            "with large expressive eyes, smooth cel-shaded skin, and vibrant hair."
        )

        # ── Input buffer ──────────────────────────────────────────
        # Keeps the last 2×chunk_size frames in a ring buffer.
        self._frame_buffer: deque = deque(maxlen=chunk_size * 2)
        self._frames_since_last_send: int = 0

        # ── Output queue ──────────────────────────────────────────
        # Holds processed frames (numpy RGB arrays) ready for display.
        # maxlen = 5 seconds worth of output frames.
        self._output_queue: deque = deque(maxlen=fps * 5)
        self._last_output_frame: Optional[np.ndarray] = None

        # ── Internal state ────────────────────────────────────────
        self._session: Optional[aiohttp.ClientSession] = None
        self._status: str = "disconnected"
        self._inference_loop_task: Optional[asyncio.Task] = None
        self._running: bool = False

        # ── Diagnostics ───────────────────────────────────────────
        self._total_batches_sent: int = 0
        self._total_frames_received: int = 0
        self._last_inference_time: float = 0.0

    # ── BaseProvider interface ────────────────────────────────────

    @property
    def status(self) -> str:
        return self._status

    def set_prompt(self, prompt: str) -> None:
        """Update the editing prompt. Takes effect on the next inference batch."""
        self._prompt = prompt
        logger.info(f"Prompt updated: {prompt[:80]}")

    def push_frame(self, frame_rgb: np.ndarray) -> None:
        """
        Add a new camera frame to the input buffer.
        Called from the async output loop at ~24fps. Non-blocking.
        """
        self._frame_buffer.append(frame_rgb)
        self._frames_since_last_send += 1

    def get_output_frame(self) -> Optional[np.ndarray]:
        """
        Return the next processed frame from the output queue, or the last
        known frame if the queue is empty (freeze-frame during inference gap).
        """
        if self._output_queue:
            frame = self._output_queue.popleft()
            self._last_output_frame = frame
            return frame
        # Return last frame during gaps (avoids black flicker)
        return self._last_output_frame

    async def start(self) -> None:
        """
        1. Creates aiohttp session with HF token auth.
        2. Polls /health until the Space returns "ready".
        3. Starts the background inference loop.
        """
        headers = {
            "Authorization": f"Bearer {self.hf_token}",
        }
        connector = aiohttp.TCPConnector(limit=4)
        self._session = aiohttp.ClientSession(headers=headers, connector=connector)

        self._status = "connecting"
        logger.info(f"Connecting to HF Space: {self.space_url}")

        await self._poll_health_until_ready()

        self._running = True
        self._status = "live"
        self._inference_loop_task = asyncio.create_task(
            self._inference_loop(), name="remote-inference-loop"
        )
        logger.info("RemoteProvider live — inference loop started.")

    async def stop(self) -> None:
        """Gracefully stop the inference loop and close the HTTP session."""
        self._running = False
        self._status = "disconnected"

        if self._inference_loop_task and not self._inference_loop_task.done():
            self._inference_loop_task.cancel()
            try:
                await self._inference_loop_task
            except asyncio.CancelledError:
                pass
            self._inference_loop_task = None

        if self._session:
            await self._session.close()
            self._session = None

        logger.info(
            f"RemoteProvider stopped. "
            f"Sent {self._total_batches_sent} batches, "
            f"received {self._total_frames_received} frames."
        )

    # ── Internal methods ──────────────────────────────────────────

    async def _poll_health_until_ready(self) -> None:
        """
        Repeatedly GET /health until the Space returns {"status": "ready"}.
        Logs progress every 15 seconds. Raises RuntimeError if model errors out.
        """
        health_url = f"{self.space_url}/health"
        poll_start = time.monotonic()
        last_log = poll_start

        logger.info("Polling /health — waiting for Space to be ready...")

        while True:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with self._session.get(health_url, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        status = data.get("status", "unknown")

                        if status == "ready":
                            elapsed = time.monotonic() - poll_start
                            logger.info(f"Space ready after {elapsed:.1f}s warm-up.")
                            return

                        elif status == "error":
                            raise RuntimeError(
                                f"Space model failed to load: {data.get('detail', 'unknown error')}"
                            )

                        elif status == "loading":
                            elapsed = time.monotonic() - poll_start
                            if time.monotonic() - last_log > 15:
                                server_elapsed = data.get("elapsed_seconds", "?")
                                logger.info(
                                    f"Still loading... ({elapsed:.0f}s waited, "
                                    f"model load time: {server_elapsed}s)"
                                )
                                last_log = time.monotonic()

                    elif resp.status == 503:
                        # Space is sleeping / waking up — normal during cold start
                        if time.monotonic() - last_log > 15:
                            logger.info(f"Space is waking from sleep... ({time.monotonic() - poll_start:.0f}s)")
                            last_log = time.monotonic()

            except aiohttp.ClientConnectorError:
                # Space container not yet accepting connections (normal during cold start)
                if time.monotonic() - last_log > 15:
                    logger.info(f"Space not yet reachable... ({time.monotonic() - poll_start:.0f}s)")
                    last_log = time.monotonic()
            except Exception as e:
                logger.warning(f"Health poll error: {e}")

            await asyncio.sleep(self.health_poll_interval)

    async def _inference_loop(self) -> None:
        """
        Background coroutine: fires inference requests when the input buffer
        has enough frames and the stride has been met.
        """
        stride_interval = self.stride / self.fps   # seconds between send checks
        while self._running:
            await asyncio.sleep(stride_interval)

            if (
                len(self._frame_buffer) >= self.chunk_size
                and self._frames_since_last_send >= self.stride
            ):
                # Snapshot the latest chunk_size frames
                frames_to_send = list(self._frame_buffer)[-self.chunk_size :]
                prompt_snapshot = self._prompt
                self._frames_since_last_send = 0

                # Fire-and-forget — multiple batches can be in-flight simultaneously
                asyncio.create_task(
                    self._send_chunk(frames_to_send, prompt_snapshot),
                    name=f"infer-batch-{self._total_batches_sent}",
                )
                self._total_batches_sent += 1
                logger.debug(
                    f"Batch {self._total_batches_sent} dispatched "
                    f"({len(frames_to_send)} frames, queue depth: {len(self._output_queue)})"
                )

    async def _send_chunk(self, frames: list, prompt: str) -> None:
        """
        Encode a list of numpy RGB frames as JPEG multipart data,
        POST them to /infer, and push the returned processed frames
        into the output queue.
        """
        infer_url = f"{self.space_url}/infer"
        t0 = time.monotonic()

        try:
            form = aiohttp.FormData()
            form.add_field("prompt", prompt)

            for i, frame_rgb in enumerate(frames):
                # Resize to model inference resolution
                pil_img = Image.fromarray(frame_rgb).resize(
                    (self.infer_width, self.infer_height), Image.LANCZOS
                )
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=self.jpeg_quality)
                buf.seek(0)
                form.add_field(
                    "frames",
                    buf,
                    filename=f"frame_{i:04d}.jpg",
                    content_type="image/jpeg",
                )

            timeout = aiohttp.ClientTimeout(total=self.infer_timeout)
            async with self._session.post(
                infer_url,
                data=form,
                timeout=timeout,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    encoded_frames: list = data.get("frames", [])
                    server_time = data.get("inference_time_seconds", 0)

                    for b64_frame in encoded_frames:
                        try:
                            raw = base64.b64decode(b64_frame)
                            pil_out = Image.open(io.BytesIO(raw)).convert("RGB")
                            frame_np = np.array(pil_out, dtype=np.uint8)
                            self._output_queue.append(frame_np)
                            self._last_output_frame = frame_np
                            self._total_frames_received += 1
                        except Exception as decode_err:
                            logger.warning(f"Could not decode output frame: {decode_err}")

                    elapsed = time.monotonic() - t0
                    self._last_inference_time = elapsed
                    logger.info(
                        f"Batch received: {len(encoded_frames)} frames in "
                        f"{elapsed:.1f}s (server: {server_time:.1f}s) — "
                        f"output queue: {len(self._output_queue)} frames"
                    )

                elif resp.status == 503:
                    body = await resp.text()
                    logger.warning(f"Space returned 503 (still loading?): {body[:200]}")

                else:
                    body = await resp.text()
                    logger.error(f"Inference request failed: HTTP {resp.status} — {body[:200]}")

        except asyncio.TimeoutError:
            logger.error(
                f"Inference request timed out after {self.infer_timeout}s. "
                "Consider reducing chunk_size or increasing infer_timeout."
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error sending inference chunk: {e}")

    # ── Diagnostic helpers ────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return current pipeline statistics for UI status display."""
        return {
            "status": self._status,
            "output_queue_depth": len(self._output_queue),
            "total_batches_sent": self._total_batches_sent,
            "total_frames_received": self._total_frames_received,
            "last_inference_time_s": round(self._last_inference_time, 1),
            "buffer_depth": len(self._frame_buffer),
        }
