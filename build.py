import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path

def main():
    print("=" * 60)
    print(" LucidCam Automated Packaging & Release Build Script")
    print(" Publisher: greatware | App: LucidCam v1.0.0")
    print("=" * 60)

    project_dir = Path(__file__).parent.resolve()
    os.chdir(project_dir)

    # 1. Ensure Icon exists
    icon_path = project_dir / "lucidcam.ico"
    logo_path = project_dir / "logo.png"

    if not icon_path.exists():
        print("[+] Creating lucidcam.ico from logo.png...")
        try:
            from PIL import Image
            img = Image.open(logo_path)
            img.save(icon_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            print("  [OK] Icon created: lucidcam.ico")
        except Exception as e:
            print(f"  [!] Warning: Could not auto-generate ico file: {e}")

    # 2. Check virtual environment python executable
    venv_py = project_dir / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    py_exec = str(venv_py) if venv_py.exists() else sys.executable

    print(f"[*] Using Python environment: {py_exec}")

    try:
        res = subprocess.run([py_exec, "-c", "import PyInstaller; print(PyInstaller.__version__)"], capture_output=True, text=True, check=True)
        print(f"[*] PyInstaller version: {res.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[!] PyInstaller not found in environment. Installing pyinstaller...")
        subprocess.run([py_exec, "-m", "pip", "install", "pyinstaller"], check=True)

    # 3. Clean previous build artifacts
    build_dir = project_dir / "build"
    dist_dir = project_dir / "dist"
    installer_out = project_dir / "installer_output"

    if build_dir.exists():
        print("[*] Cleaning build directory...")
        shutil.rmtree(build_dir, ignore_errors=True)

    if dist_dir.exists():
        print("[*] Cleaning dist directory...")
        shutil.rmtree(dist_dir, ignore_errors=True)

    if installer_out.exists():
        print("[*] Cleaning installer_output directory...")
        shutil.rmtree(installer_out, ignore_errors=True)

    # 4. Hidden Imports List
    hidden_imports = [
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "qasync",
        "pyvirtualcam",
        "decart",
        "decart.realtime",
        "livekit",
        "livekit.rtc",
        "livekit.api",
        "av",
        "av.video",
        "av.audio",
        "av.codec",
        "keyring",
        "keyring.backends",
        "keyring.backends.Windows",
        "aiohttp",
        "aiortc",
        "tenacity",
        "prompt_handler",
        "video_pipeline",
        "diagnostics",
        "setup_wizard",
    ]

    # Data files to bundle
    datas = []
    if logo_path.exists():
        datas.append(f"{logo_path}{os.pathsep}.")
    if icon_path.exists():
        datas.append(f"{icon_path}{os.pathsep}.")

    # Packages to collect all submodules, data, and binaries for
    collect_all_packages = [
        "PyQt6",
        "keyring",
        "qasync",
        "pyvirtualcam",
        "decart",
        "livekit",
        "av",
    ]

    # Build PyInstaller Command
    cmd = [
        py_exec, "-m", "PyInstaller",
        "--name=LucidCam",
        "--onedir",             # Build as directory (recommended for C/C++ WebRTC DLL bindings)
        "--windowed",           # No console window
        "--noconfirm",          # Overwrite dist
        "--clean",              # Clean PyInstaller cache
    ]

    for pkg in collect_all_packages:
        cmd.append(f"--collect-all={pkg}")

    # Unused heavy Qt modules to exclude to optimize build size
    excludes = [
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtQml",
        "PyQt6.QtQuick",
        "PyQt6.Qt3D",
        "PyQt6.QtPdf",
        "PyQt6.QtBluetooth",
        "PyQt6.QtNfc",
        "PyQt6.QtSensors",
        "PyQt6.QtSerialPort",
        "PyQt6.QtPositioning",
    ]

    for ex in excludes:
        cmd.append(f"--exclude-module={ex}")

    if icon_path.exists():
        cmd.append(f"--icon={icon_path}")

    for item in hidden_imports:
        cmd.append(f"--hidden-import={item}")

    for data_item in datas:
        cmd.append(f"--add-data={data_item}")

    cmd.append("app.py")

    print("\n[+] Step 1: Running PyInstaller compilation...")
    print(" ".join(cmd))
    print("-" * 60)

    res = subprocess.run(cmd)

    if res.returncode != 0:
        print("\n[!] PyInstaller build failed with return code:", res.returncode)
        return

    lucidcam_dist = dist_dir / "LucidCam"
    if not lucidcam_dist.exists():
        print("[!] Compiled dist folder not found.")
        return

    print("\n[OK] Step 1 Complete: PyInstaller app compiled.")

    # Step 2: Create Portable ZIP Archive
    print("\n[+] Step 2: Creating Portable ZIP Archive...")
    zip_path = dist_dir / "LucidCam-v1.0.0-portable.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(lucidcam_dist):
            for file in files:
                file_path = Path(root) / file
                arcname = Path("LucidCam") / file_path.relative_to(lucidcam_dist)
                zipf.write(file_path, arcname)

    print(f"  [OK] Portable ZIP created: {zip_path}")

    # Step 3: Inno Setup Compiler (if available)
    print("\n[*] Step 3: Checking for Inno Setup Compiler (ISCC.exe)...")
    iscc_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        shutil.which("ISCC.exe")
    ]
    iscc_cmd = next((p for p in iscc_paths if p and os.path.exists(p)), None)

    if iscc_cmd:
        print(f"  Found Inno Setup at: {iscc_cmd}")
        print("  Building LucidCam_Setup_v1.0.0.exe...")
        iscc_res = subprocess.run([iscc_cmd, "installer.iss"])
        if iscc_res.returncode == 0:
            print("  [OK] Inno Setup Installer compiled successfully in installer_output/")
        else:
            print("  [!] Inno Setup compilation failed.")
    else:
        print("  [i] ISCC.exe not found in standard PATH. You can compile installer.iss manually with Inno Setup GUI.")

    print("\n" + "=" * 60)
    print(" ALL PACKAGING PREPARATION COMPLETE!")
    print(f" Executable: {lucidcam_dist / 'LucidCam.exe'}")
    print(f" Portable ZIP Archive: {zip_path}")
    if (project_dir / "installer_output" / "LucidCam_Setup_v1.0.0.exe").exists():
        print(f" Windows Installer: {project_dir / 'installer_output' / 'LucidCam_Setup_v1.0.0.exe'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
