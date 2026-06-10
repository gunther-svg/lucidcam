import os
import sys
import subprocess
import venv
import platform
import shutil

# Target directory for the virtual environment
VENV_DIR = os.path.join(os.path.dirname(__file__), ".venv")

def get_python_executable():
    """Returns the path to the python executable within the venv."""
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    else:
        return os.path.join(VENV_DIR, "bin", "python")

def is_venv_valid():
    """Checks if the venv exists and has the required executable."""
    return os.path.exists(get_python_executable())

def create_venv():
    """Creates a fresh virtual environment."""
    print(f"--- Creating virtual environment in {VENV_DIR} ---")
    if os.path.exists(VENV_DIR):
        shutil.rmtree(VENV_DIR)
    venv.create(VENV_DIR, with_pip=True)

def install_dependencies():
    """Installs packages from requirements.txt into the venv."""
    print("--- Installing dependencies (this may take a minute) ---")
    python_exe = get_python_executable()
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    
    # Upgrade pip first
    subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Install requirements
    subprocess.check_call([python_exe, "-m", "pip", "install", "-r", requirements_path])

def check_system_dependencies():
    """Checks for OS-specific system requirements."""
    sys_platform = platform.system()
    if sys_platform == "Linux":
        # Check for v4l2loopback
        try:
            result = subprocess.run(["lsmod"], capture_output=True, text=True)
            if "v4l2loopback" not in result.stdout:
                print("\n[WARNING] v4l2loopback module not detected.")
                print("You may need to run: sudo modprobe v4l2loopback")
        except Exception:
            pass
    elif sys_platform == "Windows":
        # We could check for OBS here, but pyvirtualcam will handle the error gracefully in-app
        pass

def launch_app():
    """Launches the main application using the venv's python."""
    python_exe = get_python_executable()
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    print(f"--- Launching AI Video Restyler ---")
    # Using subprocess.run to keep the terminal open for logs if needed, 
    # or subprocess.Popen if we want to detach.
    subprocess.run([python_exe, app_path])

if __name__ == "__main__":
    if os.geteuid() == 0:
        print("\n[WARNING] You are running this as ROOT/SUDO.")
        print("This will cause permission issues. Please run as a normal user.")
        print("If you need to install system drivers, do that separately.\n")

    try:
        if not is_venv_valid():
            try:
                create_venv()
            except subprocess.CalledProcessError as e:
                if "ensurepip" in str(e) or e.returncode != 0:
                    print("\n[ERROR] Python 'venv' module is incomplete on your system.")
                    print("On Debian/Ubuntu/Kali, please run:")
                    print("    sudo apt update && sudo apt install python3-venv")
                    sys.exit(1)
                raise e
            install_dependencies()
        
        check_system_dependencies()
        launch_app()
        
    except Exception as e:
        print(f"\n[ERROR] Installation or Launch failed: {e}")
        input("\nPress Enter to exit...")
