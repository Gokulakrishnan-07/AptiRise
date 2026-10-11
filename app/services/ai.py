import re
import difflib
from typing import Dict, Any, List, Optional, Tuple
import httpx
from app.config import settings

# Comprehensive dictionary of aptitude topics and characteristic keywords
TOPIC_KEYWORDS = {
    "Percentage": [
        "percent", "%", "percentage", "discount", "marked price", "depreciation", "population increase"
    ],
    "Profit & Loss": [
        "cost price", "selling price", "profit", "loss", "cp", "sp", "gain percent", "loss percent", "marked price", "markup"
    ],
    "Simple Interest": [
        "simple interest", "principal", "rate of interest", "per annum", "si =", "sum of money amounts to", "loan"
    ],
    "Compound Interest": [
        "compound interest", "compounded annually", "compounded half-yearly", "ci =", "difference between ci and si"
    ],
    "Time & Work": [
        "can do a piece of work", "days to complete", "working together", "work together",
        "efficiency", "alone can finish", "alone can do", "do a work", "leaves the work",
        "alternate days", "days will b take", "days will they take", "man days"
    ],
    "Time, Speed & Distance": [
        "speed", "km/h", "m/s", "train", "distance", "relative speed", "crosses a pole", "crosses a platform", "average speed", "car", "boat and stream", "downstream", "upstream"
    ],
    "Pipes & Cisterns": [
        "pipe", "cistern", "fill a tank", "empties the tank", "leak", "tap", "inlet", "outlet"
    ],
    "Ratio & Proportion": [
        "ratio", "proportion", "divided in the ratio", "mean proportional", "third proportional", "duplicate ratio"
    ],
    "Average": [
        "average", "mean", "average age", "average weight", "average score", "runs scored"
    ],
    "Problems on Ages": [
        "years ago", "years hence", "age of father", "son's age", "ratio of ages", "present age"
    ],
    "Number System": [
        "divisible by", "remainder", "prime number", "unit digit", "sum of digits", "integer", "odd number", "even number"
    ],
    "HCF & LCM": [
        "hcf", "lcm", "highest common factor", "least common multiple", "greatest number which divides"
    ],
    "Probability": [
        "probability", "dice", "card drawn", "pack of cards", "coin tossed", "marbles", "sample space"
    ],
    "Permutation & Combination": [
        "permutations", "combinations", "arranged in a row", "committee of", "ways to choose", "factorial"
    ],
    "Simplification": [
        "simplify", "bodmas", "square root", "cube root", "surds", "indices", "fractions"
    ],
    "Logical Reasoning": [
        "coding decoding", "blood relation", "syllogism", "direction sense", "seating arrangement", "statement and conclusion"
    ],
    "Verbal Ability": [
        "synonym", "antonym", "sentence correction", "comprehension", "idiom", "one word substitution"
    ],
    "Quantitative Aptitude": [
        "solve", "calculate", "find the value", "equation", "algebra"
    ]
}


def normalize_text(text: str) -> str:
    """Strip punctuation and extra whitespace for duplicate detection and classification."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate sequence matcher similarity between two questions."""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    if not norm1 or not norm2:
        return 0.0
    return difflib.SequenceMatcher(None, norm1, norm2).ratio()


