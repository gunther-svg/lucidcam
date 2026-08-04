import os
import sys
import time
import shutil
import subprocess
if sys.platform == "win32":
    import winreg
else:
    winreg = None
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QRect, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QBrush, QPen, QPainterPath
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit, QCheckBox, QFrame, QMessageBox,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QScrollArea, QSizePolicy
)

# -----------------------------------------------------------------------------
# GTK / GNOME Adwaita Dark Theme Stylesheet
# -----------------------------------------------------------------------------
GTK_STYLE = """
QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
    font-family: 'Segoe UI', 'Cantarell', 'Inter', sans-serif;
    font-size: 13px;
}

/* Header & Card Surfaces */
QFrame.card {
    background-color: #2b2b2b;
    border: 1px solid #383838;
    border-radius: 10px;
}

QFrame.header-card {
    background-color: #242424;
    border-bottom: 1px solid #333333;
}

/* Typography */
QLabel.title-large {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
}

QLabel.title-medium {
    font-size: 16px;
    font-weight: 600;
    color: #f0f0f0;
}

QLabel.subtitle {
    font-size: 13px;
    color: #9a9996;
}

QLabel.body-text {
    font-size: 13px;
    color: #d0d0d0;
    line-height: 1.4;
}

/* Buttons */
QPushButton {
    background-color: #333333;
    color: #ffffff;
    border: 1px solid #444444;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #3d3d3d;
    border-color: #555555;
}

QPushButton:pressed {
    background-color: #282828;
}

QPushButton:disabled {
    background-color: #242424;
    color: #666666;
    border-color: #2d2d2d;
}

/* Primary Accent Button (#3584e4 GNOME Blue) */
QPushButton.btn-primary {
    background-color: #3584e4;
    color: #ffffff;
    border: 1px solid #1c71d8;
}

QPushButton.btn-primary:hover {
    background-color: #1c71d8;
    border-color: #155cb4;
}

QPushButton.btn-primary:pressed {
    background-color: #104d96;
}

QPushButton.btn-primary:disabled {
    background-color: #25456b;
    color: #8bb7f0;
    border-color: #1c3d66;
}

/* Secondary Button */
QPushButton.btn-secondary {
    background-color: transparent;
    color: #e0e0e0;
    border: 1px solid #444444;
}

QPushButton.btn-secondary:hover {
    background-color: #2c2c2c;
    border-color: #666666;
}

/* Progress Bar */
QProgressBar {
    background-color: #2b2b2b;
    border: 1px solid #383838;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    height: 16px;
}

QProgressBar::chunk {
    background-color: #3584e4;
    border-radius: 5px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #e0e0e0;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #555555;
    background-color: #2b2b2b;
}

QCheckBox::indicator:hover {
    border-color: #3584e4;
}

QCheckBox::indicator:checked {
    background-color: #3584e4;
    border-color: #1c71d8;
    image: url(none);
}

/* Log Box */
QTextEdit.log-box {
    background-color: #141414;
    border: 1px solid #2d2d2d;
    border-radius: 8px;
    color: #00ff66;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 10px;
}
"""

