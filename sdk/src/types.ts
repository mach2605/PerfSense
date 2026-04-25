/**
 * PerfSense SDK — Type definitions
 */

export interface PerfSenseConfig {
  /** Backend API endpoint, e.g. "http://localhost:3001" */
  endpoint: string;
  /** Project API key (for future auth) */
  apiKey?: string;
  /** Fraction of sessions to sample. 1.0 = 100%, 0.1 = 10%. Default: 1.0 */
  sampleRate?: number;
  /** How often to flush metrics to backend (ms). Default: 30000 */
  flushInterval?: number;
  /** Enable console debug logging. Default: false */
  debug?: boolean;
}

export interface WebVitalMetric {
  name: "LCP" | "FID" | "CLS" | "FCP" | "TTFB" | "INP";
  value: number;
  rating: "good" | "needs-improvement" | "poor";
  timestamp: number;
}

export interface ComponentRenderMetric {
  componentName: string;
  renderCount: number;
  totalRenderTime: number;  // ms
  lastRenderTime: number;   // ms
  timestamp: number;
}

export interface PerfSensePayload {
  sessionId: string;
  url: string;
  userAgent: string;
  timestamp: number;
  webVitals: WebVitalMetric[];
  componentRenders: ComponentRenderMetric[];
}
