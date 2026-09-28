import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { APP_DIR, PATHS } from "@/lib/paths";
import { spawnPython } from "@/lib/python-runner";

function expandIdentifierVariants(ident: string): string[] {
  const set = new Set<string>();
  if (!ident) return [];
  const norm = ident.toUpperCase().trim();
  set.add(norm);
  const baseNoDate = norm.replace(/_\d{2}-\d{2}$/, "").trim();
  set.add(baseNoDate);

  if (baseNoDate === "ZP 41 BOO") set.add("ZP 41B BOO");
  if (baseNoDate === "ZP 41B BOO") set.add("ZP 41 BOO");

  if (baseNoDate.includes("JPL 26N")) {
    set.add("JPL 26N CLT");
    set.add("JPL 26N BJD");
    set.add("JPL 26N CLT-BJD");
    set.add("JPL 26N BJD-CLT");
  }

  const m0 = baseNoDate.match(/^(JPL\s+)0?(\d+[A-Z]?)\s+(.*)$/i);
  if (m0) {
    const num = parseInt(m0[2], 10);
    const padNum = String(num).padStart(2, "0");
    set.add(`${m0[1].toUpperCase()}${num} ${m0[3].toUpperCase()}`);
    set.add(`${m0[1].toUpperCase()}${padNum} ${m0[3].toUpperCase()}`);
  }

  const m = baseNoDate.match(/^(JPL\s+(?:BNR|\d+[A-Z]?))\s+([A-Z]{2,3}(?:-[A-Z]{2,3})+)$/i);
  if (m) {
    const prefix = m[1].toUpperCase();
    const stations = m[2].toUpperCase().split("-");
    stations.forEach((st) => set.add(`${prefix} ${st}`));
    const sortedStations = stations.slice().sort().join("-");
    const reversedStations = stations.slice().reverse().join("-");
    set.add(`${prefix} ${sortedStations}`);
    set.add(`${prefix} ${reversedStations}`);
  }
  return Array.from(set);
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { targetPdfName, rawRelPath, mode = "standard" } = body;

    let targetPdf = targetPdfName;

    // If targetPdfName not given, try to find target pdf by identifier in rawRelPath
    if (!targetPdf && rawRelPath) {
      const parts = String(rawRelPath).replace(/\\/g, "/").split("/");
      const ident = parts.length >= 3 ? parts[parts.length - 2] : "";
      const variants = expandIdentifierVariants(ident);

      // Check schedule.json
      if (fs.existsSync(PATHS.scheduleJson)) {
        try {
          const sched = JSON.parse(fs.readFileSync(PATHS.scheduleJson, "utf-8"));
          for (const s of sched.schedules || []) {
            const sId = (s.identifier || "").toUpperCase();
            const baseId = (s.base_identifier || "").toUpperCase();
            if (variants.some((v) => v === sId || v === baseId)) {
              if (s.file) {
                targetPdf = s.file;
                break;
              }
            }
          }
        } catch (e) {}
      }

      if (!targetPdf && fs.existsSync(PATHS.pdfTarget)) {
        const files = fs.readdirSync(PATHS.pdfTarget);
        const match = files.find((f) => {
          const u = f.toUpperCase();
          return variants.some((v) => u.includes(v)) && u.endsWith(".PDF");
        }) || files.find((f) => f.includes(ident) && f.endsWith(".pdf"));
        if (match) targetPdf = match;
      }
    }

    if (!targetPdf) {
      return NextResponse.json(
        { error: "Nama berkas PDF target tidak dapat ditemukan." },
        { status: 400 }
      );
    }

    const targetPdfPath = path.join(PATHS.pdfTarget, targetPdf);
    if (!fs.existsSync(targetPdfPath)) {
      return NextResponse.json(
        { error: `Berkas target tidak ditemukan di 02_pdf_target: ${targetPdf}` },
        { status: 404 }
      );
    }

    const modeConfig = {
      standard: { photos: "./04_photos_edited", output: "./05_pdf_merged" },
      time: { photos: "./04_Time", output: "./05_pdf_merged_Time" },
      coord: { photos: "./04_koordinat", output: "./05_koordinat" },
    } as const;
    const selected = modeConfig[mode as keyof typeof modeConfig] || modeConfig.standard;
    const photosDir = selected.photos;
    const outputDir = selected.output;

    const args = [
      "--input",
      PATHS.pdfTarget,
      "--photos",
      photosDir,
      "--output",
      outputDir,
      "--file",
      targetPdf,
    ];

    const result = await new Promise<{ success: boolean; output: string }>((resolve) => {
      const proc = spawnPython("merge_pdf_foto", args);
      let outputText = "";
      proc.stdout.on("data", (d) => (outputText += d.toString("utf-8")));
      proc.stderr.on("data", (d) => (outputText += d.toString("utf-8")));
      proc.on("close", (code) => {
        resolve({ success: code === 0, output: outputText });
      });
    });

    if (!result.success) {
      return NextResponse.json(
        { error: "Gagal menggabungkan PDF", details: result.output },
        { status: 500 }
      );
    }

    let fileUrl = "";
    const summaryMatch = result.output.match(/__SUMMARY__:(.+)/);
    if (summaryMatch) {
      try {
        const parsed = JSON.parse(summaryMatch[1].trim());
        if (parsed.outputPath) {
          const absOut = path.resolve(parsed.outputPath);
          const absBase = path.resolve(outputDir);
          const rel = path.relative(absBase, absOut).replace(/\\/g, "/");
          const routePrefix = mode === "time" ? "/static/pdf-merged-time" : mode === "coord" ? "/static/pdf-merged-coord" : "/static/pdf-merged";
          fileUrl = `${routePrefix}/${rel}?v=${Date.now()}`;
        }
      } catch (_) {}
    }

    return NextResponse.json({
      success: true,
      status: "ok",
      pdfName: targetPdf,
      mode,
      fileUrl,
      details: result.output,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
