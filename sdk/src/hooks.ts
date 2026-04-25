/**
 * PerfSense SDK — React hooks
 *
 * usePerfSenseTracker(componentName)
 *   Wraps React.Profiler to measure render time of the host component.
 *   Returns a ProfilerOnRenderCallback-compatible <Profiler> wrapper.
 *
 * useWebVitals()
 *   Returns the latest observed web vitals for display in dashboards.
 */

import React, { useRef, useEffect, useCallback } from "react";
import { getTransport } from "./sdk";
import { WebVitalMetric } from "./types";

/**
 * Track render performance of a component by name.
 *
 * Usage:
 *   const Tracked = usePerfSenseTracker("MyExpensiveList");
 *   return <Tracked.Profiler><MyExpensiveList /></Tracked.Profiler>;
 *
 * Or simpler — just call the hook; it self-instruments via useRef timing:
 *   usePerfSenseTracker("MyComponent");
 */
export function usePerfSenseTracker(componentName: string): void {
  const renderCount = useRef(0);
  const renderStart = useRef(performance.now());

  // Mark render start (runs synchronously during render)
  renderStart.current = performance.now();
  renderCount.current += 1;

  useEffect(() => {
    const renderTime = performance.now() - renderStart.current;
    const transport  = getTransport();
    if (transport) {
      transport.addRender({
        componentName,
        renderCount:     1,
        totalRenderTime: renderTime,
        lastRenderTime:  renderTime,
        timestamp:       Date.now(),
      });
    }
  });
}

/**
 * Profiler wrapper component — alternative to usePerfSenseTracker.
 * Wraps children in a React.Profiler that reports to PerfSense.
 *
 * Usage:
 *   <PerfSenseProfiler id="UserList">
 *     <UserList />
 *   </PerfSenseProfiler>
 */
export function PerfSenseProfiler({
  id,
  children,
}: {
  id: string;
  children: React.ReactNode;
}): React.ReactElement {
  const onRender: React.ProfilerOnRenderCallback = useCallback(
    (_id, _phase, actualDuration) => {
      const transport = getTransport();
      if (transport) {
        transport.addRender({
          componentName:   id,
          renderCount:     1,
          totalRenderTime: actualDuration,
          lastRenderTime:  actualDuration,
          timestamp:       Date.now(),
        });
      }
    },
    [id]
  );

  return React.createElement(
    React.Profiler,
    { id, onRender },
    children
  );
}

/**
 * Returns latest observed web vitals as a live-updating object.
 * Useful for building an on-screen perf overlay in dev mode.
 *
 * Usage:
 *   const vitals = useWebVitals();
 *   // vitals.LCP, vitals.CLS, vitals.FID, vitals.FCP, vitals.TTFB, vitals.INP
 */
export function useWebVitals(): Partial<Record<WebVitalMetric["name"], WebVitalMetric>> {
  const [vitals, setVitals] = React.useState<Partial<Record<WebVitalMetric["name"], WebVitalMetric>>>({});

  useEffect(() => {
    // Subscribe to vital updates by polling the transport's stored vitals
    // (lightweight polling rather than a full event emitter)
    const interval = setInterval(() => {
      const transport = getTransport();
      if (!transport) return;
      const stored = (transport as unknown as { vitals?: WebVitalMetric[] }).vitals;
      if (!stored) return;
      const map: Partial<Record<WebVitalMetric["name"], WebVitalMetric>> = {};
      stored.forEach(v => { map[v.name] = v; });
      setVitals(map);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return vitals;
}
