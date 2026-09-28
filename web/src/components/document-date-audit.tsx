"use client";

import React, { useState } from "react";
import {
  CalendarCheck2,
  Play,
  Wrench,
  CheckCircle2,
} from "lucide-react";

interface DateAuditItem {
  file: string;
  pdf_path?: string;
  filename_date?: string;
  pdf_date?: string;
  photo_dates?: string[];
  status?: string;
}

export const DocumentDateAudit: React.FC = () => {
  const [mode, setMode] = useState<"pipeline" | "custom">("pipeline");
  const [customPath, setCustomPath] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [correcting, setCorrecting] = useState<boolean>(false);
  const [result, setResult] = useState<{
    total?: number;
    sesuai?: number;
    berbeda?: number;
    tidak_terbaca?: number;
    gagal?: number;
    records?: DateAuditItem[];
  } | null>(null);

  const runAudit = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/pdf-dates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "audit", mode, folderPath: customPath }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Gagal audit tanggal PDF");
      setResult(data);
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCorrectDates = async () => {
    if (!confirm("Apakah Anda yakin ingin mengoreksi seluruh berkas PDF yang berstatus BERBEDA?")) {
      return;
    }
    setCorrecting(true);
    try {
      const res = await fetch("/api/pdf-dates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "correct", mode, folderPath: customPath }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Gagal mengoreksi tanggal PDF");
      alert("Koreksi tanggal PDF berhasil dilakukan!");
      runAudit();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setCorrecting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/80 shadow-lg space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
              <CalendarCheck2 className="w-5 h-5 text-cyan-400" />
              Audit & Koreksi Tanggal Lembar Dokumen PDF
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Menyelaraskan tanggal pada text layer lembar pertama dan header FOTO DOKUMENTASI dengan tanggal nama berkas.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={runAudit}
              disabled={loading || correcting}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs shadow-md transition-colors"
            >
              <Play className="w-4 h-4 fill-white" />
              {loading ? "Memindai..." : "Jalankan Audit Tanggal"}
            </button>

            {result && (result.berbeda || 0) > 0 && (
              <button
                onClick={handleCorrectDates}
                disabled={correcting}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow-md transition-colors"
              >
                <Wrench className="w-3.5 h-3.5" />
                {correcting ? "Mengoreksi..." : "Koreksi Otomatis (BERBEDA)"}
              </button>
            )}
          </div>
        </div>

        {/* Mode Selector */}
        <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-slate-800 text-xs">
          <label className="font-medium text-slate-300">Sumber Dokumen:</label>
          <div className="flex rounded-lg border border-slate-800 bg-slate-950 p-0.5">
            <button
              onClick={() => setMode("pipeline")}
              className={`px-3 py-1 rounded-md transition-colors ${
                mode === "pipeline"
                  ? "bg-cyan-600 text-white font-medium"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Pipeline (02_pdf_target)
            </button>
            <button
              onClick={() => setMode("custom")}
              className={`px-3 py-1 rounded-md transition-colors ${
                mode === "custom"
                  ? "bg-cyan-600 text-white font-medium"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Folder Eksternal
            </button>
          </div>

          {mode === "custom" && (
            <div className="flex-1 min-w-[280px]">
              <input
                type="text"
                placeholder="Path folder PDF..."
                value={customPath}
                onChange={(e) => setCustomPath(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>
          )}
        </div>
      </div>

      {/* Metric Cards */}
      {result && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60">
            <div className="text-[11px] font-medium text-slate-400">Total Berkas Dipindai</div>
            <div className="text-2xl font-bold text-slate-100 mt-1">{result.total || 0}</div>
          </div>

          <div className="p-3.5 rounded-xl border border-emerald-800/40 bg-emerald-950/20">
            <div className="text-[11px] font-medium text-emerald-300">Sesuai Tanggal Filename</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">{result.sesuai || 0}</div>
          </div>

          <div className="p-3.5 rounded-xl border border-rose-800/40 bg-rose-950/20">
            <div className="text-[11px] font-medium text-rose-300">Berbeda dengan Filename</div>
            <div className="text-2xl font-bold text-rose-400 mt-1">{result.berbeda || 0}</div>
          </div>

          <div className="p-3.5 rounded-xl border border-amber-800/40 bg-amber-950/20">
            <div className="text-[11px] font-medium text-amber-300">Tanggal Tidak Terbaca</div>
            <div className="text-2xl font-bold text-amber-400 mt-1">{result.tidak_terbaca || 0}</div>
          </div>
        </div>
      )}

      {/* Findings Table */}
      {result?.records && result.records.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-slate-800 text-xs font-semibold text-slate-200">
            Hasil Audit Tanggal PDF ({result.records.length} berkas)
          </div>

          <div className="overflow-x-auto max-h-[500px]">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-slate-950 border-b border-slate-800 text-slate-400 text-[11px]">
                <tr>
                  <th className="px-4 py-2.5">Nama Berkas PDF</th>
                  <th className="px-3 py-2.5">Tgl Filename</th>
                  <th className="px-3 py-2.5">Tgl Hal 1</th>
                  <th className="px-3 py-2.5">Tgl Header Foto</th>
                  <th className="px-3 py-2.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {result.records.map((rec, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-2 text-slate-200 font-sans font-medium">
                      {rec.file}
                    </td>
                    <td className="px-3 py-2 text-cyan-400 whitespace-nowrap">
                      {rec.filename_date || "-"}
                    </td>
                    <td className="px-3 py-2 text-slate-300 whitespace-nowrap">
                      {rec.pdf_date || "-"}
                    </td>
                    <td className="px-3 py-2 text-slate-400 whitespace-nowrap">
                      {rec.photo_dates ? rec.photo_dates.join(", ") : "-"}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {rec.status === "SESUAI" ? (
                        <span className="text-emerald-400 font-semibold flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          SESUAI
                        </span>
                      ) : rec.status === "BERBEDA" ? (
                        <span className="text-rose-400 font-semibold bg-rose-950/40 px-2 py-0.5 rounded">
                          BERBEDA
                        </span>
                      ) : (
                        <span className="text-amber-400">{rec.status || "-"}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
