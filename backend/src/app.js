"use strict";

require("dotenv").config({ path: require("path").join(__dirname, "..", ".env.example") });

const express = require("express");
const cors    = require("cors");

const analyzeRoutes  = require("./routes/analyze");
const healthRoutes   = require("./routes/health");
const metricsRoutes  = require("./routes/metrics");

const app  = express();
const PORT = process.env.PORT || 3001;

// ── Middleware ────────────────────────────────────────────────
app.use(cors());
app.use(express.json({ limit: "5mb" }));  // diffs can be large

// ── Routes ────────────────────────────────────────────────────
app.use("/api/health",   healthRoutes);
app.use("/api/analyze",  analyzeRoutes);
app.use("/api/metrics",  metricsRoutes);

// ── 404 handler ───────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({ error: "Not found", path: req.path });
});

// ── Error handler ─────────────────────────────────────────────
app.use((err, req, res, _next) => {
  console.error("[ERROR]", err.message);
  res.status(500).json({ error: "Internal server error", detail: err.message });
});

// ── Start ─────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`PerfSense API running on http://localhost:${PORT}`);
  console.log(`Inference service: ${process.env.INFERENCE_SERVICE_URL}`);
});

module.exports = app;
