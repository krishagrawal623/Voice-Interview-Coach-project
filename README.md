# 🎙️ Voice Interview Coach

**🌐 Live Demo:** https://voice-interview-coach.streamlit.app/

A modern **AI-powered Voice Interview Coach** built with **Streamlit**, **OpenAI Whisper**, and **VADER Sentiment Analysis**. The application helps users practice technical and HR interviews by asking interview questions, recording spoken answers, transcribing speech, analyzing communication, and providing instant feedback.

---

# ✨ Features

* 🎤 Record interview answers directly from your browser
* 🔊 Listen to interview questions using browser-compatible speech
* 🧠 Automatic speech-to-text transcription using **OpenAI Whisper**
* 📊 Analyze speaking performance

  * Words Per Minute (WPM)
  * Filler Word Detection
  * Sentiment Analysis
* 💡 Personalized interview feedback
* 📜 Session summary after interview completion
* 🎯 Practice category-wise or mixed interview questions
* ☁️ Fully compatible with Streamlit Community Cloud

---

# 🚀 Live Demo

**Try the application here**

https://voice-interview-coach.streamlit.app/

---

# 🛠️ Technologies Used

* Python
* Streamlit
* OpenAI Whisper
* VADER Sentiment Analysis
* NumPy
* Browser Audio Components
* JSON

---

# 📦 Installation

Clone the repository:

```bash
git clone https://github.com/krishagrawal623/Voice-Interview-Coach-project.git
cd Voice-Interview-Coach-project
```

Create a virtual environment:

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# ▶️ Run the Application

```bash
streamlit run app.py
```

The application will open in your browser.

---

# 🎯 How It Works

1. Select an interview category.
2. Choose the number of questions.
3. Click **Start Question**.
4. Listen to the interview question.
5. Record your spoken answer.
6. Whisper converts your speech to text.
7. The application analyzes:

   * Speaking speed
   * Filler words
   * Sentiment
8. Receive personalized interview feedback.
9. Review your complete interview summary at the end.

---

# 📁 Project Structure

```text
Voice-Interview-Coach-project/
│
├── app.py
├── voice_bot_core.py
├── interview_question.json
├── requirements.txt
├── packages.txt
├── README.md
└── __pycache__/
```

---

# 📊 Analysis Performed

The application evaluates:

* ✅ Words Per Minute (Speaking Pace)
* ✅ Filler Word Usage
* ✅ Sentiment Analysis
* ✅ Overall Communication Quality

---

# 📸 Features Included

* Browser-based Voice Recording
* Speech-to-Text using Whisper
* Sentiment Analysis using VADER
* Automatic Feedback Generation
* Progress Tracking
* Session History
* Interactive Streamlit Interface

---

# 🌟 Future Improvements

* AI-generated interview feedback using Large Language Models
* Resume-based personalized interview questions
* Difficulty levels (Beginner, Intermediate, Advanced)
* PDF Interview Report
* Interview Score Dashboard
* Authentication and User Profiles
* Interview History Database
* Multi-language Interview Support
* Performance Analytics

---

# 👨‍💻 Developer

**Krish Agrawal**

* GitHub: https://github.com/krishagrawal623
* LinkedIn: https://www.linkedin.com/in/krishagrawal75/

---

# ⭐ Support

If you found this project helpful, consider giving it a ⭐ on GitHub.

Contributions, suggestions, and feedback are always welcome!
