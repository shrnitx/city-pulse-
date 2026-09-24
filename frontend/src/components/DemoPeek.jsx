import { useState, useEffect, useRef } from 'react';
import useSWR from 'swr';
import { Link } from 'react-router-dom';
import { Activity, ArrowUpRight, MapPin, Users, ShieldCheck } from 'lucide-react';
import { fetcher } from '../lib/api';

const STATUS_TONE = {
  Reported: 'tone-blue', 'AI Analyzed': 'tone-teal', 'Under Review': 'tone-amber',
  Verified: 'tone-green', Assigned: 'tone-teal', 'In Progress': 'tone-amber',
  Resolved: 'tone-green', Closed: 'tone-grey',
};

const PLACEHOLDER = [
  { case_number: 'p1', title: 'Road incident near Block B intersection', category: 'Road', location: 'Block B · North Gate Avenue', status: 'AI Analyzed', reports: 50, verified: false },
  { case_number: 'p2', title: 'Low water pressure in Sector 4', category: 'Water', location: 'Sector 4 · Utility Junction', status: 'Under Review', reports: 22, verified: false },
  { case_number: 'p3', title: 'Streetlights out along the Crossroad Path', category: 'Electricity', location: 'Block C · 3rd Crossroad Path', status: 'In Progress', reports: 8, verified: true },
  { case_number: 'p4', title: 'Waste collection completed at the East Gate', category: 'Garbage', location: 'East Gate · Collection Point', status: 'Resolved', reports: 6, verified: true },
];

export default function DemoPeek() {
  const { data } = useSWR('/public/demo-feed', fetcher, { revalidateOnFocus: false });
  const cases = (data?.cases?.length ? data.cases : PLACEHOLDER).slice(0, 5);
  const [active, setActive] = useState(0);
  const [inView, setInView] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return undefined;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setInView(true); io.disconnect(); }
    }, { threshold: 0.2 });
    io.observe(ref.current);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    if (!inView || cases.length < 2) return undefined;
    const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return undefined;
    const t = setInterval(() => setActive((a) => (a + 1) % cases.length), 2600);
    return () => clearInterval(t);
  }, [inView, cases.length]);

  const society = data?.society || { name: 'Green Valley Residency', location: 'Sector 14, Gurugram' };

  return (
    <section className={`society-pulse-band ${inView ? 'in' : ''}`} ref={ref} id="live-peek">
      <div className="sp-copy">
        <span className="eyebrow">THE COMMUNITY PULSE, RIGHT NOW</span>
        <h2>See a society in motion.</h2>
        <p>A live snapshot from {society.name}.<br />Real reports, organized into clear, trackable cases.</p>
        <Link to="/enter" className="sp-cta" data-testid="demo-peek-cta">Explore the live demo <ArrowUpRight size={16} /></Link>
      </div>
      <div className="sp-feed" aria-label="Community feed preview" data-testid="demo-peek-feed">
        <div className="sp-feed-head">
          <span className="sp-live"><span className="sp-live-dot" />LIVE FEED</span>
          <span className="sp-loc"><MapPin size={12} /> {society.location}</span>
        </div>
        <div className="sp-rows">
          {cases.map((c, i) => (
            <div key={c.case_number} className={`sp-row ${i === active ? 'active' : ''}`} style={{ transitionDelay: `${i * 70}ms` }}>
              <span className={`sp-badge ${STATUS_TONE[c.status] || 'tone-teal'}`}>{c.status}</span>
              <div className="sp-row-main">
                <strong>{c.title}</strong>
                <span className="sp-meta">{c.category} · {c.location}</span>
              </div>
              <div className="sp-row-metrics">
                <span title="community reports"><Users size={12} /> {c.reports ?? '—'}</span>
                {c.verified && <span className="sp-verified" title="verified by an administrator"><ShieldCheck size={12} /></span>}
              </div>
            </div>
          ))}
        </div>
        <div className="sp-feed-foot"><Activity size={13} /> Signals become cases. Cases become action.</div>
      </div>
    </section>
  );
}
