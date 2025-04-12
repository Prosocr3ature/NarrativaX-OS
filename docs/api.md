# NarrativaX API Reference

Base URL: `https://yourserver.com/api/`

---

## POST `/classify-story`

Classifies story genre, NSFW flag, and best-fit publishing platform.

### Request Body
```json
{
  "text": "Your story or chapter text goes here..."
}
```

### Example Response
```json
{
  "genre": "sci-fi",
  "nsfw": "yes",
  "platform": "KDP",
  "vibe": "for fans of Bladerunner meets Mass Effect"
}
```

---

## POST `/generate-book`

Generates a full book or chapter-by-chapter sequence using GPT-4 or local LLMs.

### Request Body
```json
{
  "prompt": "A romance between an AI and a human spy",
  "chapters": 5,
  "style": "dark, poetic, emotionally charged"
}
```

### Example Response
```json
{
  "title": "Hearts of Steel",
  "chapters": [
    "Chapter 1: Memory Glitch",
    "Chapter 2: Forbidden Firewall",
    "Chapter 3: Code & Confession",
    "Chapter 4: The Last Override",
    "Chapter 5: Eternal Return"
  ]
}
```

---

## POST `/voice-narrate`

Uses ElevenLabs or Bark to convert text to narrated MP3 audio.

### Request Body
```json
{
  "text": "Welcome to NarrativaX...",
  "voice": "Rachel",
  "emotion": "neutral"
}
```

### Example Response
```json
{
  "audio_url": "https://yourcdn.com/audio/abcd1234.mp3"
}
```

---

## POST `/publish-kdp`

Auto-publishes your content to Amazon KDP with meta-tags and cover.

### Request Body
```json
{
  "title": "Cyber Lovers",
  "author": "Anonymous",
  "cover_url": "https://yourcdn.com/images/cover.png",
  "content": "<EPUB content here>"
}
```

### Example Response
```json
{
  "status": "success",
  "kdp_url": "https://amazon.com/dp/B0XXXXXX"
}
```

---

## Authentication

Use your API key in the `Authorization` header:

```
Authorization: Bearer YOUR_API_KEY
```

---

> Need help? Open an issue or join the [NarrativaX Discord](https://discord.gg/YOUR-LINK)
