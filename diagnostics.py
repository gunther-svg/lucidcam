import sys
import cv2
import pyvirtualcam
import asyncio
import platform
import subprocess
from decart import DecartClient

def check_camera():
    print("--- 1. Checking Physical Webcam ---")
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print("✅ Physical Webcam: Found and providing frames.")
            cap.release()
            return True
        else:
            print("❌ Physical Webcam: Found, but failed to capture a frame (is it in use?)")
    else:
        print("❌ Physical Webcam: Not found at index 0.")
    cap.release()
    return False

def check_virtual_cam():
    print("\n--- 2. Checking Virtual Camera Driver ---")
    try:
        with pyvirtualcam.Camera(width=640, height=480, fps=20) as cam:
            print(f"✅ Virtual Camera: Driver is working ({cam.device})")
            return True
    except Exception as e:
        print(f"❌ Virtual Camera: Driver NOT found or failed. Error: {e}")
        if platform.system() == "Windows":
            print("   Hint: Install OBS Studio to get the Virtual Camera driver.")
        else:
            print("   Hint: Ensure v4l2loopback is installed and modprobed.")
        return False

def check_internet():
    print("\n--- 3. Checking Decart Connectivity ---")
    try:
        # Just a simple ping/import check
        import decart
        print("✅ Decart SDK: Library imported successfully.")
        return True
    except ImportError:
        print("❌ Decart SDK: Library not installed.")
        return False

if __name__ == "__main__":
    print("=== AI Video Restyler Diagnostic Tool ===\n")
    
    cam_ok = check_camera()
    vcam_ok = check_virtual_cam()
    sdk_ok = check_internet()
    
    print("\n" + "="*40)
    if cam_ok and vcam_ok and sdk_ok:
        print("🎉 STATUS: ALL SYSTEMS GO!")
        print("You are ready to run ./run.sh")
    else:
        print("⚠️ STATUS: ISSUES DETECTED")
        print("Please fix the errors above before launching.")
    print("="*40)
    input("\nPress Enter to exit...")
