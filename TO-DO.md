# 📋 LucidCam Release Roadmap

This document outlines the remaining steps to transition **LucidCam** from a Python source project into a professional, distributed `.exe` application.

---

## 🛠 Phase 1: Verification (Tomorrow's Goal)
Before building the installer, ensure the core logic is perfect on a native Windows environment.
- [ ] **Hardware Test:** Run `run.bat` on Windows and verify physical webcam access.
- [ ] **Driver Test:** Verify that `pyvirtualcam` successfully connects to the OBS Virtual Camera.
- [ ] **AI Latency Test:** Confirm the restyling feels "real-time" on your specific hardware.
- [ ] **Persistence Test:** Verify that window size and prompts are remembered after closing the app.

## 📦 Phase 2: Professional Bundling
Turning 800MB of Python code into a single, optimized executable.
- [ ] **PyInstaller Integration:** Create a `build.py` script using `PyInstaller`.
- [ ] **Hidden Imports:** Explicitly link "hidden" binaries for `PyQt6`, `livekit`, and `av`.
- [ ] **Icon Support:** Create/add a `lucidcam.ico` for the taskbar and file icon.
- [ ] **Splash Screen:** (Optional) Add a loading splash image to mask the initial 5-second environment startup.

## 🌐 Phase 3: Infrastructure
Setting up the backend for updates and sharing.
- [ ] **GitHub Repository:** Create the public/private repo for LucidCam.
- [ ] **Update Server:** 
    - Upload `version.txt` to the main branch.
    - Update `UPDATE_URL` in `app.py` to point to your actual GitHub username.
- [ ] **Documentation:** Finalize the `README.md` with your specific GitHub links and installation instructions.

## 🚀 Phase 4: Distribution & UX
Making it easy for others to use.
- [ ] **Installer Generator:** Use a tool like **Inno Setup** or **NSIS** to create a proper "Setup.exe" that checks for Python and OBS automatically.
- [ ] **Security Bypass:** Prepare a "How to Run" note for users to explain the Windows "Unknown Publisher" warning (or look into self-signing).
- [ ] **Presets Library:** Finalize the default styles in `app.py` based on your AI testing.

---
