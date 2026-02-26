import os
import json
from typing import List
import streamlit as st

# --- Core functions imported from the logic module ---
from voice_bot_core import (
    macos_say,
    AudioRecorder,
    load_questions,
    transcribe_with_whisper,
    analyze_speech,
    generate_feedback,
)

# --- UI: Hero/Header section ---
def _hero() -> None:
    """Render the top header with title and a quick session stat."""
    left, right = st.columns([0.75, 0.25])
    with left:
        st.markdown("<h1 style='margin-bottom:0'>🗣️ Voice Interview Coach</h1>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#6b7280;margin-top:4px'>Practice interviews with real-time analysis of pace, clarity, and tone.</p>",
            unsafe_allow_html=True
        )
    with right:
        st.metric("Session Questions", f"{st.session_state.get('total_q', 0)}")


# --- UI: Linear progress indicator ---
def _progress(total: int, current: int) -> None:
    """Show interview progress as a progress bar."""
    if total <= 0:
        return
    pct = min(max(current / total, 0.0), 1.0)
    st.progress(pct, text=f"Progress: {current} / {total}")


# --- UI: Main interview flow ---
def run_interview(questions: List[str], seconds_per_answer: int) -> None:
    """Run the interview flow: question -> record -> transcribe -> analyze -> feedback."""
    if "q_index" not in st.session_state:
        st.session_state.q_index = 0
    if "history" not in st.session_state:
        st.session_state.history = []
    if "recorder" not in st.session_state:
        st.session_state.recorder = None
    st.session_state.total_q = len(questions)

    _hero()
    _progress(len(questions), min(st.session_state.q_index, len(questions)))
    st.info("Click ‘Start Question’ to hear it, then ‘Record Answer’. We’ll transcribe and analyze automatically.")

    # --- Completed state ---
    if st.session_state.q_index >= len(questions):
        st.success("Interview complete.")
        if st.session_state.history:
            st.subheader("Session Summary")
            for i, item in enumerate(st.session_state.history, start=1):
                with st.expander(f"Q{i}: {item['question']}"):
                    c1, c2, c3 = st.columns([1, 1, 1])
                    c1.metric("WPM", f"{item['metrics']['wpm']:.1f}")
                    c2.metric("Filler", f"{int(item['metrics']['filler_count'])}")
                    c3.metric("Tone", f"{item['metrics']['sentiment_label']}")
                    st.markdown("---")
                    st.markdown("**Transcript**")
                    st.write(item["transcript"] or "(No speech detected)")
                    st.markdown("**Feedback**")
                    st.info(item["feedback"])
        return

    # --- Active question ---
    question = questions[st.session_state.q_index]
    st.markdown("---")
    st.subheader(f"Question {st.session_state.q_index + 1} of {len(questions)}")
    st.markdown(f"> {question}")

    # --- Controls: play TTS and record ---
    nav_col, col1, col2 = st.columns([0.35, 0.325, 0.325])
    with nav_col:
        can_go_prev = st.session_state.q_index > 0
        if st.button("⬅️ Previous Question", use_container_width=True, disabled=not can_go_prev):
            st.session_state.q_index = max(st.session_state.q_index - 1, 0)
            if st.session_state.history:
                st.session_state.history.pop()
            st.rerun()

    with col1:
        if st.button("🔊 Start Question", use_container_width=True):
            macos_say(f"Question {st.session_state.q_index + 1}. {question}. You have {seconds_per_answer} seconds.")
            st.toast("Speaking question…")

    with col2:
        is_recording = bool(getattr(st.session_state.recorder, "is_recording", False))
        if not is_recording:
            if st.button("🎙️ Start Recording", type="primary", use_container_width=True):
                try:
                    st.session_state.recorder = AudioRecorder(samplerate=16000)
                    st.session_state.recorder.start(max_seconds=seconds_per_answer)
                except Exception as e:
                    st.error(f"Recording failed: {e}")
                    return
                st.toast("Recording started… Click ‘Stop Recording’ when you’re done.")
                st.rerun()
        else:
            if not st.button("⏹️ Stop Recording", type="primary", use_container_width=True):
                st.info("Recording… click ‘Stop Recording’ to finish.")
                return

            try:
                audio_path, dur = st.session_state.recorder.stop()
            except Exception as e:
                st.error(f"Recording failed: {e}")
                return
            finally:
                st.session_state.recorder = None

            # --- Transcription ---
            with st.spinner("Transcribing answer with Whisper…"):
                try:
                    transcript = transcribe_with_whisper(audio_path)
                except Exception as e:
                    st.error(f"Transcription failed: {e}")
                    return
                finally:
                    try:
                        os.remove(audio_path)
                    except Exception:
                        pass

            # --- Analysis + feedback ---
            metrics = analyze_speech(transcript, duration_seconds=float(dur))
            feedback = generate_feedback(metrics)

            tcol, acol, fcol = st.columns([1, 1, 1])
            with tcol:
                st.markdown("**📝 Transcript**")
                st.write(transcript or "(No speech detected)")
            with acol:
                st.markdown("**📊 Analysis**")
                c1, c2, c3 = st.columns(3)
                c1.metric("WPM", f"{metrics['wpm']:.1f}")
                c2.metric("Filler", f"{int(metrics['filler_count'])}")
                c3.metric("Tone", metrics["sentiment_label"])
            with fcol:
                st.markdown("**💡 Feedback**")
                st.info(feedback)

            # Optional spoken feedback
            macos_say("Here is your feedback.")
            macos_say(feedback)

            # Save to history & advance
            st.session_state.history.append({
                "question": question,
                "transcript": transcript,
                "metrics": metrics,
                "feedback": feedback,
            })
            st.session_state.q_index += 1
            st.rerun()


# --- App entrypoint ---
def main() -> None:
    st.set_page_config(page_title="Voice Interview Coach", page_icon="🗣️", layout="wide")

    dataset_path = os.path.join(os.path.dirname(__file__), "interview_question.json")

    with st.sidebar:
        st.header("⚙️ Settings")

        # Load JSON safely
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

    # Reset session if settings changed
    if (
        "prev_category" not in st.session_state
        or st.session_state.prev_category != category
        or "prev_num_questions" not in st.session_state
        or st.session_state.prev_num_questions != num_questions
    ):
        st.session_state.q_index = 0
        st.session_state.history = []
        st.session_state.prev_category = category
        st.session_state.prev_num_questions = num_questions

    # Load questions based on selection
    if category == "mixed":
        questions = load_questions(dataset_path, None, num_questions)
    else:
        questions = load_questions(dataset_path, category, num_questions)

    run_interview(questions, seconds_per_answer)


if __name__ == "__main__":
    main()
