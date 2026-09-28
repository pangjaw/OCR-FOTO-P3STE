import path from "path";
import fs from "fs";

function getRootDir(): string {
  const cwd = process.cwd();
  if (path.basename(cwd).toLowerCase() === "web") {
    return path.resolve(cwd, "..");
  }
  if (fs.existsSync(path.join(cwd, "01_pdf_source")) || fs.existsSync(path.join(cwd, "scripts"))) {
    return cwd;
  }
  return path.resolve(cwd, "..");
}

export const APP_DIR = getRootDir();

export const PATHS = {
  root: APP_DIR,
  pdfSource: path.join(APP_DIR, "01_pdf_source"),
  pdfTarget: path.join(APP_DIR, "02_pdf_target"),
  photosExport: path.join(APP_DIR, "03_photos_export"),
  photosCroppedTemp: path.join(APP_DIR, "03_photos_cropped_temp"),
  photosEdited: path.join(APP_DIR, "04_photos_edited"),
  photosTime: path.join(APP_DIR, "04_Time"),
  photosCoord: path.join(APP_DIR, "04_koordinat"),
  pdfMerged: path.join(APP_DIR, "05_pdf_merged"),
  pdfMergedTime: path.join(APP_DIR, "05_pdf_merged_Time"),
  pdfMergedCoord: path.join(APP_DIR, "05_koordinat"),
  scripts: path.join(APP_DIR, "scripts"),
  logs: path.join(APP_DIR, "logs"),
  config: path.join(APP_DIR, "config"),
  scheduleJson: path.join(APP_DIR, "schedule.json"),
};
