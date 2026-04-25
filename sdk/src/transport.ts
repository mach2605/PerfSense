/**
 * PerfSense SDK — Metric transport
 * Batches metrics and flushes to the backend on an interval
 * and on page hide/unload (using sendBeacon for reliability).
 */

import { PerfSenseConfig, PerfSensePayload, WebVitalMetric, ComponentRenderMetric } from "./types";

function generateSessionId(): string {
  return `ps_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export class Transport {
  private config: Required<PerfSenseConfig>;
  private sessionId: string;
  private vitals: WebVitalMetric[] = [];
  private renders: ComponentRenderMetric[] = [];
  private timer: ReturnType<typeof setInterval> | null = null;
  private active = false;

  constructor(config: PerfSenseConfig) {
    this.config = {
      apiKey:        config.apiKey        ?? "",
      sampleRate:    config.sampleRate    ?? 1.0,
      flushInterval: config.flushInterval ?? 30_000,
      debug:         config.debug         ?? false,
      endpoint:      config.endpoint,
    };
    this.sessionId = generateSessionId();
  }

  start(): void {
    // Honour sample rate
    if (Math.random() > this.config.sampleRate) {
      this.log("Session excluded by sampleRate");
      return;
    }
    this.active = true;
    this.timer = setInterval(() => this.flush("interval"), this.config.flushInterval);
    document.addEventListener("visibilitychange", this.onVisibilityChange);
    window.addEventListener("pagehide", this.onPageHide);
    this.log(`SDK started  session=${this.sessionId}`);
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    document.removeEventListener("visibilitychange", this.onVisibilityChange);
    window.removeEventListener("pagehide", this.onPageHide);
    this.active = false;
  }

  addVital(metric: WebVitalMetric): void {
    if (!this.active) return;
    // Deduplicate same vital (keep latest)
    this.vitals = this.vitals.filter(v => v.name !== metric.name);
    this.vitals.push(metric);
    this.log(`Vital ${metric.name}=${metric.value} (${metric.rating})`);
  }

  addRender(metric: ComponentRenderMetric): void {
    if (!this.active) return;
    const existing = this.renders.find(r => r.componentName === metric.componentName);
    if (existing) {
      existing.renderCount    += metric.renderCount;
      existing.totalRenderTime += metric.totalRenderTime;
      existing.lastRenderTime  = metric.lastRenderTime;
      existing.timestamp       = metric.timestamp;
    } else {
      this.renders.push({ ...metric });
    }
  }

  private buildPayload(): PerfSensePayload {
    return {
      sessionId:        this.sessionId,
      url:              window.location.href,
      userAgent:        navigator.userAgent,
      timestamp:        Date.now(),
      webVitals:        [...this.vitals],
      componentRenders: [...this.renders],
    };
  }

  private flush(reason: string): void {
    if (this.vitals.length === 0 && this.renders.length === 0) return;
    const payload = this.buildPayload();
    const url     = `${this.config.endpoint}/api/metrics`;
    const body    = JSON.stringify(payload);
    this.log(`Flush (${reason}) vitals=${this.vitals.length} renders=${this.renders.length}`);

    // sendBeacon on unload for guaranteed delivery; fetch otherwise
    if (reason === "pagehide" && "sendBeacon" in navigator) {
      navigator.sendBeacon(url, new Blob([body], { type: "application/json" }));
    } else {
      fetch(url, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
      }).catch(err => this.log(`Flush error: ${err.message}`));
    }

    // Clear after send (vitals are idempotent — re-added on next observation)
    this.renders = [];
  }

  private onVisibilityChange = (): void => {
    if (document.visibilityState === "hidden") this.flush("visibility-hidden");
  };

  private onPageHide = (): void => {
    this.flush("pagehide");
    this.stop();
  };

  private log(msg: string): void {
    if (this.config.debug) console.log(`[PerfSense] ${msg}`);
  }
}
