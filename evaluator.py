import os
import re

from anthropic import Anthropic
from pydantic import BaseModel, Field


class Evaluation(BaseModel):
    naturalness_score: int = Field(ge=0, le=10)
    verdict: str
    needs_improvement: bool
    positive_feedback_ja: str
    improvement_feedback_ja: str
    interpreted_answer: str
    ignored_hesitation: list[str]
    natural_version: str
    why_ja: str


HESITATION_PATTERN = re.compile(
    r"^\s*(?:(um+|uh+|erm+|er+)\b[,.!?…\s-]*)+",
    flags=re.IGNORECASE,
)


def separate_leading_hesitation(user_answer: str) -> tuple[str, list[str]]:
    """Remove only unmistakable leading hesitation sounds for local test mode."""
    match = HESITATION_PATTERN.match(user_answer)
    if not match:
        return user_answer.strip(), []

    hesitation_text = match.group(0)
    ignored = re.findall(r"\b(?:um+|uh+|erm+|er+)\b", hesitation_text, re.IGNORECASE)
    interpreted = user_answer[match.end() :].strip()
    return interpreted or user_answer.strip(), ignored


def normalize_for_comparison(expression: str) -> str:
    """Ignore capitalization, extra spaces, quotes, and sentence-ending punctuation."""
    normalized = expression.strip().casefold()
    normalized = re.sub(r"^[\s\"“”'‘’]+|[\s\"“”'‘’]+$", "", normalized)
    normalized = re.sub(r"[.!?。！？…]+$", "", normalized)
    return " ".join(normalized.split())


def correct_japanese_copy(evaluation: Evaluation) -> Evaluation:
    """Fix known Japanese spelling slips before AI feedback reaches the UI."""
    for field in (
        "verdict",
        "positive_feedback_ja",
        "improvement_feedback_ja",
        "why_ja",
    ):
        value = getattr(evaluation, field)
        setattr(evaluation, field, value.replace("キャジュアル", "カジュアル"))
    return evaluation


def evaluate_answer_locally(question: dict, user_answer: str) -> Evaluation:
    """Return predictable sample feedback without making an API request."""
    interpreted_answer, ignored_hesitation = separate_leading_hesitation(user_answer)
    normalized_answer = interpreted_answer.casefold().rstrip(".!?")
    normalized_jack = question["jacks_pick"].casefold().rstrip(".!?")
    normalized_survival = question["survival"].casefold().rstrip(".!?")

    if normalized_answer == normalized_jack:
        score = 10
        verdict = "とても自然（テスト判定）"
    elif normalized_answer == normalized_survival:
        score = 8
        verdict = "しっかり伝わる（テスト判定）"
    else:
        score = 7
        verdict = "テストモードのサンプル判定"

    return Evaluation(
        naturalness_score=score,
        verdict=verdict,
        needs_improvement=score < 10,
        positive_feedback_ja="意味が伝わる答えになっています。これは画面確認用のテスト判定です。",
        improvement_feedback_ja=f"本番では表現に合わせて具体的に提案します。例：{question['jacks_pick']}",
        interpreted_answer=interpreted_answer,
        ignored_hesitation=ignored_hesitation,
        natural_version=question["jacks_pick"],
        why_ja="テストモードでは固定ルールで表示を確認できます。本番判定を試すときだけClaude APIを有効にしてください。",
    )


