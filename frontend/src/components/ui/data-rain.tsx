"use client";

import { useEffect, useRef } from "react";

export interface DataRainPalette {
  calm: string;
  mid: string;
  hot: string;
}

export interface DataRainProps {
  className?: string;
  count?: number;
  flowSpeed?: number;
  obstacleRadius?: number;
  autopilot?: boolean;
  fullscreen?: boolean;
  palette?: DataRainPalette;
}

type RGB = readonly [number, number, number];

interface Particle {
  x: number;
  y: number;
  vx: number;
  speed: number;
  phase: number;
  depth: number;
  color: number;
  historyX: Float32Array;
  historyY: Float32Array;
}

const HISTORY = 10;
const TAU = Math.PI * 2;
const DEFAULT_PALETTE: DataRainPalette = {
  calm: "#22b99a",
  mid: "#4ccdb1",
  hot: "#91dfca",
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function parseHex(value: string | undefined, fallback: RGB): RGB {
  if (!value) return fallback;
  let hex = value.trim().replace(/^#/, "");
  if (hex.length === 3) {
    hex = hex.split("").map((part) => part + part).join("");
  }
  if (!/^[0-9a-f]{6}$/i.test(hex)) return fallback;
  const parsed = Number.parseInt(hex, 16);
  return [(parsed >> 16) & 255, (parsed >> 8) & 255, parsed & 255];
}

export default function DataRain(props: DataRainProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const bloomRef = useRef<HTMLCanvasElement | null>(null);
  const propsRef = useRef<DataRainProps>(props);
  propsRef.current = props;

  useEffect(() => {
    const root = rootRef.current;
    const canvas = canvasRef.current;
    const bloom = bloomRef.current;
    if (!root || !canvas || !bloom) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    const bctx = bloom.getContext("2d", { alpha: true });
    if (!ctx || !bctx) return;

    const reduceMotion =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let width = 1;
    let height = 1;
    let dpr = 1;
    let bloomWidth = 1;
    let bloomHeight = 1;
    let raf = 0;
    let disposed = false;
    let last = 0;
    let elapsed = 0;
    let pointerActive = false;
    let pointerX = 0;
    let pointerY = 0;
    let cursorX = 0;
    let cursorY = 0;
    let alive = false;
    const particles: Particle[] = [];

    let seed = 7;
    const random = (): number => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 4294967296;
    };

    const palette = (): RGB[] => {
      const chosen = propsRef.current.palette ?? DEFAULT_PALETTE;
      return [
        parseHex(chosen.calm, [34, 185, 154]),
        parseHex(chosen.mid, [76, 205, 177]),
        parseHex(chosen.hot, [145, 223, 202]),
      ];
    };

    const makeParticle = (index: number, resetAbove = false): Particle => {
      const x = random() * width;
      const y = resetAbove ? -random() * height * 0.45 : random() * height;
      const depth = 0.35 + random() * 0.65;
      const historyX = new Float32Array(HISTORY);
      const historyY = new Float32Array(HISTORY);
      historyX.fill(x);
      historyY.fill(y);
      return {
        x,
        y,
        vx: 0,
        speed: (52 + random() * 86) * depth,
        phase: random() * TAU,
        depth,
        color: index % 3,
        historyX,
        historyY,
      };
    };

    const seedParticles = (): void => {
      particles.length = 0;
      const automatic = clamp(Math.round((width * height) / 1250), 650, 1900);
      const count = clamp(Math.round(propsRef.current.count ?? automatic), 1, 5000);
      for (let i = 0; i < count; i += 1) {
        particles.push(makeParticle(i));
      }
      cursorX = width * 0.52;
      cursorY = height * 0.42;
    };

    const resize = (): void => {
      const bounds = root.getBoundingClientRect();
      width = Math.max(1, bounds.width || window.innerWidth);
      height = Math.max(1, bounds.height || window.innerHeight);
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      if (width * height * dpr * dpr > 4_500_000) {
        dpr = Math.sqrt(4_500_000 / (width * height));
      }

      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
      bloomWidth = Math.max(1, Math.ceil(width / 4));
      bloomHeight = Math.max(1, Math.ceil(height / 4));
      bloom.width = bloomWidth;
      bloom.height = bloomHeight;
      bctx.imageSmoothingEnabled = true;
      bctx.imageSmoothingQuality = "medium";

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      seedParticles();
      draw();
    };

    const draw = (): void => {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = "lighter";
      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      const colors = palette();
      for (let group = 0; group < 3; group += 1) {
        const color = colors[group];
        ctx.beginPath();
        for (const particle of particles) {
          if (particle.color !== group) continue;
          const hx = particle.historyX;
          const hy = particle.historyY;
          ctx.moveTo(hx[HISTORY - 1], hy[HISTORY - 1]);
          for (let point = HISTORY - 2; point >= 0; point -= 1) {
            ctx.lineTo(hx[point], hy[point]);
          }
        }
        ctx.strokeStyle = `rgba(${color[0]},${color[1]},${color[2]},0.42)`;
        ctx.lineWidth = group === 2 ? 1.15 : 0.9;
        ctx.stroke();
      }

      ctx.beginPath();
      for (const particle of particles) {
        ctx.moveTo(particle.x + 1.1, particle.y);
        ctx.arc(particle.x, particle.y, particle.depth > 0.7 ? 1 : 0.65, 0, TAU);
      }
      ctx.fillStyle = "rgba(232,255,248,0.46)";
      ctx.fill();
      ctx.globalCompositeOperation = "source-over";
      bctx.clearRect(0, 0, bloomWidth, bloomHeight);
      bctx.drawImage(canvas, 0, 0, bloomWidth, bloomHeight);
    };

    const simulate = (delta: number): void => {
      const p = propsRef.current;
      const flow = clamp(p.flowSpeed ?? 1, 0.05, 5);
      const radius = clamp(p.obstacleRadius ?? 64, 8, 240);
      const autopilot = p.autopilot ?? true;

      if (!pointerActive && autopilot && !reduceMotion) {
        cursorX = width * (0.5 + 0.31 * Math.sin(elapsed * 0.31));
        cursorY = height * (0.5 + 0.27 * Math.sin(elapsed * 0.43 + 1.1));
      } else if (pointerActive) {
        cursorX += (pointerX - cursorX) * Math.min(1, delta * 10);
        cursorY += (pointerY - cursorY) * Math.min(1, delta * 10);
      }

      for (const particle of particles) {
        const { historyX, historyY } = particle;
        const desiredX =
          Math.sin(particle.y * 0.003 + particle.phase + elapsed * 0.36) *
          15 *
          particle.depth;
        particle.vx += (desiredX - particle.vx) * Math.min(1, delta * 1.6);

        let xVelocity = particle.vx;
        let yVelocity = particle.speed * flow;

        const dx = particle.x - cursorX;
        const dy = particle.y - cursorY;
        const distance = Math.sqrt(dx * dx + dy * dy) + 0.001;
        const influence = pointerActive || autopilot ? clamp(1 - distance / (radius * 3.2), 0, 1) : 0;

        if (influence > 0) {
          const swirl = (pointerActive ? 1 : 0.55) * influence;
          xVelocity += ((dx / distance) * 110 - (dy / distance) * 78) * swirl;
          yVelocity += ((dy / distance) * 62 + (dx / distance) * 34) * swirl;
        }

        particle.x += xVelocity * delta;
        particle.y += yVelocity * delta;

        if (
          particle.y > height + 24 ||
          particle.x < -32 ||
          particle.x > width + 32
        ) {
          const replacement = makeParticle(particle.color, true);
          particle.x = random() * width;
          particle.y = -random() * 70;
          particle.vx = 0;
          historyX.fill(particle.x);
          historyY.fill(particle.y);
        } else {
          for (let i = HISTORY - 1; i > 0; i -= 1) {
            historyX[i] = historyX[i - 1];
            historyY[i] = historyY[i - 1];
          }
          historyX[0] = particle.x;
          historyY[0] = particle.y;
        }
      }
    };

    const frame = (now: number): void => {
      if (disposed || !alive) return;
      const delta = last ? clamp((now - last) / 1000, 0, 0.033) : 0;
      last = now;
      elapsed += delta;
      if (!reduceMotion && delta > 0) simulate(delta);
      draw();
      if (!reduceMotion) raf = window.requestAnimationFrame(frame);
    };

    const onPointerMove = (event: PointerEvent): void => {
      const bounds = root.getBoundingClientRect();
      pointerX = event.clientX - bounds.left;
      pointerY = event.clientY - bounds.top;
      pointerActive = true;
    };
    const onPointerLeave = (): void => {
      pointerActive = false;
    };
    const onVisibility = (): void => {
      if (document.hidden) {
        window.cancelAnimationFrame(raf);
        raf = 0;
      } else if (alive && !reduceMotion) {
        last = 0;
        raf = window.requestAnimationFrame(frame);
      }
    };

    const observer = new ResizeObserver(resize);
    observer.observe(root);
    resize();
    alive = true;

    if (!reduceMotion) {
      window.addEventListener("pointermove", onPointerMove, { passive: true });
      document.documentElement.addEventListener("pointerleave", onPointerLeave);
      document.addEventListener("visibilitychange", onVisibility);
      raf = window.requestAnimationFrame(frame);
    }

    return () => {
      disposed = true;
      alive = false;
      window.cancelAnimationFrame(raf);
      observer.disconnect();
      window.removeEventListener("pointermove", onPointerMove);
      document.documentElement.removeEventListener("pointerleave", onPointerLeave);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [props.count, props.palette?.calm, props.palette?.mid, props.palette?.hot]);

  const fullscreen = props.fullscreen ?? true;
  const className = [
    "dr-root",
    fullscreen ? "" : "dr-root--contained",
    props.className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div ref={rootRef} className={className} aria-hidden="true">
      <canvas ref={bloomRef} className="dr-bloom" />
      <canvas ref={canvasRef} className="dr-main" />
      <div className="dr-vignette" />
      <div className="dr-grain" />
    </div>
  );
}
