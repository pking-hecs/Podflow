const express = require('express');

const app = express();
const PORT = 3000;

app.get('/', (req, res) => {
  res.json({
    service: 'PodFlow Demo Service',
    status: 'running',
    timestamp: new Date().toISOString()
  });
});

app.get('/health', (req, res) => {
  res.status(200).send('OK');
});

app.listen(PORT, () => {
  console.log(`Service running on port ${PORT}`);
});
