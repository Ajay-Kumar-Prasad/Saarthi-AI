"use client";

import { useEffect, useState } from "react";

interface CategoryTotal {
  category: string;
  total: number;
}

const COLORS: Record<string, string> = {
  food:       "#f59e0b",
  transport:  "#60a5fa",
  shopping:   "#a78bfa",
  health:     "#34d399",
  utilities:  "#fb923c",
  other:      "#6b7280",
};

export default function SpendingChart({ refreshKey }: { refreshKey: number }) {
  const [data, setData] = useState<CategoryTotal[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"category" | "trend">("category");

  useEffect(() => {
    setLoading(true);
    fetch("/api/finance/summary")
      .then((r) => r.json())
      .then((d) => setData(d.summary ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [refreshKey]);

  const grand = data.reduce((s, d) => s + d.total, 0);
  const sorted = [...data].sort((a, b) => b.total - a.total);

  return (
    <div className="chart-root">
      <div className="chart-header">
        <span className="section-label">// SPENDING BREAKDOWN</span>
        <div className="view-toggle">
          <button
            className={view === "category" ? "toggle-btn active" : "toggle-btn"}
            onClick={() => setView("category")}
          >
            CATEGORY
          </button>
          <button
            className={view === "trend" ? "toggle-btn active" : "toggle-btn"}
            onClick={() => setView("trend")}
          >
            TREND
          </button>
        </div>
      </div>

      {loading && (
        <div className="chart-empty">
          <span className="blink">computing_</span>
        </div>
      )}

      {!loading && data.length === 0 && (
        <div className="chart-empty muted">No spending data yet.</div>
      )}

      {!loading && data.length > 0 && (
        <>
          {/* Grand total */}
          <div className="grand-total">
            <span className="gt-label">TOTAL OUTFLOW</span>
            <span className="gt-amount">
              ₹{grand.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            </span>
          </div>

          {/* Stacked bar */}
          <div className="stacked-bar">
            {sorted.map((d) => (
              <div
                key={d.category}
                className="stack-segment"
                style={{
                  width: `${(d.total / grand) * 100}%`,
                  background: COLORS[d.category] ?? COLORS.other,
                }}
                title={`${d.category}: ₹${d.total}`}
              />
            ))}
          </div>

          {/* Legend rows */}
          <div className="legend">
            {sorted.map((d) => {
              const color = COLORS[d.category] ?? COLORS.other;
              const pct = ((d.total / grand) * 100).toFixed(1);
              return (
                <div key={d.category} className="legend-row">
                  <div className="legend-left">
                    <div className="legend-dot" style={{ background: color }} />
                    <span className="legend-cat" style={{ color }}>
                      {d.category}
                    </span>
                  </div>
                  <div className="legend-right">
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${pct}%`,
                          background: color,
                        }}
                      />
                    </div>
                    <span className="legend-pct">{pct}%</span>
                    <span className="legend-amount">
                      ₹{d.total.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Alert */}
          {grand > 3000 && (
            <div className="alert-bar">
              <span className="alert-icon">▲</span>
              High spending detected — ₹{grand.toLocaleString("en-IN")} total
            </div>
          )}
        </>
      )}

      <style jsx>{`
        .chart-root {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          font-family: "IBM Plex Mono", monospace;
        }

        .chart-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .section-label {
          font-size: 0.6rem;
          letter-spacing: 0.15em;
          color: #2e2e2e;
        }

        .view-toggle {
          display: flex;
          gap: 0.25rem;
        }

        .toggle-btn {
          background: transparent;
          border: 1px solid #1a1a1a;
          color: #3a3a3a;
          font-family: "IBM Plex Mono", monospace;
          font-size: 0.55rem;
          letter-spacing: 0.1em;
          padding: 0.2rem 0.5rem;
          cursor: pointer;
          transition: all 0.15s;
        }

        .toggle-btn.active {
          border-color: #2a2a2a;
          color: #e8e8e0;
          background: #111;
        }

        .chart-empty {
          padding: 4rem 2rem;
          text-align: center;
          color: #2a2a2a;
          font-size: 0.75rem;
        }

        .blink {
          color: #f59e0b;
          animation: blink 1s step-start infinite;
        }

        @keyframes blink { 50% { opacity: 0; } }

        .grand-total {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          padding-bottom: 1rem;
          border-bottom: 1px solid #111;
        }

        .gt-label {
          font-size: 0.6rem;
          letter-spacing: 0.15em;
          color: #2e2e2e;
        }

        .gt-amount {
          font-size: 2.2rem;
          font-weight: 300;
          letter-spacing: -0.03em;
          color: #e8e8e0;
        }

        .stacked-bar {
          display: flex;
          height: 6px;
          border-radius: 1px;
          overflow: hidden;
          gap: 1px;
        }

        .stack-segment {
          height: 100%;
          transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .legend {
          display: flex;
          flex-direction: column;
          gap: 0.85rem;
        }

        .legend-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
        }

        .legend-left {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          min-width: 90px;
        }

        .legend-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          flex-shrink: 0;
        }

        .legend-cat {
          font-size: 0.68rem;
          letter-spacing: 0.05em;
          text-transform: uppercase;
        }

        .legend-right {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          flex: 1;
        }

        .bar-track {
          flex: 1;
          height: 3px;
          background: #111;
          border-radius: 1px;
          overflow: hidden;
        }

        .bar-fill {
          height: 100%;
          border-radius: 1px;
          transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
          opacity: 0.8;
        }

        .legend-pct {
          font-size: 0.6rem;
          color: #3a3a3a;
          min-width: 36px;
          text-align: right;
        }

        .legend-amount {
          font-size: 0.72rem;
          color: #9ca3af;
          min-width: 70px;
          text-align: right;
          font-variant-numeric: tabular-nums;
        }

        .alert-bar {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.6rem 0.9rem;
          background: rgba(245, 158, 11, 0.05);
          border: 1px solid rgba(245, 158, 11, 0.2);
          border-radius: 2px;
          font-size: 0.7rem;
          color: #f59e0b;
          letter-spacing: 0.03em;
        }

        .alert-icon {
          font-size: 0.6rem;
          animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}