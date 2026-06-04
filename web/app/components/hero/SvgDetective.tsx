"use client";

import { motion, useReducedMotion } from "motion/react";

/** A hand-built noir-detective illustration. The eyes are deliberately shadowed
 *  under the hat brim (iconic detective, avoids the uncanny-face problem) with
 *  two bright glints. Animated with buttery, layered motion: a slow idle bob, a
 *  scanning sweep of the magnifying glass, a lens glint, an eye blink, a pulsing
 *  "clue" under the lens, and drifting dust motes. Honors reduced-motion. */
export function SvgDetective() {
  const reduced = useReducedMotion();
  const bob = reduced ? {} : { y: [0, -6, 0], rotate: [0, -0.8, 0] };
  const scan = reduced ? {} : { rotate: [-5, 7, -5] };

  return (
    <div className="svg-detective" aria-hidden>
      <svg viewBox="0 0 280 360" className="h-auto w-full overflow-visible">
        <defs>
          <linearGradient id="coat" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#322a20" />
            <stop offset="60%" stopColor="#241d15" />
            <stop offset="100%" stopColor="#16110b" />
          </linearGradient>
          <linearGradient id="coatDark" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#16110b" />
            <stop offset="100%" stopColor="#2c241a" />
          </linearGradient>
          <radialGradient id="lens" cx="38%" cy="32%" r="75%">
            <stop offset="0%" stopColor="#dff0f7" stopOpacity="0.85" />
            <stop offset="45%" stopColor="#9fc6da" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#37607a" stopOpacity="0.55" />
          </radialGradient>
          <radialGradient id="spot" cx="50%" cy="0%" r="90%">
            <stop offset="0%" stopColor="#fff1d4" stopOpacity="0.5" />
            <stop offset="60%" stopColor="#fff1d4" stopOpacity="0.06" />
            <stop offset="100%" stopColor="#fff1d4" stopOpacity="0" />
          </radialGradient>
          <clipPath id="lensClip">
            <circle cx="208" cy="206" r="23" />
          </clipPath>
        </defs>

        {/* interrogation spotlight */}
        <path d="M120 -20 L160 -20 L250 330 L30 330 Z" fill="url(#spot)" />

        {/* ground shadow */}
        <ellipse cx="140" cy="332" rx="78" ry="13" fill="#1a1612" opacity="0.16" />

        {/* drifting dust motes */}
        <g className="dust">
          <circle cx="70" cy="150" r="2.2" fill="#b8231a" />
          <circle cx="225" cy="120" r="1.8" fill="#1a3a5c" />
          <circle cx="60" cy="250" r="1.6" fill="#1a1612" />
          <circle cx="235" cy="270" r="2" fill="#b8231a" />
        </g>

        {/* ── the detective (idle bob) ── */}
        <motion.g
          animate={bob}
          transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
          style={{ transformOrigin: "140px 330px" }}
        >
          {/* back arm tucked into coat */}
          <path
            d="M112 168 C96 176 92 210 100 260 L126 256 C120 214 122 188 130 176 Z"
            fill="url(#coatDark)"
          />

          {/* coat body */}
          <path
            d="M104 166 C104 152 118 146 140 146 C162 146 176 152 176 166
               L192 300 C193 312 186 318 176 318 L104 318 C94 318 87 312 88 300 Z"
            fill="url(#coat)"
          />
          {/* coat form-shadow (left) */}
          <path
            d="M104 166 C104 152 118 146 140 146 L140 318 L104 318 C94 318 87 312 88 300 Z"
            fill="#000"
            opacity="0.16"
          />
          {/* lapels / open collar V */}
          <path d="M140 150 L120 168 L132 250 L140 250 Z" fill="#16110b" />
          <path d="M140 150 L160 168 L148 250 L140 250 Z" fill="#241d15" />
          {/* center buttons */}
          <circle cx="140" cy="206" r="2.6" fill="#caa64a" />
          <circle cx="140" cy="232" r="2.6" fill="#caa64a" />
          <circle cx="140" cy="258" r="2.6" fill="#caa64a" />

          {/* belt */}
          <rect x="96" y="248" width="88" height="13" rx="3" fill="#16110b" />
          <rect x="132" y="249" width="16" height="11" rx="2" fill="#b8231a" />

          {/* shoes */}
          <path d="M118 316 q-4 12 8 13 q12 1 12 -7 l0 -6 Z" fill="#16110b" />
          <path d="M162 316 q4 12 -8 13 q-12 1 -12 -7 l0 -6 Z" fill="#16110b" />

          {/* popped collar */}
          <path d="M118 150 L138 150 L130 132 Z" fill="#2c241a" />
          <path d="M162 150 L142 150 L150 132 Z" fill="#2c241a" />
          {/* red scarf */}
          <path d="M124 146 q16 12 32 0 l0 10 q-16 11 -32 0 Z" fill="#b8231a" />
          <path d="M150 152 l10 26 l-7 3 l-8 -25 Z" fill="#9c1d15" />

          {/* head */}
          <ellipse cx="140" cy="119" rx="23" ry="25" fill="#e7d0aa" />
          {/* soft form-shadow on the left cheek */}
          <path d="M117 119 q0 17 12 22 q-12 -2 -15 -14 Z" fill="#16110b" opacity="0.12" />
          {/* warm rim light on the right cheek */}
          <path d="M163 119 q0 14 -9 20 q9 -1 13 -11 Z" fill="#fff1d4" opacity="0.35" />
          {/* brim shadow over the eyes (the noir trick) */}
          <path d="M116 114 q24 14 48 0 l0 -15 q-24 -9 -48 0 Z" fill="#241a0f" opacity="0.92" />
          {/* glinting eyes */}
          <g className="eyes">
            <rect x="128" y="110" width="6" height="3" rx="1.5" fill="#fff4dc" />
            <rect x="147" y="110" width="6" height="3" rx="1.5" fill="#fff4dc" />
          </g>
          {/* subtle confident smile */}
          <path d="M133 130 q7 4.5 14 0" stroke="#9a7c4c" strokeWidth="2" fill="none" strokeLinecap="round" />

          {/* fedora */}
          <path d="M104 104 q36 22 72 0 q-6 -12 -36 -12 q-30 0 -36 12 Z" fill="#16110b" />
          <path d="M118 96 q22 -8 44 0 l-6 -34 q-16 -6 -32 0 Z" fill="#1d160e" />
          <path d="M118 96 q22 10 44 0 l-2 -9 q-20 9 -40 0 Z" fill="#b8231a" />
          {/* hat dent highlight */}
          <path d="M134 64 q6 -3 12 0 l-1 8 q-5 -2 -10 0 Z" fill="#2c2114" opacity="0.7" />
          {/* warm top-light sheen on hat + shoulders for form */}
          <path d="M122 70 q18 -7 36 0" stroke="#4a3a26" strokeWidth="2" fill="none" opacity="0.6" strokeLinecap="round" />
          <path d="M110 163 q30 -12 60 0" stroke="#3d3122" strokeWidth="2.4" fill="none" opacity="0.5" strokeLinecap="round" />

          {/* ── scanning arm + magnifier ── */}
          <motion.g
            animate={scan}
            transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut" }}
            style={{ transformOrigin: "172px 170px" }}
          >
            {/* sleeve */}
            <path
              d="M168 162 C188 162 206 176 206 196 L188 206 C184 190 176 180 162 180 Z"
              fill="url(#coat)"
            />
            {/* cuff + hand */}
            <rect x="184" y="196" width="20" height="12" rx="4" transform="rotate(34 194 202)" fill="#16110b" />
            <circle cx="196" cy="216" r="8" fill="#e6cfa8" />

            {/* magnifier handle */}
            <line x1="198" y1="222" x2="180" y2="240" stroke="#7a5a32" strokeWidth="7" strokeLinecap="round" />
            <line x1="198" y1="222" x2="180" y2="240" stroke="#caa64a" strokeWidth="3" strokeLinecap="round" />

            {/* lens */}
            <circle cx="208" cy="206" r="23" fill="url(#lens)" />
            {/* magnified clue: a little fingerprint */}
            <g clipPath="url(#lensClip)" className="clue">
              <g fill="none" stroke="#1a3a5c" strokeWidth="1.4" opacity="0.7">
                <path d="M200 214 q8 -12 18 -2" />
                <path d="M201 209 q9 -12 17 -1" />
                <path d="M203 204 q7 -9 14 -1" />
                <path d="M205 199 q5 -6 10 0" />
              </g>
            </g>
            {/* lens glint sweep */}
            <g clipPath="url(#lensClip)">
              <rect className="lens-glint" x="176" y="180" width="14" height="60" rx="6" fill="#ffffff" opacity="0.5" transform="rotate(28 208 206)" />
            </g>
            {/* brass ring */}
            <circle cx="208" cy="206" r="23" fill="none" stroke="#3a2c1c" strokeWidth="9" />
            <circle cx="208" cy="206" r="23" fill="none" stroke="#caa64a" strokeWidth="4.5" />
            <circle cx="208" cy="206" r="23" fill="none" stroke="#e9d49a" strokeWidth="1.4" />
          </motion.g>
        </motion.g>
      </svg>
    </div>
  );
}
