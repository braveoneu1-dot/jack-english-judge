import json
import base64
from html import escape
from pathlib import Path

import streamlit as st

from evaluator import evaluate_answer
from quiz import choose_question


APP_DIR = Path(__file__).parent
JACK_ICON_PATH = APP_DIR / "assets" / "jack-channel-icon.png"


def image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def correct_display_copy(evaluation):
    """Correct known Japanese spelling slips, including saved session results."""
    for field in (
        "verdict",
        "positive_feedback_ja",
        "improvement_feedback_ja",
        "why_ja",
    ):
        value = getattr(evaluation, field)
        setattr(evaluation, field, value.replace("キャジュアル", "カジュアル"))
    return evaluation


@st.cache_data
def load_questions() -> list[dict]:
    with (APP_DIR / "questions.json").open(encoding="utf-8") as file:
        questions = json.load(file)
    if len(questions) != 30:
        raise ValueError("questions.json must contain exactly 30 questions.")
    return questions


def reset_for_next_question(questions: list[dict]) -> None:
    previous_id = st.session_state.question["id"]
    st.session_state.question = choose_question(questions, previous_id)
    st.session_state.evaluation = None
    st.session_state.submitted_answer = ""
    st.session_state.answer_version += 1


st.set_page_config(
    page_title="Jackの英語ジャッジ",
    page_icon=str(JACK_ICON_PATH),
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root { --sunset: #f26b4f; --pacific: #237ba5; --sun: #f4bd3f; --cream: #fff9ed; --ink: #20303c; }
    .stApp { background: var(--cream); color: var(--ink); }
    .block-container { max-width: 720px; padding-top: 2.25rem; padding-bottom: 4rem; }
    h1 { color: var(--ink); letter-spacing: -0.045em; line-height: 1.08 !important; }
    .brand-header { display: flex; align-items: center; gap: .9rem; margin: .2rem 0 .1rem; }
    .brand-icon { width: 74px; height: 74px; flex: 0 0 74px; border-radius: 50%; object-fit: cover;
        box-shadow: 0 5px 15px rgba(32, 48, 60, .18); }
    .brand-copy { min-width: 0; display: flex; flex-direction: column; align-items: flex-start; overflow: visible; }
    .app-name { display: inline-flex; color: #a83d2a; background: #ffe5dc; border: 1px solid #f6baa9;
        border-radius: 999px; padding: .22rem .58rem; font-size: .88rem; line-height: 1.3; font-weight: 900;
        letter-spacing: .035em; margin-bottom: .32rem; white-space: nowrap; position: relative; z-index: 1; }
    .brand-title { color: var(--ink); font-size: clamp(2rem, 8vw, 2.75rem); font-weight: 850;
        letter-spacing: -.045em; line-height: 1.08; }
    .brand-tagline { color: var(--pacific); font-size: .95rem; font-weight: 750; font-style: italic; letter-spacing: .02em; margin-bottom: .3rem; }
    .prompt-card { padding: 1.55rem; border-radius: 22px; background: linear-gradient(145deg, #eaf7fb, #dff1f7);
        color: var(--ink); margin: 1rem 0 1.2rem; border: 1px solid #b9dce8; box-shadow: 0 10px 25px rgba(35, 123, 165, .10); }
    .prompt-label { font-size: .85rem; font-weight: 800; color: #286986; margin-bottom: .4rem; }
    .prompt-context { display: inline-block; margin: .1rem 0 .4rem; padding: .28rem .55rem;
        border-radius: 8px; background: rgba(255, 255, 255, .62); color: #416779 !important;
        font-size: .78rem; font-weight: 700; }
    .prompt-card .jp { font-size: clamp(1.85rem, 7vw, 2.65rem); line-height: 1.35; font-weight: 800; letter-spacing: -.025em; }
    .answer-card { padding: 1rem 1.1rem; border-radius: 16px; background: #ffffff; color: var(--ink);
        margin: .7rem 0; border: 1px solid #e7ddcc; box-shadow: 0 5px 16px rgba(72, 54, 28, .05); }
    .card-tagline { display: block; margin: .08rem 0 .48rem 1.65rem; font-size: .78rem;
        line-height: 1.25; font-style: italic; font-weight: 650; color: #6e7780 !important; }
    .jack-card { padding: 1.3rem 1.25rem; border-radius: 20px;
        background: linear-gradient(145deg, #fff1a8, #ffd96a); color: #493300;
        margin: 1rem 0 .75rem; border: 2px solid #e6b72f;
        box-shadow: 0 10px 24px rgba(151, 102, 0, .16); }
    .jack-title { font-size: 1.05rem; letter-spacing: .035em; }
    .jack-heading { display: flex; align-items: center; gap: .75rem; }
    .jack-avatar { width: 62px; height: 62px; flex: 0 0 62px; border-radius: 50%; object-fit: cover;
        border: 3px solid rgba(73, 51, 0, .9); box-shadow: 0 4px 10px rgba(73, 51, 0, .16); }
    .jack-heading-copy { min-width: 0; }
    .jack-expression { display: block; margin-top: .25rem; font-size: clamp(1.35rem, 6vw, 1.7rem);
        line-height: 1.3; font-weight: 900; letter-spacing: -.02em; }
    .compare-label { margin: 1.25rem 0 .35rem; color: #68727b; font-size: .78rem;
        font-weight: 800; letter-spacing: .08em; }
    .feedback-good { padding: .9rem 1rem; border-radius: 14px; background: #e7f5ef; color: #174e35;
        margin: .7rem 0; border: 1px solid #b9e1ce; }
    .feedback-next { padding: .9rem 1rem; border-radius: 14px; background: #fff0e8; color: #71311f;
        margin: .7rem 0; border: 1px solid #f2c5b7; }
    .user-answer-card { padding: 1rem 1.1rem; border-radius: 16px; background: #ffffff; color: var(--ink);
        margin: .25rem 0 1.15rem; border: 2px solid #b9dce8; box-shadow: 0 5px 16px rgba(35, 123, 165, .07); }
    .user-answer-label { display: block; margin-bottom: .3rem; color: #286986 !important;
        font-size: .78rem; font-weight: 850; letter-spacing: .06em; }
    .user-answer-text { display: block; font-size: clamp(1.15rem, 5vw, 1.4rem); line-height: 1.4; font-weight: 800; }
    .jack-note { padding: .9rem 1rem; border-left: 4px solid var(--pacific); color: var(--ink);
        background: #eaf7fb; border-radius: 4px 13px 13px 4px; margin: .75rem 0 1rem; }
    .prompt-card *, .answer-card *, .jack-card *, .feedback-good *, .feedback-next *, .jack-note *, .user-answer-card * { color: inherit; }
    .score { display: flex; align-items: baseline; gap: .35rem; flex-wrap: wrap; color: var(--sunset); letter-spacing: -.04em; }
    .score-label { font-size: clamp(1.2rem, 5.5vw, 1.55rem); font-weight: 800; }
    .score-number { font-size: clamp(2.4rem, 12vw, 3.25rem); line-height: 1; font-weight: 900; }
    .score-total { font-size: clamp(1rem, 4.5vw, 1.3rem); font-weight: 750; opacity: .78; }
    div.stButton > button, div.stFormSubmitButton > button { min-height: 3.15rem; border-radius: 13px; font-weight: 750; }
    div.stFormSubmitButton > button { background: var(--sunset); color: white; border-color: var(--sunset); }
    div.stFormSubmitButton > button:hover { background: #d9563e; color: white; border-color: #d9563e; }
    div[data-testid="stTextInput"] input { min-height: 3.1rem; border-radius: 12px; font-size: 1rem; }
    @media (max-width: 600px) {
        .block-container { padding: 1.15rem 1rem 3rem; }
        h1 { font-size: 2.05rem !important; }
        .brand-header { gap: .55rem; align-items: center; }
        .brand-icon { width: 52px; height: 52px; flex-basis: 52px; }
        .brand-title { font-size: 1.65rem; line-height: 1.08; white-space: nowrap; }
        .app-name { font-size: .74rem; line-height: 1.3; padding: .16rem .42rem; margin-bottom: .28rem; }
        .jack-avatar { width: 54px; height: 54px; flex-basis: 54px; }
        .prompt-card { padding: 1.2rem; border-radius: 17px; }
        .answer-card, .jack-card { padding: .9rem 1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

questions = load_questions()
if "question" not in st.session_state:
    st.session_state.question = choose_question(questions)
if "evaluation" not in st.session_state:
    st.session_state.evaluation = None
if "answer_version" not in st.session_state:
    st.session_state.answer_version = 0
if "submitted_answer" not in st.session_state:
    st.session_state.submitted_answer = ""

question = st.session_state.question
jack_icon_uri = image_data_uri(JACK_ICON_PATH)
answer_key = f"answer_{st.session_state.answer_version}"

st.markdown(
    f'<div class="brand-header"><img class="brand-icon" src="{jack_icon_uri}" alt="Jack">'
    f'<div class="brand-copy"><div class="app-name">Jackの英語ジャッジ</div>'
    f'<div class="brand-title">その英語、いい感じ？</div></div></div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="brand-tagline">Keep it simple. Keep it real.</div>', unsafe_allow_html=True)
st.caption("難しくしなくていい。シンプルで、本当に使える英語を。")
context_html = ""
if question.get("context_ja"):
    context_html = f'<div class="prompt-context">場面：{question["context_ja"]}</div>'
st.markdown(
    f'<div class="prompt-card"><div class="prompt-label">🇯🇵 この日本語、英語でどう言う？</div>'
    f'{context_html}<div class="jp">{question["japanese"]}</div></div>',
    unsafe_allow_html=True,
)

with st.form("answer_form"):
    st.text_input(
        "貴方の答え",
        key=answer_key,
        placeholder="英語を入力、または音声入力…",
        help="iPhoneではキーボードのマイクをタップして音声入力できます。判定前に文字を修正できます。",
        disabled=st.session_state.evaluation is not None,
    )
    st.caption("🎙️ iPhoneではキーボードのマイクから音声入力できます。送信前に文字を確認・修正できます。")
    submitted = st.form_submit_button(
        "この英語をジャッジ",
        use_container_width=True,
        disabled=st.session_state.evaluation is not None,
    )

if submitted:
    answer = st.session_state[answer_key].strip()
    if not answer:
        st.warning("英語を入力してから判定してください。")
    else:
        try:
            st.session_state.submitted_answer = answer
            with st.spinner("英語の自然さを判定中…"):
                st.session_state.evaluation = evaluate_answer(question, answer)
            st.rerun()
        except Exception:
            st.error("うまく判定できませんでした。少し時間をおいて、もう一度試してください。")

evaluation = st.session_state.evaluation
if evaluation:
    evaluation = correct_display_copy(evaluation)
    st.session_state.evaluation = evaluation
    st.divider()
    st.markdown(
        f'<div class="user-answer-card"><span class="user-answer-label">貴方の回答</span>'
        f'<span class="user-answer-text">{escape(st.session_state.submitted_answer)}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="score"><span class="score-label">リアル会話度</span>'
        f'<span class="score-number">{evaluation.naturalness_score}</span>'
        f'<span class="score-total">/ 10</span></div>',
        unsafe_allow_html=True,
    )
    st.subheader(evaluation.verdict)
    st.markdown(
        f'<div class="feedback-good">✅ <b>ここがいい</b><br>{evaluation.positive_feedback_ja}</div>',
        unsafe_allow_html=True,
    )
    if evaluation.needs_improvement:
        st.markdown(
            f'<div class="feedback-next">🔧 <b>もっと自然にするなら</b><br>{evaluation.improvement_feedback_ja}</div>',
            unsafe_allow_html=True,
        )

    if evaluation.ignored_hesitation:
        ignored = ", ".join(evaluation.ignored_hesitation)
        st.caption(f"🎙️ 判定した答え：{evaluation.interpreted_answer}")
        st.caption(f"判定から外した言いよどみ：{ignored}")

    if (
        evaluation.needs_improvement
        and evaluation.natural_version.casefold() != evaluation.interpreted_answer.casefold()
    ):
        st.info(f"もっと自然に言うなら： **{evaluation.natural_version}**")

    st.markdown(
        f'<div class="jack-card"><div class="jack-heading">'
        f'<img class="jack-avatar" src="{jack_icon_uri}" alt="Jack">'
        f'<div class="jack-heading-copy"><span class="jack-title">⭐ <b>JACK’S PICK</b></span>'
        f'<span class="card-tagline">シンプルが、いちばん自然。</span></div></div>'
        f'<span class="jack-expression">{question["jacks_pick"]}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="jack-note">📝 <b>Jackのひとこと</b><br>{question["jack_note"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="compare-label">ほかの言い方と比べる</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="answer-card">🔰 <b>英語サバイバー</b>'
        f'<span class="card-tagline">ギリ伝われば勝ち。</span>{question["survival"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="answer-card">📘 <b>受験英語モンスター</b>'
        f'<span class="card-tagline">正しい。でも、さすがに長い。</span>{question["exam_monster"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"💡 **ここがポイント**  \n{evaluation.why_ja}")

    st.button(
        "次の問題へ →",
        use_container_width=True,
        on_click=reset_for_next_question,
        args=(questions,),
    )

st.caption(f"問題 {question['id']} / 30 · BETA")
