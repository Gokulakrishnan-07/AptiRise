from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class OptionSchema(BaseModel):
    label: str  # "A", "B", "C", "D"
    text: str

    model_config = ConfigDict(from_attributes=True)


class QuestionCardSchema(BaseModel):
    id: int
    collection_id: int
    collection_name: str
    level_id: int
    level_number: int
    level_title: str
    question_number: int
    total_questions: int
    question_text: str
    options: List[OptionSchema]
    difficulty: str
    time_limit: int
    xp_value: int


class SubmitAnswerRequest(BaseModel):
    question_id: int
    level_id: Optional[int] = None
    selected_option_label: str  # "A", "B", "C", "D"
    time_taken_seconds: float = Field(default=0.0, ge=0.0)


class SubmitAnswerResponse(BaseModel):
    is_correct: bool
    correct_option_label: str
    correct_option_text: str
    explanation: Optional[str] = None
    shortcut: Optional[str] = None
    time_taken_seconds: float
    xp_earned: int
    speed_bonus: int
    streak_bonus: int
    total_user_xp: int
    new_user_level: int
    level_up: bool
    unlocked_achievements: List[Dict[str, Any]] = []


class CompleteLevelRequest(BaseModel):
    level_id: int
    time_taken_seconds: float
    total_score: int
    correct_count: int
    wrong_count: int


class CompleteLevelResponse(BaseModel):
    level_completed: bool
    next_level_unlocked: bool
    next_level_id: Optional[int] = None
    xp_earned: int
    accuracy: float
    is_perfect: bool
    unlocked_achievements: List[Dict[str, Any]] = []


class UserStatSummary(BaseModel):
    current_level: int
    level_progress_pct: float
    xp_in_level: int
    xp_for_next_level: int
    total_xp: int
    current_streak: int
    questions_solved: int
    accuracy: float
    completed_collections: int
    total_collections: int
