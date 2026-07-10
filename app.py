import os
import sys
import json
import subprocess
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from flask import Flask, jsonify, request, Response, render_template

app = Flask(__name__)

# Config file path
CONFIG_FILE = Path("ui_config.json")
DEFAULT_CONFIG = {
    "input_pdf": str(Path("./input_pdf").resolve()),
    "pdf_imo": str(Path("./pdf_imo").resolve()),
    "output_pdf_foto": str(Path("./output_pdf_foto").resolve()),
    "hasil_gabung": str(Path("./hasil_gabung").resolve())
}

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure all default keys exist
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception:
        pass

# Global state
state = {
    "is_running": False,
    "current_step": None,
    "progress": 0,
    "status_text": "Idle",
}

log_queue = []
log_lock = threading.Lock()

def add_log(message, type="info"):
    with log_lock:
        log_entry = {
            "timestamp": time.strftime("%H:%M:%S"),
            "message": message,
            "type": type
        }
        log_queue.append(log_entry)
        # Keep last 1000 logs
        if len(log_queue) > 1000:
            log_queue.pop(0)

def run_command_stream(cmd, step_name):
    add_log(f"Menjalankan perintah: {' '.join(cmd)}", "command")
    try:
        # Gunakan shell=True pada Windows agar virtual env terpanggil dengan benar
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            shell=True
        )
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str:
                add_log(line_str, "stdout")
                
        process.wait()
        return process.returncode == 0
    except Exception as e:
        add_log(f"Gagal menjalankan skrip {step_name}: {str(e)}", "error")
        return False

def pipeline_thread(step_id, config):
    global state
    state["is_running"] = True
    
    add_log(f"=== Memulai Pemrosesan Tahap: {step_id.upper()} ===", "system")
    
    success = True
    try:
        # Step 1: Export PDF Foto
        if step_id == "step1" or step_id == "all":
            state["current_step"] = "step1"
            state["status_text"] = "Mengekstrak foto asli dari PDF 2026..."
            state["progress"] = 10
            
            cmd = [
                sys.executable, "-u",
                "export_pdf_foto.py", 
                "--input", config["input_pdf"], 
                "--output", config["output_pdf_foto"]
            ]
            ok = run_command_stream(cmd, "Export PDF Foto")
            if not ok:
                success = False
                add_log("Tahap 1 (Export PDF Foto) gagal dijalankan.", "error")
            else:
                state["progress"] = 30
                add_log("Tahap 1 (Export PDF Foto) selesai dengan sukses.", "success")
                
        # Step 2: Edit Watermark Timemark (termasuk ekstraksi tanggal otomatis)
        if (step_id == "step2" or step_id == "all") and success:
            state["current_step"] = "step2"
            state["status_text"] = "Mengekstrak tanggal target & merevisi watermark..."
            state["progress"] = 40
            
            # Step 2a: extract dates (otomatis)
            add_log("Melakukan ekstraksi tanggal target dari pdf_imo...", "system")
            cmd_dates = [
                sys.executable, "-u",
                "extract_pdf_dates.py", 
                "--pdf-dir", config["pdf_imo"], 
                "--output-dir", config["output_pdf_foto"]
            ]
            ok = run_command_stream(cmd_dates, "Extract PDF Dates")
            if not ok:
                success = False
                add_log("Ekstraksi tanggal target (extract_pdf_dates) gagal.", "error")
            else:
                state["progress"] = 60
                
                # Step 2b: edit timemark
                add_log("Melakukan revisi tanggal watermark Timemark...", "system")
                cmd_edit = [
                    sys.executable, "-u",
                    "edit_timemark_ide1.py", 
                    "--input", config["output_pdf_foto"]
                ]
                ok = run_command_stream(cmd_edit, "Edit Timemark")
                if not ok:
                    success = False
                    add_log("Tahap 2 (Edit Timemark) gagal dijalankan.", "error")
                else:
                    state["progress"] = 80
                    add_log("Tahap 2 (Edit Timemark) selesai dengan sukses.", "success")
                    
        # Step 3: Merge PDF Foto
        if (step_id == "step3" or step_id == "all") and success:
            state["current_step"] = "step3"
            state["status_text"] = "Menggabungkan foto baru ke template PDF 2025..."
            state["progress"] = 90
            
            photos_dir = str(Path(config["output_pdf_foto"]) / "Export_Foto")
            cmd = [
                sys.executable, "-u",
                "merge_pdf_foto.py", 
                "--input", config["pdf_imo"], 
                "--photos", photos_dir, 
                "--output", config["hasil_gabung"]
            ]
            ok = run_command_stream(cmd, "Merge PDF Foto")
            if not ok:
                success = False
                add_log("Tahap 3 (Merge PDF Foto) gagal dijalankan.", "error")
            else:
                state["progress"] = 100
                add_log("Tahap 3 (Merge PDF Foto) selesai dengan sukses.", "success")
                
        if success:
            state["status_text"] = "Semua proses selesai dengan sukses!"
            add_log("Alur kerja selesai sepenuhnya tanpa error.", "success")
        else:
            state["status_text"] = "Proses terhenti karena kesalahan."
            add_log("Pemrosesan dibatalkan akibat kegagalan pada salah satu langkah.", "error")
            
    except Exception as e:
        success = False
        state["status_text"] = f"Kesalahan: {str(e)}"
        add_log(f"Sistem mengalami crash: {str(e)}", "error")
        
    finally:
        state["is_running"] = False
        state["current_step"] = None

