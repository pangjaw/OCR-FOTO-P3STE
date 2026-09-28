import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { PATHS } from "@/lib/paths";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const fileName = searchParams.get("file");

    if (!fileName) {
      return new NextResponse("Parameter 'file' diperlukan", { status: 400 });
    }

    const safeName = path.basename(fileName);
    const filePath = path.join(PATHS.logs, safeName);

    if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
      return new NextResponse("Berkas Excel tidak ditemukan", { status: 404 });
    }

    const fileBuffer = fs.readFileSync(filePath);

    return new NextResponse(fileBuffer, {
      status: 200,
      headers: {
        "Content-Type":
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": `attachment; filename="${encodeURIComponent(safeName)}"`,
      },
    });
  } catch (err: any) {
    return new NextResponse(`Error: ${err.message}`, { status: 500 });
  }
}
