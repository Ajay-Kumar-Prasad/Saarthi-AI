"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "bot";
  text: string;
  ts: string;
}

export default function ExpenseInput({ onSaved }: { onSaved: () => void }) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "bot",
      text: 'Log expenses in plain English. Try "spent 450 on lunch" or "ask for weekly summary".',
      ts: now(),
    },
  ]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: msg, ts: now() }]);
    setLoading(true);

    try {
      const res = await fetch("/api/finance/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });
      const data = await res.json();
      setMessages((m) => [...m, { role: "bot", text: data.reply, ts: now() }]);

      // Trigger parent refresh if it looks like a save action
      if (data.reply?.includes("Saved")) onSaved();
    } catch {
      setMessages((m) => [
        ...m,
        { role: "bot", text: "⚠ Connection error. Try again.", ts: now() },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <section className="input-section">
      <div className="section-label">// CHAT INTERFACE</div>

      <div className="message-list">
        {messages.map((m, i) => (
          <div key={i} className={`message message-${m.role}`}>
            <span className="message-prefix">
              {m.role === "user" ? "> " : "$ "}
            </span>
            <span className="message-text">{m.text}</span>
            <span className="message-ts">{m.ts}</span>
          </div>
        ))}
        {loading && (
          <div className="message message-bot">
            <span className="message-prefix">$ </span>
            <span className="blink">processing_</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="input-row">
        <span className="prompt-arrow">›</span>
        <input
          className="text-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="spent 200 on groceries..."
          autoComplete="off"
          spellCheck={false}
        />
        <button className="send-btn" onClick={send} disabled={loading}>
          {loading ? "…" : "RUN"}
        </button>
      </div>

      <style jsx>{`
        .input-section {
          display: flex;
          flex-direction: column;
          gap: 0;
        }

        .section-label {
          font-size: 0.6rem;
          letter-spacing: 0.15em;
          color: #2e2e2e;
          margin-bottom: 0.75rem;
        }

        .message-list {
          background: #0d0d0d;
          border: 1px solid #1a1a1a;
          border-radius: 2px;
          padding: 1rem;
          min-height: 200px;
          max-height: 280px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 0.6rem;
          scrollbar-width: thin;
          scrollbar-color: #1e1e1e #0d0d0d;
        }

        .message {
          display: flex;
          align-items: baseline;
          gap: 0.4rem;
          font-size: 0.8rem;
          line-height: 1.5;
          flex-wrap: wrap;
        }

        .message-user .message-prefix { color: #4ade80; }
        .message-user .message-text   { color: #c8c8c0; }
        .message-bot  .message-prefix { color: #f59e0b; }
        .message-bot  .message-text   { color: #9ca3af; white-space: pre-line; }

        .message-ts {
          font-size: 0.55rem;
          color: #2a2a2a;
          margin-left: auto;
          flex-shrink: 0;
        }

        .blink {
          color: #f59e0b;
          animation: blink 1s step-start infinite;
        }

        @keyframes blink {
          50% { opacity: 0; }
        }

        .input-row {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          border: 1px solid #1a1a1a;
          border-top: none;
          background: #0d0d0d;
          padding: 0.6rem 0.75rem;
        }

        .prompt-arrow {
          color: #4ade80;
          font-size: 1rem;
          line-height: 1;
          flex-shrink: 0;
        }

        .text-input {
          flex: 1;
          background: transparent;
          border: none;
          outline: none;
          color: #e8e8e0;
          font-family: "IBM Plex Mono", monospace;
          font-size: 0.8rem;
          caret-color: #4ade80;
        }

        .text-input::placeholder { color: #2e2e2e; }

        .send-btn {
          background: transparent;
          border: 1px solid #1e1e1e;
          color: #4ade80;
          font-family: "IBM Plex Mono", monospace;
          font-size: 0.65rem;
          letter-spacing: 0.1em;
          padding: 0.3rem 0.6rem;
          cursor: pointer;
          transition: border-color 0.15s, background 0.15s;
        }

        .send-btn:hover:not(:disabled) {
          border-color: #4ade80;
          background: rgba(74, 222, 128, 0.05);
        }

        .send-btn:disabled { opacity: 0.3; cursor: default; }
      `}</style>
    </section>
  );
}

function now() {
  return new Date().toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}