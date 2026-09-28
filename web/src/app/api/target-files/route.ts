import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { PATHS } from "@/lib/paths";

export async function GET() {
  try {
    const schedPath = PATHS.scheduleJson;
    if (fs.existsSync(schedPath)) {
      try {
        const sched = JSON.parse(fs.readFileSync(schedPath, "utf-8"));
        const targetMap = new Map();
        (sched.schedules || []).forEach((item: any) => {
          const fn = item.file;
          if (!fn) return;
          if (!targetMap.has(fn)) {
            targetMap.set(fn, {
              file: fn,
              category: item.category || "",
              btp: item.btp || "",
              date: item.iso_date || "",
              tim: item.tim || 1,
              identifiers: [],
            });
          }
          const entry = targetMap.get(fn);
          const ident = item.identifier;
          const baseIdent = item.base_identifier || ident;
          if (ident && !entry.identifiers.includes(ident)) entry.identifiers.push(ident);
          if (baseIdent && !entry.identifiers.includes(baseIdent)) entry.identifiers.push(baseIdent);
        });

        const targets = Array.from(targetMap.values()).sort((a: any, b: any) =>
          a.file.localeCompare(b.file)
        );
        return NextResponse.json({ success: true, targets });
      } catch (err) {
        console.error("Error reading schedule.json:", err);
      }
    }

    // Fallback: scan 02_pdf_target directly
    const list: any[] = [];
    if (fs.existsSync(PATHS.pdfTarget)) {
      const files = fs.readdirSync(PATHS.pdfTarget).filter((f) => f.toLowerCase().endsWith(".pdf"));
      files.sort().forEach((file) => {
        list.push({
          file,
          category: "",
          btp: "",
          date: "",
          tim: 1,
          identifiers: [],
        });
      });
    }
    return NextResponse.json({ success: true, targets: list });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
