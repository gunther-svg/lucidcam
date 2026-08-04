# 🎭 LucidCam

[![Release](https://img.shields.io/badge/release-v1.0.1-blue.svg)](https://github.com/gunther-svg/lucidcam/releases/tag/v1.0.1)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](#-prerequisites--drivers)

Transform your live webcam feed into a work of art using **Decart AI's Lucy 2.5** real-time video model. **LucidCam** provides a real-time, AI-powered video restyler and character replacer that you can pipe directly into Zoom, OBS, or Teams via a Virtual Camera.

Published by **greatware** | **Version 1.0.1**

---

## ✨ Key Features

* ⚡ **Real-Time AI Inference:** Ultra-low latency video restyling using WebRTC powered by Decart Lucy 2.5.
* 🧙 **GTK/GNOME Adwaita Setup Wizard:** Interactive 5-screen setup and onboarding wizard with dependency checking and status badges.
* 🧠 **Lucy 2.5 Prompting Engine:** Built-in prompt optimizer that structures requests for character replacement, attribute modifications, scene restyling, and object additions alongside Decart's prompt enhancer (`enhance=True`).
* 🖼️ **Character Replacer & Reference Images:** Attach reference images and match specific identification features (hair style/color, outfit, facial features, accessories).
* 🎥 **Virtual Camera Integration:** Broadcast your restyled video feed directly to OBS Virtual Camera, Zoom, Microsoft Teams, Discord, and Google Meet (`pyvirtualcam`).
* 🎨 **Modern Dark UI:** Intuitive, responsive desktop application built with PyQt6.
* 🔑 **Secure Credential Storage:** API keys are stored securely using your OS-native keyring/keychain.
* 🚀 **Optimized Pipeline:** Non-blocking async frame processing (`qasync`) ensures smooth, real-time video playback without dropped frames.
* 🔄 **Auto-Update Checker:** Notifies you automatically when new package releases are published.

---

## 📥 Downloads & Installation (v1.0.1)

Choose the setup method that works best for you:

### Option 1: Standalone Windows Setup Installer (Recommended)
1. Download **`LucidCam_Setup_v1.0.1.exe`** from the [v1.0.1 GitHub Release](https://github.com/gunther-svg/lucidcam/releases/tag/v1.0.1).
2. Run the installer and follow the setup wizard.
3. Launch **LucidCam** from your Start Menu or Desktop shortcut.

### Option 2: Portable Zip Package
1. Download **`LucidCam-v1.0.1-portable.zip`** from [Releases](https://github.com/gunther-svg/lucidcam/releases/tag/v1.0.1).
2. Extract the archive to any directory.
3. Double-click **`LucidCam.exe`** inside the extracted folder.

### Option 3: Run from Source (Developers)
```bash
# Clone the repository
git clone https://github.com/gunther-svg/lucidcam.git
cd lucidcam

# Run the automated setup and launcher
run.bat    # Windows
# OR
./run.sh   # Linux / macOS
```

---

## 🛠️ Prerequisites & Drivers

LucidCam requires a Virtual Camera driver to route the AI feed to video conferencing software:

| OS | Driver Requirement | Installation Link / Command |
| :--- | :--- | :--- |
| **Windows** | OBS Virtual Camera | Included automatically in [OBS Studio](https://obsproject.com/) |
| **Linux** | v4l2loopback | `sudo apt install v4l2loopback-dkms` |
| **macOS** | OBS Virtual Camera | Included automatically in [OBS Studio](https://obsproject.com/) |

---

## 💡 How to Use

1. **Launch LucidCam** (via Installed Shortcut, `LucidCam.exe`, or `run.bat`).
2. **API Key Setup:** Enter your Decart API key in the API Key field and click **Save Key**. It will be securely stored in your OS keyring.
3. **Connect Feed:** Click **Connect**. LucidCam initializes your webcam and establishes a real-time WebRTC session with Decart AI.
4. **Apply Restyling & Prompts:**
   * **Custom Prompt:** Type any descriptive prompt formatted for Lucy 2.5 (e.g., *"Replace the character in the video with an astronaut in a detailed sci-fi suit."*).
   * **Reference Image:** Upload an image to lock character identification features (*"short curly hair, green leather jacket"*).
   * **Presets:** Click any preset button (*Reference Replacer*, *Albert Einstein*, *Tuxedo*, *Cyberpunk*).
5. **Stream to Apps:** Open Zoom, Teams, Discord, or OBS Studio -> Go to **Video Settings** -> Select **"OBS Virtual Camera"** or **"pyvirtualcam"** as your camera source.

---

## 🏗️ Building Executable & Package Bundles

To build the standalone executable, portable ZIP, and Inno Setup installer from source:

```bash
python build.py
```

`build.py` automatically generates:
1. **PyInstaller Application Folder:** `dist/LucidCam/LucidCam.exe`
2. **Portable ZIP Archive:** `dist/LucidCam-v1.0.0-portable.zip`
3. **Windows Setup Installer:** `installer_output/LucidCam_Setup_v1.0.0.exe` *(requires Inno Setup)*

---

## 🔍 Diagnostic & Troubleshooting Tool

If you encounter issues with camera permissions, WebRTC streaming, or virtual camera drivers:

```bash
python diagnostics.py
```

This diagnostic utility verifies:
* Physical camera availability
* OBS Virtual Camera driver status
* Network connectivity to Decart AI (`api.decart.ai`)
* OS Keyring credentials storage

---

## 🤓 Technical Architecture

* **Event Loop Integration:** Built with `PyQt6` and `qasync` to run PyQt's event loop and `asyncio` WebRTC tasks on a single thread safely.
* **Prompt Handler:** `prompt_handler.py` strictly follows Decart's official Lucy 2.5 prompting guidelines to optimize live model output.
* **Low-Latency Video Pipeline:** `video_pipeline.py` implements custom frame capture with automatic drop strategies for zero frame buffering.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
