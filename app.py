import sys
import asyncio
import keyring
import pyvirtualcam
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QLabel, QScrollArea, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap, QColor, QPalette
from qasync import QEventLoop, asyncSlot

from decart import DecartClient, models
from decart.realtime import RealtimeClient, RealtimeConnectOptions
from decart.types import ModelState, Prompt

from video_pipeline import CameraThread, LocalVideoStreamTrack, FrameEmitter

# --- Styling ---
DARK_THEME = """
QMainWindow {
    background-color: #121212;
}
QWidget {
    background-color: #121212;
    color: #E0E0E0;
    font-family: 'Segoe UI', sans-serif;
}
QLineEdit {
    background-color: #1E1E1E;
    border: 1px solid #333;
    border-radius: 4px;
    padding: 8px;
    color: white;
}
QPushButton {
    background-color: #2C2C2C;
    border: none;
    border-radius: 4px;
    padding: 10px 20px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #3D3D3D;
}
QPushButton#applyBtn {
    background-color: #007AFF;
}
QPushButton#applyBtn:hover {
    background-color: #0063CC;
}
QPushButton#presetBtn {
    background-color: #1E1E1E;
    border: 1px solid #333;
    padding: 5px 15px;
}
QLabel#statusLabel {
    color: #888;
}
"""

class DecartApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LucidCam - Real-time AI Restyling")
        self.setMinimumSize(1000, 800)
        self.setStyleSheet(DARK_THEME)

        # State
        self.realtime_client = None
        self.camera_thread = None
        self.vcam = None
        self.frame_emitter = FrameEmitter()
        self.frame_emitter.frame_received.connect(self.update_video_canvas)

        self.init_ui()
        self.load_api_key()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Bar: API Key
        top_bar = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter Decart API Key")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        save_key_btn = QPushButton("Save Key")
        save_key_btn.clicked.connect(self.save_api_key)
        top_bar.addWidget(self.api_key_input)
        top_bar.addWidget(save_key_btn)
        main_layout.addLayout(top_bar)

        # Central: Video Canvas
        self.video_canvas = QLabel("Connect to start")
        self.video_canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_canvas.setStyleSheet("""
            QLabel {
                background-color: black; 
                border-radius: 8px; 
                color: #555; 
                font-size: 18px;
                border: 2px solid #222;
            }
        """)
        self.video_canvas.setMinimumHeight(500)
        main_layout.addWidget(self.video_canvas, stretch=1)

        # Control Panel
        control_panel = QVBoxLayout()
        
        # Prompt Input
        prompt_layout = QHBoxLayout()
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Describe the style change...")
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("applyBtn")
        self.apply_btn.clicked.connect(self.apply_prompt)
        prompt_layout.addWidget(self.prompt_input)
        prompt_layout.addWidget(self.apply_btn)
        control_panel.addLayout(prompt_layout)

        # Presets
        presets_scroll = QScrollArea()
        presets_scroll.setWidgetResizable(True)
        presets_scroll.setFixedHeight(60)
        presets_scroll.setFrameShape(QFrame.Shape.NoFrame)
        presets_content = QWidget()
        presets_layout = QHBoxLayout(presets_content)
        
        presets = ["Albert Stylestein", "Capybara", "Statue of Liberty", "Cyberpunk", "Oil Painting"]
        for p in presets:
            btn = QPushButton(p)
            btn.setObjectName("presetBtn")
            btn.clicked.connect(lambda checked, text=p: self.set_preset(text))
            presets_layout.addWidget(btn)
        
        presets_scroll.setWidget(presets_content)
        control_panel.addWidget(presets_scroll)

        # Bottom Bar: Status and Connect
        bottom_bar = QHBoxLayout()
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setObjectName("statusLabel")
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        bottom_bar.addWidget(self.status_label)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.connect_btn)
        control_panel.addLayout(bottom_bar)

        main_layout.addLayout(control_panel)

    # --- API Key Management ---
    def load_api_key(self):
        key = keyring.get_password("DecartApp", "API_KEY")
        if key:
            self.api_key_input.setText(key)

    def save_api_key(self):
        key = self.api_key_input.text().strip()
        if key:
            keyring.set_password("DecartApp", "API_KEY", key)
            QMessageBox.information(self, "Success", "API Key saved securely.")

    # --- Connection Logic ---
    @asyncSlot()
    async def toggle_connection(self):
        if self.realtime_client and self.realtime_client.is_connected:
            await self.disconnect()
        else:
            await self.connect()

    async def connect(self):
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter an API Key.")
            return

        self.status_label.setText("Status: Connecting...")
        self.connect_btn.setEnabled(False)

        try:
            # 1. Initialize Virtual Camera
            try:
                self.vcam = pyvirtualcam.Camera(width=1280, height=720, fps=24)
                print(f"Virtual camera started: {self.vcam.device}")
            except Exception as e:
                QMessageBox.critical(self, "Driver Missing", 
                    f"Could not start virtual camera. Please ensure OBS Virtual Camera or v4l2loopback is installed.\nError: {e}")
                self.reset_ui()
                return

            # 2. Start Camera Thread
            self.camera_thread = CameraThread(target_width=1280, target_height=720)
            self.camera_thread.start()
            
            # Wait a bit for the camera to warm up
            await asyncio.sleep(1)
            if not self.camera_thread.running:
                raise Exception("Could not open local camera. It might be in use by another app.")

            # 3. Setup Decart SDK
            model = models.realtime("lucy-2.1")
            client = DecartClient(api_key=api_key)
            
            local_track = LocalVideoStreamTrack(self.camera_thread)

            self.realtime_client = await RealtimeClient.connect(
                base_url=client.base_url,
                api_key=client.api_key,
                local_track=local_track,
                options=RealtimeConnectOptions(
                    model=model,
                    on_remote_stream=self.handle_remote_stream,
                    initial_state=ModelState(
                        prompt=Prompt(text=self.prompt_input.text() or "A cinematic portrait"),
                    ),
                ),
            )

            self.status_label.setText("Status: Live")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect: {str(e)}")
            await self.disconnect()

    async def disconnect(self):
        self.status_label.setText("Status: Disconnecting...")
        if self.realtime_client:
            await self.realtime_client.disconnect()
            self.realtime_client = None
        
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread = None
        
        if self.vcam:
            self.vcam.close()
            self.vcam = None

        self.reset_ui()

    def reset_ui(self):
        self.status_label.setText("Status: Disconnected")
        self.connect_btn.setText("Connect")
        self.connect_btn.setEnabled(True)
        self.video_canvas.setPixmap(QPixmap())
        self.video_canvas.setText("Connect to start")

    # --- Stream Handling ---
    def handle_remote_stream(self, transformed_stream):
        """
        Callback from Decart SDK. Runs in an aiortc background task.
        """
        async def process_frames():
            async for frame in transformed_stream:
                # 1. Update UI (Thread-safe via Signal)
                self.frame_emitter.emit_frame(frame)

                # 2. Update Virtual Camera
                if self.vcam:
                    # av.VideoFrame -> ndarray (RGB) -> vcam (RGB)
                    img_rgb = frame.to_ndarray(format="rgb24")
                    self.vcam.send(img_rgb)
                    self.vcam.sleep_until_next_frame()

        # Schedule the processing task
        asyncio.create_task(process_frames())

    @pyqtSlot(QImage)
    def update_video_canvas(self, q_img):
        pixmap = QPixmap.fromImage(q_img)
        # Scale pixmap to fit label while keeping aspect ratio
        scaled_pixmap = pixmap.scaled(self.video_canvas.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.video_canvas.setPixmap(scaled_pixmap)

    # --- UI Actions ---
    @asyncSlot()
    async def apply_prompt(self):
        if self.realtime_client and self.realtime_client.is_connected:
            prompt_text = self.prompt_input.text()
            await self.realtime_client.set_prompt(prompt_text)
            self.status_label.setText(f"Status: Live (Prompt: {prompt_text})")

    def set_preset(self, text):
        self.prompt_input.setText(f"Transform the video into {text} style")
        # Trigger apply
        asyncio.create_task(self.apply_prompt())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = DecartApp()
    window.show()

    with loop:
        loop.run_forever()
