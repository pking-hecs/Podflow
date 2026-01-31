const express = require('express');
const httpProxy = require('http-proxy');

const app = express();
const proxy = httpProxy.createProxyServer();

const BACKEND_URL = process.env.BACKEND_URL || 'http://user-service:3000';

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'API Gateway running' });
});

// 🔥 THIS ROUTE WAS MISSING / NOT WORKING BEFORE
app.all('/api/*', (req, res) => {
  console.log('Gateway received:', req.method, req.url);

  // remove /api before forwarding
  req.url = req.url.replace('/api', '');

  proxy.web(req, res, { target: BACKEND_URL }, (err) => {
    console.error('Proxy error:', err.message);
    res.status(502).json({ error: 'Backend service unavailable' });
  });
});

app.listen(8080, () => {
  console.log('API Gateway listening on port 8080');
});
