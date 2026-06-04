"use client";

import { useCallback, useRef, useState } from "react";

/** Hidden "intelligence" scattered across the hero that only becomes visible
 *  inside a magnifier lens following the cursor — drag the lens to decrypt it.
 *  Implemented with a CSS radial mask (GPU-cheap, no per-frame clip math). */

const GLYPHS: { x: string; y: string; t: string }[] = [
  { x: "13%", y: "22%", t: "lat 40.71°N · lon 74.00°W" },
  { x: "80%", y: "15%", t: "sha256:9f2a…e41c" },
  { x: "32%", y: "72%", t: "ASN AS13335" },
  { x: "67%", y: "80%", t: "CT-LOG ▸ +31 subdomains" },
  { x: "49%", y: "38%", t: "// ACCESS GRANTED" },
  { x: "19%", y: "52%", t: "104.18.x.x" },
  { x: "85%", y: "58%", t: "MX ▸ mimecast" },
  { x: "9%", y: "85%", t: "spf ✓  dmarc ✓  dkim ✓" },
  { x: "58%", y: "60%", t: "TLS ▸ ECDSA P-256" },
  { x: "40%", y: "12%", t: "whois ▸ redacted" },
];

export function ScanLens({ children }: { children: React.ReactNode }) {
  const host = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);

  const onMove = useCallback((e: React.PointerEvent) => {
    const el = host.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setPos({ x: e.clientX - r.left, y: e.clientY - r.top });
  }, []);

  return (
    <div
      ref={host}
      className="scan-host"
      data-lens={pos ? "on" : "off"}
      onPointerMove={onMove}
      onPointerLeave={() => setPos(null)}
      style={
        pos
          ? ({ "--lx": `${pos.x}px`, "--ly": `${pos.y}px` } as React.CSSProperties)
          : undefined
      }
    >
      {children}

      {/* the decrypted-intel layer, masked to the lens circle */}
      <div className="scan-reveal" aria-hidden>
        {GLYPHS.map((g, i) => (
          <span key={i} className="scan-glyph" style={{ left: g.x, top: g.y }}>
            {g.t}
          </span>
        ))}
        <svg className="scan-print" viewBox="0 0 44 44" aria-hidden>
          <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
            <path d="M10 30 Q22 8 34 26" />
            <path d="M12 24 Q22 6 32 22" />
            <path d="M14 19 Q22 8 30 18" />
            <path d="M16 15 Q22 9 28 15" />
            <path d="M19 13 Q22 11 25 13" />
          </g>
        </svg>
      </div>

      {/* the magnifier ring tracking the cursor */}
      <div className="scan-ring" aria-hidden />
    </div>
  );
}
