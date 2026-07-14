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
    "step_statuses": {
        "step1": "waiting",
        "step2": "waiting",
        "step3": "waiting",
        "step4": "waiting",
        "step5": "waiting"
    },
}

log_queue = []
log_lock = threading.Lock()

log_generation = 0
log_generation_lock = threading.Lock()

stage_queue = []
stage_lock = threading.Lock()

stage_counts_lock = threading.Lock()
stage_details_lock = threading.Lock()
stage_details = []

stage_counts = {
    "stage_0_override": 0,
    "stage_1c_guide_original": 0,
    "stage_1c_guide_consensus": 0,
    "stage_fallback": 0
}

# Summary storage for each step
step_summaries = {}
step_summaries_lock = threading.Lock()


def clear_stage_data():
    global stage_counts, stage_details
    with stage_counts_lock:
        stage_counts = {
            "stage_0_override": 0,
            "stage_1c_guide_original": 0,
            "stage_1c_guide_consensus": 0,
            "stage_fallback": 0
        }
    with stage_details_lock:
        stage_details.clear()
    # Reset step statuses too
    for step in ["step1", "step2", "step3", "step4", "step5"]:
        state["step_statuses"][step] = "waiting"


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
    last_lines = []
    try:
        env = os.environ.copy()
        env["OVERWRITE"] = overwrite
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        # Use shell=False — sys.executable already points to correct Python
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            shell=False,
            env=env
        )
        
        state["process"] = process
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str:
                last_lines.append(line_str)
                if len(last_lines) > 10:
                    last_lines.pop(0)
                add_log(line_str, "stdout")
                # Parse JSON stage events from edit_timemark_ide1.py
                if line_str.startswith('{') and line_str.endswith('}'):
                    try:
                        data = json.loads(line_str)
                        if data.get("type") == "stage":
                            stage = data.get("stage")
                            with stage_counts_lock:
                                if stage in stage_counts:
                                    stage_counts[stage] += 1
                            with stage_details_lock:
                                stage_details.append({
                                    "file": data.get("file"),
                                    "stage": stage,
                                    "asset_type": data.get("asset_type"),
                                    "detail": data.get("detail"),
                                    "photo": data.get("photo")
                                })
                            with stage_lock:
                                stage_queue.append(data)
                    except json.JSONDecodeError:
                        pass
                # Capture __SUMMARY__ from scripts
                elif line_str.startswith("__SUMMARY__:"):
                    try:
                        summary_json = line_str.split("__SUMMARY__:", 1)[1]
                        summary = json.loads(summary_json)
                        with step_summaries_lock:
                            step_summaries[summary.get("step", step_name)] = summary
                    except json.JSONDecodeError:
                        pass
                
        process.wait()
        state["process"] = None
        ok = process.returncode == 0
        if not ok:
            add_log(f"✖ {step_name} keluar dengan kode {process.returncode}", "error")
            for l in last_lines[-5:]:
                add_log(f"  ⚠ {l}", "error")
        return ok
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
            state["step_statuses"]["step1"] = "active"
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
                state["step_statuses"]["step1"] = "error"
                add_log("Tahap 1 (Export PDF Foto) gagal.", "error")
            else:
                state["step_statuses"]["step1"] = "done"
                state["progress"] = 25
                add_log("Tahap 1 (Export PDF Foto) selesai.", "success")

        if (step_id == "step2" or step_id == "all") and success:
            state["current_step"] = "step2"
            state["step_statuses"]["step2"] = "active"
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
                state["step_statuses"]["step2"] = "error"
                add_log("Ekstraksi tanggal target gagal.", "error")
            else:
                state["step_statuses"]["step2"] = "done"
                state["progress"] = 45
                add_log("Tahap 2 (Extract PDF Dates) selesai.", "success")

        if (step_id == "step3" or step_id == "all") and success:
            state["current_step"] = "step3"
            state["step_statuses"]["step3"] = "active"
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
                state["step_statuses"]["step3"] = "error"
                add_log("Tahap 3 (Scheduler) gagal.", "error")
            else:
                state["step_statuses"]["step3"] = "done"
                state["progress"] = 60
                add_log("Tahap 3 (Scheduler) selesai.", "success")

        if (step_id == "step4" or step_id == "all") and success:
            state["current_step"] = "step4"
            state["step_statuses"]["step4"] = "active"
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
                state["step_statuses"]["step4"] = "error"
                add_log("Tahap 4 (Edit Timemark) gagal.", "error")
            else:
                state["step_statuses"]["step4"] = "done"
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
                state["step_statuses"]["step5"] = "error"
                add_log("Tahap 5 (Merge PDF Foto) gagal.", "error")
            else:
                state["step_statuses"]["step5"] = "done"
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
        # Steps that never ran -> stay waiting


