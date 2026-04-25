// CS3: Analytics Widget — BEFORE (clean)
import React, { useState, useCallback, useMemo } from 'react';

interface DataPoint { date: string; value: number; label: string; }

interface ChartBarProps {
  point: DataPoint;
  max: number;
  onHover: (label: string | null) => void;
}

const ChartBar = React.memo(function ChartBar({ point, max, onHover }: ChartBarProps) {
  const height = `${(point.value / max) * 100}%`;
  return (
    <div
      className="bar-wrap"
      onMouseEnter={() => onHover(point.label)}
      onMouseLeave={() => onHover(null)}
    >
      <div className="bar" style={{ height }} />
      <span className="bar-label">{point.date}</span>
    </div>
  );
});

export default function AnalyticsWidget({ data }: { data: DataPoint[] }) {
  const [range, setRange] = useState<'7d' | '30d' | '90d'>('30d');
  const [hoveredLabel, setHoveredLabel] = useState<string | null>(null);

  const days = range === '7d' ? 7 : range === '30d' ? 30 : 90;

  const filtered = useMemo(() => data.slice(-days), [data, days]);

  const max = useMemo(() => Math.max(...filtered.map(d => d.value), 1), [filtered]);

  const stats = useMemo(() => ({
    total:   filtered.reduce((s, d) => s + d.value, 0),
    average: filtered.reduce((s, d) => s + d.value, 0) / Math.max(filtered.length, 1),
    peak:    Math.max(...filtered.map(d => d.value)),
  }), [filtered]);

  const handleHover = useCallback((label: string | null) => setHoveredLabel(label), []);

  return (
    <div className="analytics-widget">
      <div className="widget-header">
        <h3>Analytics</h3>
        <div className="range-selector">
          {(['7d', '30d', '90d'] as const).map(r => (
            <button key={r} className={range === r ? 'active' : ''} onClick={() => setRange(r)}>{r}</button>
          ))}
        </div>
      </div>
      <div className="stats-row">
        <div className="stat"><span className="val">{stats.total.toLocaleString()}</span><span className="lbl">Total</span></div>
        <div className="stat"><span className="val">{stats.average.toFixed(1)}</span><span className="lbl">Average</span></div>
        <div className="stat"><span className="val">{stats.peak.toLocaleString()}</span><span className="lbl">Peak</span></div>
      </div>
      <div className="chart">
        {filtered.map(d => <ChartBar key={d.date} point={d} max={max} onHover={handleHover} />)}
      </div>
      {hoveredLabel && <div className="tooltip">{hoveredLabel}</div>}
    </div>
  );
}
