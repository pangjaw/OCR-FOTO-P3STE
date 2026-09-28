import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { APP_DIR, PATHS } from "@/lib/paths";
import { spawnPython } from "@/lib/python-runner";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const { action = "audit", mode = "pipeline", folderPath = "" } = body;
    const isExternal = mode === "external" || mode === "custom";
    const inputDir = isExternal ? path.resolve(String(folderPath).trim()) : PATHS.pdfTarget;

    if (!fs.existsSync(inputDir) || !fs.statSync(inputDir).isDirectory()) {
      return NextResponse.json(
        { error: `Folder PDF tidak ditemukan: ${inputDir}` },
        { status: 400 }
      );
    }

    const args = ["--input", inputDir];
    if (action === "correct") {
      args.push("--output", inputDir);
    }

    const proc = spawnPython("correct_pdf_dates", args);

    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d.toString("utf-8")));
    proc.stderr.on("data", (d) => (stderr += d.toString("utf-8")));

    const result = await new Promise<any>((resolve, reject) => {
      proc.on("close", (code) => {
        let parsed = null;
        try {
          const lines = stdout.trim().split(/\r?\n/).filter(Boolean);
          const lastLine = lines.pop() || "{}";
          parsed = JSON.parse(lastLine);
        } catch {
          const start = stdout.indexOf("{");
          const end = stdout.lastIndexOf("}");
          if (start >= 0 && end > start) {
            try {
              parsed = JSON.parse(stdout.slice(start, end + 1));
            } catch {}
          }
        }

        if (code !== 0 || !parsed) {
          reject(new Error(stderr || stdout || `Gagal menjalankan audit tanggal (Exit ${code})`));
        } else {
          resolve(parsed);
        }
      });
    });

    return NextResponse.json(result);
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