def get_pdf_list(directory):
    path = Path(directory)
    if not path.is_dir():
        return []
    # Cari berkas PDF secara rekursif dan pertahankan path relatifnya
    return [str(p.relative_to(path).as_posix()) for p in path.rglob("*.pdf") if p.is_file()]

# Web routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/select-folder", methods=["POST"])
def api_select_folder():
    initial_dir = request.json.get("initial_dir", None)
    if initial_dir and not Path(initial_dir).is_dir():
        initial_dir = None
        
    result = []
    def ask():
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(initialdir=initial_dir, title="Pilih Folder")
            root.destroy()
            result.append(folder)
        except Exception as e:
            result.append(f"error: {str(e)}")
            
    t = threading.Thread(target=ask)
    t.start()
    t.join()
    
    if not result:
        return jsonify({"status": "ok", "folder": ""})
    
    res_val = result[0]
    if res_val.startswith("error:"):
        return jsonify({"status": "error", "message": res_val})
        
    return jsonify({"status": "ok", "folder": res_val})

@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        new_cfg = request.json
        cfg = load_config()
        for k in DEFAULT_CONFIG.keys():
            if k in new_cfg:
                cfg[k] = str(Path(new_cfg[k]).resolve())
        save_config(cfg)
        add_log("Konfigurasi folder diperbarui oleh pengguna.", "system")
        return jsonify({"status": "ok", "config": cfg})
    else:
        return jsonify(load_config())

@app.route("/api/status")
def api_status():
    return jsonify(state)

@app.route("/api/files")
def api_files():
    config = load_config()
    return jsonify({
        "input_pdf": get_pdf_list(config["input_pdf"]),
        "pdf_imo": get_pdf_list(config["pdf_imo"]),
        "hasil_gabung": get_pdf_list(config["hasil_gabung"])
    })

@app.route("/api/run", methods=["POST"])
def api_run():
    if state["is_running"]:
        return jsonify({"status": "error", "message": "Proses lain sedang berjalan."}), 400
        
    step_id = request.json.get("step", "all")
    if step_id not in ["step1", "step2", "step3", "all"]:
        return jsonify({"status": "error", "message": "Tahap tidak valid."}), 400
        
    config = load_config()
    
    # Validasi direktori sebelum jalan
    for name, dir_path in config.items():
        if name != "hasil_gabung" and not Path(dir_path).is_dir():
            # Coba buat foldernya jika belum ada
            try:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
            except Exception:
                return jsonify({"status": "error", "message": f"Folder {name} ({dir_path}) tidak valid dan tidak dapat dibuat."}), 400
                
    # Jalankan di background thread
    threading.Thread(target=pipeline_thread, args=(step_id, config), daemon=True).start()
    return jsonify({"status": "ok", "message": f"Memulai tahap: {step_id}"})

@app.route("/api/stream-logs")
def stream_logs():
    def event_stream():
        # Kirim log yang sudah ada
        with log_lock:
            for log in log_queue:
                yield f"data: {json.dumps(log)}\n\n"
        
        last_index = len(log_queue)
        while True:
            time.sleep(0.2)
            with log_lock:
                if len(log_queue) > last_index:
                    for i in range(last_index, len(log_queue)):
                        yield f"data: {json.dumps(log_queue[i])}\n\n"
                    last_index = len(log_queue)
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == "__main__":
    import webbrowser
    port = 5000
    # Jalankan server secara lokal
    add_log("Server Web Lokal OCR Foto Timemark dimulai.", "system")
    # Buka browser secara otomatis setelah jeda singkat
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    app.run(host="127.0.0.1", port=port, debug=False)
