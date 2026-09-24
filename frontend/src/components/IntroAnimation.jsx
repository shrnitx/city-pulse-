import { useEffect, useRef } from 'react';

// The intro reuses the EXISTING hero city image so the final frame matches the hero exactly.
const CITY = '/assets/city-neighborhood.jpg';

// Community signal points, normalized (0..1) to the hero box. depth: 0 = distant, 1 = foreground.
// Ordered so the first 7 (used on mobile) stay well spread across the composition.
const SIGNALS = [
  { x: 0.30, y: 0.44, depth: 0.55 }, // 0 - first signal
  { x: 0.58, y: 0.60, depth: 0.80 }, // 1
  { x: 0.70, y: 0.47, depth: 0.60 }, // 2
  { x: 0.41, y: 0.34, depth: 0.35 }, // 3
  { x: 0.49, y: 0.50, depth: 0.65 }, // 4 - near centre
  { x: 0.23, y: 0.61, depth: 0.75 }, // 5
  { x: 0.78, y: 0.42, depth: 0.50 }, // 6
  { x: 0.36, y: 0.55, depth: 0.72 }, // 7
  { x: 0.62, y: 0.30, depth: 0.32 }, // 8
  { x: 0.53, y: 0.40, depth: 0.50 }, // 9
  { x: 0.82, y: 0.55, depth: 0.66 }, // 10
  { x: 0.16, y: 0.46, depth: 0.50 }, // 11
];

// Relationships between signals (subtle information pathways).
const CONNECTIONS = [
  [0, 4], [4, 1], [1, 2], [2, 6], [4, 3], [3, 9],
  [9, 8], [4, 7], [7, 5], [0, 11], [6, 10], [9, 2],
];

