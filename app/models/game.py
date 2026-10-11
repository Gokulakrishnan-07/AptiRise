from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, Float, Index
)
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), default="sparkles")
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    collections = relationship("Collection", back_populates="category", cascade="all, delete-orphan")


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), default="target")
    total_levels = Column(Integer, default=5, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="collections")
    levels = relationship("Level", back_populates="collection", order_by="Level.level_number", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="collection", cascade="all, delete-orphan")
    user_topic_progress = relationship("UserTopicProgress", back_populates="collection", cascade="all, delete-orphan")


class Level(Base):
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    level_number = Column(Integer, nullable=False)  # 1 to 5
    title = Column(String(50), nullable=False)  # e.g., Beginner, Easy, Intermediate, Advanced, Expert
    description = Column(String(255), nullable=True)
    required_xp_to_unlock = Column(Integer, default=0, nullable=False)
    question_count = Column(Integer, default=10, nullable=False)
    time_limit_seconds = Column(Integer, default=45, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    collection = relationship("Collection", back_populates="levels")
    questions = relationship("Question", back_populates="level", cascade="all, delete-orphan")
    user_progress = relationship("UserProgress", back_populates="level", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_collection_level_num", "collection_id", "level_number", unique=True),
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("levels.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    shortcut = Column(Text, nullable=True)
    difficulty = Column(String(30), default="Intermediate")  # Beginner, Easy, Intermediate, Advanced, Expert
    time_limit = Column(Integer, default=45, nullable=False)
    xp_value = Column(Integer, default=100, nullable=False)
    tags = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    source = Column(String(50), default="seed")  # manual, pdf_import, seed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    collection = relationship("Collection", back_populates="questions")
    level = relationship("Level", back_populates="questions")
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")
    attempts = relationship("QuestionAttempt", back_populates="question", cascade="all, delete-orphan")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_label = Column(String(5), nullable=False)  # "A", "B", "C", "D"
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    question = relationship("Question", back_populates="options")


class QuestionAttempt(Base):
    __tablename__ = "question_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("levels.id", ondelete="SET NULL"), nullable=True)
    selected_option_label = Column(String(5), nullable=True)
    is_correct = Column(Boolean, nullable=False)
    time_taken_seconds = Column(Float, default=0.0)
    xp_earned = Column(Integer, default=0)
    attempt_date = Column(Date, default=date.today, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="attempts")
    question = relationship("Question", back_populates="attempts")


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("levels.id", ondelete="CASCADE"), nullable=False, index=True)
    is_unlocked = Column(Boolean, default=False, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    best_score = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    xp_earned = Column(Integer, default=0)
    attempts_count = Column(Integer, default=0)
    perfect_run = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="progress")
    level = relationship("Level", back_populates="user_progress")

    __table_args__ = (
        Index("ix_user_level_unique", "user_id", "level_id", unique=True),
    )


class UserTopicProgress(Base):
    __tablename__ = "user_topic_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    current_level_number = Column(Integer, default=1, nullable=False)
    completion_percentage = Column(Float, default=0.0)
    total_xp_earned = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="topic_progress")
    collection = relationship("Collection", back_populates="user_topic_progress")

    __table_args__ = (
        Index("ix_user_topic_unique", "user_id", "collection_id", unique=True),
    )


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False)
    icon = Column(String(50), default="trophy")
    badge_color = Column(String(30), default="gold")
    xp_reward = Column(Integer, default=100)
    requirement_type = Column(String(50), nullable=False)
    # Types: first_question, streak_days, speed_master, perfect_level, topic_master, global_level, questions_count
    requirement_value = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_achievements = relationship("UserAchievement", back_populates="achievement", cascade="all, delete-orphan")


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    achievement_id = Column(Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True)
    unlocked_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

    __table_args__ = (
        Index("ix_user_achievement_unique", "user_id", "achievement_id", unique=True),
    )


class DailyChallenge(Base):
    __tablename__ = "daily_challenges"

    id = Column(Integer, primary_key=True, index=True)
    challenge_date = Column(Date, unique=True, nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(String(255), nullable=True)
    question_ids = Column(Text, nullable=False)  # Comma-separated or JSON list of IDs
    bonus_xp = Column(Integer, default=500)
    created_at = Column(DateTime, default=datetime.utcnow)

    attempts = relationship("DailyChallengeAttempt", back_populates="challenge", cascade="all, delete-orphan")


class DailyChallengeAttempt(Base):
    __tablename__ = "daily_challenge_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    daily_challenge_id = Column(Integer, ForeignKey("daily_challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="challenge_attempts")
    challenge = relationship("DailyChallenge", back_populates="attempts")

    __table_args__ = (
        Index("ix_user_daily_challenge_unique", "user_id", "daily_challenge_id", unique=True),
    )
