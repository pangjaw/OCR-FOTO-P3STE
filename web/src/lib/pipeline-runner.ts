import { spawn, ChildProcess } from "child_process";
import path from "path";
import { APP_DIR, PATHS } from "./paths";
import { spawnPython } from "./python-runner";

export interface StepConfig {
  script: string;
  args: string[];
  label?: string;
}

export const STEP_SCRIPTS: Record<string, StepConfig> = {
  step1: { script: "export_pdf_foto.py", args: [], label: "Step 1: Ekstraksi Foto (Asli)" },
  step1_crop: { script: "export_pdf_foto.py", args: ["--render-crop"], label: "Step 1 Crop: Ekstraksi Render 300 DPI" },
  "step1.5": { script: "auto_crop_collages.py", args: [], label: "Step 1.5: Auto-Crop Kolase" },
  step2: { script: "extract_pdf_dates.py", args: [], label: "Step 2: Ekstraksi Tanggal" },
  step3: { script: "scheduler.py", args: [], label: "Step 3: Penjadwalan Tim & Jam" },
  "step3.5": {
    script: "audit_and_correct_personnel.py",
    args: ["--action", "auto-correct-batch", "--folder", "02_pdf_target"],
    label: "Step 3.5: Koreksi Personil",
  },
  step4: { script: "edit_timemark_ide1.py", args: [], label: "Step 4: Edit Timemark" },
  step5: { script: "merge_pdf_foto.py", args: [], label: "Step 5: Gabung PDF" },
  step6_core_optik: {
    script: "correct_serat_optik_cores.py",
    args: ["--apply", "--folders", "05_pdf_merged"],
    label: "Step 6: Koreksi Core Optik",
  },
  // Time pipeline
  step4_time: {
    script: "edit_photo_time_only.py",
    args: ["--schedule", "schedule.json"],
    label: "Step 4 Time: Edit Jam Foto",
  },
  step5_time: {
    script: "merge_pdf_foto.py",
    args: ["--photos", "./04_Time", "--output", "./05_pdf_merged_Time"],
    label: "Step 5 Time: Gabung PDF Jam",
  },
  step6_core_optik_time: {
    script: "correct_serat_optik_cores.py",
    args: ["--apply", "--folders", "05_pdf_merged_Time"],
    label: "Step 6 Time: Koreksi Core Optik",
  },
  // Coordinate pipeline
  step4_coord: {
    script: "edit_photo_coordinate_only.py",
    args: ["--schedule", "schedule.json"],
    label: "Step 4 Coord: Edit Koordinat Foto",
  },
  step5_coord: {
    script: "merge_pdf_foto.py",
    args: ["--photos", "./04_koordinat", "--output", "./05_koordinat"],
    label: "Step 5 Coord: Gabung PDF Koordinat",
  },
  step6_core_optik_coord: {
    script: "correct_serat_optik_cores.py",
    args: ["--apply", "--folders", "05_koordinat"],
    label: "Step 6 Coord: Koreksi Core Optik",
  },
};

interface PipelineState {
  isRunning: boolean;
  currentStepName: string | null;
  stepStatuses: Record<string, "waiting" | "running" | "completed" | "error">;
  logHistory: string[];
  activeProcess: ChildProcess | null;
  subscribers: Set<(msg: any) => void>;
}

const g = globalThis as unknown as { __pipelineState?: PipelineState };

if (!g.__pipelineState) {
  g.__pipelineState = {
    isRunning: false,
    currentStepName: null,
    stepStatuses: {},
    logHistory: [],
    activeProcess: null,
    subscribers: new Set(),
  };
}

const state = g.__pipelineState;

export function broadcastMessage(msg: any) {
  if (msg.type === "log" && typeof msg.line === "string") {
    state.logHistory.push(msg.line);
    if (state.logHistory.length > 2000) {
      state.logHistory = state.logHistory.slice(-1000);
    }
  }
  state.subscribers.forEach((sub) => {
    try {
      sub(msg);
    } catch {
      state.subscribers.delete(sub);
    }
  });
}

export function subscribeLogs(cb: (msg: any) => void) {
  state.subscribers.add(cb);
  return () => {
    state.subscribers.delete(cb);
  };
}

