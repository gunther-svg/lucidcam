import sys
import asyncio
import keyring
import pyvirtualcam
import numpy as np
import base64
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QLabel, QScrollArea, QFrame, QMessageBox,
    QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSlot, QSettings
from PyQt6.QtGui import QImage, QPixmap, QColor, QPalette, QIcon
from qasync import QEventLoop, asyncSlot

from decart import DecartClient, models
from decart.realtime import RealtimeClient, RealtimeConnectOptions
from decart.types import ModelState, Prompt

from video_pipeline import CameraThread, LocalVideoStreamTrack, FrameEmitter
import aiohttp

VERSION = "1.0.0"
# Placeholder URL for version checking
UPDATE_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/LucidCam/main/version.txt"

# Supported image formats
SUPPORTED_IMAGE_FORMATS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
MAX_IMAGE_SIZE_MB = 10

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
QPushButton#imageUploadBtn {
    background-color: #2C2C2C;
    border: 1px solid #555;
    padding: 8px 15px;
    font-size: 12px;
}
QPushButton#clearImageBtn {
    background-color: #4C2C2C;
    padding: 5px 10px;
    font-size: 11px;
}
QLabel#statusLabel {
    color: #888;
}
QLabel#imagePreviewLabel {
    background-color: #0A0A0A;
    border: 1px dashed #444;
    border-radius: 4px;
}
"""

class DecartApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LucidCam - Real-time AI Restyling")
        self.setMinimumSize(1000, 800)
        self.setStyleSheet(DARK_THEME)

        # Native settings persistence
        self.settings = QSettings("LucidCam", "AI_Restyler")

        # State
        self.realtime_client = None
        self.camera_thread = None
        self.vcam = None
        self.frame_emitter = FrameEmitter()
        self.frame_emitter.frame_received.connect(self.update_video_canvas)

        self.latest_transformed_frame = None
        self.output_task = None
        self.target_fps = 24
        
        # Image/reference support
        self.reference_image_path = None
        self.reference_image_data = None

        self.init_ui()
        self.load_settings()
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
        
        # Prompt Input with Image Upload
        prompt_layout = QHBoxLayout()
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Describe the style change...")
        
        self.upload_image_btn = QPushButton("📁 Upload Image")
        self.upload_image_btn.setObjectName("imageUploadBtn")
        self.upload_image_btn.clicked.connect(self.upload_reference_image)
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("applyBtn")
        self.apply_btn.clicked.connect(self.apply_prompt)
        
        prompt_layout.addWidget(self.prompt_input)
        prompt_layout.addWidget(self.upload_image_btn)
        prompt_layout.addWidget(self.apply_btn)
        control_panel.addLayout(prompt_layout)
        
        # Image Preview Area
        self.image_preview_container = QHBoxLayout()
        self.image_preview_label = QLabel()
        self.image_preview_label.setObjectName("imagePreviewLabel")
        self.image_preview_label.setFixedSize(80, 80)
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview_label.setText("No image")
        self.image_preview_label.setStyleSheet("""
            QLabel {
                background-color: #0A0A0A;
                border: 1px dashed #444;
                border-radius: 4px;
                font-size: 11px;
                color: #666;
            }
        """)
        
        self.image_info_label = QLabel("No image selected")
        self.image_info_label.setStyleSheet("color: #888; font-size: 11px;")
        
        self.clear_image_btn = QPushButton("✕")
        self.clear_image_btn.setObjectName("clearImageBtn")
        self.clear_image_btn.setFixedSize(30, 30)
        self.clear_image_btn.clicked.connect(self.clear_reference_image)
        self.clear_image_btn.setEnabled(False)
        
        self.image_preview_container.addWidget(self.image_preview_label)
        self.image_preview_container.addWidget(self.image_info_label)
        self.image_preview_container.addStretch()
        self.image_preview_container.addWidget(self.clear_image_btn)
        
        control_panel.addLayout(self.image_preview_container)

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
        self.status_label = QLabel(f"LucidCam v{VERSION} | Status: Disconnected")
        self.status_label.setObjectName("statusLabel")
        
        update_btn = QPushButton("Check for Updates")
        update_btn.setFixedWidth(150)
        update_btn.clicked.connect(self.check_for_updates_task)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        bottom_bar.addWidget(self.status_label)
        bottom_bar.addStretch()
        bottom_bar.addWidget(update_btn)
        bottom_bar.addWidget(self.connect_btn)
        control_panel.addLayout(bottom_bar)

        main_layout.addLayout(control_panel)

    # --- Image Upload and Management ---
    def upload_reference_image(self):
        """Open file dialog to select a reference image."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Images (*.jpg *.jpeg *.png *.bmp *.webp)")
        
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            file_path = file_dialog.selectedFiles()[0]
            self.load_reference_image(file_path)

    def load_reference_image(self, file_path):
        """Load and validate a reference image from file path."""
        try:
            file_path = Path(file_path)
            
            # Validate file exists
            if not file_path.exists():
                QMessageBox.warning(self, "Error", "File not found.")
                return
            
            # Validate file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > MAX_IMAGE_SIZE_MB:
                QMessageBox.warning(self, "Error", 
                    f"Image exceeds {MAX_IMAGE_SIZE_MB}MB limit. Current: {file_size_mb:.1f}MB")
                return
            
            # Validate file format
            if file_path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
                QMessageBox.warning(self, "Error", 
                    f"Unsupported format. Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}")
                return
            
            # Read and encode image
            with open(file_path, "rb") as f:
                self.reference_image_data = base64.b64encode(f.read()).decode("utf-8")
            
            self.reference_image_path = str(file_path)
            
            # Update UI preview
            pixmap = QPixmap(str(file_path))
            scaled_pixmap = pixmap.scaledToWidth(80, Qt.TransformationMode.SmoothTransformation)
            self.image_preview_label.setPixmap(scaled_pixmap)
            self.image_preview_label.setText("")
            
            # Update info label
            file_name = file_path.name
            self.image_info_label.setText(f"📷 {file_name}\n{file_size_mb:.1f}MB")
            
            # Enable clear button
            self.clear_image_btn.setEnabled(True)
            
            print(f"Reference image loaded: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
            print(f"Error loading image: {e}")

    def clear_reference_image(self):
        """Clear the loaded reference image."""
        self.reference_image_path = None
        self.reference_image_data = None
        self.image_preview_label.setPixmap(QPixmap())
        self.image_preview_label.setText("No image")
        self.image_info_label.setText("No image selected")
        self.clear_image_btn.setEnabled(False)
        print("Reference image cleared.")

    # --- Persistence Logic ---
    def load_settings(self):
        # Restore last prompt
        last_prompt = self.settings.value("last_prompt", "A cinematic portrait")
        self.prompt_input.setText(last_prompt)
        
        # Restore window geometry (size/position)
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        # Save settings on exit
        self.settings.setValue("last_prompt", self.prompt_input.text())
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

    # --- Update Logic ---
    @asyncSlot()
    async def check_for_updates_task(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(UPDATE_URL) as response:
                    if response.status == 200:
                        latest_version = (await response.text()).strip()
                        if latest_version > VERSION:
                            QMessageBox.information(self, "Update Available", 
                                f"A new version of LucidCam (v{latest_version}) is available!\n\nPlease visit the GitHub repo to download.")
                        else:
                            QMessageBox.information(self, "Up to Date", "You are running the latest version of LucidCam.")
                    else:
                        raise Exception(f"Server returned status {response.status}")
        except Exception as e:
            # We fail silently or with a quiet warning as this isn't critical for core app use
            print(f"Update check failed: {e}")
            QMessageBox.warning(self, "Update Check Failed", "Could not check for updates. Check your internet connection.")

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
            # 3. Setup Decart SDK
            model = models.realtime("lucy-2.1")
            client = DecartClient(api_key=api_key)
            
            target_width = getattr(model, "width", 1280)
            target_height = getattr(model, "height", 720)
            self.target_fps = getattr(model, "fps", 24)

            # 1. Initialize Virtual Camera
            try:
                self.vcam = pyvirtualcam.Camera(width=target_width, height=target_height, fps=self.target_fps)
                print(f"Virtual camera started: {self.vcam.device} ({target_width}x{target_height} @ {self.target_fps}fps)")
            except Exception as e:
                QMessageBox.critical(self, "Driver Missing", 
                    f"Could not start virtual camera. Please ensure OBS Virtual Camera or v4l2loopback is installed.\nError: {e}")
                self.reset_ui()
                return

            # 2. Start Camera Thread
            self.camera_thread = CameraThread(target_width=target_width, target_height=target_height)
            self.camera_thread.start()
            
            # Wait a bit for the camera to warm up
            await asyncio.sleep(1)
            if not self.camera_thread.running:
                raise Exception("Could not open local camera. It might be in use by another app.")

            local_track = LocalVideoStreamTrack(self.camera_thread)

            self.realtime_client = await RealtimeClient.connect(
                base_url=client.base_url,
                api_key=client.api_key,
                local_track=local_track,
                options=RealtimeConnectOptions(
                    model=model,
                    on_remote_stream=self.handle_remote_stream,
                    initial_state=ModelState(
                        prompt=self.build_prompt(),
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
        
        if self.output_task:
            self.output_task.cancel()
            self.output_task = None

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
        Callback from Decart SDK.
        """
        async def receive_frames():
            try:
                async for frame in transformed_stream:
                    self.latest_transformed_frame = frame
            except Exception as e:
                print(f"Error receiving remote stream: {e}")

        async def run_output_loop():
            # Target FPS for the virtual camera output
            frame_time = 1 / float(self.target_fps)
            while True:
                start_time = asyncio.get_event_loop().time()
                
                try:
                    if self.latest_transformed_frame:
                        # 1. Update UI (Thread-safe via Signal)
                        self.frame_emitter.emit_frame(self.latest_transformed_frame)

                        # 2. Update Virtual Camera
                        if self.vcam:
                            img_rgb = self.latest_transformed_frame.to_ndarray(format="rgb24")
                            self.vcam.send(img_rgb)
                except Exception as e:
                    print(f"Error in output loop: {e}")
                
                # Sleep to maintain constant FPS, even if API is slow (simulates frozen frame)
                elapsed = asyncio.get_event_loop().time() - start_time
                await asyncio.sleep(max(0.001, frame_time - elapsed))

        # Start both the receiver and the output pump
        asyncio.create_task(receive_frames())
        self.output_task = asyncio.create_task(run_output_loop())

    @pyqtSlot(QImage)
    def update_video_canvas(self, q_img):
        pixmap = QPixmap.fromImage(q_img)
        # Scale pixmap to fit label while keeping aspect ratio
        scaled_pixmap = pixmap.scaled(self.video_canvas.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.video_canvas.setPixmap(scaled_pixmap)

    # --- Prompt Building ---
    def build_prompt(self):
        """
        Build a Prompt object with both text and optional image data.
        Returns a Decart Prompt object compatible with the RealtimeClient.
        """
        prompt_text = self.prompt_input.text() or "A cinematic portrait"
        
        # Create base Prompt with text
        prompt_dict = {"text": prompt_text}
        
        # Add image data if available
        if self.reference_image_data:
            prompt_dict["image"] = self.reference_image_data
            print(f"Building prompt with text and reference image ({len(self.reference_image_data)} bytes encoded)")
        else:
            print(f"Building prompt with text only: {prompt_text}")
        
        return Prompt(**prompt_dict)

    # --- UI Actions ---
    @asyncSlot()
    async def apply_prompt(self):
        """
        Apply the current prompt (text + optional image) to the Decart realtime stream.
        Supports both text-only and text+image prompts.
        """
        if not self.realtime_client or not self.realtime_client.is_connected:
            QMessageBox.warning(self, "Warning", "Not connected. Please click Connect first.")
            return
        
        try:
            prompt_text = self.prompt_input.text()
            if not prompt_text.strip():
                QMessageBox.warning(self, "Warning", "Please enter a prompt description.")
                return
            
            # Build prompt with text and optional image
            prompt = self.build_prompt()
            
            # Send to Decart API
            await self.realtime_client.set_prompt(prompt)
            
            # Update status with prompt info
            status_text = f"Status: Live (Prompt: {prompt_text}"
            if self.reference_image_data:
                status_text += " + 📷 Reference Image"
            status_text += ")"
            self.status_label.setText(status_text)
            
            print(f"Prompt applied successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply prompt: {str(e)}")
            print(f"Error applying prompt: {e}")

    def set_preset(self, text):
        self.prompt_input.setText(f"Transform the video into {text} style")
        # Trigger apply
        asyncio.create_task(self.apply_prompt())

if __name__ == "__main__":
    # High DPI scaling support
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    app.setApplicationName("LucidCam")
    app.setApplicationVersion(VERSION)
    
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = DecartApp()
    window.show()

    with loop:
        loop.run_forever()
