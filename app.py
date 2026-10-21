import json
import base64
import re
import secrets
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from evaluator import evaluate_answer
from quiz import choose_question


APP_DIR = Path(__file__).parent
JACK_ICON_PATH = APP_DIR / "assets" / "jack-channel-icon.png"
APP_ICON_PATH = APP_DIR / "static" / "judge-app-icon.png"
PROFILE_ID_PATTERN = re.compile(r"^EJ-[A-F0-9]{12}$")
PROFILE_STORAGE_KEY = "jack_english_judge_profile_v1"
PROGRESS_STORAGE_PREFIX = "jack_english_judge_progress_v1:"


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


def safe_progress_int(name: str) -> int:
    try:
        return max(0, int(st.query_params.get(name, "0")))
    except (TypeError, ValueError):
        return 0


def install_app_icon() -> None:
    """Install a real favicon and iOS home-screen icon in Streamlit's parent page."""
    components.html(
        """
        <script>
        (() => {
          const iconUrl = new URL("app/static/judge-app-icon.png?v=4", window.parent.document.baseURI).href;
          const documents = [window.parent.document];
          try {
            if (window.top.document !== window.parent.document) documents.push(window.top.document);
          } catch (_) {}
          documents.forEach((doc) => {
            const install = (rel, sizes) => {
              let link = doc.querySelector('link[rel="' + rel + '"]');
              if (!link) {
                link = doc.createElement("link");
                link.rel = rel;
                doc.head.appendChild(link);
              }
              if (sizes) link.sizes = sizes;
              link.href = iconUrl;
            };
            install("apple-touch-icon", "180x180");
            install("icon", "512x512");
          });
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def ensure_profile_id() -> str:
    """Restore or create a private profile without requiring a login."""
    query_id = str(st.query_params.get("jack_id", "")).strip().upper()
    if PROFILE_ID_PATTERN.fullmatch(query_id):
        return query_id

    try:
        cookie_id = str(st.context.cookies.get(PROFILE_STORAGE_KEY, "")).strip().upper()
    except AttributeError:
        cookie_id = ""

    profile_id = (
        cookie_id
        if PROFILE_ID_PATTERN.fullmatch(cookie_id)
        else f"EJ-{secrets.token_hex(6).upper()}"
    )
    st.query_params["jack_id"] = profile_id
    st.rerun()


def load_saved_progress(profile_id: str) -> tuple[int, int, int]:
    if any(name in st.query_params for name in ("p_attempts", "p_score_sum", "p_best")):
        return (
            safe_progress_int("p_attempts"),
            safe_progress_int("p_score_sum"),
            min(10, safe_progress_int("p_best")),
        )

    try:
        raw_progress = str(st.context.cookies.get("jack_english_judge_progress_v1", ""))
    except AttributeError:
        raw_progress = ""

    parts = raw_progress.split("|")
    if len(parts) == 4 and parts[0] == profile_id:
        try:
            return (
                max(0, int(parts[1])),
                max(0, int(parts[2])),
                min(10, max(0, int(parts[3]))),
            )
        except ValueError:
            pass
    return 0, 0, 0


def sync_profile_progress(profile_id: str, attempts: int, score_sum: int, best: int) -> None:
    payload = {
        "profileId": profile_id,
        "attempts": attempts,
        "scoreSum": score_sum,
        "best": best,
    }
    components.html(
        f"""
        <script>
        (() => {{
          const payload = {json.dumps(payload)};
          const ID_KEY = {json.dumps(PROFILE_STORAGE_KEY)};
          const PROGRESS_KEY = {json.dumps(PROGRESS_STORAGE_PREFIX)} + payload.profileId;
          const cookieOptions = "; path=/; max-age=31536000; SameSite=Lax; Secure";
          document.cookie = ID_KEY + "=" + encodeURIComponent(payload.profileId) + cookieOptions;
          document.cookie = "jack_english_judge_progress_v1=" +
            encodeURIComponent([
              payload.profileId,
              payload.attempts,
              payload.scoreSum,
              payload.best
            ].join("|")) + cookieOptions;
          try {{
            localStorage.setItem(ID_KEY, payload.profileId);
            localStorage.setItem(PROGRESS_KEY, JSON.stringify(payload));
          }} catch (_) {{}}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


st.set_page_config(
    page_title="Jackの英語ジャッジ",
    page_icon=str(APP_ICON_PATH),
    layout="centered",
    initial_sidebar_state="collapsed",
)

install_app_icon()
profile_id = ensure_profile_id()
if st.session_state.get("progress_profile_id") != profile_id:
    attempts, score_sum, best = load_saved_progress(profile_id)
    st.session_state.progress_profile_id = profile_id
    st.session_state.progress_attempts = attempts
    st.session_state.progress_score_sum = score_sum
    st.session_state.progress_best = best

sync_profile_progress(
    profile_id,
    st.session_state.progress_attempts,
    st.session_state.progress_score_sum,
    st.session_state.progress_best,
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
    .profile-strip { display: grid; grid-template-columns: 1.35fr repeat(3, 1fr); gap: .55rem; margin: 1rem 0 .45rem; }
    .profile-cell { padding: .72rem .76rem; border: 1px solid #c6dce6; border-radius: 14px;
        background: rgba(255,255,255,.72); box-shadow: 0 5px 14px rgba(35,123,165,.06); }
    .profile-kicker { display: block; color: #5e7380 !important; font-size: .65rem; font-weight: 850; letter-spacing: .08em; }
    .profile-value { display: block; margin-top: .12rem; color: #173c5a !important; font-size: 1rem; font-weight: 900; }
    .profile-cell:first-child { background: linear-gradient(145deg, #173c5a, #225f7e); border-color: #173c5a; }
    .profile-cell:first-child .profile-kicker { color: #a9d8eb !important; }
    .profile-cell:first-child .profile-value { color: #fff9ed !important; letter-spacing: .05em; }
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
        /* Safari/Streamlit's mobile toolbar overlaps the top of the app. */
        .block-container { padding: 3.25rem 1rem 3rem; }
        h1 { font-size: 2.05rem !important; }
        .brand-header { gap: .55rem; align-items: center; }
        .brand-icon { width: 52px; height: 52px; flex-basis: 52px; }
        .brand-title { font-size: 1.65rem; line-height: 1.08; white-space: nowrap; }
        .app-name { font-size: .74rem; line-height: 1.3; padding: .16rem .42rem; margin-bottom: .28rem; }
        .jack-avatar { width: 54px; height: 54px; flex-basis: 54px; }
        .profile-strip { grid-template-columns: repeat(3, 1fr); }
        .profile-cell:first-child { grid-column: 1 / -1; }
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

attempts = st.session_state.progress_attempts
average_score = (st.session_state.progress_score_sum / attempts) if attempts else 0
profile_short = profile_id.removeprefix("EJ-")
st.markdown(
    f'<div class="profile-strip">'
    f'<div class="profile-cell"><span class="profile-kicker">PRIVATE JACK ID</span>'
    f'<span class="profile-value">{profile_short}</span></div>'
    f'<div class="profile-cell"><span class="profile-kicker">JUDGED</span>'
    f'<span class="profile-value">{attempts}</span></div>'
    f'<div class="profile-cell"><span class="profile-kicker">AVERAGE</span>'
    f'<span class="profile-value">{average_score:.1f}</span></div>'
    f'<div class="profile-cell"><span class="profile-kicker">BEST</span>'
    f'<span class="profile-value">{st.session_state.progress_best}</span></div>'
    f'</div>',
    unsafe_allow_html=True,
)
with st.expander("🔐 貴方のJack ID"):
    st.caption("この端末だけの匿名IDです。回答数・平均点・ベストスコアをブラウザに保存します。")
    st.code(profile_id, language=None)
    if st.button("このIDの進捗をリセット", type="secondary"):
        st.session_state.progress_attempts = 0
        st.session_state.progress_score_sum = 0
        st.session_state.progress_best = 0
        st.query_params["p_attempts"] = "0"
        st.query_params["p_score_sum"] = "0"
        st.query_params["p_best"] = "0"
        st.rerun()

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
            score = st.session_state.evaluation.naturalness_score
            st.session_state.progress_attempts += 1
            st.session_state.progress_score_sum += score
            st.session_state.progress_best = max(st.session_state.progress_best, score)
            st.query_params["p_attempts"] = str(st.session_state.progress_attempts)
            st.query_params["p_score_sum"] = str(st.session_state.progress_score_sum)
            st.query_params["p_best"] = str(st.session_state.progress_best)
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
    ):        st.info(f"もっと自然に言うなら： **{evaluation.natural_version}**")

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
        f'<div class="answer-card">🔰 <b>これでもイケる英語</b>'
        f'<span class="card-tagline">ちゃんと伝わる。全然アリ。</span>{question["survival"]}</div>',
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