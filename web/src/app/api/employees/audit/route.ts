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

    const pyProc = spawnPython("audit_and_correct_personnel", [
      "--action",
      "audit",
      "--folder",
      targetFolder,
    ]);

    let stdout = "";
    let stderr = "";
    pyProc.stdout.on("data", (d) => (stdout += d.toString("utf-8")));
    pyProc.stderr.on("data", (d) => (stderr += d.toString("utf-8")));

    const result = await new Promise<any>((resolve, reject) => {
      pyProc.on("close", (code) => {
        if (code !== 0) {
          return reject(new Error(`Audit gagal (Exit ${code}): ${stderr || stdout}`));
        }
        try {
          let parsed;
          try {
            parsed = JSON.parse(stdout.trim());
          } catch {
            const start = stdout.indexOf("{");
            const end = stdout.lastIndexOf("}");
            if (start >= 0 && end > start) {
              parsed = JSON.parse(stdout.slice(start, end + 1));
            }
          }
          if (!parsed || typeof parsed !== "object") {
            throw new Error("Format output JSON audit tidak valid");
          }
          resolve(parsed);
        } catch (e: any) {
          reject(new Error(`Gagal mem-parse hasil audit: ${e.message}`));
        }
      });
    });

    return NextResponse.json({ success: true, mode, folder: targetFolder, ...result });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
