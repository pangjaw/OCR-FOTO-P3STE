import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";
import { PATHS } from "@/lib/paths";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { rel, mode = "tanggal", detector = "guide" } = body;

    if (!rel) {
      return NextResponse.json({ success: false, error: "rel path is required" }, { status: 400 });
    }

    const pyScript = path.join(PATHS.scripts, "replace_export_photo.py");
    const pyArgs = [
      pyScript,
      "--action",
      "revert",
      "--target",
      rel,
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
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