class AIService:
    def __init__(self):
        self.token = settings.HF_TOKEN
        self.api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    async def classify_question_online(self, question_text: str, candidate_topics: List[str]) -> Optional[Tuple[str, float]]:
        """
        Query Hugging Face zero-shot classification if HF_TOKEN is configured.
        Returns (best_topic, confidence_score) or None if API fails.
        """
        if not self.token:
            return None

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                payload = {
                    "inputs": question_text,
                    "parameters": {"candidate_labels": candidate_topics[:10]}
                }
                response = await client.post(self.api_url, json=payload, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    labels = data.get("labels", [])
                    scores = data.get("scores", [])
                    if labels and scores:
                        return labels[0], float(scores[0])
        except Exception as e:
            # Fallback smoothly to offline heuristic
            pass
        return None

    def classify_question_heuristic(self, question_text: str) -> Tuple[str, float]:
        """
        Rule-based high-accuracy classifier for aptitude topics.
        """
        lower = question_text.lower()
        topic_scores = {}

        for topic, keywords in TOPIC_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw in lower:
                    # Longer keyword matches get higher weight
                    score += 1.5 + len(kw) * 0.1
            if score > 0:
                topic_scores[topic] = score

        if not topic_scores:
            return "Quantitative Aptitude", 0.70

        best_topic = max(topic_scores, key=topic_scores.get)
        highest_score = topic_scores[best_topic]
        # Calculate normalized confidence
        confidence = min(0.96, 0.75 + (highest_score * 0.05))
        return best_topic, round(confidence, 2)

    async def classify_topic(self, question_text: str) -> Tuple[str, float]:
        """
        Classifies topic with Hugging Face online inference, falling back to local heuristics.
        """
        topics = list(TOPIC_KEYWORDS.keys())
        online_result = await self.classify_question_online(question_text, topics)
        if online_result:
            return online_result
        return self.classify_question_heuristic(question_text)

    def estimate_difficulty(self, question_text: str) -> Tuple[str, int]:
        """
        Estimates difficulty ('Beginner', 'Easy', 'Intermediate', 'Advanced', 'Expert')
        and maps it to level (1 to 5).
        """
        text = question_text.strip()
        length = len(text.split())
        lower = text.lower()

        # Indicators of high difficulty: multiple variables, complex calculations, conditional clauses
        expert_indicators = ["compound interest", "permutations", "probability", "downstream", "leak", "together"]
        advanced_indicators = ["difference between", "ratio of", "efficiency", "depreciation", "alternate"]

        points = 0
        if length > 45:
            points += 2
        elif length > 25:
            points += 1

        for ind in expert_indicators:
            if ind in lower:
                points += 1
        for ind in advanced_indicators:
            if ind in lower:
                points += 1

        if points >= 4:
            return "Expert", 5
        elif points == 3:
            return "Advanced", 4
        elif points == 2:
            return "Intermediate", 3
        elif points == 1:
            return "Easy", 2
        else:
            return "Beginner", 1

    def generate_explanation_and_shortcut(self, topic: str, question_text: str, answer_letter: str) -> Tuple[str, str]:
        """
        Generates clean explanation and quick formula shortcut for aptitude questions.
        """
        explanation = f"Step-by-step resolution for {topic}: Review the given conditions in the problem, apply the fundamental formula, and solve for the unknown variable to obtain option ({answer_letter})."

        shortcut_map = {
            "Percentage": "Formula: Required % = (Value / Total) × 100. For successive % changes: a + b + (ab/100).",
            "Profit & Loss": "Shortcut: Profit% = (P / CP) × 100. SP = CP × (100 + Gain%)/100.",
            "Simple Interest": "Quick Formula: SI = (P × R × T) / 100. Amount = P + SI.",
            "Compound Interest": "Shortcut: A = P(1 + R/100)^T. For 2 years diff: Diff = P(R/100)^2.",
            "Time & Work": "Shortcut: Total Work = LCM of individual days. Efficiency = Work / Time.",
            "Time, Speed & Distance": "Shortcut: Speed = Distance / Time. To convert km/h to m/s: multiply by 5/18.",
            "Pipes & Cisterns": "Shortcut: Net inlet rate per hour = (1/A + 1/B - 1/C).",
            "Average": "Shortcut: Average = (Sum of Observations) / (Number of Observations).",
            "Ratio & Proportion": "Shortcut: If a:b = c:d, then product of extremes = product of means (ad = bc).",
            "Problems on Ages": "Shortcut: Set up linear equations: Present age = x; 'n' years ago = (x - n).",
            "Number System": "Shortcut: Check divisibility rules for 3, 9, 11 to eliminate invalid options quickly."
        }

        shortcut = shortcut_map.get(
            topic,
            "Key Shortcut: Eliminate extreme or contradictory options first before applying algebraic substitution."
        )

        return explanation, shortcut


ai_service = AIService()
