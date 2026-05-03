"""Router Student — /student/*."""

import logging
import os
import base64
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from typing import Annotated, Optional

from api.auth import get_current_user as _get_current_user
from api.routers.deps import get_api_key, limiter

log = logging.getLogger("api.student")

# ─── NotebookLM storage init (Option B — cookies sans Playwright) ─────────────
# En prod Railway : NOTEBOOKLM_STORAGE=<base64 du storage.json>
# En dev local : notebooklm login génère ~/.config/notebooklm/storage.json
_NLM_STORAGE_PATH = Path.home() / ".config" / "notebooklm" / "storage.json"

def _init_notebooklm_storage() -> bool:
    """Initialise le fichier storage NotebookLM depuis la variable d'env Railway."""
    encoded = os.environ.get("NOTEBOOKLM_STORAGE", "")
    if not encoded:
        return _NLM_STORAGE_PATH.exists()
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
        json.loads(decoded)  # valide que c'est du JSON
        _NLM_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _NLM_STORAGE_PATH.write_text(decoded, encoding="utf-8")
        log.info("NotebookLM storage initialisé depuis NOTEBOOKLM_STORAGE")
        return True
    except Exception as e:
        log.warning(f"NotebookLM storage init échoué : {e}")
        return False

_NLM_READY = _init_notebooklm_storage()

router = APIRouter(prefix="/student", tags=["student"])

STUDENT_BRANCHES = [
    "Droit du travail", "Droit familial", "Droit fiscal", "Droit penal",
    "Droit civil", "Droit administratif", "Droit commercial", "Droit immobilier",
    "Droit de l'environnement", "Propriete intellectuelle", "Securite sociale",
    "Droit des etrangers", "Droits fondamentaux", "Marches publics", "Droit europeen",
]

VALID_SUBJECTS = [
    "droit_penal", "droit_civil", "droit_constitutionnel", "droit_administratif",
    "droit_commercial", "droit_travail", "droit_fiscal", "droit_social",
    "droit_familial", "droit_immobilier", "droit_europeen", "droit_international",
    "droit_environnement", "droit_ip", "procedure_civile", "procedure_penale",
    "philosophie_droit", "introduction_droit", "autre",
]


@router.get("/branches")
def student_branches():
    """Liste les branches du droit disponibles pour les étudiants."""
    return {"branches": STUDENT_BRANCHES}


