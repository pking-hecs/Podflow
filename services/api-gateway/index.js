const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");

const app = express();
const PORT = 8080;
const BACKEND_URL = process.env.BACKEND_URL;

// Health check
app.get("/health", (req, res) => {
  res.json({ status: "API Gateway is healthy" });
});

// Proxy all /api requests
app.use(
  "/api",
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    pathRewrite: {
      "^/api": ""
    }
  })
);

app.listen(PORT, "0.0.0.0", () => {
  console.log(`API Gateway running on port ${PORT}`);
  console.log(`Forwarding /api/* to ${BACKEND_URL}`);
});