export function getPipelineState() {
  return {
    is_running: state.isRunning,
    current_step: state.currentStepName,
    step_statuses: { ...state.stepStatuses },
    recent_logs: state.logHistory.slice(-80),
  };
}

export function clearLogs() {
  state.logHistory = [];
  broadcastMessage({ type: "clear" });
}

export function stopPipeline(): boolean {
  if (!state.isRunning || !state.activeProcess) {
    state.isRunning = false;
    state.currentStepName = null;
    return false;
  }

  const pid = state.activeProcess.pid;
  try {
    if (pid && process.platform === "win32") {
      spawn("taskkill", ["/pid", String(pid), "/f", "/t"]);
    } else if (state.activeProcess) {
      state.activeProcess.kill("SIGTERM");
    }
  } catch (err: any) {
    console.error("Error stopping process:", err);
  }

  state.isRunning = false;
  state.activeProcess = null;
  state.currentStepName = null;
  broadcastMessage({ type: "status", is_running: false, step: "stopped" });
  broadcastMessage({ type: "log", line: "\n🛑 [SYSTEM] Proses berhasil dihentikan oleh pengguna.\n" });
  return true;
}

function runSingleScript(scriptItem: { script: string; args: string[] }): Promise<void> {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(PATHS.scripts, scriptItem.script);
    broadcastMessage({
      type: "log",
      line: `\n=== Executing ${scriptItem.script} ${scriptItem.args.join(" ")} ===\n`,
    });

    const pyProc = spawnPython(scriptItem.script, scriptItem.args);

    state.activeProcess = pyProc;
    const recentStderr: string[] = [];

    pyProc.stdout.on("data", (data) => {
      const text = data.toString("utf-8");
      text.split("\n").forEach((line: string) => {
        const trimmed = line.trim();
        if (!trimmed) return;
        if (trimmed.startsWith('{"type":"stage"') || trimmed.startsWith('{"type":"quota_exceeded"')) {
          try {
            const parsed = JSON.parse(trimmed);
            broadcastMessage(parsed);
            return;
          } catch {}
        }
        if (trimmed.startsWith("__SUMMARY__:")) {
          try {
            const sumData = JSON.parse(trimmed.slice(12));
            broadcastMessage({ type: "summary", summary: sumData });
            return;
          } catch {}
        }
        broadcastMessage({ type: "log", line });
      });
    });

    pyProc.stderr.on("data", (data) => {
      const text = data.toString("utf-8");
      text.split("\n").forEach((line: string) => {
        const trimmed = line.trim();
        if (!trimmed) return;
        // Suppress noisy C-level zbar warnings
        if (
          trimmed.includes("zbar") ||
          trimmed.includes("Assertion") ||
          trimmed.includes("seg->finder") ||
          trimmed.includes("part=1") ||
          trimmed.includes("part=0")
        ) {
          return;
        }
        recentStderr.push(trimmed);
        if (recentStderr.length > 15) recentStderr.shift();
        broadcastMessage({ type: "log", line: `[STDERR] ${trimmed}` });
      });
    });

    pyProc.on("close", (code) => {
      state.activeProcess = null;
      if (code === 0) {
        broadcastMessage({
          type: "log",
          line: `\n✅ ${scriptItem.script} selesai dengan sukses (Exit code 0).\n`,
        });
        resolve();
      } else {
        let errBanner = `\n============================================================\n`;
        errBanner += `❌ [ERROR] ${scriptItem.script} berhenti dengan kode kesalahan (Exit Code: ${code})\n`;
        if (recentStderr.length > 0) {
          errBanner += `Keterangan Kesalahan:\n`;
          recentStderr.forEach((l) => (errBanner += `  • ${l}\n`));
        }
        errBanner += `============================================================\n`;
        broadcastMessage({ type: "log", line: errBanner });
        reject(new Error(`Script exited with code ${code}`));
      }
    });

    pyProc.on("error", (err) => {
      state.activeProcess = null;
      broadcastMessage({ type: "log", line: `\n❌ [ERROR] Gagal menjalankan python: ${err.message}\n` });
      reject(err);
    });
  });
}

