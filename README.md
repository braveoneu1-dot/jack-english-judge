# Jackの英語ジャッジ — BETA

*Keep it simple. Keep it real.*

## 公開アプリ

**▶ [Jackの英語ジャッジを開く](https://jack-english-judge-by-jack.streamlit.app)**

YouTubeの概要欄や固定コメントには、上のStreamlit URLを使用してください。GitHubのURLはソースコードを見るためのページで、視聴者がクイズを使うためのURLとは別です。

**Active project:** the Japanese-language beginner English quiz. This is separate from Jack American Mode, the advanced English-only app.

Deployment: [Streamlit](https://jack-english-judge-by-jack.streamlit.app), with `app.py` as the entry point.

A beginner-friendly Streamlit quiz for learning simple, natural conversational English.

## What it does

- Chooses one of 30 Japanese prompts at random
- Accepts any English answer (not just an exact match)
- Uses AI to score real conversational usefulness from 0–10
- Shows これでもイケる英語, 受験英語モンスター, and Jack’s Pick
- Moves to a different random question with one tap
- Uses a narrow, responsive layout that works well in a mobile browser
- Uses Claude for every submitted answer
- Supports phone keyboard dictation while keeping the transcript visible and editable

## Voice typing

On iPhone, users can tap the microphone on the keyboard and dictate into the answer field. This uses the phone's speech-to-text feature, so it adds no transcription API cost. The transcript stays visible and can be corrected before submission.

The evaluator may ignore unmistakable hesitation sounds such as “um” and “uh,” but it preserves meaningful conversational wording such as “well,” “like,” and “I think.”

## 10-point scoring rubric

- Intended meaning: 3 points
- Conversational naturalness: 3 points
- Grammar and clarity: 2 points
- Simplicity and situational fit: 2 points

Jack’s Pick is a reference, not an exact-match answer key. Other genuinely natural expressions can also receive a high score.

## Setup

1. Open a terminal in this folder.
2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Add your API key. The simplest local option is:

   ```bash
   export ANTHROPIC_API_KEY="your_api_key_here"
   ```

   Alternatively, create `.streamlit/secrets.toml`:

   ```toml
   ANTHROPIC_API_KEY = "your_api_key_here"
   ```

5. Start the app:

   ```bash
   streamlit run app.py
   ```

Streamlit will show a local address. Open it in a browser. The same responsive interface can be opened from an iPhone after deployment; a native iOS app is not required.

## Files

- `questions.json` — the agreed 30-question dataset
- `app.py` — screen and quiz flow
- `evaluator.py` — Claude evaluation and response structure

The API key stays outside the source code. Do not commit `.env` or `.streamlit/secrets.toml`.

## Development and credentials

`quiz.py` selects the next question; `assets/` contains the channel icon; `test_app.py` contains automated checks. Run them with `python -m unittest test_app` after installing dependencies.

`.env.example` is a placeholder reference. The evaluator reads an environment variable or Streamlit secrets; it does not automatically load `.env`. A valid Anthropic key and API credits are required for AI scoring. Keep real keys outside GitHub.

The default branch is `main`. Confirm the deployed commit in Streamlit before assuming the live app matches the newest GitHub commit.

## Yuichi's app directory

| App | Repository | Public app |
| --- | --- | --- |
| Yuichi AI Terminal | [yuichi-ai-terminal](https://github.com/braveoneu1-dot/yuichi-ai-terminal) | Streamlit |
| Household Finance / Harbor | [household-finance-app](https://github.com/braveoneu1-dot/household-finance-app) — private; source import pending | ChatGPT Sites |
| Jackの英語ジャッジ | [jack-english-judge](https://github.com/braveoneu1-dot/jack-english-judge) | [アプリを開く](https://jack-english-judge-by-jack.streamlit.app) |
| Jack American Mode | [jack-american-mode](https://github.com/braveoneu1-dot/jack-american-mode) — private; source import pending | [アプリを開く](https://jack-american-mode.jackaudio.chatgpt.site) |

Verified October 15, 2026: both private repositories exist, but currently contain only placeholder documentation. Their application source has not yet been imported. Sites keeps its own source and saved versions; those are separate from GitHub.
