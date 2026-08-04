# 🎭 LucidCam

Transform your live webcam feed into a work of art using **Decart AI's Lucy 2.5** realtime video model. **LucidCam** provides a real-time, AI-powered video restyler and character replacer that you can pipe directly into Zoom, OBS, or Teams via a Virtual Camera.

Published by **greatware** | Version 1.0.0

---

## ✨ Features

*   **Real-time AI Inference:** Ultra-low latency video restyling using WebRTC powered by Decart Lucy 2.5.
*   **Lucy 2.5 Prompting Guide Engine:** Automatic prompt structuring for character replacement, attribute changes, scene restyling, and object additions alongside Decart's prompt enhancer (`enhance=True`).
*   **Character Replacer & Reference Images:** Attach reference images and match specific identification features (hair, outfit, face, glasses, accessories).
*   **One-Click Installation:** Automatic virtual environment setup and dependency management.
*   **Virtual Camera Output:** Seamless integration with standard video conferencing software (OBS Virtual Camera / pyvirtualcam).
*   **Modern Dark UI:** Intuitive, mobile-inspired design built with PyQt6.
*   **Secure Credential Storage:** API keys are stored securely in your OS-native keychain.
*   **Optimized Pipeline:** Uses a non-blocking frame strategy to maintain real-time performance.

---

## 🚀 Quick Start (One-Click)

### **Windows**
1.  **Install Python:** Download from [python.org](https://www.python.org/) (ensure "Add to PATH" is checked).
2.  **Install OBS:** Download [OBS Studio](https://obsproject.com/) (required for the Virtual Camera driver).
3.  **Run:** Double-click **`run.bat`**.

---

## 📦 Building Executable & Installer

To build the standalone executable and Windows installer package:

```bash
python build.py
```

`build.py` automatically generates:
1. **PyInstaller Application Folder:** `dist/LucidCam/LucidCam.exe`
2. **Portable ZIP Archive:** `dist/LucidCam-v1.0.0-portable.zip`
3. **Windows Setup Installer:** `installer_output/LucidCam_Setup_v1.0.0.exe` (via Inno Setup script `installer.iss`)

---

## 🛠️ Prerequisites & Drivers

| OS | Driver Requirement | Source |
| :--- | :--- | :--- |
| **Windows** | OBS Virtual Camera | Included in [OBS Studio](https://obsproject.com/) |
| **Linux** | v4l2loopback | `sudo apt install v4l2loopback-dkms` |
| **macOS** | OBS Virtual Camera | Included in [OBS Studio](https://obsproject.com/) |

---

## 💡 How to Use

1.  **Launch:** Run `run.bat` or run `LucidCam.exe`.
2.  **API Key:** Enter your Decart API key at the top. Click **Save Key** to store it securely.
3.  **Connect:** Click **Connect**. Your physical webcam will activate and connect to Decart AI.
4.  **Style & Prompts:**
    *   **Custom Prompt:** Type any prompt formatted with Lucy 2.5 templates (e.g. *"Replace the character in the video with an astronaut."*).
    *   **Reference Image:** Upload an image to match identification features (*"short curly hair, green jacket"*).
    *   **Presets:** Choose from top built-in presets (*Reference Replacer*, *Albert Einstein*, *Tuxedo*, *Hot Blonde Girl*).
5.  **Go Live:** Open Zoom/Teams/OBS, go to Settings -> Video, and select **"OBS Virtual Camera"** or **"pyvirtualcam"**.

---

## 🔍 Diagnostic Tool

If you encounter issues, run the diagnostic tool:
```bash
python diagnostics.py
```

---

## 🤓 Technical Architecture

*   **Async Core:** Managed via `qasync`, integrating PyQt6 UI and WebRTC `asyncio` event loops seamlessly.
*   **Decart Lucy 2.5 Handler:** Formats prompt inputs according to Decart's official Lucy 2.5 prompt guide templates, removing low-value buzzwords and optimizing prompt enhancer output.
*   **Video Pipeline:** Custom `aiortc.MediaStreamTrack` streaming BGR frames in real-time with automatic oldest-frame dropping.
