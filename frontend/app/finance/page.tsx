"use client";

import { useState } from "react";
import ExpenseInput from "@/components/finance/ExpenseInput";
import SpendingChart from "@/components/finance/SpendingChart";
import ExpenseFeed from "@/components/finance/ExpenseFeed";
import GmailSyncButton from "@/components/finance/GmailSyncButton";

export default function FinancePage() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSaved = () => setRefreshKey((k) => k + 1);

  return (
    <main className="finance-root">
      <div className="finance-header">
        <div className="header-left">
          <span className="header-label">SAARTHI / FINANCE</span>
          <h1 className="header-title">Expense Ledger</h1>
        </div>
        <div className="header-right">
          <GmailSyncButton onSynced={handleSaved} />
        </div>
      </div>

      <div className="finance-grid">
        {/* Left column: input + feed */}
        <div className="col-left">
          <ExpenseInput onSaved={handleSaved} />
          <ExpenseFeed refreshKey={refreshKey} />
        </div>

        {/* Right column: chart */}
        <div className="col-right">
          <SpendingChart refreshKey={refreshKey} />
        </div>
      </div>

      <style jsx>{`
        .finance-root {
          min-height: 100vh;
          background: #0a0a0a;
          color: #e8e8e0;
          font-family: "IBM Plex Mono", "Courier New", monospace;
          padding: 0 0 4rem 0;
        }

        .finance-header {
          display: flex;
          align-items: flex-end;
          justify-content: space-between;
          padding: 2.5rem 2.5rem 1.5rem;
          border-bottom: 1px solid #1e1e1e;
          background: #0a0a0a;
          position: sticky;
          top: 0;
          z-index: 10;
        }

        .header-label {
          display: block;
          font-size: 0.65rem;
          letter-spacing: 0.2em;
          color: #3a3a3a;
          margin-bottom: 0.4rem;
        }

        .header-title {
          font-size: 1.6rem;
          font-weight: 400;
          letter-spacing: -0.02em;
          color: #e8e8e0;
          margin: 0;
        }

        .finance-grid {
          display: grid;
          grid-template-columns: 1fr 1.2fr;
          gap: 0;
          min-height: calc(100vh - 100px);
        }

        .col-left {
          border-right: 1px solid #1a1a1a;
          padding: 2rem 2.5rem;
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .col-right {
          padding: 2rem 2.5rem;
        }

        @media (max-width: 900px) {
          .finance-grid {
            grid-template-columns: 1fr;
          }
          .col-left {
            border-right: none;
            border-bottom: 1px solid #1a1a1a;
          }
        }
      `}</style>
    </main>
  );
}