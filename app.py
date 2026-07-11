import os
import sys
import json
import subprocess
import threading
import time
from pathlib import Path
from flask import Flask, jsonify, request, Response, render_template

app = Flask(__name__)

# Fixed folder structure — user hanya upload file
WORK_DIR = Path(__file__).parent.resolve()
FOLDERS = {
    "01_pdf_source": str(WORK_DIR / "01_pdf_source"),
    "02_pdf_target": str(WORK_DIR / "02_pdf_target"),
    "03_photos_export": str(WORK_DIR / "03_photos_export"),
    "04_photos_edited": str(WORK_DIR / "04_photos_edited"),
    "05_pdf_merged": str(WORK_DIR / "05_pdf_merged"),
}

# Global state
state = {
    "is_running": False,
    "current_step": None,
    "progress": 0,
    "status_text": "Idle",
    "process": None,
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
        if len(log_queue) > 1000:
            log_queue.pop(0)

def run_command_stream(cmd, step_name, overwrite="1"):
    add_log(f"Menjalankan perintah: {' '.join(cmd)}", "command")
    try:
        env = os.environ.copy()
        env["OVERWRITE"] = overwrite
        # Gunakan shell=True pada Windows agar virtual env terpanggil dengan benar
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            shell=True,
            env=env
        )
        
        state["process"] = process
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str:
                add_log(line_str, "stdout")
                
        process.wait()
        state["process"] = None
        return process.returncode == 0
    except Exception as e:
        add_log(f"Gagal menjalankan skrip {step_name}: {str(e)}", "error")
        state["process"] = None
        return False

def pipeline_thread(step_id, overwrite="1"):
    global state
    state["is_running"] = True

    add_log(f"=== Memulai Pemrosesan Tahap: {step_id.upper()} ===", "system")

    success = True
    try:
        if step_id == "step1" or step_id == "all":
            state["current_step"] = "step1"
            state["status_text"] = "Mengekstrak foto asli dari PDF 2026..."
            state["progress"] = 10

            cmd = [
                sys.executable, "-u",
                "export_pdf_foto.py",
                "--input", FOLDERS["01_pdf_source"],
                "--output", FOLDERS["03_photos_export"]
            ]
            ok = run_command_stream(cmd, "Export PDF Foto", overwrite)
            if not ok:
                success = False
                add_log("Tahap 1 (Export PDF Foto) gagal.", "error")
            else:
                state["progress"] = 25
                add_log("Tahap 1 (Export PDF Foto) selesai.", "success")

        if (step_id == "step2" or step_id == "all") and success:
            state["current_step"] = "step2"
            state["status_text"] = "Mengekstrak tanggal target dari PDF 2025..."
            state["progress"] = 30

            cmd_dates = [
                sys.executable, "-u",
                "extract_pdf_dates.py",
                "--pdf-dir", FOLDERS["02_pdf_target"],
                "--output-dir", FOLDERS["03_photos_export"]
            ]
            ok = run_command_stream(cmd_dates, "Extract PDF Dates", overwrite)
            if not ok:
                success = False
                add_log("Ekstraksi tanggal target gagal.", "error")
            else:
                state["progress"] = 45
                add_log("Tahap 2 (Extract PDF Dates) selesai.", "success")

        if (step_id == "step3" or step_id == "all") and success:
            state["current_step"] = "step3"
            state["status_text"] = "Menjadwalkan Tim & waktu pengerjaan..."
            state["progress"] = 50

            schedule_path = str(WORK_DIR / "schedule.json")
            cmd_sched = [
                sys.executable, "-u",
                "scheduler.py",
                "--pdf-dir", FOLDERS["02_pdf_target"],
                "--photos-dir", FOLDERS["03_photos_export"],
                "--output", schedule_path
            ]
            ok = run_command_stream(cmd_sched, "Scheduler", overwrite)
            if not ok:
                success = False
                add_log("Tahap 3 (Scheduler) gagal.", "error")
            else:
                state["progress"] = 60
                add_log("Tahap 3 (Scheduler) selesai.", "success")

        if (step_id == "step4" or step_id == "all") and success:
            state["current_step"] = "step4"
            state["status_text"] = "Merevisi watermark Timemark per Tim..."
            state["progress"] = 65

            schedule_arg = str(WORK_DIR / "schedule.json")
            cmd_edit = [
                sys.executable, "-u",
                "edit_timemark_ide1.py",
                "--input", FOLDERS["03_photos_export"],
                "--schedule", schedule_arg
            ]
            ok = run_command_stream(cmd_edit, "Edit Timemark", overwrite)
            if not ok:
                success = False
                add_log("Tahap 4 (Edit Timemark) gagal.", "error")
            else:
                state["progress"] = 80
                add_log("Tahap 4 (Edit Timemark) selesai.", "success")

        if (step_id == "step5" or step_id == "all") and success:
            state["current_step"] = "step5"
            state["status_text"] = "Menggabungkan foto baru ke PDF 2025..."
            state["progress"] = 85

            schedule_arg = str(WORK_DIR / "schedule.json")
            photos_dir = FOLDERS["04_photos_edited"]
            cmd = [
                sys.executable, "-u",
                "merge_pdf_foto.py",
                "--input", FOLDERS["02_pdf_target"],
                "--photos", photos_dir,
                "--output", FOLDERS["05_pdf_merged"],
                "--schedule", schedule_arg
            ]
            ok = run_command_stream(cmd, "Merge PDF Foto", overwrite)
            if not ok:
                success = False
                add_log("Tahap 5 (Merge PDF Foto) gagal.", "error")
            else:
                state["progress"] = 100
                add_log("Tahap 5 (Merge PDF Foto) selesai.", "success")

        if success:
            state["status_text"] = "Semua proses selesai dengan sukses!"
            add_log("Alur kerja selesai tanpa error.", "success")
        else:
            state["status_text"] = "Proses terhenti karena kesalahan."
            add_log("Pemrosesan dibatalkan.", "error")

    except Exception as e:
        success = False
        state["status_text"] = f"Kesalahan: {str(e)}"
        add_log(f"Crash: {str(e)}", "error")

    finally:
        state["is_running"] = False
        state["current_step"] = None
        state["process"] = None

