import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { PATHS } from "@/lib/paths";

function countFilesRecursive(dir: string, ext: string): number {
  if (!fs.existsSync(dir)) return 0;
  let count = 0;
  const walk = (current: string) => {
    const entries = fs.readdirSync(current, { withFileTypes: true });
    for (const e of entries) {
      const full = path.join(current, e.name);
      if (e.isDirectory()) {
        walk(full);
      } else if (e.isFile() && e.name.toLowerCase().endsWith(ext)) {
        count++;
      }
    }
  };
  walk(dir);
  return count;
}

export async function GET() {
  try {
    const counts = {
      pdf_source: countFilesRecursive(PATHS.pdfSource, ".pdf"),
      pdf_target: countFilesRecursive(PATHS.pdfTarget, ".pdf"),
      photos_export: countFilesRecursive(PATHS.photosExport, ".jpg"),
      photos_edited: countFilesRecursive(PATHS.photosEdited, ".jpg"),
      photos_time: countFilesRecursive(PATHS.photosTime, ".jpg"),
      photos_coord: countFilesRecursive(PATHS.photosCoord, ".jpg"),
      pdf_merged: countFilesRecursive(PATHS.pdfMerged, ".pdf"),
      pdf_merged_time: countFilesRecursive(PATHS.pdfMergedTime, ".pdf"),
      pdf_merged_coord: countFilesRecursive(PATHS.pdfMergedCoord, ".pdf"),
    };

    return NextResponse.json({ success: true, counts });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
