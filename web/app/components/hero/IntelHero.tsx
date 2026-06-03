"use client";

import { motion, useReducedMotion } from "motion/react";
import { LinkGraph } from "./LinkGraph";
import { Typewriter } from "./Typewriter";

export function IntelHero() {
  const reduced = useReducedMotion();

  return (
    <section className="hero-frame relative overflow-hidden border-2 border-ink mb-12">
      {/* slow radar sweep behind everything */}
      {!reduced && <div className="hero-radar" aria-hidden />}
      {/* scanline overlay */}
      <div className="hero-scan" aria-hidden />

      {/* top classification strip */}
      <div className="relative z-10 flex items-center justify-between border-b border-ink/30 px-5 py-2 font-data text-[10px] tracking-[0.25em] text-faded-ink">
        <span>FILE NO. 0001-A</span>
        <motion.span
          initial={{ opacity: reduced ? 1 : 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="flex items-center gap-2"
        >
          <span className="hero-dot" /> LIVE COLLECTION
        </motion.span>
        <span>CLASSIFICATION: PUBLIC</span>
      </div>

      <div className="relative z-10 grid gap-6 px-6 py-8 md:grid-cols-[1.05fr_1fr] md:px-8 md:py-10">
        {/* left: title block */}
        <div className="flex flex-col justify-center">
          <p className="font-data text-[11px] tracking-[0.3em] text-stamp-red mb-3">
            ▸ OSINT FIELD UNIT
          </p>

          <h1 className="font-typewriter text-6xl md:text-7xl leading-[0.95] text-ink">
            <Typewriter text="tradecraft" speed={70} startDelay={250} />
          </h1>

          <p className="font-prose italic text-faded-ink text-lg mt-4 max-w-md">
            <Typewriter
              text="Recon your future employer before the interview."
              speed={22}
              startDelay={1100}
              cursor={false}
            />
          </p>

          {/* DECLASSIFIED stamp thuds in */}
          <motion.div
            className="mt-7 self-start"
            initial={
              reduced
                ? { opacity: 1, scale: 1, rotate: -5 }
                : { opacity: 0, scale: 1.9, rotate: -22 }
            }
            animate={{ opacity: 1, scale: 1, rotate: -5 }}
            transition={{ delay: 2.0, type: "spring", stiffness: 260, damping: 12 }}
          >
            <span className="declassified-stamp">DECLASSIFIED</span>
          </motion.div>
        </div>

        {/* right: animated link-analysis graph */}
        <div className="flex items-center justify-center">
          <LinkGraph />
        </div>
      </div>
    </section>
  );
}
