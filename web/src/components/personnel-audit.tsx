"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Play,
  Wrench,
} from "lucide-react";

interface AuditFileItem {
  file: string;
  pdf_path?: string;
  date?: string;
  kaur?: string[];
  pnc?: string[];
  status?: string;
  status_rule?: string;
  status_label?: string;
  is_main_finding?: boolean;
  is_compliant?: boolean;
  needs_sc_correction?: boolean;
  missing_no_sc?: string[];
  no_sc_missing_count?: number;
  missing_sc?: number;
  dilaksanakan_oleh?: string;
}

export const PersonnelAudit: React.FC = () => {
  const [mode, setMode] = useState<"pipeline" | "custom">("pipeline");
  const [customPath, setCustomPath] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [auditResult, setAuditResult] = useState<{
    total?: number;
    main_findings?: number;
    normal_findings?: number;
    compliant?: number;
    files?: AuditFileItem[];
  } | null>(null);

  const [filterStatus, setFilterStatus] = useState<"all" | "main" | "sc" | "compliant">("all");

  const runAudit = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/employees/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, customPath }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Gagal audit personil");

      const files: AuditFileItem[] = (data.files || []).map((f: any) => ({
        ...f,
        is_main_finding: f.is_main_finding ?? (f.severity === "CRITICAL" || f.needs_correction),
        is_compliant: f.is_compliant ?? (f.severity === "OK" && !f.needs_sc_correction),
        needs_sc_correction: f.needs_sc_correction ?? ((f.no_sc_missing_count && f.no_sc_missing_count > 0) || (f.missing_sc && f.missing_sc > 0)),
        no_sc_missing_count: f.no_sc_missing_count ?? (f.missing_no_sc?.length || f.missing_sc || 0),
      }));

      const total = data.total ?? data.total_files ?? files.length;
      const main_findings = data.main_findings ?? data.critical_count ?? files.filter((f) => f.is_main_finding).length;
      const normal_findings = data.normal_findings ?? files.filter((f) => f.needs_sc_correction).length;
      const compliant = data.compliant ?? data.ok_count ?? files.filter((f) => f.is_compliant).length;

      setAuditResult({
        total,
        main_findings,
        normal_findings,
        compliant,
        files,
      });
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleBatchCorrect = async (type: "batch" | "no-sc") => {
    setActionLoading(type);
    try {
      const res = await fetch("/api/employees/correct", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: type,
          mode,
          customPath,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Gagal menjalankan koreksi");
      alert(
        type === "batch"
          ? "Koreksi massal temuan utama berhasil!"
          : "Koreksi nomor SC berhasil!"
      );
      runAudit();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const filteredFiles = auditResult?.files
    ? auditResult.files.filter((f) => {
        if (filterStatus === "main") return f.is_main_finding;
        if (filterStatus === "compliant") return f.is_compliant;
        if (filterStatus === "sc") return f.needs_sc_correction || (f.no_sc_missing_count ?? 0) > 0;
        return true;
      })
    : [];

  return (
    <div className="space-y-6">
      {/* Header & Mode Controls */}
      <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/80 shadow-lg space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-purple-400" />
              Audit & Koreksi Aturan Personil (1 KAUR, 2 PNC)
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Pemeriksaan lembar pertama PDF untuk memastikan terpenuhinya syarat 1 Kepala Urusan (KAUR) dan 2 Pelaksana (PNC).
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={runAudit}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs shadow-lg shadow-purple-950/40 transition-colors"
            >
              <Play className="w-4 h-4 fill-white" />
              {loading ? "Memindai PDF..." : "Jalankan Audit Personil"}
            </button>
          </div>
        </div>

        {/* Source Mode Selector */}
        <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-slate-800 text-xs">
          <label className="font-medium text-slate-300">Sumber Folder PDF:</label>
          <div className="flex rounded-lg border border-slate-800 bg-slate-950 p-0.5">
            <button
              onClick={() => setMode("pipeline")}
              className={`px-3 py-1 rounded-md transition-colors ${
                mode === "pipeline"
                  ? "bg-purple-600 text-white font-medium"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Pipeline (02_pdf_target)
            </button>
            <button
              onClick={() => setMode("custom")}
              className={`px-3 py-1 rounded-md transition-colors ${
                mode === "custom"
                  ? "bg-purple-600 text-white font-medium"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Folder Kustom Lain
            </button>
          </div>

          {mode === "custom" && (
            <div className="flex-1 min-w-[280px]">
              <input
                type="text"
                placeholder="Path folder absolut (misal: C:\Users\...\TargetPDF)..."
                value={customPath}
                onChange={(e) => setCustomPath(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs text-slate-200 font-mono focus:outline-none focus:border-purple-500"
              />
            </div>
          )}
        </div>
      </div>

      {/* Metrics Cards */}
      {auditResult && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div
            onClick={() => setFilterStatus("all")}
            className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
              filterStatus === "all"
                ? "border-purple-500 bg-purple-950/30 ring-1 ring-purple-500/50"
                : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
            }`}
          >
            <div className="text-[11px] font-medium text-slate-400">Total Berkas PDF</div>
            <div className="text-2xl font-bold text-slate-100 mt-1">{auditResult.total || 0}</div>
            <div className="text-[10px] text-slate-500 mt-0.5">Semua berkas</div>
          </div>

          <div
            onClick={() => setFilterStatus(filterStatus === "main" ? "all" : "main")}
            className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
              filterStatus === "main"
                ? "border-rose-500 bg-rose-950/40 ring-1 ring-rose-500/50"
                : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
            }`}
          >
            <div className="text-[11px] font-medium text-rose-300">Temuan Utama</div>
            <div className="text-2xl font-bold text-rose-400 mt-1">
              {auditResult.main_findings || 0}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">&lt; 1 KAUR / &lt; 2 PNC</div>
          </div>

          <div
            onClick={() => setFilterStatus(filterStatus === "sc" ? "all" : "sc")}
            className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
              filterStatus === "sc"
                ? "border-amber-500 bg-amber-950/40 ring-1 ring-amber-500/50"
                : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
            }`}
          >
            <div className="text-[11px] font-medium text-amber-300">Temuan SC</div>
            <div className="text-2xl font-bold text-amber-400 mt-1">
              {auditResult.normal_findings || 0}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Nomor SC kosong/strip</div>
          </div>

          <div
            onClick={() => setFilterStatus(filterStatus === "compliant" ? "all" : "compliant")}
            className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
              filterStatus === "compliant"
                ? "border-emerald-500 bg-emerald-950/40 ring-1 ring-emerald-500/50"
                : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
            }`}
          >
            <div className="text-[11px] font-medium text-emerald-300">Sesuai Aturan</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              {auditResult.compliant || 0}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">1 KAUR & 2 PNC</div>
          </div>
        </div>
      )}

      {/* Batch Correction Actions */}
      {auditResult && (auditResult.main_findings || 0) > 0 && (
        <div className="p-4 rounded-xl border border-rose-900/40 bg-rose-950/20 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-rose-300 text-xs">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>
              Ditemukan <strong className="text-white">{auditResult.main_findings}</strong> berkas PDF yang belum memenuhi aturan 1 KAUR & 2 PNC.
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleBatchCorrect("batch")}
              disabled={actionLoading !== null}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs shadow-md transition-colors"
            >
              <Wrench className="w-3.5 h-3.5" />
              {actionLoading === "batch" ? "Mengoreksi..." : "Auto-Correct Temuan Utama"}
            </button>

            <button
              onClick={() => handleBatchCorrect("no-sc")}
              disabled={actionLoading !== null}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
            >
              {actionLoading === "no-sc" ? "Mengoreksi SC..." : "Auto-Correct Nomor SC"}
            </button>
          </div>
        </div>
      )}

      {/* Table of Files */}
      {auditResult?.files && auditResult.files.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-slate-200">
                Daftar Berkas Hasil Audit ({filteredFiles.length} berkas)
              </span>
              <div className="flex rounded-md border border-slate-800 bg-slate-950 p-0.5 text-[11px]">
                <button
                  onClick={() => setFilterStatus("all")}
                  className={`px-2 py-0.5 rounded transition-colors ${
                    filterStatus === "all" ? "bg-slate-700 text-white font-medium" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Semua ({auditResult.total || 0})
                </button>
                <button
                  onClick={() => setFilterStatus("main")}
                  className={`px-2 py-0.5 rounded transition-colors ${
                    filterStatus === "main" ? "bg-rose-700 text-white font-medium" : "text-rose-400 hover:text-rose-200"
                  }`}
                >
                  🚨 Temuan Utama ({auditResult.main_findings || 0})
                </button>
                <button
                  onClick={() => setFilterStatus("sc")}
                  className={`px-2 py-0.5 rounded transition-colors ${
                    filterStatus === "sc" ? "bg-amber-600 text-white font-medium" : "text-amber-400 hover:text-amber-200"
                  }`}
                >
                  🧾 Temuan SC ({auditResult.normal_findings || 0})
                </button>
                <button
                  onClick={() => setFilterStatus("compliant")}
                  className={`px-2 py-0.5 rounded transition-colors ${
                    filterStatus === "compliant" ? "bg-emerald-700 text-white font-medium" : "text-emerald-400 hover:text-emerald-200"
                  }`}
                >
                  ✅ Sesuai ({auditResult.compliant || 0})
                </button>
              </div>
            </div>
            {filterStatus !== "all" && (
              <button
                onClick={() => setFilterStatus("all")}
                className="text-purple-400 hover:underline text-[11px]"
              >
                Reset Filter
              </button>
            )}
          </div>

          <div className="overflow-x-auto max-h-[500px]">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-slate-950 border-b border-slate-800 text-slate-400 text-[11px]">
                <tr>
                  <th className="px-4 py-2.5">Nama Berkas PDF</th>
                  <th className="px-3 py-2.5">Tanggal</th>
                  <th className="px-4 py-2.5">Personil Terbaca</th>
                  <th className="px-3 py-2.5">Status Kepatuhan</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {filteredFiles.map((file, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-2 text-slate-200 font-sans font-medium">
                      {file.file}
                    </td>
                    <td className="px-3 py-2 text-slate-400 whitespace-nowrap">
                      {file.date || "-"}
                    </td>
                    <td className="px-4 py-2 text-slate-300 font-sans text-xs">
                      {file.dilaksanakan_oleh ||
                        [...(file.kaur || []), ...(file.pnc || [])].join(", ") ||
                        "-"}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {file.is_compliant && !file.needs_sc_correction ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          1 KAUR, 2 PNC
                        </span>
                      ) : file.is_main_finding ? (
                        <span className="inline-flex items-center gap-1 text-rose-400 font-semibold bg-rose-950/40 px-2 py-0.5 rounded">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Temuan Utama
                        </span>
                      ) : file.needs_sc_correction ? (
                        <span className="inline-flex items-center gap-1 text-amber-400 font-medium bg-amber-950/40 px-2 py-0.5 rounded">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Temuan SC {file.no_sc_missing_count ? `(${file.no_sc_missing_count})` : ""}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-slate-400 font-medium">
                          {file.status_label || file.status_rule || "Kelebihan Personil"}
                        </span>
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
