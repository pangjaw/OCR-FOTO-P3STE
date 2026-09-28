import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { APP_DIR, PATHS } from "@/lib/paths";
import { spawnPython } from "@/lib/python-runner";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const { mode = "pipeline", folderPath = "" } = body;
    const isExternal = mode === "external" || mode === "custom";
    const pdfDir = isExternal ? path.resolve(String(folderPath).trim()) : PATHS.pdfTarget;

    if (!fs.existsSync(pdfDir) || !fs.statSync(pdfDir).isDirectory()) {
      return NextResponse.json(
        { error: `Folder PDF tidak ditemukan: ${pdfDir}` },
        { status: 400 }
      );
    }

    const stamp = Date.now();
    const schedulePath = isExternal
      ? path.join(PATHS.logs, `asset_schedule_${stamp}.json`)
      : PATHS.scheduleJson;

    if (!isExternal && !fs.existsSync(schedulePath)) {
      return NextResponse.json(
        { error: "schedule.json belum tersedia. Jalankan Step 3 terlebih dahulu." },
        { status: 400 }
      );
    }

    // If external, run scheduler first
    if (isExternal) {
      const schedProc = spawnPython("scheduler", [
        "--pdf-dir",
        pdfDir,
        "--photos-dir",
        PATHS.photosExport,
        "--mapping",
        path.join(PATHS.config, "asset_waktu_mapping.json"),
        "--data-acuan",
        path.join(PATHS.config, "data_acuan_tenaga_gabungan.json"),
        "--output",
        schedulePath,
      ]);

      await new Promise<void>((resolve, reject) => {
        schedProc.on("close", (code) =>
          code === 0 && fs.existsSync(schedulePath)
            ? resolve()
            : reject(new Error(`Gagal membaca jadwal aset eksternal`))
        );
      });
    }

    const outputName = `DATA_ASET_${stamp}.xlsx`;
    const outputPath = path.join(PATHS.logs, outputName);

    const proc = spawnPython("export_asset_data_excel", [
      "--schedule",
      schedulePath,
      "--pdf-dir",
      pdfDir,
      "--output",
      outputPath,
    ]);

    let stderr = "";
    proc.stderr.on("data", (d) => (stderr += d.toString("utf-8")));

    const result = await new Promise<{ fileName: string }>((resolve, reject) => {
      proc.on("close", (code) => {
        if (isExternal && fs.existsSync(schedulePath)) {
          try {
            fs.unlinkSync(schedulePath);
          } catch {}
        }
        if (code === 0 && fs.existsSync(outputPath)) {
          resolve({ fileName: outputName });
        } else {
          reject(new Error(stderr || `Gagal membuat Excel data aset (Exit ${code})`));
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
