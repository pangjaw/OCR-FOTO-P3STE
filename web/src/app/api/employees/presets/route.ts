import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { PATHS } from "@/lib/paths";

function getPresetFilePath() {
  return path.join(PATHS.config, "employee_presets.json");
}

function getDaftarPegawaiPath() {
  return path.join(PATHS.config, "daftar_pegawai.json");
}

function loadPresets() {
  const fpath = getPresetFilePath();
  if (fs.existsSync(fpath)) {
    try {
      return JSON.parse(fs.readFileSync(fpath, "utf-8"));
    } catch {}
  }
  return { active_preset_id: "preset_default", presets: [] };
}

function savePresets(obj: any) {
  const fpath = getPresetFilePath();
  fs.mkdirSync(path.dirname(fpath), { recursive: true });
  fs.writeFileSync(fpath, JSON.stringify(obj, null, 2), "utf-8");
}

function syncActive(activeData: any) {
  const dpath = getDaftarPegawaiPath();
  fs.mkdirSync(path.dirname(dpath), { recursive: true });
  fs.writeFileSync(dpath, JSON.stringify(activeData, null, 2), "utf-8");
}

export async function GET() {
  try {
    const data = loadPresets();
    return NextResponse.json({
      success: true,
      active_preset_id: data.active_preset_id,
      presets: data.presets || [],
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { action } = body;
    const presetsObj = loadPresets();

    if (action === "select") {
      const { presetId } = body;
      const target = presetsObj.presets.find((p: any) => p.id === presetId);
      if (!target) {
        return NextResponse.json({ error: "Preset tidak ditemukan" }, { status: 404 });
      }
      presetsObj.active_preset_id = presetId;
      savePresets(presetsObj);
      syncActive(target.data);
      return NextResponse.json({
        success: true,
        message: `Preset "${target.name}" diaktifkan`,
        active_preset_id: presetId,
        presets: presetsObj.presets,
      });
    }

    if (action === "save") {
      const { presetId, name, data, isNew } = body;
      if (!data || !Array.isArray(data.kaur) || !Array.isArray(data.pnc)) {
        return NextResponse.json(
          { error: "Format data personil tidak valid" },
          { status: 400 }
        );
      }

      const cleanData = {
        resor: data.resor || {
          nama: "FURQON SUSILO WARDOYO",
          nipp: "64465",
          no_sc: "PRP.090190.126696",
        },
        kaur: data.kaur,
        pnc: data.pnc,
      };

      if (isNew) {
        const newId = `preset_${Date.now()}`;
        const newName = (name && name.trim()) || `List Pegawai ${presetsObj.presets.length + 1}`;
        const newPreset = {
          id: newId,
          name: newName,
          created_at: new Date().toISOString(),
          data: cleanData,
        };
        presetsObj.presets.push(newPreset);
        presetsObj.active_preset_id = newId;
        savePresets(presetsObj);
        syncActive(cleanData);
        return NextResponse.json({
          success: true,
          message: `List baru "${newName}" berhasil disimpan & diaktifkan`,
          active_preset_id: newId,
          presets: presetsObj.presets,
        });
      } else {
        const targetId = presetId || presetsObj.active_preset_id;
        const target = presetsObj.presets.find((p: any) => p.id === targetId);
        if (!target) {
          return NextResponse.json({ error: "Preset tidak ditemukan" }, { status: 404 });
        }
        target.data = cleanData;
        if (name && name.trim()) target.name = name.trim();
        savePresets(presetsObj);
        if (presetsObj.active_preset_id === targetId) {
          syncActive(cleanData);
        }
        return NextResponse.json({
          success: true,
          message: `Preset "${target.name}" berhasil diperbarui`,
          active_preset_id: presetsObj.active_preset_id,
          presets: presetsObj.presets,
        });
      }
    }

    if (action === "rename") {
      const { presetId, newName } = body;
      const target = presetsObj.presets.find((p: any) => p.id === presetId);
      if (!target) {
        return NextResponse.json({ error: "Preset tidak ditemukan" }, { status: 404 });
      }
      target.name = (newName || "").trim() || target.name;
      savePresets(presetsObj);
      return NextResponse.json({
        success: true,
        message: "Nama preset berhasil diubah",
        presets: presetsObj.presets,
      });
    }

    if (action === "delete") {
      const { presetId } = body;
      if (presetsObj.presets.length <= 1) {
        return NextResponse.json(
          { error: "Minimal harus ada 1 preset list pegawai tersisa." },
          { status: 400 }
        );
      }
      const idx = presetsObj.presets.findIndex((p: any) => p.id === presetId);
      if (idx === -1) {
        return NextResponse.json({ error: "Preset tidak ditemukan" }, { status: 404 });
      }
      const removed = presetsObj.presets.splice(idx, 1)[0];
      if (presetsObj.active_preset_id === presetId) {
        presetsObj.active_preset_id = presetsObj.presets[0].id;
        syncActive(presetsObj.presets[0].data);
      }
      savePresets(presetsObj);
      return NextResponse.json({
        success: true,
        message: `Preset "${removed.name}" dihapus`,
        active_preset_id: presetsObj.active_preset_id,
        presets: presetsObj.presets,
      });
    }

    return NextResponse.json({ error: "Aksi tidak dikenal" }, { status: 400 });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
