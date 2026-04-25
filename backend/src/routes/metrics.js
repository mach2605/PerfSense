"use strict";

const express = require("express");
const { body, validationResult } = require("express-validator");
const { v4: uuidv4 } = require("uuid");

const router = express.Router();

// In-memory store (replace with PostgreSQL in production)
const metricsStore = [];

/**
 * POST /api/metrics
 * Receives a PerfSensePayload from the SDK.
 * Stores it and logs a summary.
 */
router.post(
  "/",
  [
    body("sessionId").isString().notEmpty(),
    body("url").isString().notEmpty(),
    body("timestamp").isNumeric(),
    body("webVitals").isArray(),
    body("componentRenders").isArray(),
  ],
  (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ error: "Validation failed", details: errors.array() });
    }

    const payload  = req.body;
    const recordId = uuidv4();
    const received = new Date().toISOString();

    // Summarise for logging
    const vitalSummary = payload.webVitals.map(v => `${v.name}=${v.value}(${v.rating})`).join(" ");
    console.log(`[metrics] session=${payload.sessionId.slice(0, 12)} vitals=[${vitalSummary}] renders=${payload.componentRenders.length}`);

    // Store (capped at 1000 entries in memory)
    metricsStore.push({ id: recordId, received, ...payload });
    if (metricsStore.length > 1000) metricsStore.shift();

    res.status(202).json({ id: recordId, received });
  }
);

/**
 * GET /api/metrics
 * Returns stored metrics (last 50).
 */
router.get("/", (req, res) => {
  const last50 = metricsStore.slice(-50).reverse();
  res.json({ count: metricsStore.length, records: last50 });
});

module.exports = router;
