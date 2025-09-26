const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const path = require('path');
const fs = require('fs').promises;
const { v4: uuidv4 } = require('uuid');
const pitchDeckService = require('./services/pitchDeckService');

const app = express();
const PORT = process.env.PORT || 3000;

// Security middleware
app.use(helmet());
app.use(cors());

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 50,
  message: 'Too many requests from this IP, please try again later.'
});
app.use(limiter);

// Body parsing middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Create uploads directory
const uploadsDir = path.join(__dirname, 'uploads');
fs.mkdir(uploadsDir, { recursive: true }).catch(console.error);

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    service: 'pitch-deck-downloader-api'
  });
});

// Main download endpoint
app.post('/download-pitch-deck', async (req, res) => {
  try {
    const { url, options = {} } = req.body;
    
    if (!url) {
      return res.status(400).json({
        success: false,
        error: 'URL is required',
        message: 'Please provide a valid pitch.com URL'
      });
    }

    if (!url.includes('pitch.com/v/')) {
      return res.status(400).json({
        success: false,
        error: 'Invalid URL format',
        message: 'Please provide a valid pitch.com presentation URL'
      });
    }

    console.log(`Starting download for URL: ${url}`);
    
    const jobId = uuidv4();
    const result = await pitchDeckService.downloadPitchDeck(url, {
      jobId,
      ...options
    });

    res.json({
      success: true,
      jobId,
      downloadUrl: result.downloadUrl,
      filename: result.filename,
      slideCount: result.slideCount,
      message: 'Pitch deck downloaded successfully'
    });

  } catch (error) {
    console.error('Error downloading pitch deck:', error);
    res.status(500).json({
      success: false,
      error: error.message,
      message: 'Failed to download pitch deck'
    });
  }
});

// Status endpoint
app.get('/status/:jobId', async (req, res) => {
  try {
    const { jobId } = req.params;
    const status = await pitchDeckService.getJobStatus(jobId);
    
    res.json({
      success: true,
      jobId,
      status: status.status,
      progress: status.progress,
      downloadUrl: status.downloadUrl,
      error: status.error
    });
  } catch (error) {
    res.status(404).json({
      success: false,
      error: 'Job not found',
      message: error.message
    });
  }
});

// Download endpoint
app.get('/download/:filename', async (req, res) => {
  try {
    const { filename } = req.params;
    const filePath = path.join(uploadsDir, filename);
    
    await fs.access(filePath);
    res.download(filePath, filename);
  } catch (error) {
    res.status(404).json({
      success: false,
      error: 'File not found',
      message: error.message
    });
  }
});

// n8n webhook endpoint
app.post('/webhook/n8n', async (req, res) => {
  try {
    const { url, options = {} } = req.body;
    
    if (!url) {
      return res.status(400).json({
        success: false,
        error: 'URL is required'
      });
    }

    const jobId = uuidv4();
    const result = await pitchDeckService.downloadPitchDeck(url, {
      jobId,
      ...options
    });

    res.json({
      success: true,
      data: {
        jobId,
        downloadUrl: result.downloadUrl,
        filename: result.filename,
        slideCount: result.slideCount,
        status: 'completed'
      }
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Error handling
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    success: false,
    error: 'Endpoint not found',
    message: 'The requested endpoint does not exist'
  });
});

app.listen(PORT, () => {
  console.log(`Pitch Deck Downloader API running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});

module.exports = app;