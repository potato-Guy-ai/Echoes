from flask import Flask, request, jsonify, Response, send_from_directory
import os
import uuid
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from google import genai
from google.genai import types

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
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds between retries

PROMPT = """
You are the memory inside a photograph.
Observe the image carefully and write a 320-380 word story in first person as if the memory itself is recalling the moment.
Return ONLY valid JSON with no markdown fences:
{
  "story": "...",
  "scene_description": "a short painterly visual description for image generation",
  "mood": ["emotion1", "emotion2", "emotion3"]
}
"""

jobs = {}
executor = ThreadPoolExecutor(max_workers=4)


def get_imagen_client():
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_audio_with_retry(text: str, job_id: str, on_retry=None):
    """Try Audixa TTS up to MAX_RETRIES times. Returns (url_or_None, error_str_or_None)."""
    if not AUDIXA_API_KEY:
        print("[TTS] Skipping: AUDIXA_API_KEY not set.")
        return None, "AUDIXA_API_KEY not configured"

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[TTS] Attempt {attempt}/{MAX_RETRIES} for job {job_id}")
        try:
            resp = requests.post(
                "https://api.audixa.ai/v3/tts",
                headers={
                    "Authorization": f"Bearer {AUDIXA_API_KEY}",
                    "X-API-Key": AUDIXA_API_KEY,
                    "Content-Type": "application/json",
                },
                json={"text": text, "voice_id": "af_lily", "model": "base", "format": "mp3"},
                timeout=120,
            )
            print(f"[TTS] Response status: {resp.status_code}")
            if not resp.ok:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                print(f"[TTS] Error on attempt {attempt}: {last_error}")
                if attempt < MAX_RETRIES:
                    if on_retry:
                        on_retry(attempt)
                    time.sleep(RETRY_DELAY)
                continue

            audio_path = os.path.join(RESULT_FOLDER, f"{job_id}.mp3")
            with open(audio_path, "wb") as f:
                f.write(resp.content)
            print(f"[TTS] Saved to {audio_path}")
            return f"/results/{job_id}.mp3", None

        except Exception as e:
            last_error = str(e)
            print(f"[TTS] Exception on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                if on_retry:
                    on_retry(attempt)
                time.sleep(RETRY_DELAY)

    print(f"[TTS] All {MAX_RETRIES} attempts failed. Last error: {last_error}")
    return None, last_error


def generate_illustration_with_retry(scene_description: str, job_id: str, on_retry=None):
    """Try Google Imagen 3 up to MAX_RETRIES times. Returns (url_or_None, error_str_or_None)."""
    if not GEMINI_API_KEY:
        print("[IMG] Skipping: GEMINI_API_KEY not set.")
        return None, "GEMINI_API_KEY not configured"

    prompt = (
        f"Painterly illustration, soft warm tones, nostalgic memory style, "
        f"film grain, golden hour light: {scene_description}"
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[IMG] Attempt {attempt}/{MAX_RETRIES} for job {job_id}")
        try:
            client = get_imagen_client()
            response = client.models.generate_images(
                model="imagen-3.0-generate-001",
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="1:1",
                    safety_filter_level="block_only_high",
                    person_generation="allow_adult",
                ),
            )

            if not response.generated_images:
                last_error = "No images returned from Imagen API"
                print(f"[IMG] Error on attempt {attempt}: {last_error}")
                if attempt < MAX_RETRIES:
                    if on_retry:
                        on_retry(attempt)
                    time.sleep(RETRY_DELAY)
                continue

            img_bytes = response.generated_images[0].image.image_bytes
            img_path = os.path.join(RESULT_FOLDER, f"{job_id}.png")
            with open(img_path, "wb") as f:
                f.write(img_bytes)
            print(f"[IMG] Saved to {img_path}")
            return f"/results/{job_id}.png", None

        except Exception as e:
            last_error = str(e)
            print(f"[IMG] Exception on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                if on_retry:
                    on_retry(attempt)
                time.sleep(RETRY_DELAY)

    print(f"[IMG] All {MAX_RETRIES} attempts failed. Last error: {last_error}")
    return None, last_error


@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files["image"]
        job_id = str(uuid.uuid4())
        filepath = os.path.join(UPLOAD_FOLDER, f"{job_id}.jpg")
        file.save(filepath)
        jobs[job_id] = {"status": "uploaded", "image_path": filepath}
        return jsonify({"job_id": job_id})
    except Exception as e:
        print(f"[UPLOAD] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.json
        job_id = data["job_id"]
    except Exception as e:
        print(f"[GENERATE] Bad request: {e}")
        return jsonify({"error": "Invalid request"}), 400

    if job_id not in jobs:
        return jsonify({"error": "invalid job id"}), 404

    image_path = jobs[job_id]["image_path"]

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"[GENERATE] Client init failed: {e}")
        return jsonify({"error": "Failed to init Gemini client"}), 500

    def stream_response():
        # ── 1. Gemini text streaming ──────────────────────────────────────────
        try:
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

        except Exception as e:
            print(f"[GENERATE] Gemini stream error: {e}")
            yield f"data: [ERROR:text:{str(e)[:100]}]\n\n"
            yield "data: [DONE]\n\n"
            return

        # ── 2. Parse JSON ──────────────────────────────────────────────────────
        try:
            text = full_text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            if text.lower().startswith("json"):
                text = text[4:].strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            clean_json = text[start:end] if start != -1 else text
            result = json.loads(clean_json)
        except Exception as e:
            print(f"[JSON] Parse failed: {e} | Raw: {full_text[:300]}")
            result = {"story": full_text, "scene_description": "", "mood": []}

        story_text = result.get("story", "")
        scene_text = result.get("scene_description", "")

        # ── 3. Signal media generation starting ───────────────────────────────
        yield "data: [MEDIA_GENERATING]\n\n"

        # ── 4. Run audio + image in parallel, streaming retry tokens back ─────
        # We use lists to collect SSE tokens from threads safely
        audio_tokens = []
        img_tokens = []

        def audio_retry_cb(attempt):
            audio_tokens.append(f"[AUDIO_RETRY:{attempt}]")

        def img_retry_cb(attempt):
            img_tokens.append(f"[IMG_RETRY:{attempt}]")

        audio_future = executor.submit(generate_audio_with_retry, story_text, job_id, audio_retry_cb)
        img_future = executor.submit(generate_illustration_with_retry, scene_text, job_id, img_retry_cb)

        audio_url, audio_err = audio_future.result(timeout=180)
        img_url, img_err = img_future.result(timeout=180)

        # Flush retry tokens
        for tok in audio_tokens:
            yield f"data: {tok}\n\n"
        for tok in img_tokens:
            yield f"data: {tok}\n\n"

        # Status tokens
        if audio_url:
            yield "data: [AUDIO_OK]\n\n"
        else:
            yield f"data: [AUDIO_FAILED:{(audio_err or 'unknown')[:80]}]\n\n"

        if img_url:
            yield "data: [IMG_OK]\n\n"
        else:
            yield f"data: [IMG_FAILED:{(img_err or 'unknown')[:80]}]\n\n"

        # ── 5. Persist result ─────────────────────────────────────────────────
        jobs[job_id]["status"] = "done"
        jobs[job_id]["result"] = {
            "story": story_text,
            "scene_description": scene_text,
            "mood": result.get("mood", []),
            "illustration_url": img_url,
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
