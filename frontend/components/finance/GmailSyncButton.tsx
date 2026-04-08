"use client";

import { useState } from "react";

export default function GmailSyncButton({ onSynced }: { onSynced: () => void }) {
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");

  async function sync() {
    if (status === "loading") return;
    setStatus("loading");
    try {
      const res = await fetch("/api/finance/sync-gmail", { method: "POST" });
      if (!res.ok) throw new Error();
      setStatus("done");
      onSynced();
      setTimeout(() => setStatus("idle"), 3000);
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  }

  const labels = {
    idle:    "SYNC GMAIL",
    loading: "SYNCING…",
    done:    "SYNCED ✓",
    error:   "FAILED ✗",
  };

  const colors = {
    idle:    "#2e2e2e",
    loading: "#f59e0b",
    done:    "#4ade80",
    error:   "#ef4444",
  };

  return (
    <>
      <button className="sync-btn" onClick={sync} disabled={status === "loading"}>
        <span className="sync-dot" />
        {labels[status]}
      </button>

      <style jsx>{`
        .sync-btn {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          background: transparent;
          border: 1px solid ${colors[status]};
          color: ${colors[status]};
          font-family: "IBM Plex Mono", monospace;
          font-size: 0.6rem;
          letter-spacing: 0.12em;
          padding: 0.4rem 0.85rem;
          cursor: pointer;
          transition: all 0.2s;
          border-radius: 2px;
        }

        .sync-btn:hover:not(:disabled) {
          background: rgba(74, 222, 128, 0.04);
          border-color: #4ade80;
          color: #4ade80;
        }

        .sync-btn:disabled { cursor: default; }

        .sync-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: ${colors[status]};
          flex-shrink: 0;
          animation: ${status === "loading" ? "pulse 1s ease-in-out infinite" : "none"};
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.2; }
        }
      `}</style>
    </>
  );
}