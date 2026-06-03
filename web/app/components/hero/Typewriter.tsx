"use client";

import { useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";

type Props = {
  text: string;
  /** ms per character */
  speed?: number;
  /** ms before typing begins */
  startDelay?: number;
  className?: string;
  /** show the blinking block cursor while typing (and briefly after) */
  cursor?: boolean;
  onDone?: () => void;
};

/**
 * Types `text` out one character at a time. Honors prefers-reduced-motion by
 * rendering the full string immediately. The label is always present for
 * screen readers via aria-label, so the animation is purely decorative.
 */
export function Typewriter({
  text,
  speed = 52,
  startDelay = 0,
  className,
  cursor = true,
  onDone,
}: Props) {
  const reduced = useReducedMotion();
  const [shown, setShown] = useState(reduced ? text.length : 0);
  const [started, setStarted] = useState(startDelay === 0);

  useEffect(() => {
    if (reduced || started) return;
    const t = setTimeout(() => setStarted(true), startDelay);
    return () => clearTimeout(t);
  }, [reduced, started, startDelay]);

  useEffect(() => {
    if (reduced || !started || shown >= text.length) {
      if (shown >= text.length) onDone?.();
      return;
    }
    const t = setTimeout(() => setShown((n) => n + 1), speed);
    return () => clearTimeout(t);
  }, [reduced, started, shown, text.length, speed, onDone]);

  const typing = shown < text.length;

  return (
    <span className={className} aria-label={text}>
      <span aria-hidden>{text.slice(0, shown)}</span>
      {cursor && (
        <span
          aria-hidden
          className="tw-cursor"
          style={{ opacity: typing || !reduced ? 1 : 0 }}
        >
          ▍
        </span>
      )}
    </span>
  );
}
