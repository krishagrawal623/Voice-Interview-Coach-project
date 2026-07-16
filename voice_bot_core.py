import json
import random
import re
import tempfile
import io
from typing import List, Dict, Optional

# --- Whisper ---
try:
    import whisper
except Exception:
    whisper = None

# Global cache — load once, reuse across reruns
_WHISPER_MODEL: Optional[object] = None

# --- Sentiment analysis ---
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = SentimentIntensityAnalyzer()
except Exception:
    _VADER = None


# ------------------------------
# Load questions from JSON
# ------------------------------
def load_questions(
    dataset_path: str,
    category: Optional[str] = None,
    num_questions: int = 5,
) -> List[str]:
    """Return a shuffled, truncated list of interview questions."""
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
def transcribe_with_whisper(audio_bytes: bytes, model_name: str = "small") -> str:
    """
    Transcribe raw audio bytes with Whisper.

    Accepts raw bytes (e.g. from streamlit-mic-recorder) and writes
    them to a temporary WAV file so Whisper can read them.
    Model is cached globally to avoid reloads between questions.
    """
    global _WHISPER_MODEL

    if whisper is None:
        raise RuntimeError(
            "openai-whisper not installed. Add it to requirements.txt."
        )

    if _WHISPER_MODEL is None:
        _WHISPER_MODEL = whisper.load_model(model_name)

    # Write bytes to a temp file; Whisper needs a file path
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        result = _WHISPER_MODEL.transcribe(tmp_path)
        return result.get("text", "").strip()
    finally:
        import os
        try:
            os.remove(tmp_path)
        except Exception:
            pass


# ------------------------------
# Speech analysis: WPM, fillers, tone
# ------------------------------
def analyze_speech(text: str, duration_seconds: float) -> Dict:
    """Compute WPM, filler-word count, and VADER sentiment."""
    words = text.split()
    num_words = len(words)
    wpm = (num_words / duration_seconds) * 60.0 if duration_seconds > 0 else 0.0

    filler_words = {"um", "uh", "like", "you know", "so", "actually", "basically", "right"}
    lowered = text.lower()
    filler_count = sum(
        len(re.findall(rf"\b{fw}\b", lowered)) for fw in filler_words
    )

    sentiment_score = 0.0
    sentiment_label = "neutral"
    if _VADER is not None:
        vs = _VADER.polarity_scores(text)
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
def generate_feedback(metrics: Dict) -> str:
    """Rule-based feedback based on WPM, filler words, and sentiment."""
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
        parts.append(
            "There were many filler words; pause briefly instead of saying 'um' or 'like'."
        )
    elif filler > 0:
        parts.append("A few filler words appeared; mindful pauses can make answers clearer.")
    else:
        parts.append("Great clarity; almost no filler words detected.")

    # Tone feedback
    if sentiment == "negative":
        parts.append(
            "Your tone skewed negative; inject more confident, positive framing where possible."
        )
    elif sentiment == "positive":
        parts.append("Your tone sounded positive and engaged; keep it up.")
    else:
        parts.append("Tone was neutral; adding enthusiasm can increase engagement.")

    return " ".join(parts)


# ------------------------------
# Browser TTS via Web Speech API
# ------------------------------
def browser_tts_js(text: str) -> str:
    """
    Return a JavaScript snippet that speaks *text* using the browser's
    built-in Web Speech API (SpeechSynthesis). Works on all modern
    browsers and requires no server-side audio library.

    Usage in Streamlit:
        import streamlit.components.v1 as components
        components.html(browser_tts_js("Hello world"), height=0)
    """
    # Escape single quotes so they don't break the JS string literal
    safe_text = text.replace("'", "\\'").replace("\n", " ")
    return f"""
<script>
(function() {{
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();          // stop any previous utterance
  var u = new SpeechSynthesisUtterance('{safe_text}');
  u.rate = 1.0;
  u.pitch = 1.0;
  u.lang = 'en-US';
  window.speechSynthesis.speak(u);
}})();
</script>
"""
