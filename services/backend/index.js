const express = require("express");

const app = express();
const PORT = 3000;

app.get("/", (req, res) => {
  console.log("Request received at backend");
  res.json({ message: "Hello from backend service" });
});

app.get("/health", (req, res) => {
  res.json({ status: "Backend healthy" });
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Backend running on port ${PORT}`);
});
