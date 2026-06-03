"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "motion/react";

/** A dark "collection console" shown while the dossier compiles. The real API
 *  returns everything at once, so this is an evocative boot sequence — sources
 *  light up one at a time — that runs until the results replace it. */

const SOURCES = [
  { id: "footprint", label: "DNS / footprint sweep", detail: "resolving + CT logs" },
  { id: "company", label: "Company profile", detail: "about / careers / press" },
  { id: "job", label: "Job-listing parse", detail: "stack extraction" },
  { id: "github", label: "GitHub footprint", detail: "org + languages" },
  { id: "news", label: "News & timeline", detail: "RSS + HN, 12-month window" },
  { id: "ma", label: "M&A / parent", detail: "wikipedia infobox" },
  { id: "business", label: "Industry classification", detail: "sector profiling" },
];

export function CompileSequence() {
  const reduced = useReducedMotion();
  const [active, setActive] = useState(reduced ? SOURCES.length : 0);

  useEffect(() => {
    if (reduced) return;
    const t = setInterval(
      () => setActive((n) => (n >= SOURCES.length ? n : n + 1)),
      560,
    );
    return () => clearInterval(t);
  }, [reduced]);

  return (
    <div className="console-panel mt-6" role="status" aria-label="Compiling dossier">
      <div className="console-scan" aria-hidden />
      <div className="console-bar">
        <span className="console-led" />
        COLLECTION CONSOLE — LIVE
        <span className="ml-auto opacity-60">iad1 · ephemeral</span>
      </div>

      <div className="console-body">
        {SOURCES.map((s, i) => {
          const status = i < active ? "done" : i === active ? "run" : "queued";
          return (
            <motion.div
              key={s.id}
              className={`console-row console-${status}`}
              initial={{ opacity: reduced ? 1 : 0, x: reduced ? 0 : -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: reduced ? 0 : i * 0.07, duration: 0.3 }}
            >
              <span className="console-glyph">
                {status === "done" ? "✓" : status === "run" ? "▸" : "·"}
              </span>
              <span className="console-label">{s.label}</span>
              <span className="console-dots" aria-hidden />
              <span className="console-detail">
                {status === "done"
                  ? "captured"
                  : status === "run"
                    ? "collecting…"
                    : "queued"}
              </span>
            </motion.div>
          );
        })}

        <div className="console-row console-cursor">
          <span className="console-glyph">$</span>
          <span className="console-label">
            {active >= SOURCES.length ? "compiling dossier" : "scanning public surface"}
          </span>
          <span className="console-blink">█</span>
        </div>
      </div>
    </div>
  );
}