export function resumePipeline(action: "continue_guide" | "stop"): boolean {
  if (!state.isRunning || !state.activeProcess || !state.activeProcess.stdin) {
    return false;
  }
  try {
    state.activeProcess.stdin.write(action + "\n");
    return true;
  } catch (err) {
    console.error("Failed to write to stdin:", err);
    return false;
  }
}

export async function runPipelineStep(
  step: string,
  options?: { detector?: string }
): Promise<{ success: boolean; error?: string }> {
  if (state.isRunning) {
    return { success: false, error: "Pipeline sedang berjalan." };
  }

  const isAllStandard = step === "all";
  const isAllTime = step === "all_time";
  const isAllCoord = step === "all_coord";
  const stepConfig = STEP_SCRIPTS[step];

  if (!isAllStandard && !isAllTime && !isAllCoord && !stepConfig) {
    return { success: false, error: `Step tidak dikenal: ${step}` };
  }

  state.isRunning = true;
  state.currentStepName = step;
  broadcastMessage({ type: "status", is_running: true, step: state.currentStepName });

  const detectorArg = options?.detector === "google_vision" ? ["--detector", "google_vision"] : [];

  let queue: { script: string; args: string[] }[] = [];

  if (isAllStandard) {
    queue = [
      { script: "export_pdf_foto.py", args: [] },
      { script: "auto_crop_collages.py", args: [] },
      { script: "extract_pdf_dates.py", args: [] },
      { script: "scheduler.py", args: [] },
      {
        script: "audit_and_correct_personnel.py",
        args: ["--action", "auto-correct-batch", "--folder", "02_pdf_target"],
      },
      { script: "extract_file_personnel.py", args: [] },
      { script: "edit_timemark_ide1.py", args: [...detectorArg] },
      { script: "merge_pdf_foto.py", args: [] },
      { script: "correct_serat_optik_cores.py", args: ["--apply", "--folders", "05_pdf_merged"] },
    ];
  } else if (isAllTime) {
    queue = [
      { script: "export_pdf_foto.py", args: [] },
      { script: "auto_crop_collages.py", args: [] },
      { script: "extract_pdf_dates.py", args: [] },
      { script: "scheduler.py", args: [] },
      {
        script: "audit_and_correct_personnel.py",
        args: ["--action", "auto-correct-batch", "--folder", "02_pdf_target"],
      },
      { script: "extract_file_personnel.py", args: [] },
      { script: "edit_photo_time_only.py", args: ["--schedule", "schedule.json"] },
      {
        script: "merge_pdf_foto.py",
        args: ["--photos", "./04_Time", "--output", "./05_pdf_merged_Time"],
      },
      { script: "correct_serat_optik_cores.py", args: ["--apply", "--folders", "05_pdf_merged_Time"] },
    ];
  } else if (isAllCoord) {
    queue = [
      { script: "export_pdf_foto.py", args: [] },
      { script: "auto_crop_collages.py", args: [] },
      { script: "extract_pdf_dates.py", args: [] },
      { script: "scheduler.py", args: [] },
      {
        script: "audit_and_correct_personnel.py",
        args: ["--action", "auto-correct-batch", "--folder", "02_pdf_target"],
      },
      { script: "extract_file_personnel.py", args: [] },
      { script: "edit_photo_coordinate_only.py", args: ["--schedule", "schedule.json"] },
      {
        script: "merge_pdf_foto.py",
        args: ["--photos", "./04_koordinat", "--output", "./05_koordinat"],
      },
      { script: "correct_serat_optik_cores.py", args: ["--apply", "--folders", "05_koordinat"] },
    ];
  } else if (step === "step4") {
    queue = [{ script: "edit_timemark_ide1.py", args: [...detectorArg] }];
  } else {
    queue = [stepConfig];
  }

  // Execute queue asynchronously so route handler returns immediately
  (async () => {
    try {
      for (const item of queue) {
        if (!state.isRunning) break;
        await runSingleScript(item);
      }
      state.isRunning = false;
      state.currentStepName = null;
      broadcastMessage({ type: "status", is_running: false, step: "completed" });
    } catch (err: any) {
      state.isRunning = false;
      state.currentStepName = null;
      broadcastMessage({ type: "status", is_running: false, step: "error" });
    }
  })();

  return { success: true };
}
