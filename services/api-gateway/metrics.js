const client = require("prom-client");

// collect default node metrics
client.collectDefaultMetrics();

const gatewayRequestsTotal = new client.Counter({
  name: "gateway_requests_total",
  help: "Total number of requests handled by API Gateway",
  labelNames: ["method", "route", "status"]
});

module.exports = {
  client,
  gatewayRequestsTotal
};