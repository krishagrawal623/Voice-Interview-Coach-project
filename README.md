# 🎙️ Voice Interview Coach

**Live Demo (Cloud):** [https://voice-interview-coach.streamlit.app/](https://voice-interview-coach.streamlit.app/)

A **voice-based interview practice app** built with **Streamlit**, **OpenAI Whisper**, and **VADER sentiment analysis**.

> ⚠️ **Note:** The live demo is a limited version. To record audio using your microphone, you need to **run the app locally**,because Streamlit Community Cloud cannot access the microphone with `sounddevice`.


## 📌 Features

* 🎤 Record interview answers locally
* 🧠 Transcribe audio using **Whisper**
* 📊 Analyze sentiment (positive/negative/neutral) with **VADER**
* 💻 Clean Streamlit interface
* ☁️ Cloud demo available for preview (playback only, no live recording)

## 🛠️ Installation (Local)

1. **Clone the repository**

```bash
git clone https://github.com/<your-username>/voice-interview-coach.git
cd voice-interview-coach
```

2. **Create a virtual environment (optional)**

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

## 📦 Usage (Local)

Run the app locally to **record your voice and get full features**:

```bash
streamlit run app.py
```

1. Click **Record** to capture your answer.
2. Playback your recording.
3. Whisper transcribes your answer to text.
4. VADER analyzes sentiment and displays the result.

> The live Streamlit Cloud demo only supports **audio playback**, not recording.

---

## 🧩 Requirements

```text
streamlit
sounddevice
scipy
numpy
soundfile
torch
openai-whisper
vaderSentiment
nltk
```

> Make sure `sounddevice` and `scipy` are installed for local microphone recording.


## 📌 Project Structure
```
voice-interview-coach/
├─ app.py                    # Main Streamlit app
├─ requirements.txt          # Dependencies
├─ README.md                 # This documentation
├─ utils/                    
│   ├─ voice_bot_core.py     # Core logic for voice interview processing
│   └─ interviev_question.json        # Predefined questions or config file
```

## 💡 Notes

* Cloud demo is for **preview only**.
* **Local setup is required** for microphone recording and full functionality.
* Whisper downloads the model on first run — this may take a few minutes.
* VADER lexicon is downloaded via NLTK if not already available.


## 🌟 Future Improvements

* Filler word detection (`um`, `ah`)
* Speaking speed analysis
* History tracking and dashboard
* Role-based question practice
