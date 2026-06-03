"use client";

import { motion, useReducedMotion } from "motion/react";

/** An animated intelligence "link analysis" chart: a central target node with
 *  satellite collection sources, edges that draw themselves on, a rotating
 *  radar beam, data packets flowing outward along the wires, and nodes that
 *  glow and pulse like live signals. Purely decorative — drawn on the dossier. */

type Node = {
  id: string;
  label: string;
  x: number;
  y: number;
  r: number;
  core?: boolean;
};

const NODES: Node[] = [
  { id: "target", label: "TARGET", x: 300, y: 208, r: 30, core: true },
  { id: "jobs", label: "JOBS", x: 300, y: 52, r: 16 },
  { id: "dns", label: "DNS", x: 108, y: 96, r: 16 },
  { id: "subs", label: "SUBDOMAINS", x: 86, y: 256, r: 16 },
  { id: "github", label: "GITHUB", x: 168, y: 356, r: 16 },
  { id: "news", label: "NEWS", x: 470, y: 78, r: 16 },
  { id: "ma", label: "M&A", x: 522, y: 214, r: 16 },
  { id: "people", label: "PEOPLE", x: 452, y: 350, r: 16 },
];

const EDGES: [string, string][] = [
  ["target", "jobs"],
  ["target", "dns"],
  ["target", "subs"],
  ["target", "github"],
  ["target", "news"],
  ["target", "ma"],
  ["target", "people"],
  ["dns", "subs"],
  ["news", "ma"],
  ["github", "people"],
];

const byId = (id: string) => NODES.find((n) => n.id === id)!;
const TARGET = byId("target");
const BEAM_R = 168;

