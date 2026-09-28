import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { APP_DIR, PATHS } from "@/lib/paths";
import { spawnPython } from "@/lib/python-runner";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const { mode = "pipeline", customPath = "" } = body;
    const isCustom = mode === "custom";

    if (isCustom && (!customPath || !fs.existsSync(customPath))) {
      return NextResponse.json(
        { error: `Folder kustom tidak ditemukan: ${customPath}` },
        { status: 400 }
      );
    }

    const args = ["--output-dir", PATHS.logs];
    if (isCustom) {
      args.push("--mode", "custom", "--folder", customPath);
    } else {
      args.push("--mode", "pipeline");
    }

    const pyProc = spawnPython("export_tablo_excel", args);
    let stdout = "";
    let stderr = "";
    pyProc.stdout.on("data", (d) => (stdout += d.toString("utf-8")));
    pyProc.stderr.on("data", (d) => (stderr += d.toString("utf-8")));

    const result = await new Promise<{ fileName: string }>((resolve, reject) => {
      pyProc.on("close", (code) => {
        const match = stdout.match(/\[OUTPUT_FILE\]\s*(.+)/);
        const resolvedPath = match ? match[1].trim() : null;
        if (code === 0 && resolvedPath && fs.existsSync(resolvedPath)) {
          resolve({ fileName: path.basename(resolvedPath) });
        } else {
          reject(new Error(stderr || stdout || `Gagal membuat Tablo Excel (Exit ${code})`));
        }
      });
    });

    return NextResponse.json({
      success: true,
      fileName: result.fileName,
      downloadUrl: `/api/export/download?file=${encodeURIComponent(result.fileName)}`,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
