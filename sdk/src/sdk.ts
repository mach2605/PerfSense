/**
 * PerfSense SDK — Core initialisation
 *
 * Usage:
 *   import PerfSense from "@perfsense/sdk";
 *
 *   PerfSense.init({
 *     endpoint:  "http://localhost:3001",
 *     sampleRate: 1.0,
 *     debug: true,
 *   });
 */

import { PerfSenseConfig } from "./types";
import { Transport } from "./transport";
import { collectAllVitals } from "./vitals";

let _transport: Transport | null = null;

/** Returns the active transport instance (null if not initialised). */
export function getTransport(): Transport | null {
  return _transport;
}

const PerfSense = {
  /**
   * Initialise the SDK. Must be called once at app startup,
   * before any components mount.
   */
  init(config: PerfSenseConfig): void {
    if (_transport) {
      console.warn("[PerfSense] Already initialised — ignoring duplicate init()");
      return;
    }
    _transport = new Transport(config);
    _transport.start();

    // Wire up all Web Vitals observers
    collectAllVitals((metric) => {
      _transport?.addVital(metric);
    });

    if (config.debug) {
      console.log("[PerfSense] Initialised", config);
    }
  },

  /**
   * Manually stop the SDK and flush any pending metrics.
   * Useful in test environments or when unmounting a SPA shell.
   */
  stop(): void {
    _transport?.stop();
    _transport = null;
  },

  /**
   * Returns true if the SDK has been initialised.
   */
  isInitialised(): boolean {
    return _transport !== null;
  },
};

export default PerfSense;
