"""
Student gamification & learning engine for Lexavo Campus.
Scientific principles: spaced repetition (Leitner), active recall,
interleaving, elaborative interrogation, feedback enrichi.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import anthropic

log = logging.getLogger("student")

# ─── Config IA ──────────────────────────────────────────────────────────────
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
STUDENT_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 4000

def _get_client():
    return anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ─── XP & Levels ────────────────────────────────────────────────────────────

XP_TABLE = {
    "quiz_pass": 50,       # >70%
    "quiz_perfect": 100,   # 100%
    "flashcards": 20,
    "summary": 10,
    "case_study": 75,
    "mock_exam": 150,
    "free_recall": 75,     # rappel libre
    "interleaved": 60,     # revision mixte
}

STREAK_MULTIPLIER = 1.5
XP_PER_LEVEL = 500
MAX_XP_PER_DAY = 500


def calculate_xp(mode: str, score: int, total: int, streak_active: bool = False) -> int:
    """Calculate XP earned for an activity."""
    if total <= 0:
        base = XP_TABLE.get(mode, 10)
    elif mode in ("quiz", "quiz_pass", "quiz_perfect", "mock_exam", "interleaved", "free_recall"):
        pct = score / total * 100
        if pct >= 100:
            base = XP_TABLE.get("quiz_perfect", 100)
        elif pct >= 70:
            base = XP_TABLE.get("quiz_pass", 50)
        else:
            base = max(10, int(XP_TABLE.get("quiz_pass", 50) * pct / 100))
    else:
        base = XP_TABLE.get(mode, 10)

    if streak_active:
        base = int(base * STREAK_MULTIPLIER)

    return min(base, MAX_XP_PER_DAY)


def compute_level(total_xp: int) -> int:
    """Convert total XP to level."""
    return max(1, total_xp // XP_PER_LEVEL + 1)


# ─── Badges ──────────────────────────────────────────────────────────────────

BADGES = [
    {"id": "first_quiz",      "name": "Premier quiz",     "emoji": "\U0001f331"},  # 🌱
    {"id": "streak_7",        "name": "Streak 7 jours",   "emoji": "\U0001f525"},  # 🔥
    {"id": "streak_30",       "name": "Streak 30 jours",  "emoji": "\u26a1"},      # ⚡
    {"id": "perfect_score",   "name": "Score parfait",    "emoji": "\U0001f3c6"},  # 🏆
    {"id": "explorer_5",      "name": "5 branches",       "emoji": "\U0001f5fa"},  # 🗺️
    {"id": "explorer_10",     "name": "10 branches",      "emoji": "\U0001f4da"},  # 📚
    {"id": "quiz_50",         "name": "50 quiz",          "emoji": "\U0001f4aa"},  # 💪
    {"id": "quiz_100",        "name": "100 quiz",         "emoji": "\U0001f3af"},  # 🎯
    {"id": "level_5",         "name": "Niveau 5",         "emoji": "\u2b50"},      # ⭐
    {"id": "level_10",        "name": "Niveau 10",        "emoji": "\U0001f48e"},  # 💎
    {"id": "level_25",        "name": "Master",           "emoji": "\U0001f393"},  # 🎓
    {"id": "case_study_1",    "name": "Juriste en herbe", "emoji": "\U0001f9e0"},  # 🧠
    {"id": "case_study_10",   "name": "Avocat stagiaire", "emoji": "\u2696"},      # ⚖️
    {"id": "all_branches_80", "name": "Encyclopedie",     "emoji": "\U0001f31f"},  # 🌟
    {"id": "flash_100",       "name": "Memoire vive",     "emoji": "\U0001f0cf"},  # 🃏
]


def check_and_award_badges(user_id: int) -> list:
    """Check all badge conditions and award any newly earned badges."""
    from api.database import get_student_progress, get_student_badges, award_student_badge, get_student_total_xp

    progress_list = get_student_progress(user_id)
    earned_ids = {b["badge_id"] for b in get_student_badges(user_id)}
    total_xp = get_student_total_xp(user_id)
    level = compute_level(total_xp)

    # Aggregate stats
    total_quizzes = sum(p.get("total_quizzes", 0) for p in progress_list)
    total_flashcards = sum(p.get("total_flashcards", 0) for p in progress_list)
    total_case_studies = sum(p.get("total_case_studies", 0) for p in progress_list)
    branches_explored = len(progress_list)
    max_streak = max((p.get("streak_count", 0) for p in progress_list), default=0)
    max_best_score = max((p.get("best_score", 0) for p in progress_list), default=0)
    all_above_80 = len(progress_list) >= 10 and all(p.get("best_score", 0) >= 80 for p in progress_list)

    conditions = {
        "first_quiz": total_quizzes >= 1,
        "streak_7": max_streak >= 7,
        "streak_30": max_streak >= 30,
        "perfect_score": max_best_score >= 100,
        "explorer_5": branches_explored >= 5,
        "explorer_10": branches_explored >= 10,
        "quiz_50": total_quizzes >= 50,
        "quiz_100": total_quizzes >= 100,
        "level_5": level >= 5,
        "level_10": level >= 10,
        "level_25": level >= 25,
        "case_study_1": total_case_studies >= 1,
        "case_study_10": total_case_studies >= 10,
        "all_branches_80": all_above_80,
        "flash_100": total_flashcards >= 100,
    }

    newly_awarded = []
    for badge in BADGES:
        bid = badge["id"]
        if bid not in earned_ids and conditions.get(bid, False):
            if award_student_badge(user_id, bid, badge["name"], badge["emoji"]):
                newly_awarded.append(badge)

    return newly_awarded


# ─── Dashboard ──────────────────────────────────────────────────────────────

def get_dashboard_data(user_id: int) -> dict:
    """Aggregate all student data for the dashboard."""
    from api.database import (
        get_student_progress, get_student_badges, get_quiz_history,
        get_student_total_xp, get_weak_branches,
    )

    progress = get_student_progress(user_id)
    badges = get_student_badges(user_id)
    history = get_quiz_history(user_id, limit=5)
    total_xp = get_student_total_xp(user_id)
    level = compute_level(total_xp)
    xp_in_level = total_xp % XP_PER_LEVEL
    weak = get_weak_branches(user_id, limit=3)

    # Streak from progress
    streak_count = max((p.get("streak_count", 0) for p in progress), default=0)
    streak_last = next((p.get("streak_last_date") for p in progress if p.get("streak_count", 0) == streak_count), None)

    return {
        "total_xp": total_xp,
        "level": level,
        "xp_in_level": xp_in_level,
        "xp_to_next_level": XP_PER_LEVEL,
        "streak_count": streak_count,
        "streak_last_date": streak_last,
        "branches_explored": len(progress),
        "total_quizzes": sum(p.get("total_quizzes", 0) for p in progress),
        "progress_by_branch": [
            {"branch": p["branch"], "xp": p["xp"], "level": p.get("level", 1),
             "best_score": p.get("best_score", 0), "total_quizzes": p.get("total_quizzes", 0)}
            for p in progress
        ],
        "badges_earned": badges,
        "badges_available": BADGES,
        "recent_activity": history,
        "weak_branches": weak,
    }


# ─── Card hash for SRS ──────────────────────────────────────────────────────

def card_hash(front: str, back: str) -> str:
    """Generate a stable hash for a flashcard."""
    return hashlib.md5(f"{front}||{back}".encode()).hexdigest()[:16]


# ─── Case Study Generation ─────────────────────────────────────────────────

def generate_case_study(branch: str, difficulty: str = "moyen", rag_context: str = "") -> dict:
    """Generate a realistic legal case study using Claude + RAG context."""
    difficulty_map = {
        "facile": "niveau Bac 1 en droit, concepts fondamentaux",
        "moyen": "niveau Bac 2-3 en droit, raisonnement juridique structure",
        "difficile": "niveau Master, cas complexe multi-branches avec nuances jurisprudentielles",
    }
    diff_desc = difficulty_map.get(difficulty, difficulty_map["moyen"])

    rag_section = f"\n\nContexte juridique belge a utiliser comme reference :\n{rag_context}\n" if rag_context else ""

    prompt = f"""Tu es un professeur de droit belge. Genere un cas pratique de droit en {branch} ({diff_desc}).
{rag_section}
Le cas doit etre REALISTE et base sur le droit belge (pas le droit francais).

