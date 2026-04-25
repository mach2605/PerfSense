/**
 * PerfSense SDK — Core Web Vitals collection
 *
 * Implements LCP, FID, CLS, FCP, TTFB via PerformanceObserver and
 * the Navigation Timing API. No external dependencies.
 *
 * Thresholds per Google Web Vitals spec (2023):
 *   LCP  : good <2500ms,  poor >4000ms
 *   FID  : good <100ms,   poor >300ms
 *   CLS  : good <0.1,     poor >0.25
 *   FCP  : good <1800ms,  poor >3000ms
 *   TTFB : good <800ms,   poor >1800ms
 *   INP  : good <200ms,   poor >500ms
 */

import { WebVitalMetric } from "./types";

type VitalCallback = (metric: WebVitalMetric) => void;

function rating(name: WebVitalMetric["name"], value: number): WebVitalMetric["rating"] {
  const thresholds: Record<string, [number, number]> = {
    LCP:  [2500, 4000],
    FID:  [100,  300],
    CLS:  [0.1,  0.25],
    FCP:  [1800, 3000],
    TTFB: [800,  1800],
    INP:  [200,  500],
  };
  const [good, poor] = thresholds[name] ?? [0, 0];
  if (value <= good) return "good";
  if (value <= poor) return "needs-improvement";
  return "poor";
}

function emit(name: WebVitalMetric["name"], value: number, cb: VitalCallback): void {
  cb({ name, value: Math.round(name === "CLS" ? value * 1000 : value) / (name === "CLS" ? 1000 : 1),
       rating: rating(name, value), timestamp: Date.now() });
}

/** Largest Contentful Paint */
export function observeLCP(cb: VitalCallback): void {
  if (!("PerformanceObserver" in window)) return;
  try {
    let latest = 0;
    const po = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const last = entries[entries.length - 1] as PerformanceEntry & { renderTime?: number; loadTime?: number };
      latest = last.renderTime || last.loadTime || last.startTime;
    });
    po.observe({ type: "largest-contentful-paint", buffered: true });
    // Report on page hide / visibility change
    const report = () => { if (latest > 0) emit("LCP", latest, cb); };
    document.addEventListener("visibilitychange", report, { once: true });
    window.addEventListener("pagehide", report, { once: true });
  } catch (_) { /* observer not supported */ }
}

/** First Input Delay */
export function observeFID(cb: VitalCallback): void {
  if (!("PerformanceObserver" in window)) return;
  try {
    const po = new PerformanceObserver((list) => {
      const entry = list.getEntries()[0] as PerformanceEntry & { processingStart: number };
      if (entry) emit("FID", entry.processingStart - entry.startTime, cb);
    });
    po.observe({ type: "first-input", buffered: true });
  } catch (_) {}
}

/** Cumulative Layout Shift */
export function observeCLS(cb: VitalCallback): void {
  if (!("PerformanceObserver" in window)) return;
  try {
    let clsValue = 0;
    let sessionValue = 0;
    let sessionEntries: PerformanceEntry[] = [];

    const po = new PerformanceObserver((list) => {
      for (const entry of list.getEntries() as Array<PerformanceEntry & { hadRecentInput: boolean; value: number }>) {
        if (!entry.hadRecentInput) {
          const firstEntry = sessionEntries[0];
          const lastEntry  = sessionEntries[sessionEntries.length - 1];
          if (sessionValue &&
              entry.startTime - lastEntry.startTime < 1000 &&
              entry.startTime - firstEntry.startTime < 5000) {
            sessionValue += entry.value;
            sessionEntries.push(entry);
          } else {
            sessionValue = entry.value;
            sessionEntries = [entry];
          }
          if (sessionValue > clsValue) {
            clsValue = sessionValue;
          }
        }
      }
    });
    po.observe({ type: "layout-shift", buffered: true });
    const report = () => emit("CLS", clsValue, cb);
    document.addEventListener("visibilitychange", report, { once: true });
    window.addEventListener("pagehide", report, { once: true });
  } catch (_) {}
}

/** First Contentful Paint */
export function observeFCP(cb: VitalCallback): void {
  if (!("PerformanceObserver" in window)) return;
  try {
    const po = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.name === "first-contentful-paint") {
          emit("FCP", entry.startTime, cb);
          po.disconnect();
          break;
        }
      }
    });
    po.observe({ type: "paint", buffered: true });
  } catch (_) {}
}

/** Time to First Byte (from Navigation Timing) */
export function observeTTFB(cb: VitalCallback): void {
  if (!("performance" in window)) return;
  const onLoad = () => {
    const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    if (nav) emit("TTFB", nav.responseStart - nav.requestStart, cb);
  };
  if (document.readyState === "complete") {
    onLoad();
  } else {
    window.addEventListener("load", onLoad, { once: true });
  }
}

/** Interaction to Next Paint (Chrome 96+) */
export function observeINP(cb: VitalCallback): void {
  if (!("PerformanceObserver" in window)) return;
  try {
    let maxDuration = 0;
    const po = new PerformanceObserver((list) => {
      for (const entry of list.getEntries() as Array<PerformanceEntry & { duration: number }>) {
        if (entry.duration > maxDuration) {
          maxDuration = entry.duration;
        }
      }
    });
    po.observe({ type: "event", buffered: true, durationThreshold: 16 } as PerformanceObserverInit);
    const report = () => { if (maxDuration > 0) emit("INP", maxDuration, cb); };
    document.addEventListener("visibilitychange", report, { once: true });
    window.addEventListener("pagehide", report, { once: true });
  } catch (_) {}
}

/** Collect all vitals, call cb for each one observed. */
export function collectAllVitals(cb: VitalCallback): void {
  observeLCP(cb);
  observeFID(cb);
  observeCLS(cb);
  observeFCP(cb);
  observeTTFB(cb);
  observeINP(cb);
}
