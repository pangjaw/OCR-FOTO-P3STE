"""
launcher.py — Desktop Window Launcher for OCR-FOTO-P3STE
Runs Next.js web application via portable Node.js and renders a native WebView2 desktop window.
"""

import sys
import os
import time
import socket
import shutil
import atexit
import signal
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# Determine App Root Directory
if getattr(sys, "frozen", False):
    # Running in a PyInstaller bundle
    APP_DIR = Path(sys.executable).resolve().parent
    # If the executable is placed in dist/ or bin/, look up to find project root
    if not (APP_DIR / "web").exists() and (APP_DIR.parent / "web").exists():
        APP_DIR = APP_DIR.parent
else:
    APP_DIR = Path(__file__).resolve().parent

NODE_BIN_CANDIDATES = [
    APP_DIR / "bin" / "node.exe",
    APP_DIR / "node.exe",
]

def find_node_executable():
    for candidate in NODE_BIN_CANDIDATES:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    system_node = shutil.which("node")
    if system_node:
        return system_node
    return None

def find_free_port(start_port=3000, max_attempts=50):
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port

def wait_for_server(url, timeout=40):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OCR-Launcher"})
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status in (200, 304):
                    return True
        except Exception:
            time.sleep(0.4)
    return False

def kill_process_tree(pid):
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/pid", str(pid), "/f", "/t"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass

def main():
    node_exe = find_node_executable()
    if not node_exe:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            "Node.js runtime tidak ditemukan di 'bin/node.exe' ataupun sistem.\n"
            "Pastikan folder bin/node.exe tersedia sebelum menjalankan aplikasi.",
            "OCR Foto Timemark - Kesalahan",
            0x10 | 0x0
        )
        return 1

    next_cli = APP_DIR / "web" / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.exists():
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"File Next.js CLI tidak ditemukan di:\n{next_cli}\n"
            "Pastikan folder web/node_modules telah terinstall.",
            "OCR Foto Timemark - Kesalahan",
            0x10 | 0x0
        )
        return 1

    port = find_free_port(3000)
    server_url = f"http://127.0.0.1:{port}"
    api_check_url = f"{server_url}/api/files"

    creation_flags = 0
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NO_WINDOW

    node_env = {
        **os.environ,
        "PORT": str(port),
        "NODE_ENV": "production",
    }

    # Start Next.js in background with no console window
    node_proc = subprocess.Popen(
        [node_exe, str(next_cli), "start", str(APP_DIR / "web"), "-p", str(port)],
        cwd=str(APP_DIR),
        env=node_env,
        creationflags=creation_flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Register cleanup
    def cleanup():
        if node_proc.poll() is None:
            kill_process_tree(node_proc.pid)

    atexit.register(cleanup)

    # Wait for server to become responsive
    is_ready = wait_for_server(api_check_url, timeout=35)
    if not is_ready:
        cleanup()
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Server Next.js gagal menyala pada port {port} dalam waktu 35 detik.\n"
            "Periksa apakah build 'web/.next' sudah lengkap.",
            "OCR Foto Timemark - Timeout",
            0x10 | 0x0
        )
        return 1

    log_dir = APP_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    launcher_log = log_dir / "launcher.log"

    def log_msg(msg: str):
        try:
            with open(launcher_log, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        except Exception:
            pass

    log_msg(f"Server ready at {server_url}. Launching desktop window...")

    # Attempt native WebView2 window
    webview_launched = False
    try:
        import webview
        window = webview.create_window(
            title="OCR Foto Timemark - P3STE Sintelis",
            url=server_url,
            width=1320,
            height=860,
            min_size=(1024, 700),
            text_select=True,
        )

        def on_closed():
            log_msg("Window closed by user. Cleaning up...")
            cleanup()

        window.events.closed += on_closed
        webview_launched = True
        log_msg("Starting webview.start(gui='edgechromium')...")
        webview.start(gui="edgechromium", debug=False)
        log_msg("webview.start finished normally.")
    except Exception as e:
        import traceback
        err_str = traceback.format_exc()
        log_msg(f"WebView2 encountered error: {e}\n{err_str}")
        # Seamless fallback to default browser
        import webbrowser
        log_msg(f"Opening in default system browser as fallback: {server_url}")
        webbrowser.open(server_url)
        try:
            node_proc.wait()
        except KeyboardInterrupt:
            pass
    finally:
        cleanup()

    return 0

if __name__ == "__main__":
    sys.exit(main())
