# EDU-MIND AI 🤖📚

EDU-MIND AI is an interactive, personalized AI tutor application designed to make learning engaging and accessible. Built with a Flask backend, the platform leverages advanced Large Language Models (LLMs) to teach custom subjects, answer student doubts in real-time, generate automated quizzes, and provide audio-based learning through Text-to-Speech (TTS) integration.

---

## 🚀 Features

* **Personalized AI Tutoring:** Natural, friendly, and encouraging text explanations tailored to the student's pacing and subject selection.
* **Voice & Text-to-Speech (TTS):** Generates high-quality, real-time speech for lessons, doubts, and quiz results using `edge-tts`. Supports customizable voice profiles (e.g., Male/Female modes).
* **Dynamic Interactive Quizzes:** Automatically structures 5-question multiple-choice tests using strict JSON parsing to evaluate the student's comprehension instantly.
* **Real-time Doubt Clearing:** Context-aware responses that combine the student's question with the immediate lesson recap to provide accurate and helpful answers.
* **Live Score Tracking:** Evaluates submissions instantly and maintains a continuous classroom leaderboard.

---

## 🛠️ Tech Stack

* **Backend Framework:** Flask (Python)
* **AI Integration:** OpenRouter API (utilizing `x-ai/grok-4-fast` or scalable fallback models)
* **Text-to-Speech:** `edge-tts` (Edge Text-to-Speech engine)
* **Data Processing:** `re`, `html` utilities for clean text vocalizations
* **Database/Session Tracking:** Volatile memory tracking (`sessions`, `quizzes`, `leaderboard` dictionaries) ready for transition to standard persistent storage like SQLite.

---

## 📂 Project Structure

```text
edu-mind-ai/
│
├── app.py               # Main Flask server containing API endpoints & core logic
├── config.py            # Local environment configuration variables (API Keys)
├── audio_files/         # Automatically generated directory storing cached MP3s
└── README.md            # Project documentation
