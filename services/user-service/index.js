const express = require('express');

const app = express();
const PORT = 3000;

app.use(express.json());

// Health check (used by monitoring / healing)
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'user-service healthy' });
});

// Sample internal endpoint
app.get('/users', (req, res) => {
  res.json({
    service: 'user-service',
    users: ['alice', 'bob', 'charlie'],
    timestamp: new Date().toISOString()
  });
});

app.listen(PORT, () => {
  console.log(`User-service running on port ${PORT}`);
});
