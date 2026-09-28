"use client";

import React, { useEffect, useState } from "react";
import clsx from "clsx";
import {
  Search,
  Sliders,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Sparkles,
  RefreshCw,
  Image as ImageIcon,
  Upload,
  RotateCcw,
} from "lucide-react";
import { TimemarkEditorModal } from "./timemark-editor-modal";

interface PhotoItem {
  name: string;
  rawUrl: string;
  editedUrl: string | null;
  timeUrl: string | null;
  coordUrl: string | null;
  hasEdited: boolean;
  hasTime: boolean;
  hasCoord: boolean;
  isCollage: boolean;
  hasBackup?: boolean;
  meta: any;
  coordMeta: any;
}

interface TargetFileItem {
  file: string;
  category: string;
  btp: string;
  date: string;
  tim: number;
  identifiers: string[];
}

interface AssetFolder {
  btp: string;
  category: string;
  identifier: string;
  relDir: string;
  dateText: string;
  photos: PhotoItem[];
}

export const PhotoGallery: React.FC = () => {
  const [items, setItems] = useState<AssetFolder[]>([]);
  const [btps, setBtps] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Filter state
  const [targetFiles, setTargetFiles] = useState<TargetFileItem[]>([]);
  const [selectedTargetFile, setSelectedTargetFile] = useState<string>("");
  const [selectedBtp, setSelectedBtp] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [viewMode, setViewMode] = useState<"dual" | "edited" | "raw">("dual");
  const [pipelineMode, setPipelineMode] = useState<"standard" | "time" | "coord">("standard");
  const [detectorFilter, setDetectorFilter] = useState<"" | "google_vision" | "guide">("");
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalItems, setTotalItems] = useState<number>(0);

  // Photo replace / revert state
  const [actionLoadingRel, setActionLoadingRel] = useState<string | null>(null);
  const [dragOverRel, setDragOverRel] = useState<string | null>(null);

  // Modal state
  const [editingPhoto, setEditingPhoto] = useState<{
    rawRelPath: string;
    rawUrl: string;
    editedUrl: string | null;
    dateText: string;
    yPos?: number;
    xPos?: number;
  } | null>(null);

  const [photoTargetsMap, setPhotoTargetsMap] = useState<Record<string, { target_files: string[] }>>({});

  useEffect(() => {
    fetch("/api/target-files")
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setTargetFiles(data.targets || []);
        }
      })
      .catch((err) => console.error("Error fetching target files:", err));

    fetch("/api/photo-targets-mapping")
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.mapping) {
          setPhotoTargetsMap(data.mapping);
        }
      })
      .catch((err) => console.error("Error fetching photo targets mapping:", err));
  }, []);

  const fetchData = async (p = page) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(p),
        limit: "12",
      });
      if (selectedTargetFile) params.append("targetFile", selectedTargetFile);
      if (selectedBtp) params.append("btp", selectedBtp);
      if (selectedCategory) params.append("category", selectedCategory);
      if (searchQuery) params.append("search", searchQuery);
      if (detectorFilter) params.append("detector", detectorFilter);

      const res = await fetch(`/api/photos?${params.toString()}`);
      const data = await res.json();
      if (data.success) {
        setItems(data.items || []);
        setBtps(data.btps || []);
        setCategories(data.categories || []);
        setTotalPages(data.totalPages || 1);
        setTotalItems(data.total || 0);
      }
    } catch (err) {
      console.error("Error fetching photos:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
    fetchData(1);
  }, [selectedTargetFile, selectedBtp, selectedCategory, searchQuery, detectorFilter]);

  const handleDirectDrop = async (rel: string, file: File) => {
    if (!file.type.startsWith("image/") && !file.name.match(/\.(jpe?g|png|webp|bmp)$/i)) {
      alert("Harap seret berkas gambar (JPG, PNG, atau WEBP)!");
      return;
    }

    setActionLoadingRel(rel);
    try {
      const formData = new FormData();
      formData.append("rel", rel);
      formData.append("file", file);
      formData.append("mode", pipelineMode);
      formData.append("detector", detectorFilter || "guide");

      const res = await fetch("/api/photos/replace", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.success) {
        await fetchData(page);
      } else {
        alert("Gagal mengganti foto: " + (data.error || "Unknown error"));
      }
    } catch (err: any) {
      alert("Error mengganti foto: " + err.message);
    } finally {
      setActionLoadingRel(null);
    }
  };

  const handleRevert = async (rel: string) => {
    if (!confirm("Kembalikan foto ini ke versi aslinya?")) return;
    setActionLoadingRel(rel);
    try {
      const res = await fetch("/api/photos/revert", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rel,
          mode: pipelineMode,
          detector: detectorFilter || "guide",
        }),
      });
      const data = await res.json();
      if (data.success) {
        await fetchData(page);
      } else {
        alert("Gagal memulihkan foto: " + (data.error || "Unknown error"));
      }
    } catch (err: any) {
      alert("Error memulihkan foto: " + err.message);
    } finally {
      setActionLoadingRel(null);
    }
  };

  const [mergingAssetRel, setMergingAssetRel] = useState<string | null>(null);

  const handleRemergeGroup = async (asset: AssetFolder) => {
    setMergingAssetRel(asset.relDir);
    try {
      const firstPhotoRel = asset.photos[0] ? `${asset.relDir}/${asset.photos[0].name}` : `${asset.relDir}/0.jpg`;
      const res = await fetch("/api/pdf/remerge-single", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rawRelPath: firstPhotoRel,
          pdfName: selectedTargetFile || undefined,
          mode: pipelineMode === "time" ? "time" : pipelineMode === "coord" ? "coord" : "standard",
        }),
      });
      const data = await res.json();
      if (data.success || data.status === "ok") {
        if (data.fileUrl) {
          window.open(data.fileUrl, "_blank");
        }
        if (data.mergedCount && data.mergedCount > 1) {
          alert(`✅ ${data.mergedCount} berkas PDF target berhasil diperbarui (${(data.durationMs / 1000).toFixed(1)}s)!`);
        } else {
          alert(`✅ PDF ${data.pdfName} berhasil diperbarui!`);
        }
      } else {
        alert("Gagal merge PDF: " + (data.error || JSON.stringify(data)));
      }
    } catch (err: any) {
      alert("Error saat merge PDF: " + err.message);
    } finally {
      setMergingAssetRel(null);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
      fetchData(newPage);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search & Filter Header Bar */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/80 shadow-lg space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ImageIcon className="w-5 h-5 text-emerald-400" />
            <h2 className="text-base font-semibold text-slate-200">
              Galeri Foto Aset & Komparasi Timemark
            </h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
              {totalItems} aset ditemukan
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-slate-800 bg-slate-950 p-0.5 text-xs">
              {(["standard", "time", "coord"] as const).map((mode) => (
                <button key={mode} onClick={() => setPipelineMode(mode)} className={`px-3 py-1 rounded-md font-medium ${pipelineMode === mode ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"}`}>
                  {mode === "standard" ? "Edit Tanggal" : mode === "time" ? "Edit Jam" : "Edit Koordinat"}
                </button>
              ))}
            </div>

            {/* View Mode Toggle */}
            <div className="flex rounded-lg border border-slate-800 bg-slate-950 p-0.5 text-xs">
              <button
                onClick={() => setViewMode("dual")}
                className={`px-3 py-1 rounded-md font-medium transition-colors ${
                  viewMode === "dual"
                    ? "bg-emerald-600 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Dual View
              </button>
              <button
                onClick={() => setViewMode("edited")}
                className={`px-3 py-1 rounded-md font-medium transition-colors ${
                  viewMode === "edited"
                    ? "bg-emerald-600 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Hasil Edit (04)
              </button>
              <button
                onClick={() => setViewMode("raw")}
                className={`px-3 py-1 rounded-md font-medium transition-colors ${
                  viewMode === "raw"
                    ? "bg-emerald-600 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Asli Mentah (03)
              </button>
            </div>

            {/* Detector Filter Toggle */}
            <div className="flex rounded-lg border border-slate-800 bg-slate-950 p-0.5 text-xs">
              <button
                onClick={() => setDetectorFilter("")}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  detectorFilter === ""
                    ? "bg-slate-700 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Semua Detektor
              </button>
              <button
                onClick={() => setDetectorFilter("google_vision")}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md font-medium transition-colors ${
                  detectorFilter === "google_vision"
                    ? "bg-purple-600 text-white font-semibold shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Sparkles className="w-3 h-3 text-purple-300" />
                Google Vision
              </button>
              <button
                onClick={() => setDetectorFilter("guide")}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  detectorFilter === "guide"
                    ? "bg-sky-600 text-white font-semibold shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Metode Biasa
              </button>
            </div>

            <button
              onClick={() => fetchData(page)}
              title="Refresh galeri"
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 pt-3 border-t border-slate-800">
          {/* Target File Filter */}
          <div className="relative">
            <select
              value={selectedTargetFile}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedTargetFile(val);
                const match = targetFiles.find((t) => t.file === val);
                if (match) {
                  if (match.category) setSelectedCategory(match.category);
                  if (match.btp) setSelectedBtp(match.btp);
                }
              }}
              className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:border-emerald-500 truncate"
              title="Filter foto berdasarkan berkas target PDF (Folder 2)"
            >
              <option value="">📄 Semua Berkas Target</option>
              {targetFiles.map((t) => (
                <option key={t.file} value={t.file} title={t.file}>
                  {t.file}
                </option>
              ))}
            </select>
          </div>

          {/* Search Box */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Cari nama aset (misal: ZP 12A)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 placeholder:text-slate-500 text-xs focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* BTP Filter */}
          <div className="relative">
            <select
              value={selectedBtp}
              onChange={(e) => setSelectedBtp(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:border-emerald-500"
            >
              <option value="">Semua Wilayah (BTP)</option>
              {btps.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>

          {/* Category Filter */}
          <div className="relative">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:border-emerald-500"
            >
              <option value="">Semua Kategori Aset</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Reset button if filtered */}
          {(selectedTargetFile || selectedBtp || selectedCategory || searchQuery || detectorFilter) && (
            <button
              onClick={() => {
                setSelectedTargetFile("");
                setSelectedBtp("");
                setSelectedCategory("");
                setSearchQuery("");
                setDetectorFilter("");
              }}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
            >
              Reset Filter
            </button>
          )}
        </div>
      </div>

      {/* Asset Cards Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64 text-slate-500 gap-2">
          <RefreshCw className="w-5 h-5 animate-spin text-emerald-400" />
          <span>Memuat galeri foto...</span>
        </div>
      ) : items.length === 0 ? (
        <div className="p-12 text-center rounded-xl border border-slate-800 bg-slate-900/40 text-slate-500 italic">
          Tidak ada aset yang cocok dengan kriteria pencarian.
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((asset) => (
            <div
              key={asset.relDir}
              className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-colors shadow-sm"
            >
              {/* Asset Card Header */}
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-slate-800/80">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-950/60 text-sky-400 border border-sky-800/60">
                    {asset.btp}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
                    {asset.category}
                  </span>
                  <span className="text-sm font-bold text-slate-100">{asset.identifier}</span>
                  <button
                    onClick={() => handleRemergeGroup(asset)}
                    disabled={mergingAssetRel === asset.relDir}
                    className="flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-sky-950 hover:bg-sky-900 text-sky-300 border border-sky-700/60 transition-colors disabled:opacity-50 ml-1 shadow-sm"
                    title="Gabungkan 1 baris aset ini ke seluruh berkas PDF target terkait"
                  >
                    {mergingAssetRel === asset.relDir ? (
                      <>
                        <RefreshCw className="w-3 h-3 animate-spin" />
                        <span>Merging...</span>
                      </>
                    ) : (
                      <>
                        <span>⚡</span>
                        <span>Merge PDF</span>
                      </>
                    )}
                  </button>
                  {(() => {
                    const key1 = `${asset.btp}/${asset.category}/${asset.identifier}`;
                    const tList = (photoTargetsMap[key1] && photoTargetsMap[key1].target_files) || [];
                    if (tList.length > 0) {
                      return (
                        <span
                          className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-950/60 text-blue-400 border border-blue-800/60 cursor-help"
                          title={`Aset ini digunakan pada ${tList.length} berkas PDF target:\n${tList.join('\n')}`}
                        >
                          📄 {tList.length} Target PDF
                        </span>
                      );
                    }
                    return null;
                  })()}
                </div>

                {asset.dateText && (
                  <span className="text-xs font-mono text-slate-400 bg-slate-950 px-2.5 py-0.5 rounded border border-slate-800">
                    📅 {asset.dateText}
                  </span>
                )}
              </div>

              {/* Photos Row (0%, 50%, 100%) */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {asset.photos.map((photo) => {
                  const rawRelPath = `${asset.relDir}/${photo.name}`;
                  const isManual = photo.meta && photo.meta.manualEdit;
                  const modeUrl = pipelineMode === "coord" ? photo.coordUrl : pipelineMode === "time" ? photo.timeUrl : photo.editedUrl;
                  const displayUrl = viewMode === "raw" ? photo.rawUrl : modeUrl || photo.rawUrl;

                  return (
                    <div
                      key={photo.name}
                      className="group relative flex flex-col rounded-lg border border-slate-800/80 bg-slate-950 overflow-hidden hover:border-slate-700 transition-all"
                    >
                      {/* Photo Header / Badge */}
                      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900/80 border-b border-slate-800/60 text-[11px]">
                        <span className="font-semibold text-slate-300">{photo.name}</span>
                        <div className="flex items-center gap-1">
                          {photo.isCollage && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                              Kolase
                            </span>
                          )}
                          {isManual ? (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-0.5">
                              <Sparkles className="w-2.5 h-2.5" />
                              Manual (Y:{photo.meta.yPos})
                            </span>
                          ) : photo.hasEdited ? (
                            <>
                              {photo.meta?.detector === "google_vision" ? (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-950 text-purple-300 border border-purple-800 flex items-center gap-0.5 font-mono">
                                  <Sparkles className="w-2 h-2 text-purple-400" />
                                  Vision AI
                                </span>
                              ) : (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-sky-950 text-sky-300 border border-sky-800 flex items-center gap-0.5 font-mono">
                                  Metode Biasa
                                </span>
                              )}
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-0.5">
                                <CheckCircle2 className="w-2.5 h-2.5" />
                                Edited
                              </span>
                            </>
                          ) : (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                              Mentah
                            </span>
                          )}
                          {photo.hasBackup && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-0.5" title="Foto ini pernah diganti dan memiliki backup asli">
                              <RotateCcw className="w-2.5 h-2.5" />
                              Diganti
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Photo Image Area & Drag Drop Target */}
                      <div
                        onDragOver={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setDragOverRel(rawRelPath);
                        }}
                        onDragLeave={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setDragOverRel(null);
                        }}
                        onDrop={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setDragOverRel(null);
                          const file = e.dataTransfer.files?.[0];
                          if (file) handleDirectDrop(rawRelPath, file);
                        }}
                        className={clsx(
                          "relative aspect-square bg-slate-950 flex items-center justify-center overflow-hidden transition-all",
                          dragOverRel === rawRelPath && "ring-4 ring-amber-500 ring-inset"
                        )}
                        title="Tarik & lepaskan berkas foto ke sini untuk mengganti foto ini"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={displayUrl}
                          alt={`${asset.identifier} - ${photo.name}`}
                          className="object-contain w-full h-full transition-transform duration-200 group-hover:scale-105"
                          loading="lazy"
                        />

                        {/* Drag Over Overlay */}
                        {dragOverRel === rawRelPath && (
                          <div className="absolute inset-0 bg-amber-600/90 flex flex-col items-center justify-center text-white p-2 z-20 pointer-events-none">
                            <Upload className="w-8 h-8 mb-1 animate-bounce" />
                            <span className="text-xs font-bold text-center">Lepaskan untuk ganti foto</span>
                          </div>
                        )}

                        {/* Hover Overlay Button */}
                        <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2 p-2">
                          {actionLoadingRel === rawRelPath ? (
                            <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium bg-slate-900/90 px-3 py-1.5 rounded-lg border border-slate-700">
                              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                              <span>Memproses...</span>
                            </div>
                          ) : (
                            <>
                              <button
                                onClick={() =>
                                  setEditingPhoto({
                                    rawRelPath,
                                    rawUrl: photo.rawUrl,
                                    editedUrl: photo.editedUrl,
                                    dateText: photo.meta?.dateText || asset.dateText || "",
                                    yPos: photo.meta?.yPos || 220,
                                    xPos: photo.meta?.xPos || 14,
                                  })
                                }
                                className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs shadow-lg transition-colors"
                              >
                                <Sliders className="w-3.5 h-3.5" />
                                Edit Timemark
                              </button>

                              <div
                                onDragOver={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  setDragOverRel(rawRelPath);
                                }}
                                onDragLeave={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  setDragOverRel(null);
                                }}
                                onDrop={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  setDragOverRel(null);
                                  const file = e.dataTransfer.files?.[0];
                                  if (file) handleDirectDrop(rawRelPath, file);
                                }}
                                className={clsx(
                                  "w-full flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-dashed text-xs select-none transition-all cursor-default",
                                  dragOverRel === rawRelPath
                                    ? "bg-amber-500/30 border-amber-400 text-amber-200 font-bold"
                                    : "bg-slate-800/80 border-amber-500/60 text-amber-400 hover:bg-amber-500/10"
                                )}
                                title="Tarik & lepaskan file foto dari folder komputer ke sini untuk langsung mengganti foto"
                              >
                                <Upload className="w-3.5 h-3.5 text-amber-400" />
                                <span>Drag & Drop Foto</span>
                              </div>

                              {photo.hasBackup && (
                                <button
                                  onClick={() => handleRevert(rawRelPath)}
                                  className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs shadow-lg transition-colors"
                                  title="Kembalikan foto ini ke versi aslinya"
                                >
                                  <RotateCcw className="w-3.5 h-3.5" />
                                  Revert Asli
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}

          {/* Pagination Controls */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-800">
            <span className="text-xs text-slate-400">
              Halaman <span className="font-semibold text-slate-200">{page}</span> dari{" "}
              <span className="font-semibold text-slate-200">{totalPages}</span>
            </span>

            <div className="flex items-center gap-2">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 text-xs font-medium transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                Sebelumnya
              </button>

              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 text-xs font-medium transition-colors"
              >
                Berikutnya
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Timemark Editor Modal */}
      {editingPhoto && (
        <TimemarkEditorModal
          isOpen={true}
          onClose={() => setEditingPhoto(null)}
          rawRelPath={editingPhoto.rawRelPath}
          rawUrl={editingPhoto.rawUrl}
          editedUrl={editingPhoto.editedUrl}
          timeUrl={items.flatMap((a) => a.photos).find((p) => p.name === editingPhoto.rawRelPath.split("/").pop())?.timeUrl}
          coordUrl={items.flatMap((a) => a.photos).find((p) => p.name === editingPhoto.rawRelPath.split("/").pop())?.coordUrl}
          mode={pipelineMode}
          currentDateText={editingPhoto.dateText}
          defaultY={editingPhoto.yPos}
          defaultX={editingPhoto.xPos}
          onSaved={() => {
            fetchData(page);
          }}
        />
      )}
    </div>
  );
};
