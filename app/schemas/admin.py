from typing import Optional, List
from pydantic import BaseModel, Field


class QuestionOptionCreate(BaseModel):
    option_label: str
    option_text: str
    is_correct: bool


class QuestionCreate(BaseModel):
    collection_id: int
    level_id: int
    question_text: str
    explanation: Optional[str] = None
    shortcut: Optional[str] = None
    difficulty: str = "Intermediate"
    time_limit: int = 45
    xp_value: int = 100
    tags: Optional[str] = None
    options: List[QuestionOptionCreate]


class QuestionUpdate(BaseModel):
    collection_id: Optional[int] = None
    level_id: Optional[int] = None
    question_text: Optional[str] = None
    explanation: Optional[str] = None
    shortcut: Optional[str] = None
    difficulty: Optional[str] = None
    time_limit: Optional[int] = None
    xp_value: Optional[int] = None
    tags: Optional[str] = None
    is_active: Optional[bool] = None
    options: Optional[List[QuestionOptionCreate]] = None


class PdfApproveQuestionItem(BaseModel):
    id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    detected_answer: str
    detected_explanation: Optional[str] = None
    detected_shortcut: Optional[str] = None
    collection_id: int
    level_id: int
    difficulty: str = "Intermediate"


class PdfApproveRequest(BaseModel):
    pdf_import_id: int
    questions: List[PdfApproveQuestionItem]


class CollectionCreate(BaseModel):
    category_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    icon: str = "target"
    total_levels: int = 5


class SettingUpdate(BaseModel):
    key: str
    value: str
