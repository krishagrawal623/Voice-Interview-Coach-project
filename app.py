import os
import json
from typing import List

import streamlit as st
import streamlit.components.v1 as components

# streamlit-mic-recorder: pip install streamlit-mic-recorder
try:
    from streamlit_mic_recorder import mic_recorder
except ImportError:
    mic_recorder = None  # graceful degradation with a clear error message

from voice_bot_core import (
    browser_tts_js,
    load_questions,
    transcribe_with_whisper,
    analyze_speech,
    generate_feedback,
)


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _hero() -> None:
    """Render the top header with title and a quick session stat."""
    left, right = st.columns([0.75, 0.25])
    with left:
        st.markdown(
            "<h1 style='margin-bottom:0'>🗣️ Voice Interview Coach</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='color:#6b7280;margin-top:4px'>"
            "Practice interviews with real-time analysis of pace, clarity, and tone."
            "</p>",
            unsafe_allow_html=True,
        )
    with right:
        st.metric("Session Questions", f"{st.session_state.get('total_q', 0)}")


def _progress(total: int, current: int) -> None:
    """Show interview progress as a Streamlit progress bar."""
    if total <= 0:
        return
    pct = min(max(current / total, 0.0), 1.0)
    st.progress(pct, text=f"Progress: {current} / {total}")


def _speak(text: str) -> None:
    """Speak *text* in the user's browser via the Web Speech API."""
    components.html(browser_tts_js(text), height=0)


# ---------------------------------------------------------------------------
# Main interview flow
# ---------------------------------------------------------------------------

