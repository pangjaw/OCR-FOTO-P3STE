"use client";

import React, { useState } from "react";
import { FileSpreadsheet, Download, RefreshCw, FileText, Table } from "lucide-react";

export const ExcelExportPanel: React.FC = () => {
  const [tabloLoading, setTabloLoading] = useState(false);
  const [tabloFile, setTabloFile] = useState<{ name: string; url: string } | null>(null);

  const [dinasanLoading, setDinasanLoading] = useState(false);
  const [dinasanWithPersonnel, setDinasanWithPersonnel] = useState(true);
  const [dinasanFile, setDinasanFile] = useState<{ name: string; url: string } | null>(null);

  const [assetLoading, setAssetLoading] = useState(false);
  const [assetFile, setAssetFile] = useState<{ name: string; url: string } | null>(null);

  // Generate Tablo
  const handleExportTablo = async () => {
    setTabloLoading(true);
    setTabloFile(null);
    try {
      const res = await fetch("/api/export/tablo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "pipeline" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Gagal membuat Tablo Excel");
      setTabloFile({ name: data.fileName, url: data.downloadUrl });
    } catch (err: any) {
      alert(`Error Tablo: ${err.message}`);
    } finally {
      setTabloLoading(false);
    }
  };

  // Generate Dinasan
  const handleExportDinasan = async () => {
    setDinasanLoading(true);
    setDinasanFile(null);
    try {
      const res = await fetch("/api/export/dinasan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ withPersonnel: dinasanWithPersonnel, mode: "pipeline" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Gagal membuat Dinasan Excel");
      setDinasanFile({ name: data.fileName, url: data.downloadUrl });
    } catch (err: any) {
      alert(`Error Dinasan: ${err.message}`);
    } finally {
      setDinasanLoading(false);
    }
  };

  // Generate Data Aset
  const handleExportAsset = async () => {
    setAssetLoading(true);
    setAssetFile(null);
    try {
      const res = await fetch("/api/export/asset-data", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "pipeline" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Gagal membuat Data Aset Excel");
      setAssetFile({ name: data.fileName, url: data.downloadUrl });
    } catch (err: any) {
      alert(`Error Data Aset: ${err.message}`);
    } finally {
      setAssetLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/80 shadow-lg">
        <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
          <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
          Ekspor Berkas Excel Resmi KAI (.xlsx)
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Generator formulir resmi siap cetak berbasis data jadwal (schedule.json) dan profil personil aktif.
        </p>
      </div>

      {/* 3 Export Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Tablo Card */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col justify-between space-y-4 shadow-sm">
          <div className="space-y-2">
            <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-emerald-400 inline-block">
              <Table className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-200">
              Tablo Checklist Perawatan Berkala
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Form No. STE-RECORD-13.4.01. Matriks tanggal 1 s.d. akhir bulan, 46 legenda peralatan sintelis, dan pengesahan KUPT & KAUR.
            </p>
          </div>

          <div className="pt-4 border-t border-slate-800/80 space-y-3">
            <button
              onClick={handleExportTablo}
              disabled={tabloLoading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold text-xs shadow-md transition-colors"
            >
              {tabloLoading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Membuat Tablo...
                </>
              ) : (
                <>
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  Generate Tablo (.xlsx)
                </>
              )}
            </button>

            {tabloFile && (
              <a
                href={tabloFile.url}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-emerald-800/60 text-xs font-mono font-medium transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Unduh: {tabloFile.name}
              </a>
            )}
          </div>
        </div>

        {/* Dinasan Card */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col justify-between space-y-4 shadow-sm">
          <div className="space-y-2">
            <div className="p-2.5 rounded-lg bg-sky-950/40 border border-sky-800/40 text-sky-400 inline-block">
              <FileText className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-200">
              Daftar Dinasan Pegawai
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Format jadwal dinasan A4 Landscape resmi KAI: No, Perawatan, Program, Realisasi, dan nama personil yang ditugaskan per tanggal.
            </p>

            <div className="pt-2 flex items-center gap-2">
              <input
                type="checkbox"
                id="withPers"
                checked={dinasanWithPersonnel}
                onChange={(e) => setDinasanWithPersonnel(e.target.checked)}
                className="w-4 h-4 rounded border-slate-700 bg-slate-800 accent-sky-500"
              />
              <label htmlFor="withPers" className="text-xs text-slate-300 select-none cursor-pointer">
                Sertakan kolom Nama Personil
              </label>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800/80 space-y-3">
            <button
              onClick={handleExportDinasan}
              disabled={dinasanLoading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-semibold text-xs shadow-md transition-colors"
            >
              {dinasanLoading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Membuat Dinasan...
                </>
              ) : (
                <>
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  Generate Dinasan (.xlsx)
                </>
              )}
            </button>

            {dinasanFile && (
              <a
                href={dinasanFile.url}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-400 border border-sky-800/60 text-xs font-mono font-medium transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Unduh: {dinasanFile.name}
              </a>
            )}
          </div>
        </div>

        {/* Data Aset Card */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col justify-between space-y-4 shadow-sm">
          <div className="space-y-2">
            <div className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-800/40 text-amber-400 inline-block">
              <Table className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-200">
              Data Aset & Funcloc
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Ekspor satu baris per aset ke format spreadsheet tabular: kolom TANGGAL, FILE NAME, KODE ASET (funcloc), dan ASET.
            </p>
          </div>

          <div className="pt-4 border-t border-slate-800/80 space-y-3">
            <button
              onClick={handleExportAsset}
              disabled={assetLoading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white font-semibold text-xs shadow-md transition-colors"
            >
              {assetLoading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Membuat Data Aset...
                </>
              ) : (
                <>
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  Generate Data Aset (.xlsx)
                </>
              )}
            </button>

            {assetFile && (
              <a
                href={assetFile.url}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-400 border border-amber-800/60 text-xs font-mono font-medium transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Unduh: {assetFile.name}
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
