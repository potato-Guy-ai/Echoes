from flask import Flask, request, jsonify, Response, send_from_directory
import os
import uuid
import json
import base64
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
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
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

print("[STARTUP] Gemini API key loaded:", bool(GEMINI_API_KEY))
print("[STARTUP] Audixa API key loaded:", bool(AUDIXA_API_KEY))
print("[STARTUP] Together API key loaded:", bool(TOGETHER_API_KEY))

MODEL = "gemini-2.5-flash"

PROMPT = """
You are the memory inside a photograph.

Observe the image carefully — the people, gestures, expressions, objects, light, and surroundings.

Write a 320-380 word story in first person as if the memory itself is recalling the moment.

The story should unfold naturally like a remembered scene.

Structure the narrative in this order:

1. Begin with vivid sensory details of the environment and atmosphere so the reader feels inside the moment.
2. Gradually notice the people in the scene and describe their expressions, gestures, and interactions.
3. Reflect on the relationships between them and the feeling of connection in the moment.
4. End with a quiet realization about how time will change their lives and why this moment became meaningful.

Writing guidelines:

- Focus on sensory details and small human moments.
- Avoid analytical or philosophical openings.
- Let meaning emerge gradually rather than explaining it early.
- Write as if the memory is gently guiding the reader through the scene.
- Maintain a nostalgic and reflective tone.
- Prefer simple, natural sentences over elaborate poetic metaphors.

Return ONLY valid JSON with no markdown fences, no preamble, nothing else:
{
  "story": "...",
  "scene_description": "...",
  "mood": ["emotion1", "emotion2", "emotion3"]
}
"""

jobs = {}
executor = ThreadPoolExecutor(max_workers=4)


def get_genai_client():
    header_key = request.headers.get("Authorization")
    if header_key and header_key.startswith("Bearer "):
        api_key = header_key.split(" ")[1]
    else:
        api_key = GEMINI_API_KEY
    return genai.Client(api_key=api_key)


def generate_audio(text: str, job_id: str) -> str | None:
    """Call Audixa TTS, save mp3 to results/, return relative URL or None."""
    if not AUDIXA_API_KEY:
        print("[TTS] Skipping: AUDIXA_API_KEY not set.")
        return None

    print(f"[TTS] Generating audio for job {job_id}")
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
            print(f"[TTS] Error: {resp.text}")
            return None

        audio_path = os.path.join(RESULT_FOLDER, f"{job_id}.mp3")
        with open(audio_path, "wb") as f:
            f.write(resp.content)
        print(f"[TTS] Saved to {audio_path}")
        return f"/results/{job_id}.mp3"
    except Exception as e:
        print(f"[TTS] Failed: {e}")
        return None


def generate_illustration(scene_description: str, job_id: str) -> str | None:
    """Generate illustration via Together AI, save png, return URL or None."""
    if not TOGETHER_API_KEY:
        print("[IMG] Skipping: TOGETHER_API_KEY not set.")
        return None

    prompt = (
        f"Painterly illustration, soft warm tones, nostalgic memory style, "
        f"film grain, golden hour light: {scene_description}"
    )
    print(f"[IMG] Generating illustration for job {job_id}")
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
        print(f"[IMG] Response status: {resp.status_code}")
        if not resp.ok:
            print(f"[IMG] Error: {resp.text}")
            return None

        data = resp.json()
        b64 = data["data"][0]["b64_json"]
        img_path = os.path.join(RESULT_FOLDER, f"{job_id}.png")
        with open(img_path, "wb") as f:
            f.write(base64.b64decode(b64))
        print(f"[IMG] Saved to {img_path}")
        return f"/results/{job_id}.png"
    except Exception as e:
        print(f"[IMG] Failed: {e}")
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

        # Parse JSON from accumulated text
        text = full_text.strip()
        # Strip markdown code fences if Gemini wraps it
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        if text.lower().startswith("json"):
            text = text[4:].strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        clean_json = text[start:end] if start != -1 else text

        try:
            result = json.loads(clean_json)
        except Exception as e:
            print(f"[JSON] Parse failed: {e}\nRaw: {text[:300]}")
            result = {"story": text, "scene_description": "", "mood": []}

        story_text = result.get("story", "")
        scene_text = result.get("scene_description", "")

        # Signal frontend: audio + image are now being generated in parallel
        yield "data: [MEDIA_GENERATING]\n\n"

        # Run audio and illustration generation in parallel
        audio_url = None
        illustration_url = None

        futures = {}
        if AUDIXA_API_KEY:
            futures["audio"] = executor.submit(generate_audio, story_text, job_id)
        if TOGETHER_API_KEY:
            futures["image"] = executor.submit(generate_illustration, scene_text, job_id)

        for key, future in futures.items():
            try:
                val = future.result(timeout=150)
                if key == "audio":
                    audio_url = val
                elif key == "image":
                    illustration_url = val
            except Exception as e:
                print(f"[{key.upper()}] Future failed: {e}")

        jobs[job_id]["status"] = "done"
        jobs[job_id]["result"] = {
            "story": story_text,
            "scene_description": scene_text,
            "mood": result.get("mood", []),
            "illustration_url": illustration_url,
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
