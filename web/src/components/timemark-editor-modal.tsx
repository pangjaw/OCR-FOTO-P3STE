"use client";

import React, { useState } from "react";
import { X, Save, FileCheck, Sliders, Clock, AlertCircle, CheckCircle2 } from "lucide-react";

interface TimemarkEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  rawRelPath: string;
  rawUrl: string;
  editedUrl: string | null;
  timeUrl?: string | null;
  coordUrl?: string | null;
  mode?: "standard" | "time" | "coord";
  currentDateText: string;
  defaultY?: number;
  defaultX?: number;
  onSaved?: () => void;
}

export const TimemarkEditorModal: React.FC<TimemarkEditorModalProps> = ({
  isOpen,
  onClose,
  rawRelPath,
  rawUrl,
  editedUrl,
  timeUrl,
  coordUrl,
  mode = "standard",
  currentDateText,
  defaultY = 220,
  defaultX = 14,
  onSaved,
}) => {
  const [yPos, setYPos] = useState<number>(defaultY);
  const [xPos, setXPos] = useState<number>(defaultX);
  const [dateText, setDateText] = useState<string>(currentDateText);
  const [coordText, setCoordText] = useState<string>("");
  const [applyToFolder, setApplyToFolder] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [remerging, setRemerging] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  if (!isOpen) return null;

  const handleSave = async (andRemerge = false) => {
    setLoading(true);
    setMessage(null);

    try {
      // 1. Execute manual edit
      const res = await fetch("/api/photos/manual-edit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rawRelPath,
          mode,
          dateText: mode === "standard" ? dateText : undefined,
          timeText: mode === "time" ? dateText : undefined,
          coordText: mode === "coord" ? coordText : undefined,
          yPos,
          xPos,
          applyToFolder,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Gagal menyimpan edit timemark");
      }

      if (andRemerge) {
        setRemerging(true);
        // 2. Execute single remerge
        const mergeRes = await fetch("/api/pdf/remerge-single", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            rawRelPath,
          }),
        });
        const mergeData = await mergeRes.json();
        if (!mergeRes.ok) {
          throw new Error(mergeData.error || "Gagal melakukan re-merge PDF");
        }
        setMessage({
          type: "success",
          text: `Timemark berhasil disimpan dan PDF ${mergeData.pdfName} telah di-remerge!`,
        });
      } else {
        setMessage({
          type: "success",
          text: "Timemark berhasil diperbarui!",
        });
      }

      if (onSaved) onSaved();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
      setRemerging(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div>
            <h3 className="text-base font-semibold text-slate-200 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-emerald-400" />
              Editor Timemark Manual
            </h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">{rawRelPath}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {message && (
            <div
              className={`p-3.5 rounded-xl border text-xs flex items-center gap-2.5 ${
                message.type === "success"
                  ? "bg-emerald-950/30 border-emerald-800/60 text-emerald-300"
                  : "bg-rose-950/30 border-rose-800/60 text-rose-300"
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

          {/* Photo Comparison Dual View */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-slate-400">Foto Asli (03_photos_export)</span>
              <div className="relative aspect-square rounded-xl border border-slate-800 bg-slate-950 overflow-hidden flex items-center justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={rawUrl} alt="Foto Asli" className="object-contain w-full h-full" />
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-slate-400">Hasil Edit ({mode === "coord" ? "04_koordinat" : mode === "time" ? "04_Time" : "04_photos_edited"})</span>
              <div className="relative aspect-square rounded-xl border border-slate-800 bg-slate-950 overflow-hidden flex items-center justify-center">
                {(mode === "coord" ? coordUrl : mode === "time" ? timeUrl : editedUrl) ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={(mode === "coord" ? coordUrl : mode === "time" ? timeUrl : editedUrl) || ""} alt="Hasil Edit" className="object-contain w-full h-full" />
                ) : (
                  <div className="text-xs text-slate-600 italic">Belum ada foto hasil edit</div>
                )}
              </div>
            </div>
          </div>

          {/* Coordinate & Date Controls */}
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Date Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  {mode === "coord" ? "🧭 Teks Koordinat GPS" : mode === "time" ? "⏱️ Teks Jam" : "📅 Teks Tanggal & Waktu"}
                </label>
                <input
                  type="text"
                  value={mode === "coord" ? coordText : dateText}
                  onChange={(e) => mode === "coord" ? setCoordText(e.target.value) : setDateText(e.target.value)}
                  placeholder={mode === "coord" ? "Contoh: -6.589733, 106.791303" : mode === "time" ? "Contoh: 07:00" : "Contoh: Kamis, Jan 09 2025 07:00"}
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700/80 text-slate-100 text-xs font-mono focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* Y Position Slider */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <label className="font-medium text-slate-300 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-amber-400" />
                    Posisi Vertikal (Y-Offset)
                  </label>
                  <span className="font-mono text-emerald-400 font-semibold">{yPos} px</span>
                </div>
                <input
                  type="range"
                  min="100"
                  max="280"
                  step="1"
                  value={yPos}
                  onChange={(e) => setYPos(parseInt(e.target.value, 10))}
                  className="w-full accent-emerald-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
                />
              </div>
            </div>

            {/* Folder Checkbox */}
            <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2.5">
              <input
                type="checkbox"
                id="applyFolder"
                checked={applyToFolder}
                onChange={(e) => setApplyToFolder(e.target.checked)}
                className="w-4 h-4 rounded border-slate-700 bg-slate-800 accent-emerald-500"
              />
              <label htmlFor="applyFolder" className="text-xs text-slate-300 cursor-pointer select-none">
                Terapkan posisi & tanggal ini ke seluruh foto (0%, 50%, 100%) dalam aset ini
              </label>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-950/60">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
          >
            Tutup
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleSave(false)}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              {loading && !remerging ? "Menyimpan..." : "Simpan Timemark"}
            </button>

            <button
              onClick={() => handleSave(true)}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-900/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <FileCheck className="w-3.5 h-3.5" />
              {remerging ? "Re-Merging PDF..." : "Simpan & Re-Merge PDF"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
