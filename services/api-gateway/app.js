const express = require("express");
const axios = require("axios");
const { client, gatewayRequestsTotal } = require("./metrics");

const app = express();

const USER_SERVICE_URL =
  process.env.USER_SERVICE_URL || process.env.BACKEND_URL || "http://user-service:3000";

app.use(express.json());

app.get("/health", (req, res) => {
  gatewayRequestsTotal.inc({
    method: req.method,
    route: "/health",
    status: 200
  });

  res.json({ status: "UP", service: "api-gateway" });
});

app.get("/api/users", async (req, res) => {
  try {
    const response = await axios.get(`${USER_SERVICE_URL}/users`);

    gatewayRequestsTotal.inc({
      method: req.method,
      route: "/api/users",
      status: response.status
    });

    res.status(response.status).json(response.data);
  } catch (error) {
    gatewayRequestsTotal.inc({
      method: req.method,
      route: "/api/users",
      status: error.response?.status || 500
    });

    res.status(error.response?.status || 500).json({
      error: "User service unavailable"
    });
  }
});

app.use("/api", async (req, res) => {
  try {
    const response = await axios({
      method: req.method,
      url: `${USER_SERVICE_URL}${req.originalUrl.replace(/^\/api/, "")}`,
      data: req.body
    });

    gatewayRequestsTotal.inc({
      method: req.method,
      route: req.path,
      status: response.status
    });

    res.status(response.status).json(response.data);
  } catch (error) {
    gatewayRequestsTotal.inc({
      method: req.method,
      route: req.path,
      status: error.response?.status || 500
    });

    res.status(error.response?.status || 500).json({
      error: "Gateway error"
    });
  }
});

app.get("/metrics", async (req, res) => {
  res.set("Content-Type", client.register.contentType);
  res.end(await client.register.metrics());
});

module.exports = app;
