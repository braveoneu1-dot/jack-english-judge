# Jackの英語ジャッジ — BETA

*Keep it simple. Keep it real.*

A beginner-friendly Streamlit quiz for learning simple, natural conversational English.

## What it does

- Chooses one of 30 Japanese prompts at random
- Accepts any English answer (not just an exact match)
- Uses AI to score real conversational usefulness from 0–10
- Shows Survival English, Exam-English Monster, and Jack’s Pick
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

Streamlit will show a local address. Open it in a browser. When the app is later deployed, the same responsive interface can be opened from an iPhone without making a native iOS app yet.

## Files

- `questions.json` — the agreed 30-question dataset
- `app.py` — screen and quiz flow
- `evaluator.py` — Claude evaluation and response structure

The API key stays outside the source code. Do not commit `.env` or `.streamlit/secrets.toml`.
