# 🎭 LucidCam

Transform your live webcam feed into a work of art using **Decart AI's Lucy 2.1** model. **LucidCam** provides a real-time, AI-powered "filter" that you can pipe directly into Zoom, OBS, or Teams via a Virtual Camera.

---

## ✨ Features

*   **Real-time AI Inference:** Ultra-low latency video restyling using WebRTC.
*   **One-Click Installation:** Automatic virtual environment and dependency management.
*   **Virtual Camera Output:** Seamless integration with standard video conferencing software.
*   **Modern Dark UI:** Intuitive, mobile-inspired design built with PyQt6.
*   **Secure Credential Storage:** API keys are stored in your OS-native keychain (Keychain/Windows Credential Locker).
*   **Optimized Pipeline:** Uses a "Drop-Oldest" frame strategy to prevent lag accumulation.
*   **Built-in Diagnostics:** Integrated tool to verify your hardware and drivers before you go live.

---

## 🚀 Quick Start (One-Click)

### **Windows**
1.  **Install Python:** Download from [python.org](https://www.python.org/) (ensure "Add to PATH" is checked).
2.  **Install OBS:** Download [OBS Studio](https://obsproject.com/) (required for the Virtual Camera driver).
3.  **Run:** Double-click **`run.bat`**.

### **Linux (Kali/Ubuntu/Debian)**
1.  **Install System Dependencies:**
    ```bash
    sudo apt update && sudo apt install -y python3-venv v4l2loopback-dkms libxcb-cursor0 libgl1-mesa-glx
    ```
2.  **Enable Driver:**
    ```bash
    sudo modprobe v4l2loopback devices=1 video_nr=10 card_label="Virtual Cam" exclusive_caps=1
    ```
3.  **Run:** Execute `./run.sh` in your terminal.

### **macOS**
1.  **Install OBS:** Download [OBS Studio](https://obsproject.com/) (required for the Virtual Camera driver).
2.  **Run:** Execute `./run.sh` in your terminal.

---

## 🛠️ Prerequisites & Drivers

The "Virtual Camera" is a piece of software that makes your computer think the AI-transformed video is a real physical webcam.

| OS | Driver Requirement | Source |
| :--- | :--- | :--- |
| **Windows** | OBS Virtual Camera | Included in [OBS Studio](https://obsproject.com/) |
| **Linux** | v4l2loopback | `sudo apt install v4l2loopback-dkms` |
| **macOS** | OBS Virtual Camera | Included in [OBS Studio](https://obsproject.com/) |

---

## 💡 How to Use

1.  **Launch:** Use the `run.bat` or `run.sh` script.
2.  **API Key:** Enter your Decart API key at the top. Click **Save Key** to store it securely in your OS keychain.
3.  **Connect:** Click the **Connect** button. Your physical webcam will turn on, and a connection to Decart AI will be established.
4.  **Style:**
    *   **Custom Prompt:** Type anything in the box (e.g., "An oil painting of a futuristic knight").
    *   **Presets:** Click a preset button (e.g., "Cyberpunk") for instant results.
5.  **Go Live:** Open Zoom/Teams, go to Settings -> Video, and select **"pyvirtualcam"** or **"OBS Virtual Camera"**.

---

## 🔍 Diagnostic Tool

If you encounter issues, run the diagnostic tool to check your hardware and environment:
```bash
# Windows
.venv\Scripts\python diagnostics.py

# Linux/macOS
./.venv/bin/python diagnostics.py
```

---

## ❓ Troubleshooting

### **General (All Platforms)**
*   **"Camera in Use":** Ensure no other app (Chrome, Zoom, etc.) is currently using your webcam before clicking Connect.
*   **Latency/Lag:** High-speed internet is required for WebRTC. If lag builds up, try restarting the connection to clear the buffer.

### **Windows**
*   **Virtual Camera not found:** Open OBS Studio once to ensure the virtual camera driver is initialized. You do **not** need to keep OBS open while using this app.

### **Linux**
*   **`Modulev4l2loopback not found`:** You need kernel headers. Run:
    `sudo apt install linux-headers-$(uname -r)` then `sudo dpkg-reconfigure v4l2loopback-dkms`.
*   **Permission Denied:** Never run the app with `sudo`. If you have permission issues with the camera, add your user to the video group: `sudo usermod -aG video $USER`.

### **macOS**
*   **Permissions:** You may need to grant Terminal or Python permission to access the Camera in `System Settings -> Security & Privacy`.

---

## 🤓 Technical Architecture

*   **Async Core:** Managed via `qasync`, allowing the PyQt6 UI and the `asyncio` WebRTC client to coexist without freezing.
*   **Video Track:** Custom `aiortc.MediaStreamTrack` that converts OpenCV BGR frames to YUV420P on-the-fly.
*   **Latency Strategy:** The pipeline uses a non-blocking `threading.Event` to ensure that only the most recent frame is sent to the AI, skipping old frames if the network slows down.
