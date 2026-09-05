import json
import unittest
from pathlib import Path

from quiz import choose_question
from evaluator import (
    Evaluation,
    correct_japanese_copy,
    evaluate_answer_locally,
    normalize_for_comparison,
    separate_leading_hesitation,
)


class QuestionDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parent / "questions.json"
        cls.questions = json.loads(path.read_text(encoding="utf-8"))

    def test_dataset_has_30_unique_questions(self):
        self.assertEqual(len(self.questions), 30)
        self.assertEqual(len({item["id"] for item in self.questions}), 30)

    def test_every_question_has_required_text(self):
        required = {"id", "japanese", "survival", "exam_monster", "jacks_pick", "jack_note"}
        for question in self.questions:
            self.assertTrue(required.issubset(question))
            for field in required - {"id"}:
                self.assertTrue(question[field].strip())

    def test_ambiguous_worry_prompt_has_context(self):
        question = next(item for item in self.questions if item["id"] == 17)
        self.assertEqual(question["japanese"], "心配しないで")
        self.assertTrue(question["context_ja"].strip())

    def test_never_mind_prompt_has_withdrawal_context(self):
        question = next(item for item in self.questions if item["id"] == 29)
        self.assertEqual(question["japanese"], "やっぱいいや")
        self.assertEqual(question["jacks_pick"], "Never mind.")
        self.assertTrue(question["context_ja"].strip())

    def test_next_question_is_different(self):
        for question in self.questions:
            chosen = choose_question(self.questions, question["id"])
            self.assertNotEqual(chosen["id"], question["id"])

    def test_local_evaluation_does_not_need_an_api_key(self):
        result = evaluate_answer_locally(self.questions[7], "I'm hungry.")
        self.assertEqual(result.naturalness_score, 10)
        self.assertIn("テスト", result.verdict)

    def test_unmistakable_hesitation_is_separated(self):
        answer, ignored = separate_leading_hesitation("Um, uh... I'm hungry.")
        self.assertEqual(answer, "I'm hungry.")
        self.assertEqual([word.casefold() for word in ignored], ["um", "uh"])

    def test_meaningful_discourse_words_are_preserved(self):
        answer, ignored = separate_leading_hesitation("Well, I think I'm hungry.")
        self.assertEqual(answer, "Well, I think I'm hungry.")
        self.assertEqual(ignored, [])

    def test_cosmetic_differences_compare_as_the_same_answer(self):
        self.assertEqual(
            normalize_for_comparison(' “I got nothing going on.” '),
            normalize_for_comparison("i got nothing going on"),
        )

    def test_casual_is_spelled_correctly_in_ai_feedback(self):
        result = Evaluation(
            naturalness_score=8,
            verdict="キャジュアル",
            needs_improvement=True,
            positive_feedback_ja="キャジュアルな表現です。",
            improvement_feedback_ja="もっとキャジュアルにできます。",
            interpreted_answer="It is fine.",
            ignored_hesitation=[],
            natural_version="It's fine.",
            why_ja="キャジュアルな会話で使えます。",
        )
        corrected = correct_japanese_copy(result)
        self.assertNotIn("キャジュアル", " ".join((
            corrected.verdict,
            corrected.positive_feedback_ja,
            corrected.improvement_feedback_ja,
            corrected.why_ja,
        )))


if __name__ == "__main__":
    unittest.main()
