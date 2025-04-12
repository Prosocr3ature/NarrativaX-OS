# NarrativaX API Reference

Base URL: `https://yourserver.com/api/`

---

## POST `/classify-story`

Classifies story genre, NSFW flag, and platform

**Body:**
```json
{ "text": "your story content here" }

{
  "genre": "sci-fi",
  "nsfw": "yes",
  "platform": "KDP",
  "vibe": "for fans of Bladerunner meets Mass Effect"
}
