require('dotenv').config({ path: require('path').join(__dirname, '../.env') });

const express = require('express');
const path    = require('path');
const fs      = require('fs');

const posterRouter = require('./controllers/posterController');

const app = express();
app.use(express.json({ limit: '2mb' }));

// Ensure temp dir exists at boot
const tempDir = path.join(__dirname, 'temp');
if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });

// API routes
app.use('/api', posterRouter);

// Static serving of generated posters
app.use('/posters', express.static(path.join(__dirname, '../posters')));
app.use('/temp',    express.static(tempDir));

// Health check
app.get('/health', (_req, res) =>
  res.json({ status: 'ok', provider: process.env.AI_PROVIDER, imageBackend: process.env.IMAGE_BACKEND })
);

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`[Boishakhi TV] Poster Engine running → http://localhost:${PORT}`);
  console.log(`  AI Provider : ${process.env.AI_PROVIDER || 'groq'}`);
  console.log(`  Image Backend: ${process.env.IMAGE_BACKEND || 'mock'}`);
});