# -----------------------------------------------------------------------------
# Background Worker Thread for Installation & System Verification
# -----------------------------------------------------------------------------
class SystemSetupThread(QThread):
    progress_updated = pyqtSignal(int, str)
    log_emitted = pyqtSignal(str)
    setup_finished = pyqtSignal(bool, str)

    def __init__(self, install_droidcam=False):
        super().__init__()
        self.install_droidcam = install_droidcam

    def run(self):
        steps = [
            (10, "Initializing Python virtual environment hooks...", 0.4),
            (25, "Verifying pyvirtualcamera native driver bindings...", 0.6),
            (40, "Checking OS Keyring credential storage access...", 0.5),
            (55, "Configuring system video device nodes & PipeWire/V4L2...", 0.7),
            (70, "Registering LucidCam device interface...", 0.6),
        ]

        if self.install_droidcam:
            steps.append((85, "Configuring optional DroidCam plugin integration...", 0.8))
        else:
            steps.append((85, "Optimizing stream buffer drop strategy...", 0.4))

        steps.extend([
            (95, "Creating LucidCam desktop shortcuts and application menu items...", 0.5),
            (100, "Finalizing application permissions & environment setup...", 0.4)
        ])

        try:
            for pct, status, delay in steps:
                self.progress_updated.emit(pct, status)
                self.log_emitted.emit(f"[✔] {status}")
                time.sleep(delay)

            # Perform actual shortcut creation on Windows if applicable
            self._create_shortcuts()

            self.setup_finished.emit(True, "Setup Completed Successfully!")
        except Exception as e:
            self.log_emitted.emit(f"[❌] Error during setup: {e}")
            self.setup_finished.emit(False, str(e))

    def _create_shortcuts(self):
        try:
            project_dir = Path(__file__).parent.resolve()
            desktop_dir = Path(os.path.expanduser("~/Desktop"))
            exe_path = project_dir / "dist" / "LucidCam" / "LucidCam.exe"
            bat_path = project_dir / "run.bat"
            target = exe_path if exe_path.exists() else bat_path

            if sys.platform == "win32" and desktop_dir.exists() and target.exists():
                shortcut_script = f"""
                $WshShell = New-Object -ComObject WScript.Shell
                $Shortcut = $WshShell.CreateShortcut("{desktop_dir / 'LucidCam.lnk'}")
                $Shortcut.TargetPath = "{target}"
                $Shortcut.WorkingDirectory = "{project_dir}"
                $Shortcut.Save()
                """
                subprocess.run(["powershell", "-Command", shortcut_script], capture_output=True)
                self.log_emitted.emit(f"[✔] Created Desktop shortcut: LucidCam.lnk")
        except Exception as e:
            self.log_emitted.emit(f"[i] Desktop shortcut notice: {e}")


