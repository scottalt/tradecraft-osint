"use client";

import type { ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";

/** Wraps a block of content with a black redaction bar that wipes away to
 *  "declassify" it. Used to reveal each interview question in sequence. */
export function RedactionReveal({
  children,
  index = 0,
}: {
  children: ReactNode;
  index?: number;
}) {
  const reduced = useReducedMotion();
  return (
    <div className="redaction-wrap">
      {children}
      {!reduced && (
        <motion.div
          className="redaction-cover"
          aria-hidden
          initial={{ scaleX: 1 }}
          whileInView={{ scaleX: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{
            delay: 0.12 + index * 0.13,
            duration: 0.5,
            ease: [0.7, 0, 0.2, 1],
          }}
          style={{ transformOrigin: "right" }}
        />
      )}
    </div>
  );
}
