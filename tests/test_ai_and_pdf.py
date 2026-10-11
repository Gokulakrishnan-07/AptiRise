import pytest
from app.services.ai import ai_service, calculate_similarity, normalize_text
from app.services.pdf_parser import pdf_parser


def test_ai_topic_classification_percentage():
    q = "A shop gives a 20% discount on an article marked at ₹500. Find the selling price."
    topic, conf = ai_service.classify_question_heuristic(q)
    assert topic == "Percentage"
    assert conf >= 0.70


def test_ai_topic_classification_time_and_work():
    q = "A can do a piece of work in 10 days and B alone can finish it in 15 days. How many days working together?"
    topic, conf = ai_service.classify_question_heuristic(q)
    assert topic == "Time & Work"
    assert conf >= 0.70


def test_ai_topic_classification_speed():
    q = "A train running at a speed of 54 km/h crosses a platform of length 200m in 20 seconds."
    topic, conf = ai_service.classify_question_heuristic(q)
    assert topic == "Time, Speed & Distance"


def test_duplicate_similarity():
    q1 = "What is 20% of 500?"
    q2 = "What is 20% of 500?"
    q3 = "Calculate twenty percent of five hundred."
    assert calculate_similarity(q1, q2) == 1.0
    assert calculate_similarity(q1, "Completely different question about trains") < 0.3


def test_pdf_regex_question_parsing():
    sample_raw_text = """
1. What is 25% of 800?
A) 150
B) 200
C) 250
D) 300
Answer: B
Explanation: 25% of 800 = 800 / 4 = 200.

2. A train 150 m long crosses a pole in 10 seconds. Find speed.
A) 15 m/s
B) 20 m/s
C) 25 m/s
D) 30 m/s
Answer: A
    """

    extracted = pdf_parser.parse_questions_from_text(sample_raw_text)
    assert len(extracted) == 2
    q1 = extracted[0]
    assert "25%" in q1["question_text"]
    assert q1["option_a"] == "150"
    assert q1["option_b"] == "200"
    assert q1["detected_answer"] == "B"
    assert "200" in (q1["detected_explanation"] or "")

    q2 = extracted[1]
    assert "train" in q2["question_text"]
    assert q2["detected_answer"] == "A"