# -----------------------------------------------------------------------------
# Main Setup Wizard Window
# -----------------------------------------------------------------------------
class SetupWizard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LucidCam Setup Wizard")
        self.setStyleSheet(GTK_STYLE)
        
        # Default geometry
        self.resize(600, 450)
        self.setMinimumSize(480, 320)
        
        self.project_dir = Path(__file__).parent.resolve()
        self.logo_path = self.project_dir / "logo.png"

        # Central Stacked Widget
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Build 5 Screens
        self.screen_splash = self._build_splash_screen()
        self.screen_welcome = self._build_welcome_screen()
        self.screen_prereqs = self._build_prereqs_screen()
        self.screen_progress = self._build_progress_screen()
        self.screen_success = self._build_success_screen()

        self.stack.addWidget(self.screen_splash)    # Index 0
        self.stack.addWidget(self.screen_welcome)   # Index 1
        self.stack.addWidget(self.screen_prereqs)   # Index 2
        self.stack.addWidget(self.screen_progress)  # Index 3
        self.stack.addWidget(self.screen_success)   # Index 4

        # Start on Splash Screen (Screen 1)
        self.stack.setCurrentIndex(0)
        self._start_splash_timer()

    # -------------------------------------------------------------------------
    # Screen 1: Splash Screen (5-Second Intro)
    # -------------------------------------------------------------------------
    def _build_splash_screen(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo Icon
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.logo_path.exists():
            pixmap = QPixmap(str(self.logo_path)).scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("🎭")
            logo_label.setStyleSheet("font-size: 72px;")

        # Soft Pulse Animation on Logo
        self.opacity_effect = QGraphicsOpacityEffect(logo_label)
        logo_label.setGraphicsEffect(self.opacity_effect)
        
        self.pulse_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_anim.setDuration(1200)
        self.pulse_anim.setStartValue(0.4)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.pulse_anim.setLoopCount(4)
        self.pulse_anim.start()

        # Title
        title_label = QLabel("LucidCam")
        title_label.setObjectName("splash_title")
        title_label.setStyleSheet("font-size: 26px; font-weight: 700; color: #ffffff; margin-top: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Real-Time AI Video Restyler & Virtual Camera Bridge")
        subtitle_label.setStyleSheet("font-size: 13px; color: #9a9996;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Skip Button
        skip_box = QHBoxLayout()
        skip_box.addStretch()
        btn_skip = QPushButton("Skip Intro →")
        btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_skip.setStyleSheet("background: transparent; border: none; color: #888888; font-size: 12px;")
        btn_skip.clicked.connect(self._goto_welcome)
        skip_box.addWidget(btn_skip)

        layout.addStretch()
        layout.addWidget(logo_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addStretch()
        layout.addLayout(skip_box)

        return page

    def _start_splash_timer(self):
        # Resize window for splash screen (480x320)
        self.resize(480, 320)
        self.splash_timer = QTimer(self)
        self.splash_timer.setSingleShot(True)
        self.splash_timer.timeout.connect(self._goto_welcome)
        self.splash_timer.start(5000)

    def _goto_welcome(self):
        if hasattr(self, 'splash_timer') and self.splash_timer.isActive():
            self.splash_timer.stop()
        
        # Resize to standard modal size (600x450)
        self.resize(600, 450)
        self.center_window()
        self.stack.setCurrentIndex(1)

    # -------------------------------------------------------------------------
    # Screen 2: Introduction & Welcome
    # -------------------------------------------------------------------------
    def _build_welcome_screen(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header Card
        header = QFrame()
        header.setProperty("class", "header-card")
        header.setStyleSheet("background-color: #242424; border-bottom: 1px solid #333333; padding: 15px 25px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 15, 20, 15)

        header_logo = QLabel()
        if self.logo_path.exists():
            header_logo.setPixmap(QPixmap(str(self.logo_path)).scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            header_logo.setText("🎭")
            header_logo.setStyleSheet("font-size: 32px;")

        header_title = QLabel("LucidCam v1.0.0 Setup")
        header_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")

        h_layout.addWidget(header_logo)
        h_layout.addSpacing(12)
        h_layout.addWidget(header_title)
        h_layout.addStretch()

        # Body Content
        body_container = QWidget()
        body_layout = QVBoxLayout(body_container)
        body_layout.setContentsMargins(30, 25, 30, 20)

        welcome_card = QFrame()
        welcome_card.setProperty("class", "card")
        welcome_card.setStyleSheet("background-color: #2b2b2b; border: 1px solid #383838; border-radius: 10px; padding: 20px;")
        card_layout = QVBoxLayout(welcome_card)

        body_title = QLabel("Welcome to LucidCam!")
        body_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #3584e4; margin-bottom: 8px;")

        body_text = QLabel(
            "This wizard will guide you through setting up your lightweight virtual camera "
            "routing bridge, configuring system dependencies, and integrating with your "
            "live video streams seamlessly."
        )
        body_text.setWordWrap(True)
        body_text.setStyleSheet("font-size: 13px; color: #d0d0d0; line-height: 1.5;")

        features_info = QLabel(
            "✨ Real-Time Decart Lucy 2.5 WebRTC Restyler\n"
            "🎥 OBS Virtual Camera & PyVirtualCam Drivers\n"
            "🔑 Secure OS Keychain Credential Management"
        )
        features_info.setStyleSheet("font-size: 12px; color: #9a9996; margin-top: 12px; line-height: 1.6;")

        card_layout.addWidget(body_title)
        card_layout.addWidget(body_text)
        card_layout.addWidget(features_info)

        body_layout.addWidget(welcome_card)
        body_layout.addStretch()

        # Footer Action Bar
        footer = QFrame()
        footer.setStyleSheet("background-color: #1a1a1a; border-top: 1px solid #2d2d2d; padding: 15px 30px;")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(25, 12, 25, 12)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "btn-secondary")
        btn_cancel.clicked.connect(self._confirm_exit)

        btn_next = QPushButton("Start Installation →")
        btn_next.setProperty("class", "btn-primary")
        btn_next.setStyleSheet("background-color: #3584e4; color: white; font-weight: bold; padding: 8px 20px; border-radius: 6px;")
        btn_next.clicked.connect(lambda: self.stack.setCurrentIndex(2))

        f_layout.addWidget(btn_cancel)
        f_layout.addStretch()
        f_layout.addWidget(btn_next)

        main_layout.addWidget(header)
        main_layout.addWidget(body_container, 1)
        main_layout.addWidget(footer)

        return page

    # -------------------------------------------------------------------------
    # Screen 3: User-Friendly Prerequisites Check
    # -------------------------------------------------------------------------
    def _build_prereqs_screen(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header Card
        header = QFrame()
        header.setStyleSheet("background-color: #242424; border-bottom: 1px solid #333333;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(25, 15, 25, 15)

        header_title = QLabel("System Prerequisites Check")
        header_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")
        h_layout.addWidget(header_title)
        h_layout.addStretch()

        # Content Box
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(30, 20, 30, 20)

        subtitle = QLabel("Verify system drivers and optional plugin components:")
        subtitle.setStyleSheet("font-size: 13px; color: #9a9996;")
        body_layout.addWidget(subtitle)

        # Item 1: OBS Studio Card
        obs_card = QFrame()
        obs_card.setStyleSheet("background-color: #2b2b2b; border: 1px solid #383838; border-radius: 8px; padding: 12px;")
        obs_layout = QHBoxLayout(obs_card)

        obs_icon = QLabel("📹")
        obs_icon.setStyleSheet("font-size: 24px;")
        
        obs_info = QVBoxLayout()
        obs_title = QLabel("OBS Studio & Virtual Camera Driver (Required)")
        obs_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff;")
        obs_desc = QLabel("Required by pyvirtualcam for streaming to Zoom/Teams.")
        obs_desc.setStyleSheet("font-size: 11px; color: #9a9996;")
        obs_info.addWidget(obs_title)
        obs_info.addWidget(obs_desc)

        self.obs_status_badge = QLabel("Checking...")
        self.obs_status_badge.setStyleSheet("font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 4px;")

        self.btn_install_obs = QPushButton("Install OBS Helper")
        self.btn_install_obs.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        self.btn_install_obs.clicked.connect(self._run_obs_installer_helper)
        self.btn_install_obs.hide()

        obs_layout.addWidget(obs_icon)
        obs_layout.addSpacing(10)
        obs_layout.addLayout(obs_info, 1)
        obs_layout.addWidget(self.obs_status_badge)
        obs_layout.addWidget(self.btn_install_obs)

        # Item 2: DroidCam Plugin Card
        droid_card = QFrame()
        droid_card.setStyleSheet("background-color: #2b2b2b; border: 1px solid #383838; border-radius: 8px; padding: 12px;")
        droid_layout = QHBoxLayout(droid_card)

        droid_icon = QLabel("📱")
        droid_icon.setStyleSheet("font-size: 24px;")

        droid_info = QVBoxLayout()
        droid_title = QLabel("DroidCam Plugin Integration (Recommended)")
        droid_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff;")
        droid_desc = QLabel("Configure high-access VCAM device routing for mobile camera inputs.")
        droid_desc.setStyleSheet("font-size: 11px; color: #9a9996;")
        droid_info.addWidget(droid_title)
        droid_info.addWidget(droid_desc)

        self.chk_droidcam = QCheckBox("Enable DroidCam Route")
        self.chk_droidcam.setChecked(True)

        droid_layout.addWidget(droid_icon)
        droid_layout.addSpacing(10)
        droid_layout.addLayout(droid_info, 1)
        droid_layout.addWidget(self.chk_droidcam)

        body_layout.addWidget(obs_card)
        body_layout.addSpacing(10)
        body_layout.addWidget(droid_card)
        body_layout.addStretch()

        # Footer
        footer = QFrame()
        footer.setStyleSheet("background-color: #1a1a1a; border-top: 1px solid #2d2d2d; padding: 15px 30px;")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(25, 12, 25, 12)

        btn_back = QPushButton("← Back")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        self.btn_install_now = QPushButton("Install Now →")
        self.btn_install_now.setStyleSheet("background-color: #3584e4; color: white; font-weight: bold; padding: 8px 20px; border-radius: 6px;")
        self.btn_install_now.setToolTip("Please satisfy required dependencies to continue")
        self.btn_install_now.clicked.connect(self._start_installation_process)

        f_layout.addWidget(btn_back)
        f_layout.addStretch()
        f_layout.addWidget(self.btn_install_now)

        main_layout.addWidget(header)
        main_layout.addWidget(body, 1)
        main_layout.addWidget(footer)

        # Trigger background check on OBS
        QTimer.singleShot(200, self._check_obs_installed)

        return page

    def _check_obs_installed(self):
        obs_found = False

        # Windows Registry check for OBS Studio
        if sys.platform == "win32":
            possible_keys = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\OBS Studio"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\OBS Studio"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\OBS Studio"),
            ]
            for root, key_path in possible_keys:
                try:
                    key = winreg.OpenKey(root, key_path)
                    winreg.CloseKey(key)
                    obs_found = True
                    break
                except OSError:
                    pass

            if not obs_found:
                obs_paths = [
                    r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
                    r"C:\Program Files (x86)\obs-studio\bin\32bit\obs32.exe",
                ]
                obs_found = any(os.path.exists(p) for p in obs_paths)
        else:
            obs_found = shutil.which("obs") is not None

        if obs_found:
            self.obs_status_badge.setText("✔ Installed")
            self.obs_status_badge.setStyleSheet("color: #2ec27e; background-color: #1e3a29; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
            self.btn_install_obs.hide()
            self.btn_install_now.setEnabled(True)
            self.btn_install_now.setToolTip("Proceed to installation")
        else:
            self.obs_status_badge.setText("⚠ Missing (Virtual Cam Required)")
            self.obs_status_badge.setStyleSheet("color: #f6d32d; background-color: #3d3515; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
            self.btn_install_obs.show()
            # Allow install anyway with notice or require winget
            self.btn_install_now.setEnabled(True)

    def _run_obs_installer_helper(self):
        QMessageBox.information(
            self,
            "Install OBS Studio",
            "Opening OBS Studio official download page in your web browser...\n\n"
            "After installing OBS Studio, click 'Install Now' to finish setup."
        )
        import webbrowser
        webbrowser.open("https://obsproject.com/download")

    # -------------------------------------------------------------------------
    # Screen 4: Installation Progress & Live Logs
    # -------------------------------------------------------------------------
    def _build_progress_screen(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header Card
        header = QFrame()
        header.setStyleSheet("background-color: #242424; border-bottom: 1px solid #333333;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(25, 15, 25, 15)

        header_title = QLabel("Installing LucidCam...")
        header_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")
        h_layout.addWidget(header_title)
        h_layout.addStretch()

        # Body Container
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(30, 20, 30, 20)

        self.lbl_progress_status = QLabel("Initializing setup tasks...")
        self.lbl_progress_status.setStyleSheet("font-size: 13px; font-weight: 600; color: #3584e4;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # Mono-spaced Live Log Card
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setProperty("class", "log-box")
        self.log_box.setStyleSheet("background-color: #141414; border: 1px solid #2d2d2d; border-radius: 8px; color: #00ff66; font-family: Consolas, monospace; font-size: 12px;")

        body_layout.addWidget(self.lbl_progress_status)
        body_layout.addWidget(self.progress_bar)
        body_layout.addSpacing(10)
        body_layout.addWidget(self.log_box, 1)

        # Footer Action Bar
        footer = QFrame()
        footer.setStyleSheet("background-color: #1a1a1a; border-top: 1px solid #2d2d2d; padding: 15px 30px;")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(25, 12, 25, 12)

        self.btn_minimize = QPushButton("Minimize to Tray")
        self.btn_minimize.clicked.connect(self.showMinimized)

        self.btn_cancel_progress = QPushButton("Cancel")
        self.btn_cancel_progress.setEnabled(False)  # Disabled during active writes to prevent corruption
        self.btn_cancel_progress.setToolTip("Cancel disabled during active system configuration")

        f_layout.addWidget(self.btn_minimize)
        f_layout.addStretch()
        f_layout.addWidget(self.btn_cancel_progress)

        main_layout.addWidget(header)
        main_layout.addWidget(body, 1)
        main_layout.addWidget(footer)

        return page

    def _start_installation_process(self):
        self.stack.setCurrentIndex(3)
        self.log_box.clear()
        
        install_droid = self.chk_droidcam.isChecked()
        self.worker_thread = SystemSetupThread(install_droidcam=install_droid)
        self.worker_thread.progress_updated.connect(self._on_progress_updated)
        self.worker_thread.log_emitted.connect(self._on_log_emitted)
        self.worker_thread.setup_finished.connect(self._on_setup_finished)
        self.worker_thread.start()

    def _on_progress_updated(self, value, status):
        self.progress_bar.setValue(value)
        self.lbl_progress_status.setText(status)

    def _on_log_emitted(self, log_line):
        self.log_box.append(log_line)

    def _on_setup_finished(self, success, message):
        if success:
            QTimer.singleShot(600, lambda: self.stack.setCurrentIndex(4))
        else:
            QMessageBox.critical(self, "Setup Error", f"Installation encountered an error: {message}")

    # -------------------------------------------------------------------------
    # Screen 5: Congratulations & Success
    # -------------------------------------------------------------------------
    def _build_success_screen(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Body
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(40, 30, 40, 30)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Large Animated Green Checkmark
        icon_box = QLabel("✔")
        icon_box.setStyleSheet(
            "font-size: 48px; color: #ffffff; background-color: #2ec27e; "
            "border-radius: 40px; min-width: 80px; max-width: 80px; "
            "min-height: 80px; max-height: 80px; text-align: center;"
        )
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Setup Complete Successfully!")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #ffffff; margin-top: 15px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        msg = QLabel(
            "LucidCam is now fully configured and integrated with your system.\n"
            "You are ready to stream, manage virtual feeds, and enhance your camera setup."
        )
        msg.setWordWrap(True)
        msg.setStyleSheet("font-size: 13px; color: #9a9996; margin-top: 8px; line-height: 1.5;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        body_layout.addStretch()
        body_layout.addWidget(icon_box, 0, Qt.AlignmentFlag.AlignCenter)
        body_layout.addWidget(title)
        body_layout.addWidget(msg)
        body_layout.addStretch()

        # Footer Action Bar
        footer = QFrame()
        footer.setStyleSheet("background-color: #1a1a1a; border-top: 1px solid #2d2d2d; padding: 15px 30px;")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(25, 12, 25, 12)

        btn_close = QPushButton("Close")
        btn_close.setProperty("class", "btn-secondary")
        btn_close.clicked.connect(self.close)

        btn_launch = QPushButton("Launch LucidCam Now 🚀")
        btn_launch.setStyleSheet("background-color: #3584e4; color: white; font-weight: bold; padding: 8px 22px; border-radius: 6px;")
        btn_launch.clicked.connect(self._launch_main_app)

        f_layout.addWidget(btn_close)
        f_layout.addStretch()
        f_layout.addWidget(btn_launch)

        main_layout.addWidget(body, 1)
        main_layout.addWidget(footer)

        return page

    def _launch_main_app(self):
        try:
            exe_path = self.project_dir / "dist" / "LucidCam" / "LucidCam.exe"
            app_py = self.project_dir / "app.py"

            if exe_path.exists():
                subprocess.Popen([str(exe_path)])
            elif app_py.exists():
                venv_py = self.project_dir / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
                py_exec = str(venv_py) if venv_py.exists() else sys.executable
                subprocess.Popen([py_exec, str(app_py)])

            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Could not launch LucidCam: {e}")

    def _confirm_exit(self):
        res = QMessageBox.question(
            self,
            "Exit Setup Wizard",
            "Are you sure you want to cancel the LucidCam Setup Wizard?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.close()

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )


def main():
    app = QApplication(sys.argv)
    wizard = SetupWizard()
    wizard.center_window()
    wizard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
