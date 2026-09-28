import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { APP_DIR, PATHS } from "@/lib/paths";
import { spawnPython } from "@/lib/python-runner";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const { withPersonnel = false, mode = "pipeline", folderPath = "" } = body;

    const outputName = `DAFTAR_DINASAN_PEGAWAI${withPersonnel ? "_DENGAN_PERSONIL" : ""}_${Date.now()}.xlsx`;
    const outputPath = path.join(PATHS.logs, outputName);

    const args = ["--output", outputPath];
    if (withPersonnel) args.push("--with-personnel");

    // If external/custom folder specified, generate temporary schedule first
    if (mode === "custom" && folderPath && fs.existsSync(folderPath)) {
      const tempSched = path.join(PATHS.logs, `schedule_dinasan_${Date.now()}.json`);
      const schedProc = spawnPython("scheduler", [
        "--pdf-dir",
        folderPath,
        "--photos-dir",
        PATHS.photosExport,
        "--mapping",
        path.join(PATHS.config, "asset_waktu_mapping.json"),
        "--data-acuan",
        path.join(PATHS.config, "data_acuan_tenaga_gabungan.json"),
        "--output",
        tempSched,
      ]);
      await new Promise<void>((resolve, reject) => {
        schedProc.on("close", (code) => (code === 0 ? resolve() : reject(new Error("Gagal membuat schedule custom"))));
      });
      args.push("--schedule", tempSched);
    }

    const pyProc = spawnPython("export_dinasan_excel", args);
    let stdout = "";
    let stderr = "";
    pyProc.stdout.on("data", (d) => (stdout += d.toString("utf-8")));
    pyProc.stderr.on("data", (d) => (stderr += d.toString("utf-8")));

    const result = await new Promise<{ fileName: string }>((resolve, reject) => {
      pyProc.on("close", (code) => {
        if (code === 0 && fs.existsSync(outputPath)) {
          resolve({ fileName: outputName });
        } else {
          // Check if latest generated dinasan file exists
          const dinasanFiles = fs
            .readdirSync(PATHS.logs)
            .filter((f) => f.startsWith("DAFTAR_DINASAN_PEGAWAI") && f.endsWith(".xlsx"));
          if (dinasanFiles.length > 0) {
            dinasanFiles.sort(
              (a, b) =>
                fs.statSync(path.join(PATHS.logs, b)).mtimeMs -
                fs.statSync(path.join(PATHS.logs, a)).mtimeMs
            );
            return resolve({ fileName: dinasanFiles[0] });
          }
          reject(new Error(stderr || stdout || `Gagal membuat Excel Dinasan (Exit ${code})`));
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
