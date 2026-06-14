# Server Guide (server.py)

## Overview

Python HTTP server based on `http.server.SimpleHTTPRequestHandler`. Runs on port **8765**, auto-opens browser on startup.

## Configuration

### VIDEO_ROOTS (required)

Map URL path prefixes to local filesystem directories:
```python
VIDEO_ROOTS = {
    "my-course": r"C:\Users\you\Videos\MyCourse",
}
```

URL `/video/my-course/01_intro/lesson.mp4` resolves to `C:\Users\you\Videos\MyCourse\01_intro\lesson.mp4`.

### Auto-detection (fallback)

If `FALLBACK = True` and `VIDEO_ROOTS` is empty, `auto_detect_video_roots()` scans common drives for directories matching configurable keywords. Edit the `candidates` list in the function to match your course folder names.

### DeepSeek API

Set via environment variable `DEEPSEEK_API_KEY`. Required only for AI summary features.

### Other Constants
- `PORT = 8765` — Server port
- `QUIZ_FILE` — Quiz data output file (relative to server directory)
- `SUMMARIES_FILE` — Summaries cache file (relative to server directory)

## API Endpoints

### Static Files
- `GET /` or `/learn.html` — Serve the SPA
- `GET /video/{prefix}/{path}` — Stream video files from `VIDEO_ROOTS[prefix]`
- `GET /course-data.json` — Course structure
- `GET /summaries_cache.json` — Cached AI summaries

### AI Summary API

**Start async analysis:**
```
POST /api/ai-summary
Body: { "lessonId": "...", "lessonName": "...", "videoUrl": "...", "stageName": "..." }
Response: { "taskId": "uuid" }
```

The server runs Whisper transcription + DeepSeek summarization in a background thread.

**Poll task status:**
```
GET /api/ai-summary/{taskId}
Response: { "status": "pending"|"done"|"error", "message": "..." }
```

When done, `message` contains `{ summary, questions, transcript }`.

### Summaries Cache

**Read all:**
```
GET /api/summaries
Response: { "lesson_id": { "summary", "questions", "transcript", "timestamp" }, ... }
```

**Save/update:**
```
POST /api/summaries
Body: { "lesson_id": { ... }, ... }
```

## Whisper Transcription

The server attempts to use Whisper (via `whisper` Python package) to transcribe video audio. If Whisper isn't installed, it falls back to sending the video content directly to DeepSeek for summarization without transcript.

## Video Path Resolution

```
URL: /video/my-course/01_intro/lesson.mp4
     └─prefix──┘ └──── relative path ─────┘

Resolves to: VIDEO_ROOTS["my-course"] + relative path
           = C:\Users\you\Videos\MyCourse\01_intro\lesson.mp4
```

## Error Handling

- 404 for missing video files with console logging
- CORS headers not needed (same-origin)
- AI task errors captured and returned via poll endpoint

## Running

```bash
python server.py        # Starts on port 8765, opens browser
# Or with AI summary support:
DEEPSEEK_API_KEY=sk-your-api-key python server.py
```