Reponds UNIQUEMENT en JSON valide :
{{
    "title": "Titre du cas",
    "facts": "Description detaillee des faits (150-300 mots). Contexte realiste avec noms fictifs, dates, circonstances precises.",
    "questions": [
        "Question 1 (ex: Qualifiez juridiquement la situation)",
        "Question 2 (ex: Quels sont les droits de M. Dupont ?)",
        "Question 3 (ex: Quelle procedure devrait-il suivre ?)"
    ],
    "difficulty": "{difficulty}",
    "branch": "{branch}",
    "key_articles": ["Art. 1382 Code civil", "Art. 63 Loi travail"],
    "expected_reasoning": "Resume du raisonnement juridique attendu (200 mots). Articles applicables, jurisprudence pertinente, conclusion."
}}"""

    try:
        client = _get_client()
        resp = client.messages.create(
            model=STUDENT_MODEL, max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        # Parse JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        log.error(f"Case study generation error: {e}")
        return {"error": str(e)}


def evaluate_case_study(case_data: dict, student_answer: str) -> dict:
    """Evaluate a student's answer to a case study."""
    prompt = f"""Tu es un professeur de droit belge. Corrige la reponse d'un etudiant a un cas pratique.

CAS PRATIQUE :
Titre : {case_data.get('title', '')}
Faits : {case_data.get('facts', '')}
Questions : {json.dumps(case_data.get('questions', []), ensure_ascii=False)}
Articles cles : {json.dumps(case_data.get('key_articles', []), ensure_ascii=False)}
Raisonnement attendu : {case_data.get('expected_reasoning', '')}

REPONSE DE L'ETUDIANT :
{student_answer}

Evalue la reponse. Reponds UNIQUEMENT en JSON valide :
{{
    "score": 0-100,
    "grade": "A/B/C/D/E",
    "feedback": "Feedback detaille (200 mots) : ce qui est bien, ce qui manque, erreurs de raisonnement",
    "missing_articles": ["articles que l'etudiant aurait du citer"],
    "missing_concepts": ["concepts juridiques oublies"],
    "strengths": ["points forts de la reponse"],
    "model_answer": "Reponse modele (200 mots) avec raisonnement complet et articles cites"
}}"""

    try:
        client = _get_client()
        resp = client.messages.create(
            model=STUDENT_MODEL, max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        log.error(f"Case study evaluation error: {e}")
        return {"error": str(e), "score": 0}


# ─── Mock Exam ──────────────────────────────────────────────────────────────

def generate_mock_exam(branches: list, num_questions: int = 20) -> dict:
    """Generate a mock exam (QCM only for V1) mixing multiple branches."""
    branches_str = ", ".join(branches)
    q_per_branch = max(2, num_questions // len(branches))

    prompt = f"""Tu es un professeur de droit belge. Genere un examen blanc QCM de {num_questions} questions.
Branches : {branches_str} (environ {q_per_branch} questions par branche, melangees aleatoirement — interleaving).
Difficulte : melange facile/moyen/difficile.

IMPORTANT : chaque question doit etre basee sur le droit BELGE (pas francais).
Cite l'article de loi belge exact dans l'explication.

Reponds UNIQUEMENT en JSON valide :
{{
    "title": "Examen blanc — {branches_str}",
    "duration_minutes": 20,
    "questions": [
        {{
            "id": 1,
            "branch": "Droit civil",
            "question": "Question...",
            "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
            "correct": "A",
            "explanation": "Explication avec article de loi belge exact. Pourquoi les autres options sont fausses.",
            "difficulty": "moyen"
        }}
    ]
}}"""

    try:
        client = _get_client()
        resp = client.messages.create(
            model=STUDENT_MODEL, max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        log.error(f"Mock exam generation error: {e}")
        return {"error": str(e)}


def evaluate_mock_exam(exam_data: dict, student_answers: dict) -> dict:
    """Evaluate a mock exam. student_answers = {question_id: "A"|"B"|"C"|"D"}."""
    questions = exam_data.get("questions", [])
    correct_count = 0
    results = []

    for q in questions:
        qid = str(q.get("id", ""))
        student_ans = student_answers.get(qid, student_answers.get(int(qid) if qid.isdigit() else qid, ""))
        is_correct = student_ans.upper() == q.get("correct", "").upper() if student_ans else False
        if is_correct:
            correct_count += 1
        results.append({
            "id": q["id"],
            "branch": q.get("branch", ""),
            "correct_answer": q.get("correct", ""),
            "student_answer": student_ans,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

    total = len(questions)
    score_pct = round(correct_count / max(total, 1) * 100)
    note_20 = round(correct_count / max(total, 1) * 20, 1)

    return {
        "score": correct_count,
        "total": total,
        "score_percent": score_pct,
        "note_20": note_20,
        "grade": "A" if note_20 >= 16 else "B" if note_20 >= 14 else "C" if note_20 >= 12 else "D" if note_20 >= 10 else "E",
        "results": results,
    }


# ─── Free Recall (rappel libre) ────────────────────────────────────────────

def generate_free_recall_question(branch: str) -> dict:
    """Generate an open-ended question for free recall (active recall max)."""
    prompt = f"""Tu es un professeur de droit belge. Genere UNE question ouverte en {branch}.
La question doit demander a l'etudiant de FORMULER une regle de droit, pas juste la reconnaitre.
C'est du rappel libre (active recall maximal).

Reponds UNIQUEMENT en JSON valide :
{{
    "question": "Formulez la regle juridique applicable quand...",
    "branch": "{branch}",
    "expected_answer": "Reponse modele detaillee (150 mots) avec articles de loi belges exacts",
    "key_points": ["point 1 a verifier", "point 2", "point 3"],
    "articles": ["Art. X Code Y"]
}}"""

    try:
        client = _get_client()
        resp = client.messages.create(
            model=STUDENT_MODEL, max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        log.error(f"Free recall generation error: {e}")
        return {"error": str(e)}


def evaluate_free_recall(question_data: dict, student_answer: str) -> dict:
    """Evaluate a free recall answer."""
    prompt = f"""Tu es un professeur de droit belge. Evalue cette reponse de rappel libre.

QUESTION : {question_data.get('question', '')}
REPONSE ATTENDUE : {question_data.get('expected_answer', '')}
POINTS CLES A VERIFIER : {json.dumps(question_data.get('key_points', []), ensure_ascii=False)}
ARTICLES : {json.dumps(question_data.get('articles', []), ensure_ascii=False)}

REPONSE DE L'ETUDIANT :
{student_answer}

Reponds UNIQUEMENT en JSON valide :
{{
    "score": 0-10,
    "feedback": "Correction detaillee (100 mots)",
    "points_found": ["points cles que l'etudiant a mentionnes"],
    "points_missing": ["points cles oublies"],
    "articles_cited": true/false,
    "elaboration_question": "Question 'pourquoi' pour approfondir (elaborative interrogation)"
}}"""

    try:
        client = _get_client()
        resp = client.messages.create(
            model=STUDENT_MODEL, max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        log.error(f"Free recall evaluation error: {e}")
        return {"error": str(e), "score": 0}


# ─── Interleaved Quiz (revision mixte) ─────────────────────────────────────

def generate_interleaved_quiz(branches: list, num_per_branch: int = 3) -> dict:
    """Generate a mixed quiz with questions from multiple branches (interleaving)."""
    import random
    branches_str = ", ".join(branches)
    total = num_per_branch * len(branches)

    prompt = f"""Tu es un professeur de droit belge. Genere {total} questions QCM melangeant ces branches :
{branches_str} ({num_per_branch} questions par branche).

IMPORTANT : les questions doivent etre MELANGEES (pas groupees par branche).
L'objectif est l'interleaving : forcer l'etudiant a identifier la branche applicable.
Chaque question doit citer l'article de loi belge exact dans l'explication.

Reponds UNIQUEMENT en JSON valide :
{{
    "title": "Revision mixte",
    "questions": [
        {{
            "id": 1,
            "branch": "Droit civil",
            "question": "Question...",
            "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
            "correct": "A",
            "explanation": "Explication avec article de loi belge. Pourquoi les autres sont fausses."
        }}
    ]
}}"""

    try:
        client = _get_client()
        resp = client.messages.create(
            model=STUDENT_MODEL, max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        data = json.loads(text)
        # Shuffle for extra interleaving
        if "questions" in data:
            random.shuffle(data["questions"])
            for i, q in enumerate(data["questions"], 1):
                q["id"] = i
        return data
    except Exception as e:
        log.error(f"Interleaved quiz generation error: {e}")
        return {"error": str(e)}
