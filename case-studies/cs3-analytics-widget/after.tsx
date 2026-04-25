// CS3: Analytics Widget — AFTER (regression introduced)
// Anti-patterns deliberately introduced:
//   - High complexity delta (many new if/switch/for/while/catch branches)
//   - Many new useState hooks (no useReducer consolidation)
//   - useEffect without dependencies
//   - Removed all memoization (no useMemo, no useCallback, no React.memo)
//   - Inline arrow functions in JSX
//   - Nested component definitions
//   - console.log debug statements
import React, { useEffect, useState } from 'react';

interface DataPoint { date: string; value: number; label: string; }

export default function AnalyticsWidget({ data }: { data: DataPoint[] }) {
  const [range, setRange] = useState('30d');
  const [hoveredLabel, setHoveredLabel] = useState<string | null>(null);
  const [selectedBar, setSelectedBar] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'bar' | 'line' | 'area'>('bar');
  const [showGrid, setShowGrid] = useState(true);
  const [showLegend, setShowLegend] = useState(true);
  const [showTooltip, setShowTooltip] = useState(true);
  const [animating, setAnimating] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [threshold, setThreshold] = useState(0);
  const [alertTriggered, setAlertTriggered] = useState(false);

  // BUG: no dependency array
  useEffect(() => {
    console.log('widget rendered, data length:', data.length);
    console.log('current range:', range);
    console.log('view mode:', viewMode);
  });

  // BUG: no dependency array — runs threshold check every render
  useEffect(() => {
    const days = range === '7d' ? 7 : range === '30d' ? 30 : 90;
    const filtered = data.slice(-days);
    const peak = filtered.length > 0 ? Math.max(...filtered.map(d => d.value)) : 0;
    if (threshold > 0 && peak > threshold) {
      setAlertTriggered(true);
      console.log('alert: peak', peak, 'exceeds threshold', threshold);
    } else {
      setAlertTriggered(false);
    }
  });

  // BUG: animation effect, also unguarded
  useEffect(() => {
    setAnimating(true);
    const t = setTimeout(() => setAnimating(false), 300);
    console.log('animation triggered');
    return () => clearTimeout(t);
  });

  const days = range === '7d' ? 7 : range === '30d' ? 30 : 90;
  const filtered = data.slice(-days);
  const max = filtered.length > 0 ? Math.max(...filtered.map(d => d.value)) : 1;

  // BUG: expensive calculations inline, not memoized — runs on every render
  let total = 0;
  let peak  = 0;
  for (let i = 0; i < filtered.length; i++) {
    total += filtered[i].value;
    if (filtered[i].value > peak) peak = filtered[i].value;
    if (filtered[i].value < 0) {
      console.log('negative value detected at', filtered[i].date);
    }
  }
  const average = filtered.length > 0 ? total / filtered.length : 0;

  // BUG: more inline complexity — trend calculation
  let trend = 0;
  if (filtered.length > 1) {
    const first = filtered.slice(0, Math.floor(filtered.length / 2));
    const second = filtered.slice(Math.floor(filtered.length / 2));
    const firstAvg = first.reduce((s, d) => s + d.value, 0) / first.length;
    const secondAvg = second.reduce((s, d) => s + d.value, 0) / second.length;
    trend = ((secondAvg - firstAvg) / firstAvg) * 100;
    if (trend > 50) {
      console.log('high growth trend detected:', trend.toFixed(1) + '%');
    } else if (trend < -50) {
      console.log('high decline trend detected:', trend.toFixed(1) + '%');
    }
  }

  // BUG: nested component — remounts on every render
  const ChartBar = ({ point }: { point: DataPoint }) => {
    const [localHovered, setLocalHovered] = useState(false);
    const height = `${(point.value / max) * 100}%`;
    const isSelected = selectedBar === point.date;
    const isAboveThreshold = threshold > 0 && point.value > threshold;

    return (
      <div
        className={`bar-wrap ${localHovered ? 'hovered' : ''} ${isSelected ? 'selected' : ''}`}
        onMouseEnter={() => { setLocalHovered(true); setHoveredLabel(point.label); }}
        onMouseLeave={() => { setLocalHovered(false); setHoveredLabel(null); }}
        onClick={() => setSelectedBar(isSelected ? null : point.date)}
      >
        <div
          className={`bar ${isAboveThreshold ? 'above-threshold' : ''}`}
          style={{ height, background: isAboveThreshold ? '#ef4444' : localHovered ? '#7c6af7' : '#4f46e5' }}
        />
        {showGrid && <div className="grid-line" />}
        {showLegend && <span className="bar-label">{point.date}</span>}
      </div>
    );
  };

  // BUG: nested stats component
  const StatsRow = () => (
    <div className="stats-row">
      <div className="stat" onClick={() => console.log('total clicked')}>
        <span className="val">{total.toLocaleString()}</span>
        <span className="lbl">Total</span>
      </div>
      <div className="stat" onClick={() => console.log('avg clicked')}>
        <span className="val">{average.toFixed(1)}</span>
        <span className="lbl">Average</span>
      </div>
      <div className="stat" onClick={() => console.log('peak clicked')}>
        <span className="val">{peak.toLocaleString()}</span>
        <span className="lbl">Peak</span>
      </div>
      <div className="stat">
        <span className="val" style={{ color: trend >= 0 ? '#22c55e' : '#ef4444' }}>
          {trend >= 0 ? '+' : ''}{trend.toFixed(1)}%
        </span>
        <span className="lbl">Trend</span>
      </div>
    </div>
  );

  return (
    <div className={`analytics-widget ${animating ? 'animating' : ''} ${alertTriggered ? 'alert' : ''}`}>
      <div className="widget-header">
        <h3>Analytics</h3>
        <div className="controls">
          <div className="range-selector">
            <button onClick={() => setRange('7d')} className={range === '7d' ? 'active' : ''}>7d</button>
            <button onClick={() => setRange('30d')} className={range === '30d' ? 'active' : ''}>30d</button>
            <button onClick={() => setRange('90d')} className={range === '90d' ? 'active' : ''}>90d</button>
          </div>
          <select value={viewMode} onChange={(e) => setViewMode(e.target.value as 'bar' | 'line' | 'area')}>
            <option value="bar">Bar</option>
            <option value="line">Line</option>
            <option value="area">Area</option>
          </select>
          <label><input type="checkbox" checked={showGrid} onChange={(e) => setShowGrid(e.target.checked)} /> Grid</label>
          <label><input type="checkbox" checked={showLegend} onChange={(e) => setShowLegend(e.target.checked)} /> Legend</label>
          <label><input type="checkbox" checked={compareMode} onChange={(e) => setCompareMode(e.target.checked)} /> Compare</label>
          <input type="number" value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} placeholder="Alert threshold" />
        </div>
      </div>
      {alertTriggered && <div className="alert-banner">Peak value exceeds threshold!</div>}
      <StatsRow />
      <div className={`chart chart-${viewMode}`}>
        {filtered.map(d => <ChartBar key={d.date} point={d} />)}
      </div>
      {showTooltip && hoveredLabel && <div className="tooltip">{hoveredLabel}</div>}
      {selectedBar && (
        <div className="selection-info">
          Selected: {selectedBar}
          <button onClick={() => setSelectedBar(null)}>Clear</button>
        </div>
      )}
    </div>
  );
}
