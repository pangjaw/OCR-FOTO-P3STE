import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { PATHS } from "@/lib/paths";

export async function POST(req: NextRequest) {
  let tempPath: string | null = null;
  try {
    const formData = await req.formData();
    const rel = formData.get("rel") as string;
    const mode = (formData.get("mode") as string) || "tanggal";
    const detector = (formData.get("detector") as string) || "guide";
    const file = formData.get("file") as File | null;

    if (!rel) {
      return NextResponse.json({ success: false, error: "rel path is required" }, { status: 400 });
    }
    if (!file) {
      return NextResponse.json({ success: false, error: "image file is required" }, { status: 400 });
    }

    const tmpDir = path.join(PATHS.root, "tmp_uploads");
    if (!fs.existsSync(tmpDir)) {
      fs.mkdirSync(tmpDir, { recursive: true });
    }

    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    const tempFileName = `upload_${Date.now()}_${path.basename(rel)}`;
    tempPath = path.join(tmpDir, tempFileName);
    fs.writeFileSync(tempPath, buffer);

    const pyScript = path.join(PATHS.scripts, "replace_export_photo.py");
    const pyArgs = [
      pyScript,
      "--action",
      "replace",
      "--target",
      rel,
      "--image",
      tempPath,
      "--mode",
      mode,
      "--detector",
      detector,
    ];

    return await new Promise<NextResponse>((resolve) => {
      const proc = spawn("python", pyArgs, { cwd: PATHS.root });
      let stdout = "";
      let stderr = "";

      proc.stdout.on("data", (d) => (stdout += d.toString()));
      proc.stderr.on("data", (d) => (stderr += d.toString()));

      proc.on("close", (code) => {
        if (tempPath && fs.existsSync(tempPath)) {
          try {
            fs.unlinkSync(tempPath);
          } catch {}
        }

        try {
          const resJson = JSON.parse(stdout.trim());
          resolve(NextResponse.json(resJson));
        } catch {
          resolve(
            NextResponse.json({
              success: code === 0,
              stdout,
              stderr,
            })
          );
        }
      });
    });
  } catch (error: any) {
    if (tempPath && fs.existsSync(tempPath)) {
      try {
        fs.unlinkSync(tempPath);
      } catch {}
    }
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
