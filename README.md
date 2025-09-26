# Pitch Deck Downloader API

REST API for downloading pitch decks from pitch.com, optimized for Render.com deployment.

## API Endpoints

- `POST /download-pitch-deck` - Download pitch deck
- `GET /status/:jobId` - Check job status  
- `GET /download/:filename` - Download PDF
- `POST /webhook/n8n` - n8n webhook
- `GET /health` - Health check

## Usage

```bash
curl -X POST https://your-app.onrender.com/webhook/n8n \
  -H "Content-Type: application/json" \
  -d '{"url": "https://pitch.com/v/yzi-ui28ms"}'
```

## n8n Integration

Use the `/webhook/n8n` endpoint with POST method and JSON body:
```json
{
  "url": "https://pitch.com/v/yzi-ui28ms"
}
```