SYSTEM_PROMPT = """You are a friendly English coach for Japanese learners.
Judge whether the user's English naturally expresses the given Japanese prompt in casual American conversation.

Product philosophy:
- Simple, natural, conversational English wins.
- Do not reward difficult vocabulary or long sentences merely for sounding advanced.
- Do not require an exact match with Jack's Pick; accept other genuinely natural expressions.
- Consider meaning, grammar, naturalness, and likely conversational context.
- Survival English may communicate successfully even when it is not fully natural.
- Give concise, encouraging feedback in Japanese. Never shame the learner.
- When referring directly to the learner in Japanese feedback, always use 「貴方」. Never call them 「ユーザー」「学習者」「回答者」or write 「あなた」.
- Spell the Japanese loanword for “casual” as 「カジュアル」, never 「キャジュアル」.
- positive_feedback_ja must identify one specific thing the user did well. Do not give generic praise.
- Do not lower the score for capitalization, surrounding quotation marks, extra spaces, or sentence-ending punctuation in a text-field answer.
- A fully natural expression must receive 10. Do not reserve 10 for Jack's Pick or for one preferred wording.
- Set needs_improvement to false if the answer is ready to use without a meaningful wording or grammar change. In that case, give a score of 10, keep natural_version exactly the same as the user's meaningful answer, and state that no correction is needed.
- Set needs_improvement to true only when you can provide a genuinely useful correction. A score of 9 must still have one small but real improvement—not merely different capitalization or punctuation.
- If the score is below 10, improvement_feedback_ja must give one short, actionable improvement.
- For natural_version, make the smallest useful correction while preserving the user's vocabulary, structure, and personal voice wherever possible.
- Do not rewrite the answer to match Jack's Pick. Use Jack's Pick only as one reference; another natural expression can be equally correct.
- Treat unmistakable hesitation sounds such as "um", "uh", "er", and "erm" as speech disfluencies rather than part of the answer.
- Do not ignore meaningful conversational words or phrases such as "well", "like", "I mean", or "I think". They may affect tone or meaning.
- interpreted_answer must contain the meaningful English answer you evaluated, while keeping all meaningful discourse words.
- ignored_hesitation must list only the unmistakable hesitation sounds you excluded. Use an empty list when there are none.
- The verdict must be one short Japanese label, such as 「とても自然」「伝わるけど少し不自然」「要改善」.
- natural_version should be one concise English expression. Keep the user's wording if it is already natural.

Scoring rubric (10 points total):
1. Meaning accuracy — 0 to 3 points: Does it correctly express the Japanese prompt's intended meaning?
2. Conversational naturalness — 0 to 3 points: Would it sound natural in real casual conversation?
3. Grammar and clarity — 0 to 2 points: Is it clear, with no grammar issue that harms communication?
4. Simplicity and situational fit — 0 to 2 points: Is it appropriately simple and well matched to the likely tone and situation?

Score bands:
- 9–10: Ready to use as-is.
- 7–8: Communicates well; a small change could make it more natural.
- 5–6: Meaning is understandable, but the wording or grammar feels unnatural.
- 3–4: Difficult to understand or open to misunderstanding.
- 0–2: Does not adequately express the intended meaning.

Judge the expression itself, not whether it exactly matches Jack's Pick. Return naturalness_score as an integer from 0 to 10.
"""


def evaluate_answer(question: dict, user_answer: str) -> Evaluation:
    client = Anthropic(api_key=_api_key())
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    context = question.get("context_ja", "No additional context provided")
    prompt = f"""Japanese prompt: {question['japanese']}
Situation/context: {context}
User's answer: {user_answer}

Reference examples (not an exact-match answer key):
Survival English: {question['survival']}
Exam-English Monster: {question['exam_monster']}
Jack's Pick: {question['jacks_pick']}

Evaluate the user's answer according to the product philosophy."""

    response = client.messages.parse(
        model=model,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_format=Evaluation,
    )
    if response.parsed_output is None:
        raise RuntimeError("The AI response could not be read. Please try again.")

    result = response.parsed_output
    same_expression = normalize_for_comparison(
        result.natural_version
    ) == normalize_for_comparison(result.interpreted_answer)

    # Keep the score, correction flag, and suggested wording internally consistent.
    if not result.needs_improvement or same_expression:
        result.needs_improvement = False
        result.naturalness_score = 10
        result.natural_version = result.interpreted_answer

    return correct_japanese_copy(result)


def _api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if key:
        return key

    try:
        import streamlit as st

        key = st.secrets.get("ANTHROPIC_API_KEY")
    except (FileNotFoundError, KeyError):
        key = None

    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY が未設定です。README のセットアップ手順を確認してください。"
        )
    return str(key)
