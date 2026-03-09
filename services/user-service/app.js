const express = require("express");
const { client, httpRequestCounter } = require("./metrics");

const app = express();

app.use(express.json());

app.get("/health", (req, res) => {
  httpRequestCounter.inc({
    method: req.method,
    route: "/health",
    status: 200
  });

  res.json({ status: "UP", service: "user-service" });
});

app.get("/users", (req, res) => {
  httpRequestCounter.inc({
    method: req.method,
    route: "/users",
    status: 200
  });

  res.json({
    service: "user-service",
    users: ["alice", "bob", "charlie"],
    timestamp: new Date().toISOString()
  });
});

app.get("/metrics", async (req, res) => {
  res.set("Content-Type", client.register.contentType);
  res.end(await client.register.metrics());
});

module.exports = app;
