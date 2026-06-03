"use client";

import { useEffect, useRef } from "react";

/** A live canvas "intelligence field": drifting nodes wired together by
 *  proximity, with the cursor acting as an active probe that lights up and
 *  links nearby nodes. Sits fixed behind the whole page as atmosphere. */
export function IntelField() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    let w = 0;
    let h = 0;
    let raf = 0;
    let nodes: { x: number; y: number; vx: number; vy: number; p: number }[] = [];
    const mouse = { x: -9999, y: -9999 };

    function resize() {
      const c = canvas!;
      w = c.clientWidth;
      h = c.clientHeight;
      c.width = Math.floor(w * dpr);
      c.height = Math.floor(h * dpr);
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.max(24, Math.min(90, Math.floor((w * h) / 15000)));
      nodes = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.22,
        vy: (Math.random() - 0.5) * 0.22,
        p: Math.random() * Math.PI * 2,
      }));
    }

    function draw() {
      const g = ctx!;
      g.clearRect(0, 0, w, h);

      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        n.p += 0.02;
        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;
      }

      // proximity edges
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.hypot(dx, dy);
          if (d < 118) {
            g.strokeStyle = `rgba(26,58,92,${(1 - d / 118) * 0.13})`;
            g.lineWidth = 1;
            g.beginPath();
            g.moveTo(a.x, a.y);
            g.lineTo(b.x, b.y);
            g.stroke();
          }
        }
      }

      // nodes + cursor probe
      for (const n of nodes) {
        const dm = Math.hypot(n.x - mouse.x, n.y - mouse.y);
        const near = dm < 170;
        const tw = 1.5 + Math.sin(n.p) * 0.5;
        g.fillStyle = near ? "rgba(184,35,26,0.7)" : "rgba(26,22,18,0.3)";
        g.beginPath();
        g.arc(n.x, n.y, near ? 2.6 : tw, 0, Math.PI * 2);
        g.fill();
        if (near) {
          g.strokeStyle = `rgba(184,35,26,${(1 - dm / 170) * 0.45})`;
          g.lineWidth = 1;
          g.beginPath();
          g.moveTo(n.x, n.y);
          g.lineTo(mouse.x, mouse.y);
          g.stroke();
        }
      }

      raf = requestAnimationFrame(draw);
    }

    function onMove(e: PointerEvent) {
      const r = canvas!.getBoundingClientRect();
      mouse.x = e.clientX - r.left;
      mouse.y = e.clientY - r.top;
    }
    function onLeave() {
      mouse.x = -9999;
      mouse.y = -9999;
    }

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerleave", onLeave);

    if (reduced) {
      draw();
      cancelAnimationFrame(raf);
    } else {
      raf = requestAnimationFrame(draw);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerleave", onLeave);
    };
  }, []);

  return <canvas ref={ref} className="intel-field" aria-hidden />;
}
