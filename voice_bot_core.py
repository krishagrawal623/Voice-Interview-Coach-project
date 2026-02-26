import os
import json
import random
import tempfile
import subprocess
import threading
import time
import re
from typing import List, Dict, Tuple, Optional

import numpy as np

# --- Audio libraries ---
try:
    import sounddevice as sd
    from scipy.io.wavfile import write as wav_write
except Exception:
    sd = None
    wav_write = None

# --- Whisper ---
try:
    import whisper
except Exception:
    whisper = None

# Global cache for Whisper model
_WHISPER_MODEL = None

# --- Sentiment analysis ---
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except Exception:
    SentimentIntensityAnalyzer = None


# ------------------------------
# MacOS text-to-speech
# ------------------------------
def macos_say(text: str) -> None:
    try:
        subprocess.run(["say", text], check=False)
    except Exception:
        pass


# ------------------------------
# Audio recording
# ------------------------------
class AudioRecorder:
    """Non-blocking audio recorder for Streamlit sessions."""

    def __init__(self, samplerate: int = 16000):
        if sd is None or wav_write is None:
            raise RuntimeError("sounddevice/scipy not available. Install them first.")
        self.samplerate = int(samplerate)
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._frames: List[np.ndarray] = []
        self._thread: Optional[threading.Thread] = None
        self._max_frames: Optional[int] = None

    @property
    def is_recording(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, max_seconds: int = 30) -> None:
        if self.is_recording:
            return

        self._stop_event.clear()
        with self._lock:
            self._frames = []
        self._max_frames = int(max(1, max_seconds) * self.samplerate)

        def _callback(indata, frames, time_info, status):
            _ = (time_info, status)
            if self._stop_event.is_set():
                raise sd.CallbackStop()
            with self._lock:
                self._frames.append(indata.copy())
                total = sum(x.shape[0] for x in self._frames)
                if total >= self._max_frames:
                    raise sd.CallbackStop()

        def _run():
            try:
                with sd.InputStream(
                    samplerate=self.samplerate,
                    channels=1,
                    dtype="float32",
                    callback=_callback,
                ):
                    while not self._stop_event.is_set():
                        time.sleep(0.05)
            except Exception:
                pass

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> Tuple[str, float]:
        """Stop recording and return (wav_path, duration_seconds)."""
        if not self.is_recording:
            raise RuntimeError("Not recording.")

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)

        with self._lock:
            if not self._frames:
                raise RuntimeError("No audio captured. Check microphone/input device.")
            audio = np.concatenate(self._frames, axis=0)

        audio = np.squeeze(audio)
        max_abs = np.max(np.abs(audio)) or 1.0
        audio_int16 = (audio / max_abs * 32767.0).astype(np.int16)

        tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_wav_path = tmp_wav.name
        tmp_wav.close()
        wav_write(tmp_wav_path, self.samplerate, audio_int16)

        duration = float(audio_int16.shape[0]) / float(self.samplerate)
        return tmp_wav_path, duration


# ------------------------------
# Load questions from JSON
# ------------------------------
def load_questions(dataset_path: str, category: Optional[str] = None, num_questions: int = 5) -> List[str]:
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        questions: List[str] = []

        if isinstance(data, dict):
            if category and category in data:
                questions = data[category]
            else:
                # Mixed mode → collect all questions
                for qlist in data.values():
                    if isinstance(qlist, list):
                        questions.extend(qlist)

        if not questions:
            raise ValueError("No questions found in dataset.")

        random.shuffle(questions)
        return questions[: min(num_questions, len(questions))]

    except Exception as e:
        raise RuntimeError(f"Error loading questions: {e}")


# ------------------------------
# Transcribe audio using Whisper
# ------------------------------
def transcribe_with_whisper(audio_path: str, model_name: str = "small") -> str:
    """
    Transcribe audio with Whisper. Model is cached globally to avoid reloads.
    """
    global _WHISPER_MODEL

    if whisper is None:
        raise RuntimeError("openai-whisper not available. Install it with `pip install openai-whisper`.")

    if _WHISPER_MODEL is None:
        _WHISPER_MODEL = whisper.load_model(model_name)

    result = _WHISPER_MODEL.transcribe(audio_path)
    return result.get("text", "").strip()


# ------------------------------
# Speech analysis: WPM, fillers, tone
# ------------------------------
def analyze_speech(text: str, duration_seconds: float) -> Dict[str, float]:
    words = text.split()
    num_words = len(words)
    wpm = (num_words / duration_seconds) * 60.0 if duration_seconds > 0 else 0.0

    filler_words = {"um", "uh", "like", "you know", "so", "actually", "basically", "right"}
    lowered = text.lower()
    filler_count = sum(len(re.findall(rf"\b{fw}\b", lowered)) for fw in filler_words)

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

    return {
        "wpm": float(wpm),
        "filler_count": float(filler_count),
        "sentiment_compound": float(sentiment_score),
        "sentiment_label": sentiment_label,
        "num_words": float(num_words),
    }


# ------------------------------
# Generate feedback
# ------------------------------
def generate_feedback(metrics: Dict[str, float]) -> str:
    wpm = metrics.get("wpm", 0.0)
    filler = int(metrics.get("filler_count", 0))
    sentiment = metrics.get("sentiment_label", "neutral")

    parts: List[str] = []

    # Pace feedback
    if wpm < 110:
        parts.append("Your pace is a bit slow; try to speak a little faster (~130-160 WPM).")
    elif wpm > 170:
        parts.append("You spoke quite fast; try to slow down slightly (~130-160 WPM).")
    else:
        parts.append("Good pacing; your speaking rate is within a clear range.")

    # Filler words feedback
    if filler > 5:
        parts.append("There were many filler words; pause briefly instead of saying 'um' or 'like'.")
    elif filler > 0:
        parts.append("A few filler words appeared; mindful pauses can make answers clearer.")
    else:
        parts.append("Great clarity; almost no filler words detected.")

    # Tone feedback
    if sentiment == "negative":
        parts.append("Your tone skewed negative; inject more confident, positive framing where possible.")
    elif sentiment == "positive":
        parts.append("Your tone sounded positive and engaged; keep it up.")
    else:
        parts.append("Tone was neutral; adding enthusiasm can increase engagement.")

    return " ".join(parts)
