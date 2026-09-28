import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { APP_DIR, PATHS } from "@/lib/paths";
import { spawnPython } from "@/lib/python-runner";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { action = "batch", mode = "pipeline", customPath = "", file = "", kaur = "", pnc1 = "", pnc2 = "" } = body;

    let targetFolder = PATHS.pdfTarget;
    if (mode === "custom") {
      if (!customPath || !fs.existsSync(customPath)) {
        return NextResponse.json(
          { error: `Folder kustom tidak ditemukan: ${customPath}` },
          { status: 400 }
        );
      }
      targetFolder = customPath;
    }

    const pyScript = path.join(PATHS.scripts, "audit_and_correct_personnel.py");
    let args: string[] = [];

    if (action === "batch") {
      args = [pyScript, "--action", "auto-correct-batch", "--folder", targetFolder];
    } else if (action === "no-sc") {
      args = [pyScript, "--action", "auto-correct-no-sc", "--folder", targetFolder];
    } else if (action === "single") {
      if (!file || !kaur || !pnc1 || !pnc2) {
        return NextResponse.json(
          { error: "Parameter file, kaur, pnc1, dan pnc2 harus diisi untuk koreksi tunggal." },
          { status: 400 }
        );
      }
      let pdfPath = file;
      if (!path.isAbsolute(pdfPath)) {
        pdfPath = path.join(targetFolder, file);
      }
      if (!fs.existsSync(pdfPath)) {
        return NextResponse.json(
          { error: `Berkas PDF tidak ditemukan: ${pdfPath}` },
          { status: 404 }
        );
      }
      args = [
        pyScript,
        "--action",
        "correct-single",
        "--file",
        pdfPath,
        "--kaur",
        kaur,
        "--pnc1",
        pnc1,
        "--pnc2",
        pnc2,
      ];
    } else {
      return NextResponse.json({ error: "Aksi tidak dikenal" }, { status: 400 });
    }

    const pyProc = spawnPython("audit_and_correct_personnel", args);
    let stdout = "";
    let stderr = "";
    pyProc.stdout.on("data", (d) => (stdout += d.toString("utf-8")));
    pyProc.stderr.on("data", (d) => (stderr += d.toString("utf-8")));

    const result = await new Promise<any>((resolve, reject) => {
      pyProc.on("close", (code) => {
        if (code !== 0) {
          return reject(new Error(`Koreksi gagal (Exit ${code}): ${stderr || stdout}`));
        }
        try {
          let parsed = {};
          const output = stdout.trim();
          if (output) {
            try {
              parsed = JSON.parse(output);
            } catch {
              const start = output.indexOf("{");
              const end = output.lastIndexOf("}");
              if (start >= 0 && end > start) {
                parsed = JSON.parse(output.slice(start, end + 1));
              }
            }
          }
          resolve(parsed);
        } catch (e: any) {
          reject(e);
        }
      });
    });

    // Invalidate cache if modified 02_pdf_target
    const cachePath = path.join(PATHS.logs, "file_personnel_cache.json");
    if (fs.existsSync(cachePath)) {
      try {
        fs.unlinkSync(cachePath);
      } catch {}
    }

    return NextResponse.json({ success: true, action, ...result });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
