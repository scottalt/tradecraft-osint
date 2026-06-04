"use client";

import { motion, useReducedMotion } from "motion/react";

/** A detective's case board: pinned index cards around a redacted SUBJECT,
 *  wired together with red string (this IS the link-analysis), worked by a
 *  noir-detective silhouette who points out a connection. One cohesive SVG so
 *  the whole scene is composed and animated together. */

type Card = { id: string; label: string; x: number; y: number; rot: number; accent?: string };

const W = 60;
const H = 44;

const CARDS: Card[] = [
  { id: "dns", label: "DNS · MX", x: 70, y: 58, rot: 4 },
  { id: "news", label: "NEWS", x: 352, y: 50, rot: -5, accent: "var(--color-stamp-red)" },
  { id: "github", label: "GITHUB", x: 60, y: 232, rot: -3 },
  { id: "ma", label: "M&A", x: 372, y: 168, rot: 5 },
  { id: "jobs", label: "JOB REQ", x: 344, y: 274, rot: -4 },
  { id: "people", label: "PEOPLE", x: 150, y: 286, rot: 3, accent: "var(--color-stamp-blue)" },
];

// SUBJECT polaroid (the second "character" — a redacted person of interest)
const SUBJ = { x: 206, y: 120, w: 76, h: 96, rot: -3 };
const subjPin = { x: SUBJ.x + SUBJ.w / 2, y: SUBJ.y + 8 };

const pinOf = (c: Card) => ({ x: c.x + W / 2, y: c.y + 7 });
const cardCenter = (c: Card) => ({ x: c.x + W / 2, y: c.y + H / 2 });

/** sagging-string path between two pins */
function stringD(a: { x: number; y: number }, b: { x: number; y: number }) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2 + 16;
  return `M${a.x} ${a.y} Q${mx} ${my} ${b.x} ${b.y}`;
}

