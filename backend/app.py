from flask import Flask, request, jsonify, Response, send_from_directory
import os
import uuid
import json
import requests
from dotenv import load_dotenv

from google import genai
from google.genai import types

# Load .env before anything else
load_dotenv()

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AUDIXA_API_KEY = os.getenv("AUDIXA_API_KEY")

print("[STARTUP] Gemini API key loaded:", bool(GEMINI_API_KEY))
print("[STARTUP] Audixa API key loaded:", bool(AUDIXA_API_KEY))

MODEL = "gemini-2.5-flash"

PROMPT = """
You are the memory inside a photograph.

Observe the image carefully — the people, gestures, expressions, objects, light, and surroundings.

Write a 320–380 word story in first person as if the memory itself is recalling the moment.

The story should unfold naturally like a remembered scene.

Structure the narrative in this order:

1. Begin with vivid sensory details of the environment and atmosphere so the reader feels inside the moment.
2. Gradually notice the people in the scene and describe their expressions, gestures, and interactions.
3. Reflect on the relationships between them and the feeling of connection in the moment.
4. End with a quiet realization about how time will change their lives and why this moment became meaningful.

Writing guidelines:

\u2022 Focus on sensory details and small human moments.
\u2022 Avoid analytical or philosophical openings.
\u2022 Let meaning emerge gradually rather than explaining it early.
\u2022 Write as if the memory is gently guiding the reader through the scene.
\u2022 Maintain a nostalgic and reflective tone.
Prefer simple, natural sentences over elaborate poetic metaphors.

Return ONLY valid JSON with:
{
  "story": "...",
  "scene_description": "...",
  "mood": ["emotion1","emotion2","emotion3"]
}
"""

jobs = {}


def get_genai_client():
    header_key = request.headers.get("Authorization")
    if header_key and header_key.startswith("Bearer "):
        api_key = header_key.split(" ")[1]
    else:
        api_key = GEMINI_API_KEY
    return genai.Client(api_key=api_key)


def generate_audio(text: str, job_id: str) -> str | None:
    """Call Audixa TTS, save mp3 to results/, return relative URL or None on failure."""
    if not AUDIXA_API_KEY:
        print("[TTS] Skipping: AUDIXA_API_KEY not set.")
        return None

    print(f"[TTS] Generating audio for job {job_id} (key present: True)")

    try:
        resp = requests.post(
            "https://api.audixa.ai/v3/tts",
            headers={
                "Authorization": f"Bearer {AUDIXA_API_KEY}",
                "X-API-Key": AUDIXA_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "voice_id": "af_lily",
                "model": "base",
                "format": "mp3",
            },
            timeout=120,
        )

        print(f"[TTS] Response status: {resp.status_code}")

        if not resp.ok:
            print(f"[TTS] Error response body: {resp.text}")
            resp.raise_for_status()

        audio_path = os.path.join(RESULT_FOLDER, f"{job_id}.mp3")
        with open(audio_path, "wb") as f:
            f.write(resp.content)

        print(f"[TTS] Audio saved to {audio_path}")
        return f"/results/{job_id}.mp3"

    except Exception as e:
        print(f"[TTS] Audio generation failed: {e}")
        return None


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["image"]
    job_id = str(uuid.uuid4())
    filepath = os.path.join(UPLOAD_FOLDER, f"{job_id}.jpg")
    file.save(filepath)
    jobs[job_id] = {"status": "uploaded", "image_path": filepath}
    return jsonify({"job_id": job_id})


@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    job_id = data["job_id"]

    if job_id not in jobs:
        return jsonify({"error": "invalid job id"}), 404

    image_path = jobs[job_id]["image_path"]
    client = get_genai_client()

    def stream_response():
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        stream = client.models.generate_content_stream(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                PROMPT,
            ],
        )

        full_text = ""
        for chunk in stream:
            if chunk.text:
                full_text += chunk.text
                yield f"data: {chunk.text}\n\n"

        text = full_text.strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        clean_json = text[start:end]

        try:
            result = json.loads(clean_json)
        except Exception:
            result = {"story": text, "scene_description": "", "mood": []}

        story_text = result.get("story", "")

        # Signal frontend that TTS is now being generated
        yield "data: [AUDIO_GENERATING]\n\n"

        # Block here until audio is ready (or fails) — ensures audio_url is always present in result
        audio_url = generate_audio(story_text, job_id)

        jobs[job_id]["status"] = "done"
        jobs[job_id]["result"] = {
            "story": story_text,
            "scene_description": result.get("scene_description", ""),
            "mood": result.get("mood", []),
            "illustration_url": "https://placehold.co/1024x1024",
            "audio_url": audio_url,
        }

        yield "data: [DONE]\n\n"

    return Response(stream_response(), mimetype="text/event-stream")


@app.route("/result", methods=["GET"])
def result():
    job_id = request.args.get("job_id")
    if job_id not in jobs:
        return jsonify({"error": "invalid job id"}), 404
    if jobs[job_id]["status"] != "done":
        return jsonify({"status": "processing"})
    return jsonify(jobs[job_id]["result"])


@app.route("/results/<path:filename>", methods=["GET"])
def serve_result(filename):
    return send_from_directory(os.path.abspath(RESULT_FOLDER), filename)


if __name__ == "__main__":
    app.run(debug=True)
