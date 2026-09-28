"use client";

import React, { useEffect, useState } from "react";
import {
  Play,
  Square,
  RefreshCw,
  FolderSync,
  Crop,
  Calendar,
  Clock,
  UserCheck,
  Stamp,
  FileCheck2,
  Cpu,
  Layers,
  Camera,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
} from "lucide-react";
import { TerminalConsole } from "./terminal-console";

interface FileCounts {
  pdf_source: number;
  pdf_target: number;
  photos_export: number;
  photos_edited: number;
  photos_time: number;
  pdf_merged: number;
  pdf_merged_time: number;
}

export const PipelineDashboard: React.FC = () => {
  const [counts, setCounts] = useState<FileCounts | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  // Detector selection: "guide" (Metode Biasa) or "google_vision"
  const [detector, setDetector] = useState<"guide" | "google_vision">("guide");

  // Quota exceeded modal state
  const [quotaModalOpen, setQuotaModalOpen] = useState(false);
  const [quotaModalMessage, setQuotaModalMessage] = useState("");
  const [resumingAction, setResumingAction] = useState<string | null>(null);

  // Fetch counts
  const fetchCounts = async () => {
    try {
      const res = await fetch("/api/files");
      const data = await res.json();
      if (data.counts) setCounts(data.counts);
    } catch (e) {
      console.error("Error fetching file counts:", e);
    }
  };

  useEffect(() => {
    fetchCounts();
    const interval = setInterval(fetchCounts, 10000);
    return () => clearInterval(interval);
  }, []);

  // Connect SSE for live logs and status
  useEffect(() => {
    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource("/api/pipeline/logs");

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "log" && data.line) {
            setLogs((prev) => [...prev, data.line]);
          } else if (data.type === "status") {
            setIsRunning(!!data.is_running);
            setCurrentStep(data.step || null);
            if (!data.is_running) {
              fetchCounts();
            }
          } else if (data.type === "quota_exceeded") {
            setQuotaModalMessage(data.message || "Kuota Google Cloud Vision telah habis.");
            setQuotaModalOpen(true);
          } else if (data.type === "clear") {
            setLogs([]);
          }
        } catch {}
      };

      eventSource.onerror = () => {
        // SSE disconnected, will auto retry
      };
    } catch (e) {
      console.error("SSE connection error:", e);
    }

    return () => {
      if (eventSource) eventSource.close();
    };
  }, []);

  const handleRunStep = async (stepKey: string) => {
    setLoadingAction(stepKey);
    try {
      const res = await fetch("/api/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step: stepKey, detector }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.error || "Gagal memulai step");
      }
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleResume = async (action: "continue_guide" | "stop") => {
    setResumingAction(action);
    try {
      const res = await fetch("/api/pipeline/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await res.json();
      if (data.success) {
        setQuotaModalOpen(false);
        if (action === "continue_guide") {
          setDetector("guide");
        }
      } else {
        alert("Gagal mengirim perintah resume ke proses.");
      }
    } catch (err: any) {
      alert(`Error saat melanjutkan proses: ${err.message}`);
    } finally {
      setResumingAction(null);
    }
  };

  const handleStop = async () => {
    try {
      await fetch("/api/pipeline", { method: "DELETE" });
    } catch (err: any) {
      alert(`Error menghentikan: ${err.message}`);
    }
  };

  const stepList = [
    {
      id: "step1",
      name: "Step 1: Ekstraksi Foto (Asli)",
      desc: "Ekstrak stream foto mentah dari 01_pdf_source ke 03_photos_export",
      icon: FolderSync,
      color: "text-sky-400 bg-sky-950/30 border-sky-800/40",
    },
    {
      id: "step1_crop",
      name: "Step 1: Crop Render (300 DPI)",
      desc: "Render halaman PDF 300 DPI lalu potong foto (bawa watermark teks)",
      icon: Camera,
      color: "text-cyan-400 bg-cyan-950/30 border-cyan-800/40",
    },
    {
      id: "step1.5",
      name: "Step 1.5: Auto-Crop Kolase",
      desc: "Deteksi & potong otomatis kolase foto 300x300",
      icon: Crop,
      color: "text-indigo-400 bg-indigo-950/30 border-indigo-800/40",
    },
    {
      id: "step2",
      name: "Step 2: Ekstraksi Tanggal",
      desc: "Ambil tanggal 02_pdf_target → date.txt per aset",
      icon: Calendar,
      color: "text-emerald-400 bg-emerald-950/30 border-emerald-800/40",
    },
    {
      id: "step3",
      name: "Step 3: Penjadwalan Tim",
      desc: "Alokasi waktu kerja & pembagian Tim ke schedule.json",
      icon: Clock,
      color: "text-amber-400 bg-amber-950/30 border-amber-800/40",
    },
    {
      id: "step3.5",
      name: "Step 3.5: Koreksi Personil",
      desc: "Audit & auto-koreksi aturan 1 KAUR 2 PNC di PDF target",
      icon: UserCheck,
      color: "text-purple-400 bg-purple-950/30 border-purple-800/40",
    },
    {
      id: "step4",
      name: "Step 4: Edit Timemark",
      desc: "Inpaint tanggal lama & tempel watermark baru ke 04",
      icon: Stamp,
      color: "text-rose-400 bg-rose-950/30 border-rose-800/40",
    },
    {
      id: "step5",
      name: "Step 5: Gabung PDF",
      desc: "Pasang foto edit ke PDF target → simpan ke 05",
      icon: FileCheck2,
      color: "text-teal-400 bg-teal-950/30 border-teal-800/40",
    },
    {
      id: "step6_core_optik",
      name: "Step 6: Core Optik",
      desc: "Koreksi jumlah core Serat Optik (JPL:12, OTB:24xN)",
      icon: Cpu,
      color: "text-yellow-400 bg-yellow-950/30 border-yellow-800/40",
    },
  ];

  return (
    <div className="space-y-6">
      {/* File Count Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
          <div className="text-[11px] font-medium text-slate-400">01 Sumber PDF</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">
            {counts?.pdf_source ?? "..."}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Berkas PDF 2026</div>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
          <div className="text-[11px] font-medium text-slate-400">02 Target PDF</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            {counts?.pdf_target ?? "..."}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Template PDF 2025</div>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
          <div className="text-[11px] font-medium text-slate-400">03 Foto Export</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">
            {counts?.photos_export ?? "..."}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Foto Mentah Asli</div>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
          <div className="text-[11px] font-medium text-slate-400">04 Foto Edited</div>
          <div className="text-2xl font-bold text-rose-400 mt-1">
            {counts?.photos_edited ?? "..."}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Watermark Baru</div>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
          <div className="text-[11px] font-medium text-slate-400">05 PDF Merged</div>
          <div className="text-2xl font-bold text-teal-400 mt-1">
            {counts?.pdf_merged ?? "..."}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Dokumen Final</div>
        </div>
      </div>

      {/* Main Execution Controls */}
      <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/80 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              Kontrol Eksekusi Alur Pipeline
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Jalankan seluruh rangkaian secara otomatis atau pilih langkah secara terpisah.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* OCR Detector Selector (seperti tombol profil, sejajar tombol tanggal/jam/koordinat) */}
            <div className="flex items-center rounded-lg border border-slate-800 bg-slate-950 p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setDetector("guide")}
                disabled={isRunning}
                className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                  detector === "guide"
                    ? "bg-emerald-600 text-white shadow-sm font-semibold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Deteksi timemark menggunakan garis panduan warna merah/oranye"
              >
                Metode Biasa (Garis Merah)
              </button>
              <button
                type="button"
                onClick={() => setDetector("google_vision")}
                disabled={isRunning}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-all ${
                  detector === "google_vision"
                    ? "bg-purple-600 text-white shadow-sm font-semibold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Deteksi timemark menggunakan Google Cloud Vision AI REST API"
              >
                <Sparkles className="w-3.5 h-3.5 text-purple-300" />
                Google Vision
              </button>
            </div>

            {isRunning ? (
              <button
                onClick={handleStop}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs shadow-lg shadow-rose-900/30 transition-colors animate-pulse"
              >
                <Square className="w-4 h-4" />
                Stop Proses Aktif
              </button>
            ) : (
              <>
                <button
                  onClick={() => handleRunStep("all")}
                  disabled={isRunning || loadingAction !== null}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs shadow-lg shadow-emerald-900/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
                >
                  <Play className="w-3.5 h-3.5 fill-white" />
                  Run All (Edit Tanggal)
                </button>

                <button
                  onClick={() => handleRunStep("all_time")}
                  disabled={isRunning || loadingAction !== null}
                  className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs shadow-md transition-colors"
                >
                  <Clock className="w-3.5 h-3.5 text-amber-400" />
                  Run All (Edit Jam)
                </button>

                <button
                  onClick={() => handleRunStep("all_coord")}
                  disabled={isRunning || loadingAction !== null}
                  className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs shadow-md transition-colors"
                >
                  <span className="text-xs">🧭</span>
                  Run All (Edit Koordinat)
                </button>
              </>
            )}

            <button
              onClick={fetchCounts}
              title="Refresh jumlah berkas"
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Step Buttons Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
          {stepList.map((step) => {
            const Icon = step.icon;
            const isThisRunning = isRunning && currentStep === step.id;
            return (
              <div
                key={step.id}
                className="flex flex-col justify-between p-3 rounded-lg border border-slate-800/80 bg-slate-950/40 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-start gap-2.5">
                  <div className={`p-2 rounded-md border ${step.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <div className="text-xs font-semibold text-slate-200">{step.name}</div>
                      {step.id === "step4" && (
                        <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono border ${
                          detector === "google_vision"
                            ? "bg-purple-950 text-purple-300 border-purple-800"
                            : "bg-emerald-950 text-emerald-300 border-emerald-800"
                        }`}>
                          {detector === "google_vision" ? "Vision AI" : "Garis Panduan"}
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5 leading-tight">
                      {step.desc}
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between">
                  <span className="text-[10px] text-slate-500">
                    {isThisRunning ? (
                      <span className="text-emerald-400 font-medium flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                        Sedang berjalan...
                      </span>
                    ) : (
                      "Siap eksekusi"
                    )}
                  </span>

                  <button
                    onClick={() => handleRunStep(step.id)}
                    disabled={isRunning || loadingAction !== null}
                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 font-medium text-[11px] border border-slate-700/80 transition-colors"
                  >
                    Jalankan
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Terminal Output Area */}
      <div className="h-[420px]">
        <TerminalConsole logs={logs} onClear={() => setLogs([])} isRunning={isRunning} />
      </div>

      {/* Modal Popup Kuota Habis */}
      {quotaModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-amber-600/50 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-amber-950/80 border border-amber-700/60 text-amber-400">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h3 className="text-base font-bold text-slate-100">
                  Kuota Google Cloud Vision Habis
                </h3>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  {quotaModalMessage || "Batas kuota gratis Google Cloud Vision API telah tercapai atau penagihan dinonaktifkan."}
                </p>
                <div className="text-xs text-amber-300/90 mt-2.5 bg-amber-950/40 p-2.5 rounded-lg border border-amber-800/40">
                  ⚠️ Proses Step 4 saat ini <strong>dijeda (paused)</strong>. Anda dapat melanjutkan pemrosesan sisa foto menggunakan <strong>Metode Biasa (Garis Panduan Merah)</strong> secara otomatis.
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => handleResume("stop")}
                disabled={resumingAction !== null}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
              >
                Hentikan Proses
              </button>
              <button
                type="button"
                onClick={() => handleResume("continue_guide")}
                disabled={resumingAction !== null}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-900/40 transition-colors"
              >
                {resumingAction === "continue_guide" ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Melanjutkan...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Lanjutkan dengan Metode Biasa
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
