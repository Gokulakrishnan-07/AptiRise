from app.services.gamification import (
    calculate_question_xp, calculate_user_level, get_xp_threshold
)


def test_calculate_question_xp_correct_fast():
    # Time limit 40s. Answered in 8s (<= 25% of 40 = 10s) -> Base 100 + Speed 100 = 200
    total_xp, speed_bonus, _ = calculate_question_xp(
        is_correct=True, time_taken=8.0, time_limit=40, base_xp=100
    )
    assert total_xp == 200
    assert speed_bonus == 100


def test_calculate_question_xp_correct_medium():
    # Time limit 40s. Answered in 18s (<= 50% of 40 = 20s) -> Base 100 + Speed 50 = 150
    total_xp, speed_bonus, _ = calculate_question_xp(
        is_correct=True, time_taken=18.0, time_limit=40, base_xp=100
    )
    assert total_xp == 150
    assert speed_bonus == 50


def test_calculate_question_xp_wrong():
    total_xp, speed_bonus, _ = calculate_question_xp(
        is_correct=False, time_taken=5.0, time_limit=40, base_xp=100
    )
    assert total_xp == 0
    assert speed_bonus == 0


def test_user_level_curve():
    # Level 1 at 0 XP
    lvl1, pct1, in_lvl1, needed1 = calculate_user_level(0)
    assert lvl1 == 1

    # Level 2 at 500 XP
    lvl2, pct2, in_lvl2, needed2 = calculate_user_level(500)
    assert lvl2 == 2

    # Level 3 at 1200 XP
    lvl3, pct3, in_lvl3, needed3 = calculate_user_level(1500)
    assert lvl3 == 3
    assert in_lvl3 == 300
