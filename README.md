# Ask the Frame

A Flask app: register/log in, upload an image, type any question about it,
and get back a written answer plus a spoken audio answer — no fixed
question list, the user can ask anything. Every question is saved to that
user's history.

- **Vision + reasoning:** Google Gemini (`gemini-2.5-flash`) via `google-genai`
- **Text-to-speech:** `gTTS`
- **Auth:** Flask-Login + Werkzeug password hashing
- **Database:** SQLAlchemy, SQLite by default (swap in Postgres/MySQL via `DATABASE_URL`)
- **Backend:** Flask
- **Frontend:** plain HTML/CSS/JS (no build step)

## Setup

```bash
cd vqa-flask-app
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Environment variables

```bash
export GEMINI_API_KEY="your_key_here"        # from https://aistudio.google.com/apikey
export SECRET_KEY="some-long-random-string"   # used to sign session cookies
# optional — defaults to a local SQLite file (app.db) if not set
export DATABASE_URL="postgresql://user:pass@host/dbname"
```

(Windows: use `set VAR=value` instead of `export`.)

## Run

```bash
python app.py
```

The database tables are created automatically on first run
(`db.create_all()`). Open **http://localhost:5000** — you'll be
redirected to `/login`. Click "Create an account" to register.

## Project structure

```
app.py            Flask app + /ask, /, /history routes (all login-protected)
auth.py           Blueprint: /register, /login, /logout
extensions.py     Shared db / login_manager instances
models.py         User and QueryHistory SQLAlchemy models
templates/
  base.html       Nav bar, flash messages, shared layout
  index.html      Upload + ask UI
  login.html
  register.html
  history.html    Per-user past questions/answers
static/
  css/style.css
  js/app.js       Drag-and-drop, fetch to /ask, audio playback
  uploads/        Saved images (auto-cleaned after 1 hour)
  audio/          Generated MP3 answers (auto-cleaned after 1 hour)
```

## How it works

1. User registers (`/register`) or logs in (`/login`). Passwords are
   hashed with Werkzeug's `generate_password_hash` — never stored in plain text.
2. `/` and `/ask` are protected with `@login_required` from Flask-Login.
3. On the ask page, the user drops/selects an image and types a question,
   submitted via `fetch` to `/ask`.
4. `/ask` saves the image, sends it + the question to Gemini in one
   `generate_content` call, converts the answer to an MP3 with `gTTS`,
   and stores the question/answer/image/audio paths in the `query_history`
   table tied to `current_user.id`.
5. `/history` lists that user's past exchanges, each with its image,
   answer text, and a playable audio clip.

## Database schema

**users**: `id, username, email, password_hash, created_at`
**query_history**: `id, user_id (FK → users.id), question, answer, image_path, audio_path, created_at`

## Notes / things you may want to change

- **Storage:** for production, swap local file storage for S3/Cloud
  Storage — local files won't survive across multiple server instances.
- **Rate limiting:** none included — add `Flask-Limiter` if this will be
  public-facing.
- **Email verification / password reset:** not included — this is a
  minimal username+email+password flow. Add Flask-Mail if you need it.
- **Voice quality:** `gTTS` is basic. For higher-quality speech, swap it
  for Gemini's native TTS model (`gemini-2.5-flash-preview-tts`) or
  another provider like ElevenLabs.
- **File size limit:** capped at 10 MB in `app.py`
  (`MAX_CONTENT_LENGTH`) — adjust as needed.
