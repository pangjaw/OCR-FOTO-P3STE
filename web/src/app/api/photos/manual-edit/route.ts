import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { APP_DIR, PATHS } from "@/lib/paths";
import { spawnPython } from "@/lib/python-runner";

function helperCalculateDate(baseDate: string, photoStem: string): string {
  let cleanDate = (baseDate || "").trim();
  const dupMatch = cleanDate.match(/^(.*?\s\d{2}:\d{2})(?:\s+\d{2}:\d{2})+$/);
  if (dupMatch) cleanDate = dupMatch[1];

  const m = cleanDate.match(/^(.*?\d{4})\s+(\d{2}):(\d{2})$/);
  if (!m) return cleanDate;

  const [_, datePart, hh, mm] = m;
  let totalMin = parseInt(hh, 10) * 60 + parseInt(mm, 10);
  let pct = 0;
  if (photoStem === "50") pct = 50;
  else if (photoStem === "100") pct = 100;
  const duration = 45;
  totalMin += Math.round((pct * duration) / 100);

  const newHH = String(Math.floor(totalMin / 60) % 24).padStart(2, "0");
  const newMM = String(totalMin % 60).padStart(2, "0");
  return `${datePart} ${newHH}:${newMM}`;
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      mode = "standard",
      rawRelPath,
      dateText,
      timeText,
      coordText,
      yPos,
      xPos,
      fontSize,
      opacity,
      timGroup,
      applyToFolder,
    } = body;

    if (!rawRelPath) {
      return NextResponse.json(
        { error: "rawRelPath wajib diisi" },
        { status: 400 }
      );
    }

    const group = timGroup || "Tim_1";
    const timNum = parseInt(group.replace(/\D+/g, ""), 10) || 1;
    const normalizedRel = rawRelPath.replace(/\\/g, "/");
    const relDir = path.dirname(normalizedRel);
    const folderPath = path.join(PATHS.photosExport, relDir);

    let targetRelPaths = [normalizedRel];
    if (applyToFolder && fs.existsSync(folderPath) && fs.statSync(folderPath).isDirectory()) {
      const files = fs.readdirSync(folderPath).filter((f) => f.toLowerCase().endsWith(".jpg"));
      if (files.length > 0) {
        targetRelPaths = files.map((f) => `${relDir}/${f}`.replace(/\\/g, "/"));
      }
    }

    const errors: string[] = [];

    // Branch 1: Mode Koordinat
    if (mode === "coord" || (!dateText && !timeText && coordText !== undefined)) {
      const pyScript = path.join(PATHS.scripts, "edit_photo_coordinate_only.py");

      for (const relP of targetRelPaths) {
        const args = [
          pyScript,
          "--input",
          relP,
          "--tim-filter",
          String(timNum),
        ];
        if (coordText) {
          args.push("--coord-override", String(coordText).trim());
        }
        if (yPos !== undefined && yPos !== null && yPos !== "") {
          args.push("--y-override", String(yPos));
        }
        if (xPos !== undefined && xPos !== null && xPos !== "") {
          args.push("--x-override", String(xPos));
        }
        if (fontSize !== undefined && fontSize !== null && fontSize !== "") {
          args.push("--font-size", String(fontSize));
        }
        if (opacity !== undefined && opacity !== null && opacity !== "") {
          args.push("--opacity", String(opacity));
        }

        await new Promise<void>((resolve, reject) => {
          const stderrChunks: Buffer[] = [];
          const proc = spawnPython("edit_photo_coordinate_only", args);
          proc.stderr.on("data", (d) => stderrChunks.push(d));
          proc.on("close", (code) => {
            if (code === 0) resolve();
            else {
              const errStr = Buffer.concat(stderrChunks).toString("utf-8").slice(-500);
              reject(new Error(`Exit ${code}: ${errStr}`));
            }
          });
          proc.on("error", (err) => reject(err));
        }).catch((err) => {
          errors.push(`${relP}: ${err.message}`);
        });
      }

      if (errors.length > 0) {
        return NextResponse.json({ error: errors.join("; ") }, { status: 500 });
      }

      const coordUrl = `/api/static/04_koordinat/${group}/${normalizedRel}?t=${Date.now()}`;
      return NextResponse.json({ success: true, coordUrl, mode: "coord" });
    }

    // Branch 2: Mode Time
    if (mode === "time" || (!dateText && timeText !== undefined)) {
      const pyScript = path.join(PATHS.scripts, "edit_photo_time_only.py");

      for (const relP of targetRelPaths) {
        const args = [
          pyScript,
          "--input",
          relP,
          "--tim-filter",
          String(timNum),
        ];
        if (timeText) {
          args.push("--time-override", String(timeText).trim());
        }
        if (yPos !== undefined && yPos !== null && yPos !== "") {
          args.push("--y-override", String(yPos));
        }
        if (xPos !== undefined && xPos !== null && xPos !== "") {
          args.push("--x-override", String(xPos));
        }
        if (fontSize !== undefined && fontSize !== null && fontSize !== "") {
          args.push("--font-size", String(fontSize));
        }
        if (opacity !== undefined && opacity !== null && opacity !== "") {
          args.push("--opacity", String(opacity));
        }

        await new Promise<void>((resolve, reject) => {
          const stderrChunks: Buffer[] = [];
          const proc = spawnPython("edit_photo_time_only", args);
          proc.stderr.on("data", (d) => stderrChunks.push(d));
          proc.on("close", (code) => {
            if (code === 0) resolve();
            else {
              const errStr = Buffer.concat(stderrChunks).toString("utf-8").slice(-500);
              reject(new Error(`Exit ${code}: ${errStr}`));
            }
          });
          proc.on("error", (err) => reject(err));
        }).catch((err) => {
          errors.push(`${relP}: ${err.message}`);
        });
      }

      if (errors.length > 0) {
        return NextResponse.json({ error: errors.join("; ") }, { status: 500 });
      }

      const timeUrl = `/api/static/04_Time/${group}/${normalizedRel}?t=${Date.now()}`;
      return NextResponse.json({ success: true, timeUrl, mode: "time" });
    }

    // Branch 3: Standard Mode (edit_timemark_ide1)
    if (!dateText) {
      return NextResponse.json(
        { error: "rawRelPath dan dateText wajib diisi" },
        { status: 400 }
      );
    }

    const pyScript = path.join(PATHS.scripts, "edit_timemark_ide1.py");

    for (const relP of targetRelPaths) {
      const inputFile = path.join(PATHS.photosExport, relP);
      const outputFile = path.join(PATHS.photosEdited, group, relP);
      fs.mkdirSync(path.dirname(outputFile), { recursive: true });

      const stem = path.basename(relP, ".jpg");
      const photoDateText = helperCalculateDate(dateText, stem);

      const args = [
        pyScript,
        "--input",
        inputFile,
        "--single-out",
        outputFile,
        "--date",
        photoDateText,
      ];

      if (yPos !== undefined && yPos !== null && yPos !== "") {
        args.push("--y-override", String(yPos));
      }
      if (xPos !== undefined && xPos !== null && xPos !== "") {
        args.push("--x-override", String(xPos));
      }

      await new Promise<void>((resolve, reject) => {
        const stderrChunks: Buffer[] = [];
        const proc = spawnPython("edit_timemark_ide1", args);
        proc.stderr.on("data", (d) => stderrChunks.push(d));
        proc.on("close", (code) => {
          if (code === 0) {
            resolve();
          } else {
            const errStr = Buffer.concat(stderrChunks).toString("utf-8").slice(-500);
            reject(new Error(`Exit ${code}: ${errStr}`));
          }
        });
        proc.on("error", (err) => reject(err));
      }).catch((err) => {
        errors.push(`${relP}: ${err.message}`);
      });

      // Update meta.json
      const metaFile = path.join(path.dirname(outputFile), "meta.json");
      let metaData: Record<string, any> = {};
      if (fs.existsSync(metaFile)) {
        try {
          metaData = JSON.parse(fs.readFileSync(metaFile, "utf-8"));
        } catch {}
      }

      const photoName = path.basename(relP);
      metaData[photoName] = {
        ...(metaData[photoName] || {}),
        manualEdit: true,
        xPos: xPos !== undefined && xPos !== "" ? parseInt(xPos, 10) : 14,
        yPos: yPos !== undefined && yPos !== "" ? parseInt(yPos, 10) : 220,
        dateText: photoDateText,
        updatedAt: new Date().toISOString(),
      };

      fs.writeFileSync(metaFile, JSON.stringify(metaData, null, 2), "utf-8");
    }

    if (errors.length > 0) {
      return NextResponse.json({ error: errors.join("; ") }, { status: 500 });
    }

    const editedUrl = `/api/static/04_photos_edited/${group}/${normalizedRel}?t=${Date.now()}`;
    return NextResponse.json({ success: true, editedUrl, mode: "standard" });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
