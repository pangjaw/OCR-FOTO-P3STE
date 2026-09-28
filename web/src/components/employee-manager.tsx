"use client";

import React, { useEffect, useState } from "react";
import { Users, Plus, Trash2, Save, CheckCircle2, AlertCircle, Edit2, RefreshCw } from "lucide-react";

interface PersonItem {
  nama: string;
  nipp: string;
  no_sc: string;
}

interface PresetItem {
  id: string;
  name: string;
  created_at: string;
  data: {
    resor: PersonItem;
    kaur: PersonItem[];
    pnc: PersonItem[];
  };
}

export const EmployeeManager: React.FC = () => {
  const [presets, setPresets] = useState<PresetItem[]>([]);
  const [activePresetId, setActivePresetId] = useState<string>("");
  const [currentData, setCurrentData] = useState<{
    resor: PersonItem;
    kaur: PersonItem[];
    pnc: PersonItem[];
  }>({
    resor: { nama: "", nipp: "", no_sc: "" },
    kaur: [],
    pnc: [],
  });

  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchPresets = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/employees/presets");
      const data = await res.json();
      if (data.success) {
        setPresets(data.presets || []);
        setActivePresetId(data.active_preset_id || "");
        const active = data.presets.find((p: PresetItem) => p.id === data.active_preset_id);
        if (active) {
          setCurrentData(JSON.parse(JSON.stringify(active.data)));
        }
      }
    } catch (err: any) {
      setMessage({ type: "error", text: `Gagal memuat preset: ${err.message}` });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPresets();
  }, []);

  const handleSelectPreset = async (id: string) => {
    try {
      const res = await fetch("/api/employees/presets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "select", presetId: id }),
      });
      const data = await res.json();
      if (data.success) {
        setActivePresetId(id);
        const active = presets.find((p) => p.id === id);
        if (active) setCurrentData(JSON.parse(JSON.stringify(active.data)));
        setMessage({ type: "success", text: data.message });
      }
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    }
  };

  const handleSave = async (isNew = false) => {
    setSaving(true);
    setMessage(null);
    try {
      let presetName = "";
      if (isNew) {
        const inputName = prompt("Masukkan nama list pegawai baru:");
        if (!inputName) {
          setSaving(false);
          return;
        }
        presetName = inputName;
      }

      const res = await fetch("/api/employees/presets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "save",
          presetId: activePresetId,
          name: presetName,
          data: currentData,
          isNew,
        }),
      });

      const data = await res.json();
      if (data.success) {
        setMessage({ type: "success", text: data.message });
        fetchPresets();
      } else {
        setMessage({ type: "error", text: data.error || "Gagal menyimpan" });
      }
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const handleRename = async () => {
    const currentPreset = presets.find((p) => p.id === activePresetId);
    if (!currentPreset) return;
    const newName = prompt("Nama baru untuk list ini:", currentPreset.name);
    if (!newName || newName.trim() === currentPreset.name) return;

    try {
      const res = await fetch("/api/employees/presets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "rename", presetId: activePresetId, newName }),
      });
      const data = await res.json();
      if (data.success) {
        setMessage({ type: "success", text: "Nama list berhasil diubah" });
        fetchPresets();
      }
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    }
  };

  const handleDelete = async () => {
    if (presets.length <= 1) {
      alert("Minimal harus ada 1 list pegawai tersisa.");
      return;
    }
    if (!confirm("Apakah Anda yakin ingin menghapus list pegawai aktif ini?")) return;

    try {
      const res = await fetch("/api/employees/presets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "delete", presetId: activePresetId }),
      });
      const data = await res.json();
      if (data.success) {
        setMessage({ type: "success", text: data.message });
        fetchPresets();
      }
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    }
  };

  const addPerson = (type: "kaur" | "pnc") => {
    setCurrentData((prev) => ({
      ...prev,
      [type]: [...prev[type], { nama: "", nipp: "", no_sc: "" }],
    }));
  };

  const removePerson = (type: "kaur" | "pnc", index: number) => {
    setCurrentData((prev) => ({
      ...prev,
      [type]: prev[type].filter((_, i) => i !== index),
    }));
  };

  const updatePerson = (type: "kaur" | "pnc", index: number, field: keyof PersonItem, value: string) => {
    setCurrentData((prev) => {
      const updated = [...prev[type]];
      updated[index] = { ...updated[index], [field]: value };
      return { ...prev, [type]: updated };
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 gap-2">
        <RefreshCw className="w-5 h-5 animate-spin text-emerald-400" />
        <span>Memuat data personil...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header & Presets Bar */}
      <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/80 shadow-lg space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
              <Users className="w-5 h-5 text-emerald-400" />
              Kelola Daftar Pegawai & Personil Dinasan
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Profil personil aktif otomatis digunakan pada koreksi berkas PDF (Step 3.5), roster dinas, dan ekspor Tablo.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleSave(false)}
              disabled={saving}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow-md transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              {saving ? "Menyimpan..." : "Simpan Perubahan"}
            </button>

            <button
              onClick={() => handleSave(true)}
              disabled={saving}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              Simpan Sebagai List Baru
            </button>
          </div>
        </div>

        {/* Preset Selector */}
        <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-slate-800">
          <label className="text-xs font-medium text-slate-300">Pilih Preset Aktif:</label>
          <select
            value={activePresetId}
            onChange={(e) => handleSelectPreset(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-xs font-medium focus:outline-none focus:border-emerald-500"
          >
            {presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>

          <button
            onClick={handleRename}
            title="Ganti nama list aktif"
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleDelete}
            title="Hapus list aktif"
            className="p-1.5 rounded bg-slate-800 hover:bg-rose-500/20 text-rose-400 border border-slate-700 text-xs"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {message && (
          <div
            className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
              message.type === "success"
                ? "bg-emerald-950/30 border border-emerald-800/60 text-emerald-300"
                : "bg-rose-950/30 border border-rose-800/60 text-rose-300"
            }`}
          >
            {message.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{message.text}</span>
          </div>
        )}
      </div>

      {/* Profile Form Cards */}
      <div className="space-y-6">
        {/* KUPT Resor */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm space-y-3">
          <h3 className="text-xs font-bold text-sky-400 uppercase tracking-wider">
            Kepala UPT / Resor (Pengesahan)
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-[11px] text-slate-400">Nama Lengkap</label>
              <input
                type="text"
                value={currentData.resor.nama}
                onChange={(e) =>
                  setCurrentData((prev) => ({
                    ...prev,
                    resor: { ...prev.resor, nama: e.target.value },
                  }))
                }
                className="w-full mt-1 px-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="text-[11px] text-slate-400">NIPP</label>
              <input
                type="text"
                value={currentData.resor.nipp}
                onChange={(e) =>
                  setCurrentData((prev) => ({
                    ...prev,
                    resor: { ...prev.resor, nipp: e.target.value },
                  }))
                }
                className="w-full mt-1 px-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="text-[11px] text-slate-400">Nomor SC</label>
              <input
                type="text"
                value={currentData.resor.no_sc}
                onChange={(e) =>
                  setCurrentData((prev) => ({
                    ...prev,
                    resor: { ...prev.resor, no_sc: e.target.value },
                  }))
                }
                className="w-full mt-1 px-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
              />
            </div>
          </div>
        </div>

        {/* KAUR Table */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
              Kepala Urusan (KAUR) — Minimal 1 Orang
            </h3>
            <button
              onClick={() => addPerson("kaur")}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-emerald-300 text-xs font-medium border border-slate-700"
            >
              <Plus className="w-3.5 h-3.5" />
              Tambah KAUR
            </button>
          </div>

          <div className="space-y-2">
            {currentData.kaur.map((item, idx) => (
              <div key={idx} className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center">
                <div className="sm:col-span-5">
                  <input
                    type="text"
                    placeholder="Nama Lengkap KAUR"
                    value={item.nama}
                    onChange={(e) => updatePerson("kaur", idx, "nama", e.target.value)}
                    className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="sm:col-span-3">
                  <input
                    type="text"
                    placeholder="NIPP"
                    value={item.nipp}
                    onChange={(e) => updatePerson("kaur", idx, "nipp", e.target.value)}
                    className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="sm:col-span-3">
                  <input
                    type="text"
                    placeholder="Nomor SC (PRP...)"
                    value={item.no_sc}
                    onChange={(e) => updatePerson("kaur", idx, "no_sc", e.target.value)}
                    className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 font-mono focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="sm:col-span-1 flex justify-end">
                  <button
                    onClick={() => removePerson("kaur", idx)}
                    className="p-1.5 rounded hover:bg-rose-500/20 text-rose-400"
                    title="Hapus baris"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* PNC Table */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wider">
              Pelaksana (PNC) — Minimal 2 Orang
            </h3>
            <button
              onClick={() => addPerson("pnc")}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-amber-300 text-xs font-medium border border-slate-700"
            >
              <Plus className="w-3.5 h-3.5" />
              Tambah PNC
            </button>
          </div>

          <div className="space-y-2">
            {currentData.pnc.map((item, idx) => (
              <div key={idx} className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center">
                <div className="sm:col-span-5">
                  <input
                    type="text"
                    placeholder="Nama Lengkap PNC"
                    value={item.nama}
                    onChange={(e) => updatePerson("pnc", idx, "nama", e.target.value)}
                    className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="sm:col-span-3">
                  <input
                    type="text"
                    placeholder="NIPP"
                    value={item.nipp}
                    onChange={(e) => updatePerson("pnc", idx, "nipp", e.target.value)}
                    className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="sm:col-span-3">
                  <input
                    type="text"
                    placeholder="Nomor SC (PRP...)"
                    value={item.no_sc}
                    onChange={(e) => updatePerson("pnc", idx, "no_sc", e.target.value)}
                    className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 font-mono focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="sm:col-span-1 flex justify-end">
                  <button
                    onClick={() => removePerson("pnc", idx)}
                    className="p-1.5 rounded hover:bg-rose-500/20 text-rose-400"
                    title="Hapus baris"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
