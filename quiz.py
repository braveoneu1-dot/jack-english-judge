import random


def choose_question(questions: list[dict], previous_id: int | None = None) -> dict:
    choices = [question for question in questions if question["id"] != previous_id]
    return random.choice(choices)
