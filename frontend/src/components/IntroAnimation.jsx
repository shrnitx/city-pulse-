import { useEffect, useRef } from 'react';

const SIGNALS = [
  { x: 0.30, y: 0.44, depth: 0.55 },
  { x: 0.58, y: 0.60, depth: 0.80 },
  { x: 0.70, y: 0.47, depth: 0.60 },
  { x: 0.41, y: 0.34, depth: 0.35 },
  { x: 0.49, y: 0.50, depth: 0.65 },
  { x: 0.23, y: 0.61, depth: 0.75 },
  { x: 0.78, y: 0.42, depth: 0.50 },
  { x: 0.36, y: 0.55, depth: 0.72 },
  { x: 0.62, y: 0.30, depth: 0.32 },
  { x: 0.53, y: 0.40, depth: 0.50 },
  { x: 0.82, y: 0.55, depth: 0.66 },
  { x: 0.16, y: 0.46, depth: 0.50 },
];
const CONNECTIONS = [[0,4],[4,1],[1,2],[2,6],[4,3],[3,9],[9,8],[4,7],[7,5],[0,11],[6,10],[9,2]];

export default function IntroAnimation({ onReveal, onComplete }) {
  const rootRef = useRef(null);
  const cityRef = useRef(null);
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  const doneRef = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas && canvas.getContext('2d');
    if (!canvas || !ctx) {
      const fallback = setTimeout(() => { onReveal(); onComplete(); }, 300);
      return () => clearTimeout(fallback);
    }

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const mobile = window.innerWidth < 768;
    const nodes = SIGNALS.slice(0, mobile ? 7 : SIGNALS.length);
    const edges = CONNECTIONS.filter(([a,b]) => a < nodes.length && b < nodes.length);
    let width = 0;
    let height = 0;
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);
    requestAnimationFrame(() => { if (cityRef.current) cityRef.current.classList.add('focus'); });

    const timings = { pulse: 300, signalsStart: 520, signalsEnd: 1720, edges: 2000, center: 2550, markIn: 2820, reveal: 3200, markOut: 3560, fade: 3620, done: 4300 };
    const appear = nodes.map((node, i) => timings.signalsStart + (nodes.length > 1 ? i / (nodes.length - 1) : 0) * (timings.signalsEnd - timings.signalsStart) + (i % 2 ? -70 : 60));
    if (appear.length) appear[0] = timings.pulse;
    const start = performance.now();
    const ease = t => 1 - Math.pow(1 - t, 3);
    const draw = now => {
      const t = now - start;
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = 'lighter';

      edges.forEach(([a,b], index) => {
        const begin = timings.edges + index * 55;
        if (t < begin) return;
        const k = ease(Math.min(1, (t - begin) / 650));
        const A = nodes[a], B = nodes[b];
        const ax = A.x * width, ay = A.y * height, bx = B.x * width, by = B.y * height;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax + (bx - ax) * k, ay + (by - ay) * k);
        ctx.strokeStyle = 'rgba(200,230,214,' + (0.2 * k) + ')';
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      nodes.forEach((node, i) => {
        if (t < appear[i]) return;
        const age = t - appear[i];
        const k = Math.min(1, age / 380);
        const x = node.x * width, y = node.y * height;
        const base = 1.6 + node.depth * 2.2;
        const ringCount = i === 0 ? 2 : 1;
        for (let r = 0; r < ringCount; r += 1) {
          const rt = age - r * 460;
          if (rt > 0 && rt < 1500) {
            const p = rt / 1500;
            ctx.beginPath();
            ctx.arc(x, y, base + ease(p) * (24 + node.depth * 20), 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(190,224,206,' + (0.26 * (1 - p) * node.depth) + ')';
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
        const glow = ctx.createRadialGradient(x, y, 0, x, y, base * 3.4);
        glow.addColorStop(0, 'rgba(235,245,238,' + (0.85 * k * (0.6 + 0.4 * node.depth)) + ')');
        glow.addColorStop(0.4, 'rgba(190,224,206,' + (0.32 * k) + ')');
        glow.addColorStop(1, 'rgba(190,224,206,0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, base * 3.4, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = 'rgba(240,248,242,' + (0.95 * k) + ')';
        ctx.beginPath();
        ctx.arc(x, y, base, 0, Math.PI * 2);
        ctx.fill();
      });

      if (t >= timings.center && t - timings.center < 1300) {
        const p = (t - timings.center) / 1300;
        const radius = ease(p) * (mobile ? 90 : 130);
        ctx.beginPath();
        ctx.arc(width / 2, height / 2, radius, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(215,238,224,' + (0.38 * (1 - p)) + ')';
        ctx.lineWidth = 1.4;
        ctx.stroke();
      }
      ctx.globalCompositeOperation = 'source-over';
      rafRef.current = requestAnimationFrame(draw);
    };
    rafRef.current = requestAnimationFrame(draw);

    const addClass = name => { if (rootRef.current) rootRef.current.classList.add(name); };
    const finish = () => {
      if (doneRef.current) return;
      doneRef.current = true;
      onComplete();
    };
    const timers = [
      setTimeout(() => addClass('mark-in'), timings.markIn),
      setTimeout(() => addClass('mark-out'), timings.markOut),
      setTimeout(() => onReveal(), timings.reveal),
      setTimeout(() => addClass('fade-out'), timings.fade),
      setTimeout(finish, timings.done),
    ];
    let skipTimer = 0;
    const skip = () => {
      if (doneRef.current) return;
      onReveal();
      addClass('fade-out');
      skipTimer = setTimeout(finish, 450);
    };
    window.addEventListener('wheel', skip, { passive: true, once: true });
    window.addEventListener('touchstart', skip, { passive: true, once: true });
    window.addEventListener('keydown', skip, { once: true });
    window.addEventListener('pointerdown', skip, { once: true });

    return () => {
      cancelAnimationFrame(rafRef.current);
      clearTimeout(skipTimer);
      timers.forEach(clearTimeout);
      window.removeEventListener('resize', resize);
      window.removeEventListener('wheel', skip);
      window.removeEventListener('touchstart', skip);
      window.removeEventListener('keydown', skip);
      window.removeEventListener('pointerdown', skip);
    };
  }, [onReveal, onComplete]);

  return <div className="cp-intro" ref={rootRef} aria-hidden="true">
    <div className="cp-intro-city" ref={cityRef} style={{ backgroundImage: "url('/assets/city-neighborhood.jpg')" }} />
    <div className="cp-intro-veil" />
    <canvas className="cp-intro-canvas" ref={canvasRef} />
    <div className="cp-intro-mark"><span>DRCivic.</span></div>
  </div>;
}
