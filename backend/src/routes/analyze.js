"use strict";

const express   = require("express");
const fetch     = require("node-fetch");
const { body, validationResult } = require("express-validator");
const { v4: uuidv4 } = require("uuid");

const router = express.Router();

const INFERENCE_URL = () =>
  (process.env.INFERENCE_SERVICE_URL || "http://localhost:8000");

// ── Shared error handler ──────────────────────────────────────
function validationGuard(req, res, next) {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ error: "Validation failed", details: errors.array() });
  }
  next();
}

// ── Helper: forward to inference service ─────────────────────
async function callInference(endpoint, payload) {
  const url = `${INFERENCE_URL()}${endpoint}`;
  const response = await fetch(url, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(payload),
    timeout: 15000,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Inference service error ${response.status}: ${text}`);
  }
  return response.json();
}

// ─────────────────────────────────────────────────────────────
// POST /api/analyze/diff
// Accept a raw git diff and return a regression prediction.
//
// Body: { diff: string, commit_hash?: string, repo?: string }
// ─────────────────────────────────────────────────────────────
router.post(
  "/diff",
  [
    body("diff")
      .isString().withMessage("diff must be a string")
      .notEmpty().withMessage("diff is required")
      .isLength({ max: 500_000 }).withMessage("diff too large (max 500 KB)"),
    body("commit_hash").optional().isString(),
    body("repo").optional().isString(),
  ],
  validationGuard,
  async (req, res) => {
    const { diff, commit_hash, repo } = req.body;
    const requestId = uuidv4();

    console.log(`[${requestId}] POST /analyze/diff  repo=${repo || "?"} hash=${(commit_hash || "?").slice(0, 8)}`);

    try {
      const prediction = await callInference("/predict/diff", { diff, commit_hash, repo });
      res.json({ request_id: requestId, ...prediction });
    } catch (err) {
      console.error(`[${requestId}] Inference call failed: ${err.message}`);
      res.status(502).json({ error: "Inference service unavailable", detail: err.message });
    }
  }
);

// ─────────────────────────────────────────────────────────────
// POST /api/analyze/features
// Accept pre-extracted features and return a regression prediction.
// Useful when the caller has already run the feature extractor.
//
// Body: { features: FeatureInput, commit_hash?: string, repo?: string }
// ─────────────────────────────────────────────────────────────
router.post(
  "/features",
  [
    body("features")
      .isObject().withMessage("features must be an object")
      .notEmpty().withMessage("features is required"),
    body("commit_hash").optional().isString(),
    body("repo").optional().isString(),
  ],
  validationGuard,
  async (req, res) => {
    const { features, commit_hash, repo } = req.body;
    const requestId = uuidv4();

    console.log(`[${requestId}] POST /analyze/features  repo=${repo || "?"} hash=${(commit_hash || "?").slice(0, 8)}`);

    try {
      const prediction = await callInference("/predict", features);
      res.json({ request_id: requestId, commit_hash, repo, ...prediction });
    } catch (err) {
      console.error(`[${requestId}] Inference call failed: ${err.message}`);
      res.status(502).json({ error: "Inference service unavailable", detail: err.message });
    }
  }
);

// ─────────────────────────────────────────────────────────────
// GET /api/analyze/model-info
// Proxy the model metadata from the inference service.
// ─────────────────────────────────────────────────────────────
router.get("/model-info", async (req, res) => {
  try {
    const info = await fetch(`${INFERENCE_URL()}/model/info`, { timeout: 5000 });
    if (!info.ok) throw new Error(`Inference service returned ${info.status}`);
    res.json(await info.json());
  } catch (err) {
    res.status(502).json({ error: "Could not fetch model info", detail: err.message });
  }
});

module.exports = router;