export function LinkGraph() {
  const reduced = useReducedMotion();
  const base = reduced ? 0 : 0.9;

  return (
    <svg
      viewBox="0 0 600 410"
      className="w-full h-auto overflow-visible"
      role="img"
      aria-label="Animated reconnaissance link-analysis chart connecting a target organization to public collection sources"
    >
      <defs>
        <radialGradient id="coreGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--color-stamp-red)" stopOpacity="0.3" />
          <stop offset="70%" stopColor="var(--color-stamp-red)" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="beamGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="var(--color-stamp-blue)" stopOpacity="0.32" />
          <stop offset="100%" stopColor="var(--color-stamp-blue)" stopOpacity="0" />
        </linearGradient>
        <filter id="nodeGlow" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="2.4" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* rotating radar beam emanating from the target */}
      {!reduced && (
        <motion.g
          style={{ transformOrigin: `${TARGET.x}px ${TARGET.y}px` }}
          initial={{ rotate: 0, opacity: 0 }}
          animate={{ rotate: 360, opacity: 1 }}
          transition={{
            rotate: { duration: 7, repeat: Infinity, ease: "linear" },
            opacity: { delay: base + 0.6, duration: 0.8 },
          }}
        >
          <polygon
            points={`${TARGET.x},${TARGET.y} ${TARGET.x + BEAM_R},${TARGET.y - 26} ${TARGET.x + BEAM_R},${TARGET.y + 8}`}
            fill="url(#beamGrad)"
          />
          <line
            x1={TARGET.x}
            y1={TARGET.y}
            x2={TARGET.x + BEAM_R}
            y2={TARGET.y}
            stroke="var(--color-stamp-blue)"
            strokeWidth={1}
            strokeOpacity={0.4}
          />
        </motion.g>
      )}

      {/* faint concentric range rings */}
      {[58, 104, 156].map((r, i) => (
        <motion.circle
          key={`ring-${r}`}
          cx={TARGET.x}
          cy={TARGET.y}
          r={r}
          fill="none"
          stroke="var(--color-rule)"
          strokeWidth={1}
          strokeDasharray="2 6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.55 }}
          transition={{ delay: base + 0.1 + i * 0.12, duration: 0.6 }}
        />
      ))}

      {/* edges draw themselves on */}
      {EDGES.map(([a, b], i) => {
        const na = byId(a);
        const nb = byId(b);
        const fromCore = a === "target";
        return (
          <motion.line
            key={`${a}-${b}`}
            x1={na.x}
            y1={na.y}
            x2={nb.x}
            y2={nb.y}
            stroke={fromCore ? "var(--color-stamp-blue)" : "var(--color-faded-ink)"}
            strokeWidth={fromCore ? 1.6 : 1}
            strokeOpacity={fromCore ? 0.6 : 0.35}
            initial={{ pathLength: reduced ? 1 : 0 }}
            animate={{ pathLength: 1 }}
            transition={{ delay: base + 0.5 + i * 0.14, duration: 0.7, ease: "easeInOut" }}
          />
        );
      })}

      {/* data packets flowing outward from the target along each spoke */}
      {!reduced &&
        EDGES.filter(([a]) => a === "target").map(([a, b], i) => {
          const na = byId(a);
          const nb = byId(b);
          return (
            <motion.circle
              key={`packet-${b}`}
              r={2.6}
              fill="var(--color-stamp-red)"
              filter="url(#nodeGlow)"
              initial={{ cx: na.x, cy: na.y, opacity: 0 }}
              animate={{
                cx: [na.x, nb.x],
                cy: [na.y, nb.y],
                opacity: [0, 1, 1, 0],
              }}
              transition={{
                duration: 1.6,
                repeat: Infinity,
                repeatDelay: 1.4,
                delay: base + 1.6 + i * 0.32,
                ease: "easeInOut",
              }}
            />
          );
        })}

      {/* nodes */}
      {NODES.map((n, i) => (
        <motion.g
          key={n.id}
          initial={{ opacity: reduced ? 1 : 0, scale: reduced ? 1 : 0.2 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{
            delay: base + (n.core ? 0.3 : 0.7 + i * 0.12),
            type: "spring",
            stiffness: 320,
            damping: 18,
          }}
          style={{ transformOrigin: `${n.x}px ${n.y}px` }}
        >
          {n.core && <circle cx={n.x} cy={n.y} r={70} fill="url(#coreGlow)" />}

          {!reduced && (
            <motion.circle
              cx={n.x}
              cy={n.y}
              r={n.r}
              fill="none"
              stroke={n.core ? "var(--color-stamp-red)" : "var(--color-stamp-blue)"}
              strokeWidth={1.2}
              initial={{ scale: 1, opacity: 0.5 }}
              animate={{ scale: [1, 2.1], opacity: [0.5, 0] }}
              transition={{
                delay: base + 1 + i * 0.18,
                duration: 2.4,
                repeat: Infinity,
                repeatDelay: n.core ? 0.4 : 1.6,
                ease: "easeOut",
              }}
              style={{ transformOrigin: `${n.x}px ${n.y}px` }}
            />
          )}

          <circle
            cx={n.x}
            cy={n.y}
            r={n.r}
            fill="var(--color-paper)"
            stroke={n.core ? "var(--color-stamp-red)" : "var(--color-ink)"}
            strokeWidth={n.core ? 2.4 : 1.6}
            filter={n.core ? "url(#nodeGlow)" : undefined}
          />
          <circle
            cx={n.x}
            cy={n.y}
            r={n.core ? 5 : 3}
            fill={n.core ? "var(--color-stamp-red)" : "var(--color-ink)"}
          />
          <text
            x={n.x}
            y={n.core ? n.y + n.r + 17 : n.y + n.r + 13}
            textAnchor="middle"
            className="select-none"
            style={{
              fontFamily: "var(--font-data)",
              fontSize: n.core ? 13 : 9.5,
              letterSpacing: "0.12em",
              fill: n.core ? "var(--color-ink)" : "var(--color-faded-ink)",
              fontWeight: n.core ? 600 : 400,
            }}
          >
            {n.label}
          </text>
        </motion.g>
      ))}
    </svg>
  );
}
