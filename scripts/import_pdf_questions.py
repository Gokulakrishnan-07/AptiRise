"""
AptiRise - Fast PDF Question Importer
"""

import os
import sys
import re
import hashlib
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.game import Category, Collection, Level, Question, QuestionOption
from app.services.pdf_parser import pdf_parser
from app.services.ai import ai_service

DEFAULT_PDF = os.path.join(os.path.dirname(__file__), "..", "Aptitude_Questions.pdf")

DIFF_TO_LEVEL = {"Beginner": 1, "Easy": 2, "Intermediate": 3, "Advanced": 4, "Expert": 5}
DIFF_TIME_XP  = {"Beginner": (30,100), "Easy": (40,110), "Intermediate": (45,130), "Advanced": (50,150), "Expert": (60,200)}
LEVEL_TITLES  = {1:"Beginner", 2:"Easy", 3:"Intermediate", 4:"Advanced", 5:"Expert"}


def normalize(t):
    return re.sub(r"\s+", " ", t.lower().strip())

def qhash(t):
    return hashlib.sha256(normalize(t).encode()).hexdigest()

def slugify(t):
    t = t.lower().strip()
    t = re.sub(r"[^\w\s-]", "", t)
    return re.sub(r"[\s_]+", "-", t)

def get_or_create(db, model, filter_kw, create_kw):
    obj = db.query(model).filter_by(**filter_kw).first()
    if not obj:
        obj = model(**{**filter_kw, **create_kw})
        db.add(obj); db.commit(); db.refresh(obj)
    return obj

def get_or_create_level(db, col, lvl_num):
    lvl = db.query(Level).filter_by(collection_id=col.id, level_number=lvl_num).first()
    if not lvl:
        title = LEVEL_TITLES.get(lvl_num, f"Level {lvl_num}")
        tl = DIFF_TIME_XP.get(title, (45,120))[0]
        lvl = Level(collection_id=col.id, level_number=lvl_num, title=title,
                    description=f"{title} {col.name} questions.",
                    required_xp_to_unlock=lvl_num*250, question_count=0, time_limit_seconds=tl)
        db.add(lvl); db.commit(); db.refresh(lvl)
    return lvl

def import_pdf(pdf_path, dry_run=False, reset=False):
    db = SessionLocal()
    stats = dict(extracted=0, dup=0, short=0, inserted=0, topics=set())
    try:
        print(f"\n{'='*60}\n  AptiRise Fast PDF Importer\n  {os.path.abspath(pdf_path)}\n  {'DRY RUN' if dry_run else 'LIVE'}\n{'='*60}\n")
        if not os.path.exists(pdf_path):
            print(f"[ERROR] File not found: {pdf_path}"); return
        if reset and not dry_run:
            n = db.query(Question).filter_by(source="pdf").delete()
            db.commit(); print(f"[RESET] Deleted {n} pdf questions.\n")

        print("[1/4] Extracting text ...")
        raw = pdf_parser.extract_text_from_pdf(pdf_path)
        print(f"      {len(raw):,} chars\n")

        print("[2/4] Parsing question blocks ...")
        parsed = pdf_parser.parse_questions_from_text(raw)
        stats["extracted"] = len(parsed)
        print(f"      {len(parsed)} questions found\n")
        if not parsed:
            print("[WARN] No questions detected."); return

        print("[3/4] Classifying & deduplicating ...")
        seen = {qhash(r.question_text) for r in db.query(Question.question_text).all()}
        batch = set()
        category = get_or_create(db, Category, {"name":"Quantitative Aptitude"},
            {"description":"Core aptitude modules.", "icon":"cpu", "display_order":1})
        grouped = {}
        for i, item in enumerate(parsed, 1):
            qt = item["question_text"]
            if len(qt.strip()) < 15:
                stats["short"] += 1; continue
            h = qhash(qt)
            if h in seen or h in batch:
                stats["dup"] += 1; continue
            batch.add(h)
            topic, _ = ai_service.classify_question_heuristic(qt)
            diff, _ = ai_service.estimate_difficulty(qt)
            exp = item.get("detected_explanation")
            if not exp:
                exp, sc = ai_service.generate_explanation_and_shortcut(topic, qt, item["detected_answer"])
            else:
                _, sc = ai_service.generate_explanation_and_shortcut(topic, qt, item["detected_answer"])
            grouped.setdefault(topic, []).append({**item, "topic":topic, "diff":diff,
                "lvl":DIFF_TO_LEVEL.get(diff,1), "exp":exp, "sc":sc, "hash":h})
            stats["topics"].add(topic)
            if i % 200 == 0:
                print(f"      {i}/{len(parsed)} processed ...")
        print(f"      Topics: {', '.join(sorted(stats['topics']))}\n")

        print("[4/4] Writing to database ...")
        for tname, qs in grouped.items():
            col = get_or_create(db, Collection, {"slug": slugify(tname)},
                {"category_id":category.id, "name":tname,
                 "description":f"Questions on {tname}.", "icon":"book-open",
                 "total_levels":5, "is_active":True})
            tc = 0
            for qd in qs:
                qt = qd["question_text"]
                if dry_run:
                    print(f"  [DRY] [{tname}] L{qd['lvl']} | {qd['diff']} | {qt[:65]}")
                    stats["inserted"] += 1; continue
                lv = get_or_create_level(db, col, qd["lvl"])
                tl, xp = DIFF_TIME_XP.get(qd["diff"], (45,120))
                q = Question(collection_id=col.id, level_id=lv.id, question_text=qt,
                    explanation=qd["exp"], shortcut=qd["sc"], difficulty=qd["diff"],
                    time_limit=tl, xp_value=xp, source="pdf", is_active=True)
                db.add(q); db.flush()
                ans = qd.get("detected_answer","A").upper()
                for lbl in ["A","B","C","D"]:
                    db.add(QuestionOption(question_id=q.id, option_label=lbl,
                        option_text=qd.get(f"option_{lbl.lower()}", f"Option {lbl}"),
                        is_correct=(lbl==ans)))
                db.commit()
                lv.question_count = db.query(Question).filter_by(level_id=lv.id, is_active=True).count()
                db.commit()
                stats["inserted"] += 1; tc += 1; seen.add(qd["hash"])
            if tc: print(f"  [OK] {tname}: +{tc}")

        print(f"\n{'='*60}\n  COMPLETE\n{'='*60}")
        print(f"  Extracted  : {stats['extracted']}")
        print(f"  Topics     : {len(stats['topics'])}")
        print(f"  Too short  : {stats['short']}")
        print(f"  Duplicates : {stats['dup']}")
        print(f"  Inserted   : {stats['inserted']}")
        if dry_run: print("  (DRY RUN - DB unchanged)")
        print(f"{'='*60}\n")
    except Exception as e:
        db.rollback()
        import traceback; traceback.print_exc()
    finally:
        db.close()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", default=DEFAULT_PDF)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--reset", action="store_true")
    args = p.parse_args()
    import_pdf(args.pdf, args.dry_run, args.reset)

if __name__ == "__main__":
    main()