@router.post("/quiz")
@limiter.limit("10/minute")
def student_quiz(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Génère un quiz de 10 questions QCM sur une branche du droit belge."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    import anthropic, json as _json

    branch = body.get("branch", "Droit civil")
    difficulty = body.get("difficulty", "moyen")
    document_content = (body.get("document_content") or "").strip()
    try:
        num_questions = min(int(body.get("num_questions", 10)), 15)
    except (ValueError, TypeError):
        raise HTTPException(400, "Paramètres numériques invalides")

    check_quota(current_user["id"])

    client = anthropic.Anthropic()
    if document_content:
        doc_excerpt = document_content[:6000]
        source_instruction = f"""Voici les notes de cours de l'étudiant. Génère les questions EXCLUSIVEMENT à partir de ce document :

---
{doc_excerpt}
---

Si le document dépasse ce que tu vois, concentre-toi sur le contenu fourni."""
    else:
        source_instruction = f"Génère un quiz sur la branche : {branch}. Difficulté : {difficulty}."

    prompt = f"""Tu es un professeur de droit belge. {source_instruction}

Génère {num_questions} questions QCM. Réponds UNIQUEMENT en JSON valide (pas de markdown, pas de ```):
{{
  "branch": "{branch}",
  "difficulty": "{difficulty}",
  "questions": [
    {{
      "id": 1,
      "question": "La question...",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct": "A",
      "explanation": "Explication juridique avec référence légale belge..."
    }}
  ]
}}

Chaque question doit référencer un article de loi belge ou un principe juridique belge réel.
Ne jamais inventer de loi ou d'article."""

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        log.error(f"Erreur API Claude (quiz): {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du quiz: {e}")
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        result = _json.loads(text)
    except _json.JSONDecodeError:
        result = {"branch": branch, "raw_response": text}

    increment_question_count(current_user["id"])
    return result


@router.post("/flashcards")
@limiter.limit("10/minute")
def student_flashcards(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Génère des flashcards recto/verso sur une branche du droit belge."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    import anthropic, json as _json

    branch = body.get("branch", "Droit civil")
    topic = body.get("topic", "")
    document_content = (body.get("document_content") or "").strip()
    try:
        num_cards = min(int(body.get("num_cards", 12)), 20)
    except (ValueError, TypeError):
        raise HTTPException(400, "Paramètres numériques invalides")

    check_quota(current_user["id"])

    client = anthropic.Anthropic()
    if document_content:
        doc_excerpt = document_content[:6000]
        source_instruction = f"""Voici les notes de cours de l'étudiant. Génère les flashcards EXCLUSIVEMENT à partir de ce document :

---
{doc_excerpt}
---"""
    else:
        extra = f" Focus sur le sujet : {topic}." if topic else ""
        source_instruction = f"Génère {num_cards} flashcards pour réviser la branche : {branch}.{extra}"

    prompt = f"""Tu es un professeur de droit belge. {source_instruction}

Génère {num_cards} flashcards. Réponds UNIQUEMENT en JSON valide (pas de markdown, pas de ```):
{{
  "branch": "{branch}",
  "cards": [
    {{
      "id": 1,
      "front": "Question ou concept (recto)",
      "back": "Réponse détaillée avec article de loi belge (verso)",
      "category": "sous-catégorie"
    }}
  ]
}}

Chaque carte doit référencer le droit belge réel. Ne jamais inventer."""

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        log.error(f"Erreur API Claude (flashcards): {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération des flashcards: {e}")
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        result = _json.loads(text)
    except _json.JSONDecodeError:
        result = {"branch": branch, "raw_response": text}

    increment_question_count(current_user["id"])
    return result


@router.post("/summary")
@limiter.limit("10/minute")
def student_summary(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Génère un résumé structuré d'un sujet de droit belge pour étudiants."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    import anthropic

    branch = body.get("branch", "Droit civil")
    topic = body.get("topic", branch)
    document_content = (body.get("document_content") or "").strip()

    check_quota(current_user["id"])

    client = anthropic.Anthropic()
    if document_content:
        doc_excerpt = document_content[:6000]
        prompt = f"""Tu es un professeur de droit belge. L'étudiant t'a fourni ses notes de cours.
Rédige un résumé structuré et pédagogique BASÉ SUR CES NOTES (complète avec le droit belge réel si besoin) :

---
{doc_excerpt}
---

Structure :
1. Définition et principes fondamentaux
2. Base légale (articles de loi belges réels)
3. Conditions d'application
4. Points clés à retenir (tirés du document)
5. Points d'attention pour l'examen

Niveau : étudiant en droit (Bachelor/Master). Ne jamais inventer de loi ou de jurisprudence."""
    else:
        prompt = f"""Tu es un professeur de droit belge. Rédige un résumé structuré et pédagogique sur :
**{topic}** (branche : {branch}).

Structure :
1. Définition et principes fondamentaux
2. Base légale (articles de loi belges réels)
3. Conditions d'application
4. Jurisprudence importante (arrêts réels belges)
5. Points d'attention pour l'examen
6. Schéma récapitulatif (en texte)

Niveau : étudiant en droit (Bachelor/Master). Droit belge uniquement.
Ne jamais inventer de loi, d'article ou de jurisprudence."""

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        log.error(f"Erreur API Claude (summary): {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du résumé: {e}")

    increment_question_count(current_user["id"])
    return {"branch": branch, "topic": topic, "summary": msg.content[0].text}


@router.get("/dashboard")
@limiter.limit("20/minute")
def student_dashboard(
    request: Request,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Dashboard etudiant : XP, level, streak, badges, progression, activite recente."""
    from api.features.student import get_dashboard_data
    return get_dashboard_data(current_user["id"])


@router.post("/activity")
@limiter.limit("30/minute")
def student_activity(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Enregistre une activite et calcule XP, streak, badges."""
    from api.features.student import calculate_xp, check_and_award_badges, compute_level
    from api.database import (
        upsert_student_progress, update_student_streak,
        save_quiz_history, get_student_total_xp,
    )

    mode = body.get("mode", "quiz")
    branch = body.get("branch", "Droit civil")
    score = int(body.get("score", 0))
    total = int(body.get("total", 0))

    streak_info = update_student_streak(current_user["id"])
    streak_active = streak_info.get("streak_count", 0) > 1

    xp_earned = calculate_xp(mode, score, total, streak_active)
    upsert_student_progress(current_user["id"], branch, xp_earned,
                            quiz_done=1 if mode in ("quiz", "mock_exam", "interleaved", "free_recall") else 0,
                            correct=score, mode=mode)
    save_quiz_history(current_user["id"], branch, mode, score, total, "moyen", xp_earned)
    new_badges = check_and_award_badges(current_user["id"])
    total_xp = get_student_total_xp(current_user["id"])
    level = compute_level(total_xp)

    return {
        "xp_earned": xp_earned,
        "total_xp": total_xp,
        "level": level,
        "streak": streak_info,
        "new_badges": new_badges,
        "streak_multiplier": streak_active,
    }


@router.get("/leaderboard")
@limiter.limit("20/minute")
def student_leaderboard(
    request: Request,
    scope: str = "global",
    branch: str = None,
    group_id: int = None,
):
    """Leaderboard global, par branche ou par groupe."""
    from api.database import get_leaderboard, get_group_leaderboard
    if scope == "group" and group_id:
        return {"scope": "group", "group_id": group_id, "ranking": get_group_leaderboard(group_id)}
    return {"scope": scope, "branch": branch, "ranking": get_leaderboard(branch=branch, limit=20)}


@router.get("/badges")
@limiter.limit("20/minute")
def student_badges_endpoint(
    request: Request,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Liste tous les badges disponibles + ceux gagnes."""
    from api.database import get_student_badges
    from api.features.student import BADGES
    earned = get_student_badges(current_user["id"])
    earned_ids = {b["badge_id"] for b in earned}
    return {
        "earned": earned,
        "available": [dict(b, earned=b["id"] in earned_ids) for b in BADGES],
    }


@router.get("/weak-branches")
@limiter.limit("20/minute")
def student_weak_branches(
    request: Request,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Branches les plus faibles pour revision ciblee."""
    from api.database import get_weak_branches
    return {"weak_branches": get_weak_branches(current_user["id"], limit=3)}


@router.post("/case-study")
@limiter.limit("5/minute")
def student_case_study(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Genere un cas pratique IA sur une branche du droit belge."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    from api.features.student import generate_case_study

    branch = body.get("branch", "Droit civil")
    difficulty = body.get("difficulty", "moyen")

    check_quota(current_user["id"])

    rag_context = ""
    try:
        from rag.retriever import search_legal
        results = search_legal(f"jurisprudence {branch} Belgique", top_k=5)
        if results:
            rag_context = "\n".join([r.get("text", "")[:300] for r in results[:3]])
    except Exception:
        pass

    result = generate_case_study(branch, difficulty, rag_context)
    increment_question_count(current_user["id"])
    return result


@router.post("/case-study/evaluate")
@limiter.limit("5/minute")
def student_case_study_evaluate(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Evalue la reponse d'un etudiant a un cas pratique."""
    from api.features.student import evaluate_case_study
    case_data = body.get("case_data", {})
    answer = body.get("answer", "")
    if not answer or len(answer.strip()) < 50:
        raise HTTPException(status_code=400, detail="Reponse trop courte (minimum 50 caracteres).")
    return evaluate_case_study(case_data, answer.strip())


@router.post("/mock-exam")
@limiter.limit("5/minute")
def student_mock_exam(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Genere un examen blanc QCM multi-branches."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    from api.features.student import generate_mock_exam

    branches = body.get("branches", ["Droit civil"])
    num_questions = min(int(body.get("num_questions", 20)), 30)

    check_quota(current_user["id"])
    result = generate_mock_exam(branches, num_questions)
    increment_question_count(current_user["id"])
    return result


@router.post("/mock-exam/submit")
@limiter.limit("10/minute")
def student_mock_exam_submit(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Corrige et note un examen blanc soumis."""
    from api.features.student import evaluate_mock_exam
    exam_data = body.get("exam_data", {})
    answers = body.get("answers", {})
    return evaluate_mock_exam(exam_data, answers)


@router.post("/podcast")
@limiter.limit("5/minute")
def student_podcast(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Génère un script podcast dialogue 2 hosts sur un sujet de droit belge."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    import anthropic, json as _json

    branch = body.get("branch", "Droit civil")
    topic = body.get("topic", branch)
    document_content = (body.get("document_content") or "").strip()
    check_quota(current_user["id"])

    client = anthropic.Anthropic()

    if document_content:
        doc_excerpt = document_content[:5000]
        source = f"""Les hosts se basent sur ces notes de cours de l'étudiant :

---
{doc_excerpt}
---"""
    else:
        source = f"Les hosts discutent du sujet : **{topic}** (branche : {branch})."

    prompt = f"""Tu es un producteur de podcast éducatif en droit belge. {source}

Génère un épisode de podcast de niveau universitaire, animé par deux hosts :
- **Alex** : le host principal, pédagogue, explique les concepts
- **Léa** : la co-host, pose des questions, donne des exemples concrets, challenge Alex

Le podcast doit :
- Durer environ 8-10 minutes à l'oral (≈ 1200-1500 mots de script)
- Couvrir 3-4 points clés du sujet
- Citer des articles de loi belges réels
- Être engageant et mémorisable pour un étudiant en droit
- Commencer par une accroche (cas concret ou fait surprenant)
- Terminer par un résumé des points clés à retenir

Réponds UNIQUEMENT en JSON valide :
{{
  "title": "Titre de l'épisode",
  "branch": "{branch}",
  "duration_minutes": 9,
  "key_points": ["point 1", "point 2", "point 3"],
  "script": [
    {{"speaker": "Alex", "text": "..."}},
    {{"speaker": "Léa", "text": "..."}}
  ]
}}"""

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=5000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        raise HTTPException(500, f"Erreur génération podcast : {e}")

    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        result = _json.loads(text)
    except _json.JSONDecodeError:
        result = {"branch": branch, "title": topic, "raw_response": text, "script": []}

    increment_question_count(current_user["id"])
    return result


@router.post("/podcast/audio")
@limiter.limit("3/minute")
async def student_podcast_audio(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Convertit un script podcast en audio MP3 via edge-tts (voix françaises)."""
    import asyncio as _aio, base64, io

    script = body.get("script", [])
    if not script or not isinstance(script, list):
        raise HTTPException(400, "Script requis (liste de {speaker, text})")

    try:
        import edge_tts
    except ImportError:
        raise HTTPException(503, "edge-tts non disponible sur ce serveur")

    VOICES = {"Alex": "fr-FR-HenriNeural", "Léa": "fr-FR-DeniseNeural"}
    audio_chunks = io.BytesIO()

    async def _tts_segment(text: str, voice: str) -> bytes:
        comm = edge_tts.Communicate(text, voice, rate="+5%")
        buf = io.BytesIO()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    segments = script[:30]
    for seg in segments:
        speaker = seg.get("speaker", "Alex")
        text = seg.get("text", "")
        if not text.strip():
            continue
        voice = VOICES.get(speaker, VOICES["Alex"])
        try:
            audio_data = await _aio.wait_for(_tts_segment(text, voice), timeout=15)
            audio_chunks.write(audio_data)
        except _aio.TimeoutError:
            continue
        except Exception as e:
            log.warning(f"TTS segment error ({speaker}): {e}")
            continue

    audio_bytes = audio_chunks.getvalue()
    if not audio_bytes:
        raise HTTPException(500, "Aucun audio généré")

    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    return {
        "audio_base64": audio_b64,
        "format": "mp3",
        "size_bytes": len(audio_bytes),
        "segments_count": len(segments),
    }


@router.post("/free-recall")
@limiter.limit("5/minute")
def student_free_recall(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Genere une question ouverte pour rappel libre (active recall maximal)."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    from api.features.student import generate_free_recall_question

    branch = body.get("branch", "Droit civil")
    document_content = (body.get("document_content") or "").strip()
    check_quota(current_user["id"])
    result = generate_free_recall_question(branch, document_content=document_content)
    increment_question_count(current_user["id"])
    return result


@router.post("/free-recall/evaluate")
@limiter.limit("5/minute")
def student_free_recall_evaluate(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Evalue une reponse de rappel libre."""
    from api.features.student import evaluate_free_recall
    question_data = body.get("question_data", {})
    answer = body.get("answer", "")
    if not answer or len(answer.strip()) < 20:
        raise HTTPException(status_code=400, detail="Reponse trop courte (minimum 20 caracteres).")
    return evaluate_free_recall(question_data, answer.strip())


@router.post("/interleaved-quiz")
@limiter.limit("5/minute")
def student_interleaved_quiz(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Genere un quiz melange multi-branches (interleaving)."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    from api.features.student import generate_interleaved_quiz

    branches = body.get("branches", ["Droit civil", "Droit penal", "Droit du travail"])
    num_per_branch = min(int(body.get("num_per_branch", 3)), 5)

    check_quota(current_user["id"])
    result = generate_interleaved_quiz(branches, num_per_branch)
    increment_question_count(current_user["id"])
    return result


# ─── Groups ───────────────────────────────────────────────────────────────────

@router.post("/groups")
@limiter.limit("10/minute")
def create_group(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Cree un groupe d'etude. Retourne le code a partager."""
    from api.database import create_student_group
    name = body.get("name", "").strip()
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Nom du groupe requis (min 2 caracteres).")
    group = create_student_group(name, current_user["id"])
    return group


@router.post("/groups/join")
@limiter.limit("10/minute")
def join_group(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Rejoindre un groupe par code."""
    from api.database import join_student_group
    code = body.get("code", "").strip().upper()
    if not code or len(code) != 6:
        raise HTTPException(status_code=400, detail="Code invalide (6 caracteres).")
    group = join_student_group(code, current_user["id"])
    if not group:
        raise HTTPException(status_code=404, detail="Groupe introuvable.")
    return group


@router.get("/groups")
@limiter.limit("20/minute")
def list_groups(
    request: Request,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Liste les groupes de l'utilisateur."""
    from api.database import get_user_groups
    return {"groups": get_user_groups(current_user["id"])}


# ─── LMS ──────────────────────────────────────────────────────────────────────

@router.get("/lms/universities")
@limiter.limit("30/minute")
def lms_universities(request: Request):
    """Liste les universités belges connues avec leurs URLs Moodle."""
    from api.features.lms import KNOWN_UNIVERSITIES
    return {"universities": KNOWN_UNIVERSITIES}


@router.post("/lms/connect")
@limiter.limit("5/minute")
def lms_connect(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Connecte l'étudiant à son Moodle. Stocke le token."""
    from api.features.lms import moodle_authenticate, get_site_info
    from api.database import save_lms_connection

    site_url = body.get("site_url", "").strip().rstrip("/")
    username = body.get("username", "").strip()
    password = body.get("password", "")
    platform = body.get("platform", "moodle")

    if not site_url or not username or not password:
        raise HTTPException(status_code=400, detail="URL, identifiant et mot de passe requis")

    try:
        token = moodle_authenticate(site_url, username, password)
        info = get_site_info(site_url, token)
        save_lms_connection(
            user_id=current_user["id"],
            platform=platform,
            site_url=site_url,
            token=token,
            site_name=info.get("site_name", ""),
            user_fullname=info.get("user_fullname", ""),
            moodle_user_id=info.get("moodle_user_id"),
        )
        return {
            "connected": True,
            "site_name": info.get("site_name", ""),
            "user_fullname": info.get("user_fullname", ""),
            "platform": platform,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"/student/lms/connect error: {e}")
        raise HTTPException(status_code=500, detail="Erreur de connexion à la plateforme")


@router.get("/lms/status")
@limiter.limit("20/minute")
def lms_status(
    request: Request,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Vérifie si l'étudiant a une connexion LMS active."""
    from api.database import get_lms_connection
    conn = get_lms_connection(current_user["id"])
    if conn:
        return {
            "connected": True,
            "platform": conn["platform"],
            "site_name": conn.get("site_name", ""),
            "user_fullname": conn.get("user_fullname", ""),
            "site_url": conn["site_url"],
        }
    return {"connected": False}


@router.get("/lms/courses")
@limiter.limit("10/minute")
def lms_courses(
    request: Request,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Récupère les cours Moodle de l'étudiant."""
    from api.database import get_lms_connection, save_lms_course, get_lms_courses
    from api.features.lms import get_courses

    conn = get_lms_connection(current_user["id"])
    if not conn:
        raise HTTPException(status_code=400, detail="Aucune connexion LMS. Connecte-toi d'abord.")

    try:
        courses = get_courses(conn["site_url"], conn["token"], conn.get("moodle_user_id"))
        for c in courses:
            save_lms_course(
                user_id=current_user["id"],
                connection_id=conn["id"],
                course_id=c["id"],
                course_name=c["name"],
                course_shortname=c.get("shortname", ""),
            )
        return {"courses": courses}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"/student/lms/courses error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des cours")


@router.get("/lms/course/{course_id}/content")
@limiter.limit("10/minute")
def lms_course_content(
    request: Request,
    course_id: int,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Récupère le contenu détaillé d'un cours (sections, modules, fichiers)."""
    from api.database import get_lms_connection
    from api.features.lms import get_course_content

    conn = get_lms_connection(current_user["id"])
    if not conn:
        raise HTTPException(status_code=400, detail="Aucune connexion LMS")

    try:
        content = get_course_content(conn["site_url"], conn["token"], course_id)
        return {"course_id": course_id, "sections": content}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/lms/import")
@limiter.limit("5/minute")
def lms_import_content(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Importe et extrait le texte d'un fichier Moodle pour alimenter les quiz/flashcards."""
    from api.database import get_lms_connection, save_lms_course
    from api.features.lms import download_and_extract

    conn = get_lms_connection(current_user["id"])
    if not conn:
        raise HTTPException(status_code=400, detail="Aucune connexion LMS")

    file_url = body.get("file_url", "")
    course_id = body.get("course_id")
    course_name = body.get("course_name", "Cours importé")

    if not file_url:
        raise HTTPException(status_code=400, detail="URL du fichier requise")

    try:
        text = download_and_extract(conn["site_url"], conn["token"], file_url)
        if course_id:
            save_lms_course(
                user_id=current_user["id"],
                connection_id=conn["id"],
                course_id=course_id,
                course_name=course_name,
                imported_content=text,
            )
        return {"imported": True, "content_length": len(text), "preview": text[:500]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"/student/lms/import error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'import")


@router.delete("/lms/disconnect")
@limiter.limit("5/minute")
def lms_disconnect(
    request: Request,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Déconnecte l'étudiant de son LMS."""
    from api.database import delete_lms_connection
    delete_lms_connection(current_user["id"])
    return {"disconnected": True}


# ─── Shared Notes ─────────────────────────────────────────────────────────────

@router.post("/notes/upload-file")
@limiter.limit("10/minute")
async def upload_note_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: Annotated[dict, Depends(_get_current_user)] = None,
):
    """Uploader un fichier de notes (PDF, DOCX, TXT) — extrait le texte côté serveur."""
    import io
    MAX_SIZE = 5 * 1024 * 1024
    filename = file.filename or ""

    raw = await file.read()
    if len(raw) > MAX_SIZE:
        raise HTTPException(400, "Fichier trop volumineux (max 5 MB)")

    from api.security import validate_upload_mime
    detected = validate_upload_mime(raw, allowed={"pdf", "docx", "txt"})

    extracted = ""
    file_type = detected

    if detected == "pdf":
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(raw))
            pages = [reader.pages[i].extract_text() or "" for i in range(min(len(reader.pages), 30))]
            extracted = "\n\n".join(p.strip() for p in pages if p.strip())
        except Exception as e:
            raise HTTPException(422, f"Impossible d'extraire le texte du PDF : {e}")

    elif detected == "docx":
        try:
            import docx
            doc = docx.Document(io.BytesIO(raw))
            extracted = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            raise HTTPException(422, f"Impossible d'extraire le texte du DOCX : {e}")

    elif detected == "txt":
        try:
            extracted = raw.decode("utf-8", errors="replace")
        except Exception as e:
            raise HTTPException(422, f"Impossible de lire le fichier texte : {e}")

    else:
        raise HTTPException(415, "Format non supporté. Utilisez PDF, DOCX ou TXT.")

    if not extracted.strip():
        raise HTTPException(422, "Le fichier ne contient pas de texte extractible.")

    return {
        "file_type": file_type,
        "filename": filename,
        "extracted_text": extracted[:20000],
        "char_count": len(extracted),
        "pages": len(extracted.split("\n\n")),
    }


@router.post("/notes/share")
@limiter.limit("5/minute")
def share_note(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Partager une note/synthèse avec la communauté étudiante."""
    from api.database import create_shared_note
    title = body.get("title", "").strip()
    subject = body.get("subject", "").strip()
    content = body.get("content_text", "").strip()
    if not title or not subject:
        raise HTTPException(400, "Titre et matière requis")
    if not content and not body.get("file_url"):
        raise HTTPException(400, "Contenu texte ou fichier requis")
    is_anon = body.get("is_anonymous", True)
    author = "Anonyme" if is_anon else (body.get("author_name") or current_user.get("email", "").split("@")[0])
    note = create_shared_note(
        user_id=current_user["id"],
        author_name=author,
        is_anonymous=is_anon,
        title=title,
        subject=subject,
        university=body.get("university"),
        study_year=body.get("study_year"),
        file_type=body.get("file_type", "text"),
        content_text=content or None,
        file_url=body.get("file_url"),
    )
    return note


@router.get("/notes")
@limiter.limit("30/minute")
def list_notes(
    request: Request,
    subject: Optional[str] = Query(default=None),
    university: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
):
    """Lister les notes partagées (filtrable par matière/université)."""
    from api.database import list_shared_notes
    return list_shared_notes(subject=subject, university=university, limit=limit, offset=offset)


@router.get("/notes/{note_id}")
@limiter.limit("30/minute")
def get_note(request: Request, note_id: int):
    """Récupérer une note partagée en entier (contenu complet)."""
    from api.database import get_shared_note, increment_note_downloads
    note = get_shared_note(note_id)
    if not note:
        raise HTTPException(404, "Note introuvable")
    increment_note_downloads(note_id)
    return note


@router.post("/notes/{note_id}/like")
@limiter.limit("10/minute")
def like_note(
    request: Request,
    note_id: int,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Liker une note partagée."""
    from api.database import get_shared_note, increment_note_likes
    note = get_shared_note(note_id)
    if not note:
        raise HTTPException(404, "Note introuvable")
    increment_note_likes(note_id)
    return {"liked": True}


@router.delete("/notes/{note_id}")
@limiter.limit("5/minute")
def remove_note(
    request: Request,
    note_id: int,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Supprimer sa propre note."""
    from api.database import delete_shared_note
    deleted = delete_shared_note(note_id, current_user["id"])
    if not deleted:
        raise HTTPException(403, "Vous ne pouvez supprimer que vos propres notes")
    return {"deleted": True}


# ─── NotebookLM ───────────────────────────────────────────────────────────────

@router.post("/notebooklm/create")
@limiter.limit("3/minute")
async def create_notebooklm_notebook(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Crée un notebook NotebookLM depuis le contenu de l'étudiant et retourne l'URL partage."""
    import asyncio as _asyncio
    if not _NLM_READY:
        raise HTTPException(503, "NotebookLM non configuré sur ce serveur (NOTEBOOKLM_STORAGE manquant)")
    try:
        from notebooklm import NotebookLMClient
    except ImportError:
        raise HTTPException(503, "notebooklm-py non installé sur ce serveur")

    title = body.get("title", "Notes Lexavo").strip() or "Notes Lexavo"
    content = (body.get("content_text") or "").strip()
    branch = (body.get("branch") or "").strip()

    if not content:
        raise HTTPException(400, "Contenu texte requis (document_content vide)")
    if len(content) < 100:
        raise HTTPException(400, "Contenu trop court pour créer un notebook")

    nb_title = f"[Lexavo] {title}" if branch not in title else f"[Lexavo] {title} — {branch}"

    async def _create():
        async with await NotebookLMClient.from_storage() as client:
            nb = await client.notebooks.create(nb_title)
            source_title = title if len(title) < 60 else title[:57] + "..."
            await client.sources.add_text(nb.id, source_title, content[:50000])
            await client.notebooks.share(nb.id, public=True)
            url = await client.notebooks.get_share_url(nb.id)
            return {"notebook_id": nb.id, "url": url, "title": nb_title}

    try:
        result = await _asyncio.wait_for(_create(), timeout=30)
        return result
    except _asyncio.TimeoutError:
        raise HTTPException(504, "NotebookLM a mis trop de temps à répondre")
    except Exception as e:
        log.error(f"NotebookLM create error: {e}")
        raise HTTPException(502, f"Erreur NotebookLM : {str(e)[:200]}")
