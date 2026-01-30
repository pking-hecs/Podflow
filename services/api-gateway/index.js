const express = require('express');
const httpProxy = require('http-proxy');

const app = express();
const proxy = httpProxy.createProxyServer();

// Backend service name (will work with replicas later)
const BACKEND_URL = process.env.BACKEND_URL || 'http://node-app:3000';

app.use(express.json());

// Health endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'API Gateway running' });
});

// Proxy API requests
app.all('/api/*', (req, res) => {
  proxy.web(req, res, { target: BACKEND_URL }, (err) => {
    console.error('[GATEWAY ERROR]', err.message);
    res.status(502).json({ error: 'Backend service unavailable' });
  });
});

// Start server
const PORT = 8080;
app.listen(PORT, () => {
  console.log(`API Gateway listening on port ${PORT}`);
});