export default function IntroAnimation({ onReveal, onComplete }) {
  const rootRef = useRef(null);
  const cityRef = useRef(null);
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  const doneRef = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const isMobile = window.innerWidth < 768;
    const count = isMobile ? 7 : SIGNALS.length;
    const signals = SIGNALS.slice(0, count);
    const connections = CONNECTIONS.filter(([a, b]) => a < count && b < count).slice(0, isMobile ? 5 : 12);

    let W = 0;
    let H = 0;
    const resize = () => {
      const r = canvas.getBoundingClientRect();
      W = r.width; H = r.height;
      canvas.width = Math.max(1, Math.round(W * dpr));
      canvas.height = Math.max(1, Math.round(H * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);

    const T = {
      firstPulse: 300, signalsStart: 520, signalsEnd: 1720,
      connStart: 2000, central: 2550, mark: 2820, markOut: 3560,
      reveal: 3200, fade: 3620, complete: 4300,
    };

    // Bring the darkened, blurred city into focus.
    requestAnimationFrame(() => { if (cityRef.current) cityRef.current.classList.add('focus'); });

    const appear = signals.map((s, i) => {
      const span = T.signalsEnd - T.signalsStart;
      const base = T.signalsStart + (count > 1 ? (i / (count - 1)) * span : 0);
      return base + (i % 2 ? -70 : 60);
    });
    appear[0] = T.firstPulse;

    const start = performance.now();
    const ease = (t) => 1 - Math.pow(1 - t, 3);
    const centerX = () => W / 2;
    const centerY = () => H * 0.5;

    const draw = (nowT) => {
      const t = nowT - start;
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'lighter';

      // Connections
      connections.forEach(([a, b], ci) => {
        const cs = T.connStart + ci * 55;
        if (t < cs) return;
        const k = ease(Math.min(1, (t - cs) / 650));
        const A = signals[a]; const B = signals[b];
        const ax = A.x * W; const ay = A.y * H; const bx = B.x * W; const by = B.y * H;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax + (bx - ax) * k, ay + (by - ay) * k);
        ctx.strokeStyle = `rgba(200,230,214,${0.2 * k})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      // Signals + soft pulses
      signals.forEach((s, i) => {
        if (t < appear[i]) return;
        const age = t - appear[i];
        const x = s.x * W; const y = s.y * H;
        const k = Math.min(1, age / 380);
        const baseR = 1.6 + s.depth * 2.2;
        const rings = i === 0 ? 2 : 1;
        for (let r = 0; r < rings; r += 1) {
          const rt = age - r * 460;
          if (rt > 0 && rt < 1500) {
            const rp = rt / 1500;
            const rr = baseR + ease(rp) * (24 + s.depth * 20);
            ctx.beginPath();
            ctx.arc(x, y, rr, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(190,224,206,${0.26 * (1 - rp) * s.depth})`;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
        const glow = ctx.createRadialGradient(x, y, 0, x, y, baseR * 3.4);
        glow.addColorStop(0, `rgba(235,245,238,${0.85 * k * (0.6 + 0.4 * s.depth)})`);
        glow.addColorStop(0.4, `rgba(190,224,206,${0.32 * k})`);
        glow.addColorStop(1, 'rgba(190,224,206,0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, baseR * 3.4, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = `rgba(240,248,242,${0.95 * k})`;
        ctx.beginPath();
        ctx.arc(x, y, baseR, 0, Math.PI * 2);
        ctx.fill();
      });

      // Central CityPulse pulse
      if (t >= T.central) {
        const rt = t - T.central;
        if (rt < 1300) {
          const rp = rt / 1300;
          const rr = ease(rp) * (isMobile ? 90 : 130);
          ctx.beginPath();
          ctx.arc(centerX(), centerY(), rr, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(215,238,224,${0.38 * (1 - rp)})`;
          ctx.lineWidth = 1.4;
          ctx.stroke();
          const g = ctx.createRadialGradient(centerX(), centerY(), 0, centerX(), centerY(), rr || 1);
          g.addColorStop(0, `rgba(225,245,232,${0.1 * (1 - rp)})`);
          g.addColorStop(1, 'rgba(225,245,232,0)');
          ctx.fillStyle = g;
          ctx.beginPath();
          ctx.arc(centerX(), centerY(), rr, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      ctx.globalCompositeOperation = 'source-over';
      rafRef.current = requestAnimationFrame(draw);
    };
    rafRef.current = requestAnimationFrame(draw);

    const finish = () => {
      if (doneRef.current) return;
      doneRef.current = true;
      if (onComplete) onComplete();
    };
    const addClass = (cls) => { if (rootRef.current) rootRef.current.classList.add(cls); };

    const timers = [
      setTimeout(() => addClass('mark-in'), T.mark),
      setTimeout(() => addClass('mark-out'), T.markOut),
      setTimeout(() => { if (onReveal) onReveal(); }, T.reveal),
      setTimeout(() => addClass('fade-out'), T.fade),
      setTimeout(finish, T.complete),
    ];

    // Never block the user: any explicit interaction gracefully finishes the intro.
    const skip = () => {
      if (doneRef.current) return;
      if (onReveal) onReveal();
      addClass('fade-out');
      setTimeout(finish, 500);
    };
    window.addEventListener('wheel', skip, { passive: true, once: true });
    window.addEventListener('touchstart', skip, { passive: true, once: true });
    window.addEventListener('keydown', skip, { once: true });
    window.addEventListener('pointerdown', skip, { once: true });

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('resize', resize);
      timers.forEach(clearTimeout);
      window.removeEventListener('wheel', skip);
      window.removeEventListener('touchstart', skip);
      window.removeEventListener('keydown', skip);
      window.removeEventListener('pointerdown', skip);
    };
  }, [onReveal, onComplete]);

  return (
    <div className="cp-intro" ref={rootRef} aria-hidden="true">
      <div className="cp-intro-city" ref={cityRef} style={{ backgroundImage: `url(${CITY})` }} />
      <div className="cp-intro-veil" />
      <canvas className="cp-intro-canvas" ref={canvasRef} />
      <div className="cp-intro-mark"><span>CityPulse.</span></div>
    </div>
  );
}
