import os
import json
import random
import tempfile
import subprocess
from typing import List, Dict, Tuple

import numpy as np

try:
    import sounddevice as sd
    from scipy.io.wavfile import write as wav_write
except Exception:  # pragma: no cover
    sd = None
    wav_write = None

try:
    import whisper
except Exception:  # pragma: no cover
    whisper = None

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except Exception:  # pragma: no cover
    SentimentIntensityAnalyzer = None


def macos_say(text: str) -> None:
    try:
        subprocess.run(["say", text], check=False)
    except Exception:
        pass


def record_audio(seconds: int = 10, samplerate: int = 16000) -> Tuple[str, float]:
    if sd is None or wav_write is None:
        raise RuntimeError("sounddevice/scipy not available. Please install them.")

    audio = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype="float32")
    sd.wait()
    audio = np.squeeze(audio)

    max_abs = np.max(np.abs(audio)) or 1.0
    audio_int16 = (audio / max_abs * 32767.0).astype(np.int16)

    tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp_wav_path = tmp_wav.name
    tmp_wav.close()

    wav_write(tmp_wav_path, samplerate, audio_int16)
    return tmp_wav_path, float(seconds)


def load_questions(dataset_path: str, num_questions: int = 5) -> List[str]:
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        questions: List[str] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    questions.append(item)
                elif isinstance(item, dict):
                    q = item.get("question") or item.get("text")
                    if isinstance(q, str):
                        questions.append(q)
        random.shuffle(questions)
        return questions[:num_questions] if questions else [
            "Tell me about yourself.",
            "Describe a challenging situation and how you handled it.",
            "Why are you interested in this role?",
            "What are your strengths?",
            "Do you have any questions for us?",
        ]
    except Exception:
        return [
            "Tell me about yourself.",
            "Describe a challenging situation and how you handled it.",
            "Why are you interested in this role?",
            "What are your strengths?",
            "Do you have any questions for us?",
        ]


def transcribe_with_whisper(audio_path: str, model_name: str = "small") -> str:
    if whisper is None:
        raise RuntimeError("openai-whisper not available. Please install it.")
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path)
    return result.get("text", "").strip()


def analyze_speech(text: str, duration_seconds: float) -> Dict[str, float]:
    words = text.split()
    num_words = len(words)
    wpm = (num_words / duration_seconds) * 60.0 if duration_seconds > 0 else 0.0

    filler_words = {"um", "uh", "like", "you know", "so", "actually", "basically", "right"}
    lowered = text.lower()
    filler_count = sum(lowered.count(fw) for fw in filler_words)

    sentiment_score = 0.0
    sentiment_label = "neutral"
    if SentimentIntensityAnalyzer is not None:
        analyzer = SentimentIntensityAnalyzer()
        vs = analyzer.polarity_scores(text)
        sentiment_score = vs.get("compound", 0.0)
        if sentiment_score >= 0.2:
            sentiment_label = "positive"
        elif sentiment_score <= -0.2:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

    return {
        "wpm": float(wpm),
        "filler_count": float(filler_count),
        "sentiment_compound": float(sentiment_score),
        "sentiment_label": sentiment_label,
        "num_words": float(num_words),
    }


def generate_feedback(metrics: Dict[str, float]) -> str:
    wpm = metrics.get("wpm", 0.0)
    filler = int(metrics.get("filler_count", 0))
    sentiment = metrics.get("sentiment_label", "neutral")

    parts: List[str] = []

    if wpm < 110:
        parts.append("Your pace is a bit slow; try to speak a little faster (~130-160 WPM).")
    elif wpm > 170:
        parts.append("You spoke quite fast; try to slow down slightly (~130-160 WPM).")
    else:
        parts.append("Good pacing; your speaking rate is within a clear range.")

    if filler > 5:
        parts.append("There were many filler words; pause briefly instead of saying 'um' or 'like'.")
    elif filler > 0:
        parts.append("A few filler words appeared; mindful pauses can make answers clearer.")
    else:
        parts.append("Great clarity; almost no filler words detected.")

    if sentiment == "negative":
        parts.append("Your tone skewed negative; inject more confident, positive framing where possible.")
    elif sentiment == "positive":
        parts.append("Your tone sounded positive and engaged; keep it up.")
    else:
        parts.append("Tone was neutral; adding enthusiasm can increase engagement.")

    return " " .join(parts)
