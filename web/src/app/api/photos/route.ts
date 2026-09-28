import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { PATHS } from "@/lib/paths";

function expandIdentifierVariants(ident: string): string[] {
  const set = new Set<string>();
  if (!ident) return [];
  const norm = ident.toUpperCase().trim();
  set.add(norm);
  const baseNoDate = norm.replace(/_\d{2}-\d{2}$/, "").trim();
  set.add(baseNoDate);

  const m = baseNoDate.match(/^(JPL\s+(?:BNR|\d+[A-Z]?))\s+([A-Z]{2,3}(?:-[A-Z]{2,3})+)$/i);
  if (m) {
    const prefix = m[1].toUpperCase();
    const stations = m[2].toUpperCase().split("-");
    stations.forEach((st) => {
      set.add(`${prefix} ${st}`);
    });
    const sortedStations = stations.slice().sort().join("-");
    const reversedStations = stations.slice().reverse().join("-");
    set.add(`${prefix} ${sortedStations}`);
    set.add(`${prefix} ${reversedStations}`);
  }
  return Array.from(set);
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const btpFilter = searchParams.get("btp") || "";
    const categoryFilter = searchParams.get("category") || "";
    const detectorFilter = searchParams.get("detector") || ""; // "google_vision" | "guide" | ""
    const targetFile = searchParams.get("targetFile") || "";
    const search = (searchParams.get("search") || "").toLowerCase();
    const page = parseInt(searchParams.get("page") || "1", 10);
    const limit = parseInt(searchParams.get("limit") || "24", 10);

    let targetIdentifiers: Set<string> | null = null;
    let targetCategory: string | null = null;
    if (targetFile) {
      const schedPath = PATHS.scheduleJson;
      if (fs.existsSync(schedPath)) {
        try {
          const sched = JSON.parse(fs.readFileSync(schedPath, "utf-8"));
          const matches = (sched.schedules || []).filter((s: any) => s.file === targetFile);
          if (matches.length > 0) {
            targetIdentifiers = new Set();
            targetCategory = matches[0].category || null;
            matches.forEach((m: any) => {
              if (m.identifier) {
                expandIdentifierVariants(m.identifier).forEach((v) => targetIdentifiers!.add(v.toLowerCase()));
              }
              if (m.base_identifier) {
                expandIdentifierVariants(m.base_identifier).forEach((v) => targetIdentifiers!.add(v.toLowerCase()));
              }
            });
          }
        } catch (e) {}
      }
    }

    const exportRoot = PATHS.photosExport;
    if (!fs.existsSync(exportRoot)) {
      return NextResponse.json({ total: 0, items: [], categories: [], btps: [] });
    }

    const btpDirs = fs
      .readdirSync(exportRoot, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name);

    const allBtps = new Set<string>();
    const allCategories = new Set<string>();
    const assetFolders: Array<{
      btp: string;
      category: string;
      identifier: string;
      relDir: string;
      dateText: string;
      coordText: string;
      photos: Array<{
        name: string;
        rawUrl: string;
        editedUrl: string | null;
        timeUrl: string | null;
        coordUrl: string | null;
        hasEdited: boolean;
        hasTime: boolean;
        hasCoord: boolean;
        isCollage: boolean;
        meta: any;
        coordMeta: any;
      }>;
    }> = [];

    let coordMapping: any = null;
    const coordMappingFile = path.join(PATHS.config, "asset_koordinat_mapping.json");
    if (fs.existsSync(coordMappingFile)) {
      try {
        coordMapping = JSON.parse(fs.readFileSync(coordMappingFile, "utf-8"));
      } catch {}
    }

    for (const btp of btpDirs) {
      allBtps.add(btp);
      const btpPath = path.join(exportRoot, btp);
      const catDirs = fs
        .readdirSync(btpPath, { withFileTypes: true })
        .filter((d) => d.isDirectory())
        .map((d) => d.name);

      for (const cat of catDirs) {
        allCategories.add(cat);
        const catPath = path.join(btpPath, cat);
        const identDirs = fs
          .readdirSync(catPath, { withFileTypes: true })
          .filter((d) => d.isDirectory())
          .map((d) => d.name);

        for (const ident of identDirs) {
          const folderPath = path.join(catPath, ident);
          const relDir = `${btp}/${cat}/${ident}`;

          // Filter early
          if (btpFilter && btp.toLowerCase() !== btpFilter.toLowerCase()) continue;
          if (categoryFilter && cat.toLowerCase() !== categoryFilter.toLowerCase()) continue;
          if (search) {
            const searchTokens = search.split(/\s+/).filter(Boolean);
            const fullSearch = `${relDir} ${ident} ${cat} ${btp}`.toLowerCase();
            if (!searchTokens.every((tok) => fullSearch.includes(tok))) {
              continue;
            }
          }

          const cleanIdent = ident.replace(/_\d{2}-\d{2}$/, "").trim().toUpperCase();

          if (targetIdentifiers && targetCategory) {
            if (cat.toLowerCase() !== targetCategory.toLowerCase()) continue;
            const identVariants = expandIdentifierVariants(ident);
            const hasMatch = identVariants.some((v) => targetIdentifiers!.has(v.toLowerCase()));
            if (!hasMatch) continue;
          }

          // Check files in folder
          const files = fs.readdirSync(folderPath);
          const jpgFiles = files.filter((f) => f.toLowerCase().endsWith(".jpg"));
          if (jpgFiles.length === 0) continue;

          // Read date.txt
          let dateText = "";
          const dateFile = path.join(folderPath, "date.txt");
          if (fs.existsSync(dateFile)) {
            dateText = fs.readFileSync(dateFile, "utf-8").trim();
          }

          // Resolve coordinate text from mapping if available
          let coordText = "";
          if (coordMapping) {
            const cInfo = coordMapping.by_identifier?.[cleanIdent] || coordMapping.by_identifier?.[ident.toUpperCase()];
            if (cInfo && cInfo.coordinate) {
              coordText = cInfo.coordinate;
            }
          }

          // Sort photos 0, 50, 100
          const order = ["0.jpg", "50.jpg", "100.jpg"];
          jpgFiles.sort((a, b) => {
            const ia = order.indexOf(a.toLowerCase());
            const ib = order.indexOf(b.toLowerCase());
            return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
          });

          // Check edited in Tim_1 / Tim_2
          const photos = jpgFiles.map((fname) => {
            const rawRel = `${relDir}/${fname}`;
            const rawUrl = `/api/static/03_photos_export/${encodeURIComponent(btp)}/${encodeURIComponent(cat)}/${encodeURIComponent(ident)}/${encodeURIComponent(fname)}`;

            // Check Tim_1 / Tim_2 in 04_photos_edited
            let editedUrl: string | null = null;
            let meta: any = null;
            for (const tim of ["Tim_1", "Tim_2"]) {
              const cand = path.join(PATHS.photosEdited, tim, btp, cat, ident, fname);
              if (fs.existsSync(cand)) {
                editedUrl = `/api/static/04_photos_edited/${tim}/${encodeURIComponent(btp)}/${encodeURIComponent(cat)}/${encodeURIComponent(ident)}/${encodeURIComponent(fname)}?t=${fs.statSync(cand).mtimeMs}`;
                const metaFile = path.join(PATHS.photosEdited, tim, btp, cat, ident, "meta.json");
                if (fs.existsSync(metaFile)) {
                  try {
                    const mData = JSON.parse(fs.readFileSync(metaFile, "utf-8"));
                    if (mData[fname]) meta = mData[fname];
                  } catch {}
                }
                break;
              }
            }

            // Check in 04_Time
            let timeUrl: string | null = null;
            for (const tim of ["Tim_1", "Tim_2"]) {
              const candTime = path.join(PATHS.photosTime, tim, btp, cat, ident, fname);
              if (fs.existsSync(candTime)) {
                timeUrl = `/api/static/04_Time/${tim}/${encodeURIComponent(btp)}/${encodeURIComponent(cat)}/${encodeURIComponent(ident)}/${encodeURIComponent(fname)}?t=${fs.statSync(candTime).mtimeMs}`;
                break;
              }
            }

            // Check in 04_koordinat
            let coordUrl: string | null = null;
            let coordMeta: any = null;
            for (const tim of ["Tim_1", "Tim_2"]) {
              const candCoord = path.join(PATHS.photosCoord, tim, btp, cat, ident, fname);
              if (fs.existsSync(candCoord)) {
                coordUrl = `/api/static/04_koordinat/${tim}/${encodeURIComponent(btp)}/${encodeURIComponent(cat)}/${encodeURIComponent(ident)}/${encodeURIComponent(fname)}?t=${fs.statSync(candCoord).mtimeMs}`;
                const coordMetaFile = path.join(PATHS.photosCoord, tim, btp, cat, ident, "meta.json");
                if (fs.existsSync(coordMetaFile)) {
                  try {
                    const cData = JSON.parse(fs.readFileSync(coordMetaFile, "utf-8"));
                    if (cData[fname]) {
                      coordMeta = cData[fname];
                      if (!coordText && coordMeta.coordinate) {
                        coordText = coordMeta.coordinate;
                      }
                    }
                  } catch {}
                }
                break;
              }
            }

            // Check cropped temp
            const isCollage = fs.existsSync(path.join(PATHS.photosCroppedTemp, btp, cat, ident, fname));

            if (meta && !meta.detector) {
              if (meta.stage === "stage_google_vision") {
                meta.detector = "google_vision";
              } else if (meta.stage) {
                meta.detector = "guide";
              }
            }

            const stem = path.basename(fname, path.extname(fname));
            const hasBackup = fs.existsSync(path.join(folderPath, `${stem}.original_backup.jpg`));

            return {
              name: fname,
              rawUrl,
              editedUrl,
              timeUrl,
              coordUrl,
              hasEdited: !!editedUrl,
              hasTime: !!timeUrl,
              hasCoord: !!coordUrl,
              isCollage,
              hasBackup,
              meta,
              coordMeta,
            };
          });

          if (detectorFilter === "google_vision") {
            const hasGv = photos.some((p) => p.meta?.detector === "google_vision");
            if (!hasGv) continue;
          } else if (detectorFilter === "guide") {
            const hasGuide = photos.some((p) => p.hasEdited && p.meta?.detector !== "google_vision");
            if (!hasGuide) continue;
          }

          assetFolders.push({
            btp,
            category: cat,
            identifier: ident,
            relDir,
            dateText,
            coordText,
            photos,
          });
        }
      }
    }

    const total = assetFolders.length;
    const startIndex = (page - 1) * limit;
    const paginatedItems = assetFolders.slice(startIndex, startIndex + limit);

    return NextResponse.json({
      success: true,
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit),
      items: paginatedItems,
      btps: Array.from(allBtps).sort(),
      categories: Array.from(allCategories).sort(),
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