def run_interview(questions: List[str], seconds_per_answer: int) -> None:
    """Run the interview flow: question → record → transcribe → analyze → feedback."""

    # --- Initialise session state ---
    if "q_index" not in st.session_state:
        st.session_state.q_index = 0
    if "history" not in st.session_state:
        st.session_state.history = []
    # Pending audio from mic_recorder that hasn't been processed yet
    if "pending_audio" not in st.session_state:
        st.session_state.pending_audio = None

    st.session_state.total_q = len(questions)

    _hero()
    _progress(len(questions), min(st.session_state.q_index, len(questions)))
    st.info(
        "Click **'🔊 Speak Question'** to hear the question, "
        "then use the **microphone widget** below to record your answer."
    )

    # -----------------------------------------------------------------------
    # Guard: mic_recorder must be importable
    # -----------------------------------------------------------------------
    if mic_recorder is None:
        st.error(
            "**streamlit-mic-recorder** is not installed. "
            "Add `streamlit-mic-recorder` to your requirements.txt and redeploy."
        )
        st.stop()

    # -----------------------------------------------------------------------
    # Interview complete
    # -----------------------------------------------------------------------
    if st.session_state.q_index >= len(questions):
        st.success("🎉 Interview complete!")
        if st.session_state.history:
            st.subheader("Session Summary")
            for i, item in enumerate(st.session_state.history, start=1):
                with st.expander(f"Q{i}: {item['question']}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("WPM", f"{item['metrics']['wpm']:.1f}")
                    c2.metric("Filler", f"{int(item['metrics']['filler_count'])}")
                    c3.metric("Tone", item["metrics"]["sentiment_label"])
                    st.markdown("---")
                    st.markdown("**Transcript**")
                    st.write(item["transcript"] or "(No speech detected)")
                    st.markdown("**Feedback**")
                    st.info(item["feedback"])
        return

    # -----------------------------------------------------------------------
    # Active question
    # -----------------------------------------------------------------------
    question = questions[st.session_state.q_index]
    st.markdown("---")
    st.subheader(f"Question {st.session_state.q_index + 1} of {len(questions)}")
    st.markdown(f"> {question}")

    # -----------------------------------------------------------------------
    # Navigation + TTS button row
    # -----------------------------------------------------------------------
    nav_col, tts_col = st.columns([0.4, 0.6])

    with nav_col:
        can_go_prev = st.session_state.q_index > 0
        if st.button("⬅️ Previous Question", use_container_width=True, disabled=not can_go_prev):
            st.session_state.q_index = max(st.session_state.q_index - 1, 0)
            if st.session_state.history:
                st.session_state.history.pop()
            st.session_state.pending_audio = None
            st.rerun()

    with tts_col:
        if st.button("🔊 Speak Question", use_container_width=True):
            _speak(
                f"Question {st.session_state.q_index + 1}. "
                f"{question}. "
                f"You have {seconds_per_answer} seconds to answer."
            )
            st.toast("Speaking question…")

    # -----------------------------------------------------------------------
    # Mic recorder widget
    # -----------------------------------------------------------------------
    st.markdown("#### 🎙️ Record Your Answer")
    st.caption(
        f"Press **▶ Start** to begin recording. "
        f"Aim for up to **{seconds_per_answer} seconds**. "
        "Press **■ Stop** when finished."
    )

    # mic_recorder returns a dict with keys: 'bytes', 'sample_rate', 'sample_width', 'num_channels'
    # It only returns a NEW value when a new recording has just finished.
    audio_data = mic_recorder(
        start_prompt="▶ Start Recording",
        stop_prompt="■ Stop Recording",
        just_once=True,           # return data once per recording
        use_container_width=True,
        key=f"mic_{st.session_state.q_index}",
    )

    # Store new audio in session state so it survives a rerun
    if audio_data is not None:
        st.session_state.pending_audio = audio_data

    # -----------------------------------------------------------------------
    # Process pending audio
    # -----------------------------------------------------------------------
    if st.session_state.pending_audio is not None:
        audio_bytes: bytes = st.session_state.pending_audio["bytes"]
        sample_rate: int = st.session_state.pending_audio.get("sample_rate", 16000)

        # Derive approximate duration from byte count
        # bytes = samples × channels × sample_width
        num_channels = st.session_state.pending_audio.get("num_channels", 1)
        sample_width = st.session_state.pending_audio.get("sample_width", 2)  # bytes per sample
        num_samples = len(audio_bytes) / (num_channels * sample_width)
        duration_seconds = float(num_samples) / float(sample_rate) if sample_rate > 0 else float(seconds_per_answer)

        # --- Transcription ---
        with st.spinner("Transcribing your answer with Whisper…"):
            try:
                transcript = transcribe_with_whisper(audio_bytes)
            except Exception as e:
                st.error(f"Transcription failed: {e}")
                st.session_state.pending_audio = None
                return

        # --- Analysis + feedback ---
        metrics = analyze_speech(transcript, duration_seconds=duration_seconds)
        feedback = generate_feedback(metrics)

        # --- Display results ---
        st.markdown("---")
        tcol, acol, fcol = st.columns(3)

        with tcol:
            st.markdown("**📝 Transcript**")
            st.write(transcript or "(No speech detected)")

        with acol:
            st.markdown("**📊 Analysis**")
            m1, m2, m3 = st.columns(3)
            m1.metric("WPM", f"{metrics['wpm']:.1f}")
            m2.metric("Filler", f"{int(metrics['filler_count'])}")
            m3.metric("Tone", metrics["sentiment_label"])

        with fcol:
            st.markdown("**💡 Feedback**")
            st.info(feedback)

        # Speak feedback back to the user via browser TTS
        _speak(f"Here is your feedback. {feedback}")

        # --- Persist + advance ---
        st.session_state.history.append(
            {
                "question": question,
                "transcript": transcript,
                "metrics": metrics,
                "feedback": feedback,
            }
        )
        st.session_state.q_index += 1
        st.session_state.pending_audio = None

        if st.button("➡️ Next Question", type="primary", use_container_width=True):
            st.rerun()


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Voice Interview Coach",
        page_icon="🗣️",
        layout="wide",
    )

    dataset_path = os.path.join(os.path.dirname(__file__), "interview_question.json")

    # --- Sidebar settings ---
    with st.sidebar:
        st.header("⚙️ Settings")

        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            st.error(f"Failed to load questions: {e}")
            st.stop()

        categories = ["mixed"] + list(data.keys())
        category = st.selectbox("Interview Type", categories)
        num_questions = st.slider("Number of questions", 1, 10, 5)
        seconds_per_answer = st.slider("Seconds per answer", 5, 120, 30)
        st.markdown("---")
        st.caption("© MADE BY KRISH")

    # --- Reset session if settings changed ---
    settings_changed = (
        "prev_category" not in st.session_state
        or st.session_state.prev_category != category
        or "prev_num_questions" not in st.session_state
        or st.session_state.prev_num_questions != num_questions
    )
    if settings_changed:
        st.session_state.q_index = 0
        st.session_state.history = []
        st.session_state.pending_audio = None
        st.session_state.prev_category = category
        st.session_state.prev_num_questions = num_questions

    # --- Load questions ---
    questions = load_questions(
        dataset_path,
        category=None if category == "mixed" else category,
        num_questions=num_questions,
    )

    run_interview(questions, seconds_per_answer)


if __name__ == "__main__":
    main()
