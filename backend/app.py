from flask import Flask, request, jsonify, Response, send_from_directory
import os
import uuid
import json
import base64
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
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

print("[STARTUP] Gemini API key loaded:", bool(GEMINI_API_KEY))
print("[STARTUP] Audixa API key loaded:", bool(AUDIXA_API_KEY))
print("[STARTUP] Together API key loaded:", bool(TOGETHER_API_KEY))

MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3
RETRY_DELAY = 2

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


def generate_audio_with_retry(text: str, job_id: str, retry_tokens: list):
    """Audixa TTS with up to MAX_RETRIES attempts. Returns (url_or_None, error_or_None)."""
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
            print(f"[TTS] Status: {resp.status_code}")
            if not resp.ok:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                print(f"[TTS] Error attempt {attempt}: {last_error}")
                if attempt < MAX_RETRIES:
                    retry_tokens.append(f"[AUDIO_RETRY:{attempt}]")
                    time.sleep(RETRY_DELAY)
                continue

            audio_path = os.path.join(RESULT_FOLDER, f"{job_id}.mp3")
            with open(audio_path, "wb") as f:
                f.write(resp.content)
            print(f"[TTS] Saved: {audio_path}")
            return f"/results/{job_id}.mp3", None

        except Exception as e:
            last_error = str(e)
            print(f"[TTS] Exception attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                retry_tokens.append(f"[AUDIO_RETRY:{attempt}]")
                time.sleep(RETRY_DELAY)

    print(f"[TTS] All attempts failed. Last error: {last_error}")
    return None, last_error


def generate_illustration_with_retry(scene_description: str, job_id: str, retry_tokens: list):
    """Together AI FLUX image gen with up to MAX_RETRIES attempts. Returns (url_or_None, error_or_None)."""
    if not TOGETHER_API_KEY:
        print("[IMG] Skipping: TOGETHER_API_KEY not set.")
        return None, "TOGETHER_API_KEY not configured"

    prompt = (
        f"Painterly illustration, soft warm tones, nostalgic memory style, "
        f"film grain, golden hour light: {scene_description}"
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[IMG] Attempt {attempt}/{MAX_RETRIES} for job {job_id}")
        try:
            resp = requests.post(
                "https://api.together.xyz/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {TOGETHER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "black-forest-labs/FLUX.1-schnell-Free",
                    "prompt": prompt,
                    "width": 1024,
                    "height": 1024,
                    "steps": 4,
                    "n": 1,
                    "response_format": "b64_json",
                },
                timeout=120,
            )
            print(f"[IMG] Status: {resp.status_code}")
            if not resp.ok:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                print(f"[IMG] Error attempt {attempt}: {last_error}")
                if attempt < MAX_RETRIES:
                    retry_tokens.append(f"[IMG_RETRY:{attempt}]")
                    time.sleep(RETRY_DELAY)
                continue

            data = resp.json()
            b64 = data["data"][0]["b64_json"]
            img_path = os.path.join(RESULT_FOLDER, f"{job_id}.png")
            with open(img_path, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"[IMG] Saved: {img_path}")
            return f"/results/{job_id}.png", None

        except Exception as e:
            last_error = str(e)
            print(f"[IMG] Exception attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                retry_tokens.append(f"[IMG_RETRY:{attempt}]")
                time.sleep(RETRY_DELAY)

    print(f"[IMG] All attempts failed. Last error: {last_error}")
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
        # ── 1. Stream Gemini text ──────────────────────────────────────────────
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

        # ── 3. Signal frontend: media generation starting ─────────────────────
        yield "data: [MEDIA_GENERATING]\n\n"

        # ── 4. Run audio + image in parallel ──────────────────────────────────
        audio_retry_tokens = []
        img_retry_tokens = []

        audio_future = executor.submit(generate_audio_with_retry, story_text, job_id, audio_retry_tokens)
        img_future = executor.submit(generate_illustration_with_retry, scene_text, job_id, img_retry_tokens)

        audio_url, audio_err = audio_future.result(timeout=180)
        img_url, img_err = img_future.result(timeout=180)

        # Flush retry tokens collected during parallel execution
        for tok in audio_retry_tokens:
            yield f"data: {tok}\n\n"
        for tok in img_retry_tokens:
            yield f"data: {tok}\n\n"

        # Status tokens
        yield f"data: {'[AUDIO_OK]' if audio_url else '[AUDIO_FAILED:' + (audio_err or 'unknown')[:80] + ']'}\n\n"
        yield f"data: {'[IMG_OK]' if img_url else '[IMG_FAILED:' + (img_err or 'unknown')[:80] + ']'}\n\n"

        # ── 5. Persist and finish ──────────────────────────────────────────────
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
