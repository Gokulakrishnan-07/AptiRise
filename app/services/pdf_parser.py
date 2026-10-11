import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models.game import Question
from app.services.ai import ai_service, calculate_similarity


class PDFQuestionParser:
    def __init__(self):
        pass

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extracts all raw text from a PDF file using pypdf."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")

        reader = PdfReader(file_path)
        full_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text.append(text)
        return "\n\n".join(full_text)

    def parse_questions_from_text(self, raw_text: str) -> List[Dict[str, Any]]:
        """
        Intelligently detects questions, options, answers, and explanations
        from raw unstructured PDF text using regex patterns and heuristics.
        """
        # Clean text
        text = re.sub(r"\r\n", "\n", raw_text)
        # Remove common headers/footers like 'Page 1 of 10' or URLs
        text = re.sub(r"(?i)page\s+\d+(\s+of\s+\d+)?", "", text)

        # Regex to split questions. Matches:
        # "1.", "1)", "Q1.", "Q1:", "Question 1.", "Question 1:", "[1]"
        question_pattern = re.compile(
            r"(?:\n\s*|^)(?:Q(?:uestion)?\.?\s*|\b)(\d{1,4})[\.\:\)\]]\s+",
            re.IGNORECASE
        )

        matches = list(question_pattern.finditer(text))
        if not matches:
            # Fallback pattern if numbered differently
            question_pattern = re.compile(r"\n(?=[0-9]{1,3}\s*[\.\)])")
            chunks = question_pattern.split(text)
            blocks = [c.strip() for c in chunks if len(c.strip()) > 30]
        else:
            blocks = []
            for i in range(len(matches)):
                start = matches[i].end()
                end = matches[i+1].start() if i + 1 < len(matches) else len(text)
                q_text_block = text[start:end].strip()
                blocks.append(q_text_block)

        parsed_questions = []

        for block in blocks:
            parsed = self._extract_single_question_data(block)
            if parsed and parsed.get("question_text") and len(parsed.get("options", {})) >= 2:
                parsed_questions.append(parsed)

        return parsed_questions

    def _extract_single_question_data(self, block: str) -> Optional[Dict[str, Any]]:
        """Extracts question text, options (A, B, C, D), answer, and explanation from a block."""
        # Detect Answer
        answer_pattern = re.compile(
            r"(?i)(?:Ans(?:wer)?|Correct\s+Option|Option)[\s\:\-\.]*\(?([A-D])\)?",
            re.IGNORECASE
        )
        answer_match = answer_pattern.search(block)
        detected_answer = answer_match.group(1).upper() if answer_match else "A"

        # Detect Explanation
        explanation_pattern = re.compile(
            r"(?i)(?:Explanation|Solution|Exp|Sol)[\s\:\-\.](.*)",
            re.DOTALL
        )
        exp_match = explanation_pattern.search(block)
        detected_explanation = exp_match.group(1).strip() if exp_match else None

        # Truncate block up to Answer / Explanation marker so options don't capture the answer line
        body = block
        if answer_match:
            body = body[:answer_match.start()].strip()
        elif exp_match:
            body = body[:exp_match.start()].strip()

        # Detect options (A, B, C, D)
        # Matches formats: A) ..., B) ... or (A) ..., (B) ... or A. ..., B. ...
        opt_pattern = re.compile(
            r"(?:\n\s*|\s{2,}|\b)(?:\(?([A-Da-d])\)|\b([A-Da-d])[\.\)])\s+",
            re.MULTILINE
        )
        opt_matches = list(opt_pattern.finditer(body))

        if len(opt_matches) < 2:
            return None

        # The question text is everything before the first option
        question_text = body[:opt_matches[0].start()].strip()
        question_text = re.sub(r"\s+", " ", question_text)

        options = {}
        for i in range(len(opt_matches)):
            m = opt_matches[i]
            label = (m.group(1) or m.group(2)).upper()
            start = m.end()
            end = opt_matches[i+1].start() if i + 1 < len(opt_matches) else len(body)
            opt_val = body[start:end].strip()
            # Clean trailing spaces / punctuation
            opt_val = re.sub(r"\s+", " ", opt_val)
            options[label] = opt_val

        # Ensure we have standard A, B, C, D labels
        opt_a = options.get("A", "Option A")
        opt_b = options.get("B", "Option B")
        opt_c = options.get("C", "Option C")
        opt_d = options.get("D", "Option D")

        return {
            "raw_block": block,
            "question_text": question_text,
            "option_a": opt_a,
            "option_b": opt_b,
            "option_c": opt_c,
            "option_d": opt_d,
            "detected_answer": detected_answer,
            "detected_explanation": detected_explanation,
            "options": options
        }

    async def process_and_classify_pdf(
        self,
        file_path: str,
        db: Session,
        default_collection_id: Optional[int] = None,
        default_level_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Full pipeline:
        1. Extract text
        2. Detect questions and options
        3. Classify topic and difficulty via AI / heuristic
        4. Detect duplicates against existing database questions
        """
        raw_text = self.extract_text_from_pdf(file_path)
        extracted = self.parse_questions_from_text(raw_text)

        # Pre-fetch existing questions for duplicate comparison
        existing_questions = db.query(Question.id, Question.question_text).all()

        processed_questions = []

        for item in extracted:
            q_text = item["question_text"]

            # AI Classification
            topic, confidence = await ai_service.classify_topic(q_text)
            diff_label, diff_level = ai_service.estimate_difficulty(q_text)

            # Generate explanation / shortcut if missing
            exp = item.get("detected_explanation")
            shortcut = None
            if not exp:
                exp, shortcut = ai_service.generate_explanation_and_shortcut(
                    topic, q_text, item["detected_answer"]
                )
            else:
                _, shortcut = ai_service.generate_explanation_and_shortcut(
                    topic, q_text, item["detected_answer"]
                )

            # Duplicate Detection
            is_dup = False
            dup_id = None
            for eq_id, eq_text in existing_questions:
                sim = calculate_similarity(q_text, eq_text)
                if sim >= 0.82:  # High similarity indicates duplicate
                    is_dup = True
                    dup_id = eq_id
                    break

            processed_questions.append({
                "raw_text": item["raw_block"],
                "question_text": q_text,
                "option_a": item["option_a"],
                "option_b": item["option_b"],
                "option_c": item["option_c"],
                "option_d": item["option_d"],
                "detected_answer": item["detected_answer"],
                "detected_explanation": exp,
                "detected_shortcut": shortcut,
                "detected_topic": topic,
                "detected_difficulty": diff_label,
                "ai_confidence": confidence,
                "is_duplicate": is_dup,
                "duplicate_question_id": dup_id,
                "final_collection_id": default_collection_id,
                "final_level_id": default_level_id
            })

        return processed_questions


pdf_parser = PDFQuestionParser()