def get_pdf_list(directory, limit=100):
    path = Path(directory)
    if not path.is_dir():
        return {"files": [], "total": 0, "truncated": False}
    all_files = sorted(
        [str(p.relative_to(path).as_posix()) for p in path.rglob("*.pdf") if p.is_file()]
    )
    total = len(all_files)
    truncated = total > limit
    return {
        "files": all_files[:limit],
        "total": total,
        "truncated": truncated
    }

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
    # Return state without the Popen object (not JSON serializable)
    safe_state = {k: v for k, v in state.items() if k != "process"}
    return jsonify(safe_state)

@app.route("/api/files")
def api_files():
    r1 = get_pdf_list(FOLDERS["01_pdf_source"])
    r2 = get_pdf_list(FOLDERS["02_pdf_target"])
    r5 = get_pdf_list(FOLDERS["05_pdf_merged"])
    return jsonify({
        "01_pdf_source": r1,
        "02_pdf_target": r2,
        "05_pdf_merged": r5,
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
    global log_queue, log_generation
    log_queue.clear()
    with log_generation_lock:
        log_generation += 1
    
    # Clear stage data
    clear_stage_data()
    
    # Buat folder kerja yang belum ada
    for name, dir_path in FOLDERS.items():
        if name != "05_pdf_merged":
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    Path(FOLDERS["05_pdf_merged"]).mkdir(parents=True, exist_ok=True)
    
    threading.Thread(target=pipeline_thread, args=(step_id, overwrite), daemon=True).start()
    return jsonify({"status": "ok", "message": f"Memulai tahap: {step_id}"})


@app.route("/api/stream-stages")
def stream_stages():
    def event_stream():
        with stage_lock:
            for stage in stage_queue:
                yield f"data: {json.dumps(stage)}\n\n"
        last_index = len(stage_queue)
        while True:
            time.sleep(0.2)
            with stage_lock:
                if len(stage_queue) > last_index:
                    for i in range(last_index, len(stage_queue)):
                        yield f"data: {json.dumps(stage_queue[i])}\n\n"
                    last_index = len(stage_queue)
    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/api/stage-summary")
def api_stage_summary():
    with stage_counts_lock:
        counts = dict(stage_counts)
    with stage_details_lock:
        details = list(stage_details)
    return jsonify({"counts": counts, "details": details})


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
        # Track generation to detect new runs
        with log_generation_lock:
            current_generation = log_generation
        while True:
            time.sleep(0.2)
            with log_lock:
                # Check if generation changed (new run started)
                with log_generation_lock:
                    if log_generation != current_generation:
                        current_generation = log_generation
                        # Send reset event
                        yield f"data: {json.dumps({'type': 'reset', 'generation': current_generation})}\n\n"
                        # Replay all current logs
                        for log in log_queue:
                            yield f"data: {json.dumps(log)}\n\n"
                        last_index = len(log_queue)
                        continue
                if len(log_queue) > last_index:
                    for i in range(last_index, len(log_queue)):
                        yield f"data: {json.dumps(log_queue[i])}\n\n"
                    last_index = len(log_queue)
    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/api/summary")
def api_summary():
    with step_summaries_lock:
        return jsonify(step_summaries)


@app.route("/api/download/<file_type>")
def api_download(file_type):
    """Download Excel summary files from logs/"""
    file_map = {
        "edit_failed": "logs/edit_failed.xlsx",
        "edit_stages": "logs/edit_stages.xlsx",
        "merge_failed": "logs/merge_failed.xlsx",
        "merge_skipped": "logs/merge_skipped.xlsx",
    }
    if file_type not in file_map:
        return jsonify({"status": "error", "message": "File type not found"}), 404
    
    file_path = Path(file_map[file_type])
    if not file_path.exists():
        return jsonify({"status": "error", "message": "File not generated yet"}), 404
    
    from flask import send_file
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    import webbrowser
    port = 5000
    add_log("Server Web Lokal OCR Foto Timemark dimulai.", "system")
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    app.run(host="127.0.0.1", port=port, debug=False)