def get_pdf_list(directory):
    path = Path(directory)
    if not path.is_dir():
        return []
    return sorted(
        [str(p.relative_to(path).as_posix()) for p in path.rglob("*.pdf") if p.is_file()]
    )

# --- Web routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/config")
def api_config():
    return jsonify(FOLDERS)

@app.route("/api/open-folder/<folder_key>")
def api_open_folder(folder_key):
    if folder_key not in FOLDERS:
        return jsonify({"status": "error", "message": "Folder tidak valid."}), 400
    path = FOLDERS[folder_key]
    Path(path).mkdir(parents=True, exist_ok=True)
    # Windows: buka folder di Explorer
    subprocess.Popen(["explorer", path], shell=True)
    return jsonify({"status": "ok", "path": path})

@app.route("/api/status")
def api_status():
    return jsonify(state)

@app.route("/api/files")
def api_files():
    return jsonify({
        "01_pdf_source": get_pdf_list(FOLDERS["01_pdf_source"]),
        "02_pdf_target": get_pdf_list(FOLDERS["02_pdf_target"]),
        "05_pdf_merged": get_pdf_list(FOLDERS["05_pdf_merged"]),
    })

@app.route("/api/run", methods=["POST"])
def api_run():
    if state["is_running"]:
        return jsonify({"status": "error", "message": "Proses lain sedang berjalan."}), 400
    
    step_id = request.json.get("step", "all")
    overwrite = "1" if request.json.get("overwrite", True) else "0"
    if step_id not in ["step1", "step2", "step3", "step4", "step5", "all"]:
        return jsonify({"status": "error", "message": "Tahap tidak valid."}), 400
    
    # Hapus log queue lama
    global log_queue
    log_queue.clear()
    
    # Buat folder kerja yang belum ada
    for name, dir_path in FOLDERS.items():
        if name != "05_pdf_merged":
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    Path(FOLDERS["05_pdf_merged"]).mkdir(parents=True, exist_ok=True)
    
    threading.Thread(target=pipeline_thread, args=(step_id, overwrite), daemon=True).start()
    return jsonify({"status": "ok", "message": f"Memulai tahap: {step_id}"})

@app.route("/api/stop", methods=["POST"])
def api_stop():
    if not state["is_running"]:
        return jsonify({"status": "error", "message": "Tidak ada proses yang berjalan."}), 400
    proc = state.get("process")
    if proc and proc.poll() is None:
        if os.name == "nt":
            # Windows: kill the process tree since shell=True leaves child processes orphan
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc.terminate()
        add_log("⏹ Proses dihentikan oleh pengguna.", "error")
    state["is_running"] = False
    state["process"] = None
    state["status_text"] = "Dihentikan"
    return jsonify({"status": "ok", "message": "Proses dihentikan."})

@app.route("/api/stream-logs")
def stream_logs():
    def event_stream():
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
    add_log("Server Web Lokal OCR Foto Timemark dimulai.", "system")
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    app.run(host="127.0.0.1", port=port, debug=False)
