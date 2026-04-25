"use strict";

const express = require("express");
const fetch   = require("node-fetch");
const router  = express.Router();

/**
 * GET /api/health
 * Returns liveness status of the backend + inference service.
 */
router.get("/", async (req, res) => {
  const inferenceUrl = process.env.INFERENCE_SERVICE_URL || "http://localhost:8000";

  let inferenceStatus = "unreachable";
  try {
    const r = await fetch(`${inferenceUrl}/health`, { timeout: 3000 });
    if (r.ok) inferenceStatus = "ok";
  } catch (_) {
    // inference service down — surface in response but don't crash
  }

  res.json({
    status:    "ok",
    service:   "perfsense-backend",
    inference: inferenceStatus,
    timestamp: new Date().toISOString(),
  });
});

module.exports = router;
