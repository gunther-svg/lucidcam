import cv2
import asyncio
import threading
import time
import av
from fractions import Fraction
from aiortc import MediaStreamTrack
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtGui import QImage

class CameraThread(threading.Thread):
    """
    Separate thread for capturing frames from the webcam using OpenCV.
    Handles resizing to target resolution (720p) and keeps the latest frame.
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

class LocalVideoStreamTrack(MediaStreamTrack):
    """
    A video track that yields frames from the CameraThread.
    """
    kind = "video"

    def __init__(self, camera_thread):
        super().__init__()
        self.camera_thread = camera_thread
        self._timestamp = 0
        self._start_time = None

    async def recv(self):
        # Wait for the next frame if none is available
        if self.camera_thread.latest_frame is None:
            # We use a non-blocking wait in the async loop
            while self.camera_thread.latest_frame is None and self.camera_thread.running:
                await asyncio.sleep(0.01)

        # Grab the latest frame and clear the event
        frame_bgr = self.camera_thread.latest_frame
        self.camera_thread.frame_ready_event.clear()

        # Convert BGR to YUV420P for aiortc/WebRTC
        # This is a CPU intensive part, but doing it here ensures it's in the WebRTC pipeline
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        video_frame = av.VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        
        # Set timing information
        if self._start_time is None:
            self._start_time = time.time()
        
        # Calculate timestamp based on real time to maintain sync
        pts = int((time.time() - self._start_time) * 90000)
        video_frame.pts = pts
        video_frame.time_base = Fraction(1, 90000)
        
        return video_frame

class FrameEmitter(QObject):
    """
    Thread-safe emitter to send frames from the WebRTC background task to the UI.
    """
    frame_received = pyqtSignal(QImage)

    def emit_frame(self, av_frame):
        # Convert av.VideoFrame to QImage
        # av_frame is usually YUV420P, convert to RGB first
        img_data = av_frame.to_ndarray(format="rgb24")
        height, width, channel = img_data.shape
        bytes_per_line = 3 * width
        q_img = QImage(img_data.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        # We need to copy the image because the underlying data might be reused
        self.frame_received.emit(q_img.copy())
