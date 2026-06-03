"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

const LINES = [
  "establishing secure channel ............ OK",
  "authenticating field operative ......... OK",
  "mounting collection modules [7] ........ OK",
  "decrypting dossier template ............ OK",
  "tradecraft online — awaiting target.",
];

/** A one-time cinematic boot overlay. Types a few "secure terminal" lines,
 *  fills a progress bar, then dissolves to reveal the site. Shows once per
 *  browser session and never under prefers-reduced-motion. */
export function BootIntro() {
  const reduced = useReducedMotion();
  const [show, setShow] = useState(false);
  const [n, setN] = useState(0);

  useEffect(() => {
    if (reduced) return;
    try {
      if (sessionStorage.getItem("tc_booted")) return;
      sessionStorage.setItem("tc_booted", "1");
    } catch {
      /* sessionStorage unavailable — just show once this mount */
    }
    setShow(true);
  }, [reduced]);

  useEffect(() => {
    if (!show) return;
    if (n >= LINES.length) {
      const t = setTimeout(() => setShow(false), 600);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setN((v) => v + 1), 340);
    return () => clearTimeout(t);
  }, [show, n]);

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="boot-overlay"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, filter: "blur(8px)", scale: 1.03 }}
          transition={{ duration: 0.6, ease: "easeInOut" }}
        >
          <div className="boot-scan" aria-hidden />
          <div className="boot-term">
            <div className="boot-bar">
              <span className="hero-dot" />
              TRADECRAFT // SECURE TERMINAL
              <span className="ml-auto opacity-60">iad1</span>
            </div>
            <div className="boot-lines">
              {LINES.slice(0, n).map((l, i) => (
                <motion.div
                  key={i}
                  className="boot-line"
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <span className="boot-prompt">▸</span> {l}
                </motion.div>
              ))}
              {n < LINES.length && (
                <div className="boot-line">
                  <span className="boot-prompt">▸</span>{" "}
                  <span className="console-blink">█</span>
                </div>
              )}
            </div>
            <div className="boot-progress">
              <motion.div
                className="boot-progress-fill"
                initial={{ width: "0%" }}
                animate={{ width: `${(n / LINES.length) * 100}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
