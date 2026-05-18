# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Two parallel implementations of the same product — a YouTube URL → Korean blog post generator powered by Gemini AI:

1. **`app.py`** — Streamlit local app (server-side transcript extraction via `youtube-transcript-api`)
2. **`index.html` / `docs/index.html`** — Pure client-side static app for GitHub Pages (calls Gemini REST API directly from the browser; no backend)

`index.html` (root) and `docs/index.html` must always be kept in sync — they are identical copies.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run Streamlit app locally
streamlit run app.py
# Opens at http://localhost:8501

# Copy root index.html to docs/ after editing
cp index.html docs/index.html
```

## Architecture

### Streamlit app (`app.py`)

Flow: `extract_video_id` → `get_video_metadata` (YouTube oEmbed API) → `get_transcript` (youtube-transcript-api) → `build_prompt` → `generate_blog_post` (streaming)

- **Transcript priority**: Korean (`ko`) → English (`en`) → any available language
- **SDK**: `from google import genai` (`google-genai>=2.0.0`). Uses `genai.Client(api_key=...)` then `client.models.generate_content_stream(model="gemini-2.0-flash", contents=prompt)`
- **youtube-transcript-api v1.x** is instance-based: `api = YouTubeTranscriptApi()`, `api.fetch(video_id, languages=[lang])`, transcript entries accessed as `segment.text` (not dict keys)
- API key loaded from `.env` (`GEMINI_API_KEY`) or Streamlit Cloud secrets; falls back to sidebar text input

### Static web app (`index.html`)

- Calls Gemini SSE endpoint directly: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?alt=sse&key=${apiKey}`
- YouTube video passed as `file_data: { file_uri: videoUrl, mime_type: 'video/mp4' }` — Gemini natively processes YouTube URLs, no transcript extraction needed
- Streams response via `ReadableStream` + `TextDecoder`, parses `data: {...}` SSE lines
- `marked.js` (CDN) renders Markdown in real-time during streaming
- User provides their own Gemini API key in the browser (never stored server-side)

### GitHub Pages deployment

- Source: `main` branch, root `/`
- `.nojekyll` file in root disables Jekyll (prevents GitHub Pages from serving README.md instead of index.html)
- Remote: `https://github.com/psh0135-arch/youtube_blog`

## Environment Setup

Copy `.env.example` to `.env` and add a Gemini API key:
```
GEMINI_API_KEY=AIza...
```

Get a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → "Create API key in new project" (important: use "new project" to get free-tier quota; existing projects may have `limit: 0`).
