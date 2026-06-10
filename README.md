# AI Video Restyler

A real-time desktop application that transforms your webcam feed using Decart AI's Lucy 2.1 model and outputs it to a virtual camera.

## Features
- **Real-time AI Restyling:** Low-latency video transformation using WebRTC.
- **Virtual Camera Output:** Use your restyled feed in Zoom, OBS, Teams, etc.
- **Modern UI:** Clean dark-mode interface built with PyQt6.
- **Secure Key Management:** Uses OS-native keychain (via `keyring`) to store your API key.
- **Optimized Pipeline:** "Drop-oldest" frame strategy and efficient BGR to YUV conversion.

## Prerequisites
1. **Virtual Camera Driver:**
   - **Windows:** Install [OBS Studio](https://obsproject.com/) (includes virtual cam) or [OBS Virtual Cam](https://github.com/Fenrirthviti/obs-virtual-cam/releases).
   - **Linux:** Install `v4l2loopback`.
     ```bash
     sudo apt install v4l2loopback-dkms
     sudo modprobe v4l2loopback devices=1 video_nr=10 card_label="Virtual Cam" exclusive_caps=1
     ```
   - **macOS:** Install [OBS Studio](https://obsproject.com/).

2. **Python 3.9+**

## Installation
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. Run the application:
   ```bash
   python app.py
   ```
2. Enter your **Decart API Key** in the top bar and click "Save Key".
3. Click **Connect**.
4. Type a prompt (e.g., "In the style of Van Gogh") or click a preset.
5. In your video conferencing app (Zoom/Teams), select the **"pyvirtualcam"** or **"Virtual Camera"** device.

## Troubleshooting
- **Camera in use:** Ensure no other app (Zoom, Browser) is using your physical webcam when you click "Connect".
- **Latency:** If the video lags significantly, ensure you have a stable internet connection and that your CPU isn't being throttled.
- **Virtual Camera not found:** Ensure the drivers mentioned in Prerequisites are installed and active.
