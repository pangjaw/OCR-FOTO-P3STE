"use client";

import React, { useEffect, useRef, useState } from "react";
import { Terminal, Trash2, Copy, Check, Pause, Play } from "lucide-react";

interface TerminalConsoleProps {
  logs: string[];
  onClear?: () => void;
  isRunning?: boolean;
}

export const TerminalConsole: React.FC<TerminalConsoleProps> = ({
  logs,
  onClear,
  isRunning,
}) => {
  const [autoScroll, setAutoScroll] = useState(true);
  const [copied, setCopied] = useState(false);
  const [filterQuery, setFilterQuery] = useState("");
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, autoScroll]);

  const handleCopy = () => {
    navigator.clipboard.writeText(logs.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filteredLogs = filterQuery
    ? logs.filter((l) => l.toLowerCase().includes(filterQuery.toLowerCase()))
    : logs;

  return (
    <div className="flex flex-col h-full rounded-xl border border-slate-800 bg-slate-950/90 shadow-2xl overflow-hidden font-mono text-xs">
      {/* Terminal Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/90 border-b border-slate-800 select-none">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5 mr-2">
            <span className="w-3 h-3 rounded-full bg-rose-500/80 inline-block" />
            <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" />
            <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" />
          </div>
          <Terminal className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-slate-300">Live Execution Terminal</span>
          {isRunning && (
            <span className="flex items-center gap-1.5 ml-2 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              RUNNING
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Cari log..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            className="px-2.5 py-1 rounded bg-slate-800/80 border border-slate-700/60 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 text-[11px] w-36"
          />

          <button
            onClick={() => setAutoScroll(!autoScroll)}
            title={autoScroll ? "Pause Auto-Scroll" : "Resume Auto-Scroll"}
            className={`p-1.5 rounded border transition-colors ${
              autoScroll
                ? "bg-slate-800 border-slate-700 text-emerald-400 hover:bg-slate-700"
                : "bg-amber-500/20 border-amber-500/40 text-amber-300 hover:bg-amber-500/30"
            }`}
          >
            {autoScroll ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={handleCopy}
            title="Salin seluruh log"
            className="p-1.5 rounded bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          {onClear && (
            <button
              onClick={onClear}
              title="Bersihkan layar"
              className="p-1.5 rounded bg-slate-800 border border-slate-700 text-slate-300 hover:bg-rose-500/20 hover:text-rose-300 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Terminal Output Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-1 select-text scroll-smooth">
        {filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-slate-600 italic">
            Belum ada output log proses. Jalankan step atau Run All untuk memulai.
          </div>
        ) : (
          filteredLogs.map((line, idx) => {
            let color = "text-slate-300";
            if (line.includes("✅") || line.includes("SUCCESS") || line.includes("selesai dengan sukses")) {
              color = "text-emerald-400 font-semibold";
            } else if (line.includes("❌") || line.includes("[ERROR]") || line.includes("FAILED")) {
              color = "text-rose-400 font-semibold bg-rose-950/20 px-1 py-0.5 rounded";
            } else if (line.includes("⚠️") || line.includes("[WARNING]")) {
              color = "text-amber-300";
            } else if (line.includes("===") || line.includes("Executing")) {
              color = "text-cyan-400 font-bold border-t border-b border-cyan-900/40 py-1 my-1";
            } else if (line.startsWith("[STDERR]")) {
              color = "text-rose-300/80";
            }

            return (
              <div key={idx} className={`leading-relaxed break-all ${color}`}>
                {line}
              </div>
            );
          })
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
};
