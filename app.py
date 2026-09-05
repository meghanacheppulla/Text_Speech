"""
Ask The Frame — Flask app
--------------------------------
Upload an image, type any question about it, get back a written
answer AND a spoken audio answer (like a museum audio guide).
Now with user accounts (register/login) backed by SQLite, and a
per-user history of past questions.

Flow:
  1. User registers / logs in.
  2. User uploads an image + types a question (dynamic, not fixed).
  3. Flask sends the image + question to Gemini (google-genai SDK).
  4. Gemini's text answer is converted to speech with gTTS.
  5. The page shows the text answer, plays the audio, and saves the
     exchange to that user's history.
"""

import os
import uuid
import time

from flask import Flask, render_template, request, jsonify, url_for
from flask_login import login_required, current_user
from PIL import Image
from gtts import gTTS
from google import genai

from extensions import db, login_manager
from models import User, QueryHistory
from auth import auth_bp

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
AUDIO_FOLDER = os.path.join(BASE_DIR, "static", "audio")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["AUDIO_FOLDER"] = AUDIO_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Secret key for sessions — set this via env var in production.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# SQLite by default; point DATABASE_URL at Postgres/MySQL etc. for production.
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager.init_app(app)
app.register_blueprint(auth_bp)

# Put your Gemini API key in an environment variable, e.g.:
#   export GEMINI_API_KEY="your_key_here"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "your_api_key")
client = genai.Client(api_key=GEMINI_API_KEY)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_old_files(folder: str, max_age_seconds: int = 3600) -> None:
    """Delete files older than max_age_seconds so uploads/audio don't pile up."""
    now = time.time()
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_seconds:
            try:
                os.remove(path)
            except OSError:
                pass


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/history")
@login_required
def history():
    entries = (
        QueryHistory.query.filter_by(user_id=current_user.id)
        .order_by(QueryHistory.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template("history.html", entries=entries)


@app.route("/ask", methods=["POST"])
@login_required
def ask():
    """
    Accepts a multipart form with:
      - image: the uploaded image file
      - question: the user's typed question (dynamic, any text)
    Returns JSON with the text answer, the image URL, and the audio URL.
    Also saves the exchange to the logged-in user's history.
    """
    cleanup_old_files(app.config["UPLOAD_FOLDER"])
    cleanup_old_files(app.config["AUDIO_FOLDER"])

    if "image" not in request.files:
        return jsonify({"error": "No image file was uploaded."}), 400

    image_file = request.files["image"]
    question = (request.form.get("question") or "").strip()

    if image_file.filename == "":
        return jsonify({"error": "No image file was selected."}), 400
    if not allowed_file(image_file.filename):
        return jsonify({"error": "Please upload a PNG, JPG, JPEG, or WEBP image."}), 400
    if not question:
        return jsonify({"error": "Please type a question about the image."}), 400

    # Save the uploaded image with a unique name
    unique_id = uuid.uuid4().hex
    ext = image_file.filename.rsplit(".", 1)[1].lower()
    saved_filename = f"{unique_id}.{ext}"
    saved_path = os.path.join(app.config["UPLOAD_FOLDER"], saved_filename)
    image_file.save(saved_path)

    try:
        # Open with PIL for Gemini's multimodal input
        pil_image = Image.open(saved_path)
        pil_image.load()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                pil_image,
                f"Answer this question about the image in 1-3 short, clear "
                f"sentences suitable for reading aloud: {question}",
            ],
        )
        answer_text = (response.text or "").strip()
        if not answer_text:
            answer_text = "I couldn't find an answer to that question in the image."

    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Could not process the image/question: {exc}"}), 500

    # Convert the answer to speech
    audio_filename = f"{unique_id}.mp3"
    audio_path = os.path.join(app.config["AUDIO_FOLDER"], audio_filename)
    try:
        tts = gTTS(text=answer_text, lang="en")
        tts.save(audio_path)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Text-to-speech failed: {exc}"}), 500

    image_url = url_for("static", filename=f"uploads/{saved_filename}")
    audio_url = url_for("static", filename=f"audio/{audio_filename}")

    # Save to this user's history
    entry = QueryHistory(
        user_id=current_user.id,
        question=question,
        answer=answer_text,
        image_path=image_url,
        audio_path=audio_url,
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify(
        {
            "question": question,
            "answer": answer_text,
            "image_url": image_url,
            "audio_url": audio_url,
        }
    )


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(AUDIO_FOLDER, exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