export function CaseBoard() {
  const reduced = useReducedMotion();
  const d0 = reduced ? 0 : 1;

  return (
    <svg
      viewBox="0 0 460 384"
      className="case-board h-auto w-full overflow-visible"
      role="img"
      aria-label="A detective's evidence board linking a redacted subject to public collection sources with red string"
    >
      <defs>
        <filter id="cork">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" result="n" />
          <feColorMatrix in="n" values="0 0 0 0 0.45  0 0 0 0 0.36  0 0 0 0 0.22  0 0 0 0.5 0" />
        </filter>
        <linearGradient id="wood" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#4a3420" />
          <stop offset="100%" stopColor="#2c1e10" />
        </linearGradient>
        <radialGradient id="lamp" cx="50%" cy="34%" r="62%">
          <stop offset="0%" stopColor="#fff3d6" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#fff3d6" stopOpacity="0" />
        </radialGradient>
        <filter id="soft" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="2" stdDeviation="2.2" floodColor="#1a1206" floodOpacity="0.4" />
        </filter>
      </defs>

      {/* wood frame + cork */}
      <rect x="8" y="8" width="444" height="368" rx="10" fill="url(#wood)" />
      <rect x="8" y="8" width="444" height="368" rx="10" fill="none" stroke="#1c1208" strokeWidth="2" />
      <rect x="20" y="20" width="420" height="344" rx="4" fill="#bda06a" />
      <rect x="20" y="20" width="420" height="344" rx="4" fill="#000" filter="url(#cork)" opacity="0.4" />
      {/* desk-lamp pool */}
      <ellipse cx="232" cy="150" rx="220" ry="170" fill="url(#lamp)" />

      {/* ── red string (drawn after the cards land) ── */}
      <g>
        {CARDS.map((c, i) => {
          const p = pinOf(c);
          return (
            <motion.path
              key={`s-${c.id}`}
              d={stringD(subjPin, p)}
              fill="none"
              stroke="#9c1d15"
              strokeWidth={1.6}
              strokeLinecap="round"
              initial={{ pathLength: reduced ? 1 : 0, opacity: reduced ? 0.85 : 0 }}
              animate={{ pathLength: 1, opacity: 0.85 }}
              transition={{ delay: d0 + 1.0 + i * 0.16, duration: 0.6, ease: "easeInOut" }}
            />
          );
        })}

        {/* a "connection found" pulse travelling a couple of strings */}
        {!reduced &&
          [CARDS[1], CARDS[3]].map((c, i) => (
            <circle key={`pulse-${c.id}`} r="3" fill="#ffd9a0">
              <animateMotion
                dur="2.6s"
                begin={`${2.2 + i * 1.1}s`}
                repeatCount="indefinite"
                path={stringD(subjPin, pinOf(c))}
                keyPoints="0;1"
                keyTimes="0;1"
                calcMode="linear"
              />
              <animate
                attributeName="opacity"
                dur="2.6s"
                begin={`${2.2 + i * 1.1}s`}
                values="0;1;1;0"
                repeatCount="indefinite"
              />
            </circle>
          ))}
      </g>

      {/* ── satellite cards ── */}
      {CARDS.map((c, i) => {
        const ctr = cardCenter(c);
        const pin = pinOf(c);
        return (
          <motion.g
            key={c.id}
            initial={{ opacity: reduced ? 1 : 0, scale: reduced ? 1 : 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: d0 + 0.2 + i * 0.12, type: "spring", stiffness: 300, damping: 18 }}
            style={{ transformOrigin: `${ctr.x}px ${ctr.y}px` }}
          >
            <g transform={`rotate(${c.rot} ${ctr.x} ${ctr.y})`} filter="url(#soft)">
              <rect x={c.x} y={c.y} width={W} height={H} rx="2" fill="#f3ead4" />
              <rect x={c.x} y={c.y} width={W} height="9" fill={c.accent ?? "#d8cbb0"} opacity={c.accent ? 0.85 : 1} />
              <text
                x={ctr.x}
                y={c.y + 26}
                textAnchor="middle"
                style={{ fontFamily: "var(--font-data)", fontSize: 9, letterSpacing: "0.06em", fill: "#2c2418", fontWeight: 600 }}
              >
                {c.label}
              </text>
              {/* faux redacted data lines */}
              <rect x={c.x + 8} y={c.y + 31} width={W - 30} height="2.4" rx="1" fill="#2c2418" opacity="0.45" />
              <rect x={c.x + 8} y={c.y + 36} width={W - 18} height="2.4" rx="1" fill="#2c2418" opacity="0.3" />
            </g>
            {/* pin */}
            <circle cx={pin.x} cy={pin.y} r="4.6" fill={c.accent ?? "#b8231a"} />
            <circle cx={pin.x - 1.3} cy={pin.y - 1.3} r="1.5" fill="#fff" opacity="0.8" />
          </motion.g>
        );
      })}

      {/* ── SUBJECT polaroid ── */}
      <motion.g
        initial={{ opacity: reduced ? 1 : 0, scale: reduced ? 1 : 0.5, y: reduced ? 0 : -10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ delay: d0 + 0.05, type: "spring", stiffness: 240, damping: 16 }}
        style={{ transformOrigin: `${SUBJ.x + SUBJ.w / 2}px ${SUBJ.y + SUBJ.h / 2}px` }}
      >
        <g transform={`rotate(${SUBJ.rot} ${SUBJ.x + SUBJ.w / 2} ${SUBJ.y + SUBJ.h / 2})`} filter="url(#soft)">
          <rect x={SUBJ.x} y={SUBJ.y} width={SUBJ.w} height={SUBJ.h} rx="2" fill="#f7f0dd" />
          {/* photo area */}
          <rect x={SUBJ.x + 6} y={SUBJ.y + 6} width={SUBJ.w - 12} height={SUBJ.h - 30} fill="#26303a" />
          {/* redacted silhouette head + shoulders */}
          <circle cx={SUBJ.x + SUBJ.w / 2} cy={SUBJ.y + 30} r="13" fill="#11181f" />
          <path d={`M${SUBJ.x + 16} ${SUBJ.y + 64} q${SUBJ.w / 2 - 16} -26 ${SUBJ.w - 32} 0 Z`} fill="#11181f" />
          {/* redaction bar over the eyes */}
          <rect x={SUBJ.x + 18} y={SUBJ.y + 24} width={SUBJ.w - 36} height="7" fill="#0b0f13" />
          {/* caption */}
          <text
            x={SUBJ.x + SUBJ.w / 2}
            y={SUBJ.y + SUBJ.h - 9}
            textAnchor="middle"
            style={{ fontFamily: "var(--font-typewriter)", fontSize: 10, letterSpacing: "0.14em", fill: "#1a1612" }}
          >
            SUBJECT
          </text>
        </g>
        {/* subject pin */}
        <circle cx={subjPin.x} cy={subjPin.y} r="5.4" fill="#b8231a" />
        <circle cx={subjPin.x - 1.6} cy={subjPin.y - 1.6} r="1.8" fill="#fff" opacity="0.85" />
        {/* CLASSIFIED stamp thuds onto the photo */}
        <motion.g
          initial={reduced ? { opacity: 1, scale: 1, rotate: -12 } : { opacity: 0, scale: 1.8, rotate: -30 }}
          animate={{ opacity: 0.9, scale: 1, rotate: -12 }}
          transition={{ delay: d0 + 0.7, type: "spring", stiffness: 260, damping: 11 }}
          style={{ transformOrigin: `${SUBJ.x + SUBJ.w / 2}px ${SUBJ.y + 44}px` }}
        >
          <rect
            x={SUBJ.x + 6}
            y={SUBJ.y + 36}
            width={SUBJ.w - 12}
            height="17"
            rx="2"
            fill="none"
            stroke="var(--color-stamp-red)"
            strokeWidth="2"
          />
          <text
            x={SUBJ.x + SUBJ.w / 2}
            y={SUBJ.y + 48}
            textAnchor="middle"
            style={{ fontFamily: "var(--font-typewriter)", fontSize: 9, letterSpacing: "0.1em", fill: "var(--color-stamp-red)" }}
          >
            CLASSIFIED
          </text>
        </motion.g>
      </motion.g>

      {/* ── detective silhouette working the board ── */}
      <motion.g
        initial={{ opacity: reduced ? 1 : 0, x: reduced ? 0 : -12 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: d0 + 0.3, duration: 0.7, ease: "easeOut" }}
      >
        <motion.g
          animate={reduced ? {} : { y: [0, -3, 0] }}
          transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
        >
          {/* coat */}
          <path d="M2 384 C-2 320 2 250 26 244 C50 250 54 320 50 384 Z" fill="#15110a" />
          <path d="M26 244 C18 244 12 252 12 268 L8 384 L26 384 Z" fill="#000" opacity="0.3" />
          {/* head + fedora */}
          <circle cx="26" cy="232" r="15" fill="#120e08" />
          <path d="M6 222 q20 13 40 0 q-4 -8 -20 -8 q-16 0 -20 8 Z" fill="#0d0a05" />
          <path d="M14 216 q12 -5 24 0 l-3 -19 q-9 -4 -18 0 Z" fill="#120d07" />
          <path d="M14 216 q12 6 24 0 l-1 -5 q-11 5 -22 0 Z" fill="var(--color-stamp-red)" opacity="0.85" />
          {/* warm rim light on the right edge */}
          <path d="M40 250 q12 50 8 130" stroke="#5a4326" strokeWidth="2.4" fill="none" opacity="0.55" strokeLinecap="round" />
          {/* pointing arm raised toward the board */}
          <path d="M42 262 C70 252 96 232 120 214 L126 226 C104 246 78 268 50 280 Z" fill="#15110a" />
          {/* hand + pointing finger */}
          <circle cx="122" cy="219" r="7" fill="#120e08" />
          <path d="M126 214 l16 -9 l3 5 l-16 9 Z" fill="#1a140c" />
        </motion.g>
      </motion.g>
    </svg>
  );
}
