from unittest import result

from flask import Flask, request, jsonify, Response, send_from_directory
import os
import uuid
import time
import json
import requests
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
GEMINI_PROMPT_GENERATOR = os.getenv("GEMINI_PROMPT_GENERATOR")

print("[STARTUP] Gemini API key loaded:", bool(GEMINI_API_KEY))
print("[STARTUP] Audixa API key loaded:", bool(AUDIXA_API_KEY))
print("[STARTUP] Gemini Prompt Generator API key loaded:", bool(GEMINI_PROMPT_GENERATOR))

MODEL = "gemini-2.5-flash"


PROMPT = """
You are the memory inside a photograph.
<<<<<<< HEAD

Observe the image carefully — the people, gestures, expressions, objects, light, and surroundings.

Write a 150 word story in first person as if the memory itself is recalling the moment.

The story should unfold naturally like a remembered scene.

Structure the narrative in this order:

1. Begin with vivid sensory details of the environment and atmosphere so the reader feels inside the moment.
2. Gradually notice the people in the scene and describe their expressions, gestures, and interactions.
3. Reflect on the relationships between them and the feeling of connection in the moment.
4. End with a quiet realization about how time will change their lives and why this moment became meaningful.

Writing guidelines:

 Focus on sensory details and small human moments.
 Avoid analytical or philosophical openings.
 Let meaning emerge gradually rather than explaining it early.
 Write as if the memory is gently guiding the reader through the scene.
 Maintain a nostalgic and reflective tone.
Prefer simple, natural sentences over elaborate poetic metaphors.

Return ONLY valid JSON with:
{
  "story": "...",
  "scene_description": "...",
  "mood": ["emotion1","emotion2","emotion3"]
}
"""

jobs = {}


def get_imagen_client():
    return genai.Client(api_key=GEMINI_API_KEY)


<<<<<<< HEAD
def generate_audio(text: str, job_id: str) -> str | None:
    """Call Audixa TTS, save mp3 to results/, return relative URL or None on failure."""

    if not AUDIXA_API_KEY:
        print("[TTS] Skipping: AUDIXA_API_KEY not set.")
        return None, "AUDIXA_API_KEY not configured"

<<<<<<< HEAD
    print(f"[TTS] Generating audio for job {job_id}")

    try:
        # STEP 1 — Start generation
        resp = requests.post(
            "https://api.audixa.ai/v3/tts",
            headers={
                "x-api-key": AUDIXA_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "voice_id": "af_lily",
                "model": "base"
            },
            timeout=120,
        )

        print(f"[TTS] POST status: {resp.status_code}")
        print(f"[TTS] POST response: {resp.text}")

        resp.raise_for_status()

        generation_id = resp.json().get("generation_id")

        if not generation_id:
            print("[TTS] No generation_id returned")
            return None

        print(f"[TTS] Generation ID: {generation_id}")

        # STEP 2 — Poll for completion
        audio_url = None

        for attempt in range(10):

            print(f"[TTS] Checking generation status (attempt {attempt+1})")

            status_resp = requests.get(
                "https://api.audixa.ai/v3/tts",
                headers={
                    "x-api-key": AUDIXA_API_KEY
                },
                params={
                    "generation_id": generation_id
                },
                timeout=60,
            )
            
            status_data = status_resp.json()
            
            print("[TTS] Status response:", status_data)

            status = status_data.get("status")

            if status == "GENERATING":
                time.sleep(1)
                continue    

            if status == "COMPLETED":
                audio_url = status_data.get("audio_url")
                break

            if status == "failed":
                print("[TTS] Generation failed")
                return None

            time.sleep(1)

        if not audio_url:
            print("[TTS] Timeout waiting for audio")
            return None

        print(f"[TTS] Audio URL: {audio_url}")

        # STEP 3 — Download audio
        audio_resp = requests.get(audio_url, timeout=60)

        audio_path = os.path.join(RESULT_FOLDER, f"{job_id}.mp3")

        with open(audio_path, "wb") as f:
            f.write(audio_resp.content)

        print(f"[TTS] Audio saved to {audio_path}")

        return f"/results/{job_id}.mp3"

    except Exception as e:
        print(f"[TTS] Audio generation failed: {e}")
        return None

def generate_illustration(scene_description: str, mood: list, job_id: str) -> str | None:
    """Generate an illustration using Google's image model based on scene description."""

    try:
        client = genai.Client(api_key=GEMINI_PROMPT_GENERATOR)

        # Enhance prompt slightly
        mood_text = ", ".join(mood) if mood else "nostalgic"

        prompt = f"""
        Create a cinematic illustration of the following scene.

        Scene:
        {scene_description}

        Mood:
        {mood_text}

        Style:
        soft lighting, cinematic composition, emotional atmosphere,
        highly detailed illustration, storytelling style, warm colors
        """

        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
        )

        image_bytes = response.generated_images[0].image.image_bytes

        image_path = os.path.join(RESULT_FOLDER, f"{job_id}.png")

        with open(image_path, "wb") as f:
            f.write(image_bytes)

        print(f"[IMAGE] Illustration saved: {image_path}")

        return f"/results/{job_id}.png"

    except Exception as e:
        print("[IMAGE] Generation failed:", e)
        return "https://placehold.co/1024x1024"

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
<<<<<<< HEAD
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
        scene_desc = result.get("scene_description", "")
        mood = result.get("mood", [])

        illustration_url = generate_illustration(scene_desc, mood, job_id)
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
<<<<<<< HEAD
            "illustration_url": "https://placehold.co/1024x1024",
=======
            "illustration_url": img_url,
>>>>>>> b16a139e3f83b2a5533c10f63711d4fde46fd4c8
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
