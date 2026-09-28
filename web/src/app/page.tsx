"use client";

import React, { useState } from "react";
import {
  Layers,
  Image as ImageIcon,
  Users,
  ShieldCheck,
  FileSpreadsheet,
} from "lucide-react";
import { PipelineDashboard } from "@/components/pipeline-dashboard";
import { PhotoGallery } from "@/components/photo-gallery";
import { EmployeeManager } from "@/components/employee-manager";
import { PersonnelAudit } from "@/components/personnel-audit";
import { DocumentDateAudit } from "@/components/document-date-audit";
import { ExcelExportPanel } from "@/components/excel-export-panel";

export default function Home() {
  const [activeTab, setActiveTab] = useState<
    "pipeline" | "gallery" | "employees" | "audit" | "export"
  >("pipeline");

  const [auditSubTab, setAuditSubTab] = useState<"personnel" | "dates">("personnel");

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      {/* Top Navbar / Header */}
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-900/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo and App Title */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center shadow-lg shadow-emerald-950/60 font-bold text-white text-base">
              P3
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-slate-100 tracking-tight">
                  OCR Foto Timemark
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Next.js App Router
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                P3STE Sintelis • Sistem Koreksi Watermark, Personil & Pelaporan Excel
              </p>
            </div>
          </div>

          {/* Tab Navigation */}
          <nav className="flex items-center gap-1 p-1 rounded-xl bg-slate-950 border border-slate-800 text-xs font-medium overflow-x-auto max-w-full">
            <button
              onClick={() => setActiveTab("pipeline")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all whitespace-nowrap ${
                activeTab === "pipeline"
                  ? "bg-emerald-600 text-white shadow-md font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Layers className="w-4 h-4" />
              Pipeline
            </button>

            <button
              onClick={() => setActiveTab("gallery")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all whitespace-nowrap ${
                activeTab === "gallery"
                  ? "bg-emerald-600 text-white shadow-md font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <ImageIcon className="w-4 h-4" />
              Galeri Foto
            </button>

            <button
              onClick={() => setActiveTab("employees")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all whitespace-nowrap ${
                activeTab === "employees"
                  ? "bg-emerald-600 text-white shadow-md font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Users className="w-4 h-4" />
              Pegawai
            </button>

            <button
              onClick={() => setActiveTab("audit")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all whitespace-nowrap ${
                activeTab === "audit"
                  ? "bg-emerald-600 text-white shadow-md font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              Audit Dokumen
            </button>

            <button
              onClick={() => setActiveTab("export")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all whitespace-nowrap ${
                activeTab === "export"
                  ? "bg-emerald-600 text-white shadow-md font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <FileSpreadsheet className="w-4 h-4" />
              Export Excel
            </button>
          </nav>

          {/* System Status Pill */}
          <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-slate-300 font-mono text-[11px]">System Ready</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === "pipeline" && <PipelineDashboard />}
        {activeTab === "gallery" && <PhotoGallery />}
        {activeTab === "employees" && <EmployeeManager />}
        {activeTab === "audit" && (
          <div className="space-y-6">
            <div className="flex rounded-xl border border-slate-800 bg-slate-900 p-1 w-fit text-xs font-medium">
              <button
                onClick={() => setAuditSubTab("personnel")}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  auditSubTab === "personnel"
                    ? "bg-purple-600 text-white font-semibold shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                1. Audit Personil (1 KAUR, 2 PNC)
              </button>
              <button
                onClick={() => setAuditSubTab("dates")}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  auditSubTab === "dates"
                    ? "bg-cyan-600 text-white font-semibold shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                2. Audit Tanggal Dokumen PDF
              </button>
            </div>

            {auditSubTab === "personnel" ? <PersonnelAudit /> : <DocumentDateAudit />}
          </div>
        )}
        {activeTab === "export" && <ExcelExportPanel />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-wrap justify-between items-center gap-2">
          <span>OCR-FOTO-P3STE • Next.js Fullstack Engine (Port 3000)</span>
          <span className="font-mono text-[11px]">P3STE Sintelis Resort 1.21 Bogor</span>
        </div>
      </footer>
    </div>
  );
}
