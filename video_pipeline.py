import cv2
import asyncio
import threading
import time
from livekit.rtc import VideoSource, LocalVideoTrack, VideoFrame, VideoBufferType
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtGui import QImage


class CameraThread(threading.Thread):
    """
    Separate thread for capturing frames from the webcam using OpenCV.
    Handles resizing to target resolution and keeps the latest frame.
    """
    def __init__(self, camera_index=0, target_width=1280, target_height=720):
        super().__init__(daemon=True)
        self.camera_index = camera_index
        self.target_width = target_width
        self.target_height = target_height
        self.latest_frame = None
        self.running = False
        self.frame_ready_event = threading.Event()
        self.cap = None

    def run(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}")
            return

        self.running = True
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # Resize to target resolution immediately
            frame = cv2.resize(frame, (self.target_width, self.target_height))

            # Store latest frame (BGR)
            self.latest_frame = frame
            self.frame_ready_event.set()

        self.cap.release()

    def stop(self):
        self.running = False


class LiveKitCameraSource:
    """
    Bridges the CameraThread to a LiveKit VideoSource.
    Continuously pushes camera frames into the LiveKit VideoSource
    so a LocalVideoTrack can be used with the Decart RealtimeClient.
    """
    def __init__(self, camera_thread: CameraThread, fps: int = 24):
        self.camera_thread = camera_thread
        self.fps = fps
        self.width = camera_thread.target_width
        self.height = camera_thread.target_height

        # Create a LiveKit VideoSource and corresponding LocalVideoTrack
        self.video_source = VideoSource(self.width, self.height)
        self.track = LocalVideoTrack.create_video_track("camera", self.video_source)

        self._running = False
        self._task = None

    async def start(self):
        """Start the async loop that pushes camera frames to the LiveKit VideoSource."""
        self._running = True
        self._task = asyncio.create_task(self._push_frames())

    async def _push_frames(self):
        """Continuously push camera frames to the LiveKit VideoSource at target FPS."""
        frame_interval = 1.0 / self.fps
        start_time = time.monotonic()
        frame_count = 0

        while self._running:
            loop_start = time.monotonic()

            if self.camera_thread.latest_frame is not None:
                frame_bgr = self.camera_thread.latest_frame

                # Convert BGR (OpenCV) to RGBA (LiveKit)
                frame_rgba = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGBA)

                # Create LiveKit VideoFrame from the RGBA data
                lk_frame = VideoFrame(
                    self.width,
                    self.height,
                    VideoBufferType.RGBA,
                    frame_rgba.tobytes(),
                )

                # Compute timestamp in microseconds
                timestamp_us = int((time.monotonic() - start_time) * 1_000_000)

                # Push the frame to the VideoSource
                self.video_source.capture_frame(lk_frame, timestamp_us=timestamp_us)
                frame_count += 1

            # Maintain target FPS
            elapsed = time.monotonic() - loop_start
            sleep_time = max(0.001, frame_interval - elapsed)
            await asyncio.sleep(sleep_time)

    async def stop(self):
        """Stop the frame push loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


class FrameEmitter(QObject):
    """
    Thread-safe emitter to send frames from the WebRTC background task to the UI.
    """
    frame_received = pyqtSignal(QImage)

    def emit_frame(self, av_frame):
        """
        Convert an av.VideoFrame or similar frame object to QImage and emit.
        Handles both av.VideoFrame (with to_ndarray) and raw numpy arrays.
        """
        try:
            if hasattr(av_frame, 'to_ndarray'):
                # av.VideoFrame from Decart remote stream
                img_data = av_frame.to_ndarray(format="rgb24")
            elif hasattr(av_frame, 'data') and hasattr(av_frame, 'width'):
                # LiveKit VideoFrame — convert from RGBA bytes to numpy
                import numpy as np
                data = bytes(av_frame.data)
                img_data = np.frombuffer(data, dtype=np.uint8).reshape(
                    av_frame.height, av_frame.width, 4
                )
                # Convert RGBA to RGB for QImage
                img_data = img_data[:, :, :3].copy()
            else:
                # Assume it's already a numpy array (RGB)
                img_data = av_frame

            height, width, channel = img_data.shape
            bytes_per_line = 3 * width
            q_img = QImage(img_data.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            # We need to copy the image because the underlying data might be reused
            self.frame_received.emit(q_img.copy())
        except Exception as e:
            print(f"Error in FrameEmitter.emit_frame: {e}")
