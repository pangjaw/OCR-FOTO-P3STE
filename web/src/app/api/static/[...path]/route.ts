import { NextRequest, NextResponse } from "next/server";
import path from "path";
import fs from "fs";
import { APP_DIR } from "@/lib/paths";

export async function GET(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  try {
    const rawSegments = params.path || [];
    // Decode segments
    const decodedSegments = rawSegments.map((seg) => decodeURIComponent(seg));
    const targetFile = path.resolve(APP_DIR, ...decodedSegments);

    // Security boundary check: targetFile must be inside APP_DIR
    const rel = path.relative(APP_DIR, targetFile);
    if (rel.startsWith("..") || path.isAbsolute(rel)) {
      return new NextResponse("Forbidden: Access outside app directory", { status: 403 });
    }

    if (!fs.existsSync(targetFile) || !fs.statSync(targetFile).isFile()) {
      return new NextResponse("File not found", { status: 404 });
    }

    const ext = path.extname(targetFile).toLowerCase();
    let contentType = "application/octet-stream";
    if (ext === ".jpg" || ext === ".jpeg") contentType = "image/jpeg";
    else if (ext === ".png") contentType = "image/png";
    else if (ext === ".webp") contentType = "image/webp";
    else if (ext === ".pdf") contentType = "application/pdf";
    else if (ext === ".json") contentType = "application/json";
    else if (ext === ".txt") contentType = "text/plain; charset=utf-8";

    const fileBuffer = fs.readFileSync(targetFile);

    return new NextResponse(fileBuffer, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
        Pragma: "no-cache",
        Expires: "0",
      },
    });
  } catch (error: any) {
    return new NextResponse(`Server error: ${error.message}`, { status: 500 });
  }
}
