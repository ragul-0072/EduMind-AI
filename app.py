import os
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import requests
import edge_tts
import html
import re
from config import OPENROUTER_API_KEY

app = Flask(__name__)
AUDIO_DIR = "audio_files"
os.makedirs(AUDIO_DIR, exist_ok=True)

VOICE_MAP = {
    "female": "pt-BR-ThalitaMultilingualNeural",
    "male": "en-US-GuyNeural"
}

sessions = {}
quizzes = {}
leaderboard = {}

async def generate_tts(text: str, voice: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{voice}_{timestamp}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    clean_text = re.sub(r'(\*\*|__|\*|_|~~)', '', text)
    clean_text = re.sub(r'#+\s*', '', clean_text)
    clean_text = re.sub(r'```', '', clean_text)
    emoji_pattern = re.compile(
        "[" "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251" "]+", flags=re.UNICODE
    )
    clean_text = emoji_pattern.sub(r'', clean_text)
    clean_text = clean_text.replace("\n", " ")
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    clean_text = html.unescape(clean_text)

    try:
        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(filepath)
        print(f"Audio saved: {filepath}")
        return filepath
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

def tts_auto(text: str, voice_mode="female") -> str:
    voice = VOICE_MAP.get(voice_mode.lower(), VOICE_MAP["female"])
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    filepath = None
    try:
        filepath = loop.run_until_complete(generate_tts(text, voice))
    except Exception as e:
        print(f"TTS Loop Error: {e}")
    finally:
        loop.close()
    return filepath

def ask_ai(prompt: str, max_tokens=1000, json_mode=False):
    url = "[https://openrouter.ai/api/v1/chat/completions](https://openrouter.ai/api/v1/chat/completions)"
    system_prompt = """
    You are an AI Tutor. Be friendly, casual, and encouraging. 
    Use simple, clear language and natural pacing.
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "AI Tutor App"
    }

    data = {
        "model": "x-ai/grok-4-fast",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens
    }

    if json_mode:
        data["messages"][1]["content"] = f"""
        Generate a 5-question multiple choice quiz for the lesson '{prompt}'.
        Respond ONLY with a valid JSON array of 5 question objects:
        [
          {{"question": "...", "options": [...], "answer": "..."}}
        ]
        """
        data["max_tokens"] = 1500
        data["response_format"] = {"type": "json_object"}

    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            return f"Error contacting AI: {response.text}"

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        if json_mode:
            import json
            try:
                if content.startswith("```json"):
                    content = content[7:-3].strip()

                parsed_json = json.loads(content)
                if isinstance(parsed_json, dict) and "questions" in parsed_json:
                    return parsed_json["questions"]
                if isinstance(parsed_json, list):
                    return parsed_json
                return {"error": "Unexpected JSON format", "raw": content}
            except Exception as e:
                print(f"JSON Parse Error: {e}")
                return {"error": "Invalid JSON", "raw": content}
        return content
    except Exception as e:
        print(f"AI Exception: {e}")
        return f"Error: {e}"

@app.route("/")
def home():
    return jsonify({"message": "Welcome to AI Classroom!"})

@app.route("/lesson/<lesson_name>/start", methods=["GET"])
def start_lesson(lesson_name):
    student = request.args.get("student", "Student")
    voice_mode = request.args.get("voice", "female")

    greeting = f"Hello {student}! Welcome to the {lesson_name} lesson."
    prompt = f"You are teaching {student}. Start the lesson '{lesson_name}' with a clear, simple explanation."
    topic = ask_ai(prompt)

    sessions[lesson_name] = {"index": 0, "topic": topic, "student": student, "voice": voice_mode}
    full_text = f"{greeting} {topic}"

    audio_path = tts_auto(full_text, voice_mode)
    audio_url = f"/audio/{os.path.basename(audio_path)}" if audio_path else None

    return jsonify({
        "status": "started",
        "topic": topic,
        "audio_url": audio_url,
        "voice_mode": voice_mode
    })

@app.route("/lesson/<lesson_name>/next", methods=["GET"])
def next_topic(lesson_name):
    if lesson_name not in sessions:
        return jsonify({"error": "Lesson not started"}), 400

    session = sessions[lesson_name]
    session["index"] += 1
    student = session["student"]
    voice_mode = session["voice"]

    prompt = f"Teach topic {session['index']+1} of {lesson_name} to {student}."
    topic = ask_ai(prompt)
    session["topic"] = topic

    audio_path = tts_auto(topic, voice_mode)
    audio_url = f"/audio/{os.path.basename(audio_path)}" if audio_path else None

    return jsonify({
        "status": "next_topic",
        "topic": topic,
        "audio_url": audio_url,
        "voice_mode": voice_mode
    })

@app.route("/lesson/<lesson_name>/doubt", methods=["POST"])
def doubt(lesson_name):
    if lesson_name not in sessions:
        return jsonify({"error": "Lesson not started"}), 400

    data = request.get_json()
    doubt_text = data.get("doubt", "")
    session = sessions[lesson_name]
    voice_mode = data.get("voice", session.get("voice", "female"))
    recap = session["topic"]

    prompt = f"A student asked: '{doubt_text}'. The last topic was '{recap}'. Explain clearly and kindly."
    answer = ask_ai(prompt)
    
    audio_path = tts_auto(answer, voice_mode)
    audio_url = f"/audio/{os.path.basename(audio_path)}" if audio_path else None

    return jsonify({
        "answer": answer,
        "recap": f"We were discussing: {recap}",
        "audio_url": audio_url,
        "voice_mode": voice_mode
    })

@app.route("/lesson/<lesson_name>/quiz", methods=["GET"])
def quiz(lesson_name):
    student = request.args.get("student", "Student")
    voice_mode = request.args.get("voice", "female")

    prompt = f"Generate a quiz for '{lesson_name}' for {student}."
    quiz_data = ask_ai(prompt, json_mode=True)
    if isinstance(quiz_data, dict) and "error" in quiz_data:
        return jsonify(quiz_data), 500
        
    quizzes[lesson_name] = quiz_data

    intro_text = f"Alright {student}, here’s your {lesson_name} quiz. Let’s go!"
    audio_path = tts_auto(intro_text, voice_mode)
    audio_url = f"/audio/{os.path.basename(audio_path)}" if audio_path else None

    return jsonify({
        "quiz": quiz_data,
        "audio_url": audio_url,
        "voice_mode": voice_mode
    })

@app.route("/lesson/<lesson_name>/submit", methods=["POST"])
def submit(lesson_name):
    if lesson_name not in quizzes:
        return jsonify({"error": "Quiz not ready"}), 400

    data = request.get_json()
    student = data.get("student", "Student")
    answers = data.get("answers", [])
    voice_mode = data.get("voice", "female")

    quiz = quizzes[lesson_name]
    score = 0
    results = []

    for i, q in enumerate(quiz):
        correct = q.get("answer")
        given = answers[i] if i < len(answers) else None
        is_correct = (given == correct)
        if is_correct:
            score += 1
        results.append({
            "question": q.get("question"),
            "your_answer": given,
            "correct_answer": correct,
            "is_correct": is_correct
        })

    leaderboard[student] = score
    result_text = f"{student}, you scored {score} out of {len(quiz)}!"
    
    audio_path = tts_auto(result_text, voice_mode)
    audio_url = f"/audio/{os.path.basename(audio_path)}" if audio_path else None

    return jsonify({
        "student": student,
        "score": score,
        "results": results,
        "leaderboard": leaderboard,
        "audio_url": audio_url,
        "voice_mode": voice_mode
    })

@app.route("/lesson/<lesson_name>/voice", methods=["POST"])
def change_voice(lesson_name):
    if lesson_name not in sessions:
        return jsonify({"error": "Lesson not started"}), 400

    new_voice = request.get_json().get("voice", "female")
    if new_voice not in VOICE_MAP:
        return jsonify({"error": "Invalid voice"}), 400

    sessions[lesson_name]["voice"] = new_voice
    confirmation_text = "Okay, I’ve changed my voice!"
    audio_path = tts_auto(confirmation_text, new_voice)
    audio_url = f"/audio/{os.path.basename(audio_path)}" if audio_path else None

    return jsonify({
        "status": "success",
        "voice_mode": new_voice,
        "audio_url": audio_url
    })

@app.route("/audio/<filename>", methods=["GET"])
def serve_audio(filename):
    filepath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(filepath):
        return send_from_directory(AUDIO_DIR, filename)
    return jsonify({"error": "Audio not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)