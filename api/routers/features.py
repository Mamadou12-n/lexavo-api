"""Router Features — diagnostic, score, response, contracts, compliance, audit,
defend, alerts, litigation, match, emergency, proof, heritage, fiscal,
newsletter, notifications."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from typing import Annotated, Optional

from api.models import AuditRequest, AuditResponse, DefendRequest, DefendResponse, SourceDoc
from api.auth import get_current_user as _get_current_user
from api.routers.deps import get_api_key, limiter

log = logging.getLogger("api.features")

router = APIRouter(tags=["features"])

_REL_MAP = {
    "enfant": "direct_line", "fils": "direct_line", "fille": "direct_line",
    "parent": "direct_line", "père": "direct_line", "pere": "direct_line",
    "mère": "direct_line", "mere": "direct_line",
    "epoux": "direct_line", "époux": "direct_line", "conjoint": "direct_line",
    "epouse": "direct_line", "épouse": "direct_line",
    "frere": "siblings", "frère": "siblings",
    "soeur": "siblings", "sœur": "siblings",
    "autre": "others", "other": "others",
    "oncle": "others", "tante": "others", "neveu": "others",
    "cousin": "others", "cousine": "others",
}


def _normalize_rel(raw: str) -> str:
    raw = str(raw).strip().lower()
    if raw in ("direct_line", "siblings", "others"):
        return raw
    return _REL_MAP.get(raw, raw)


# ─── Diagnostic ───────────────────────────────────────────────────────────────

@router.get("/diagnostic/questions")
def diagnostic_questions():
    from api.features.diagnostic import get_questions
    return {"questions": get_questions()}


@router.post("/diagnostic/analyze")
@limiter.limit("5/minute")
def diagnostic_analyze(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Génère un diagnostic personnalisé à partir des réponses."""
    from api.features.diagnostic import generate_diagnostic
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    answers = body.get("answers", [])
    description = body.get("description", "")
    if not answers and description:
        answers = [
            {"question_id": 1, "answer": description},
            {"question_id": 2, "answer": body.get("region", "bruxelles")},
            {"question_id": 3, "answer": "analyse demandée"},
        ]
    if len(answers) < 3:
        raise HTTPException(400, "Minimum 3 réponses requises pour un diagnostic.")
    check_quota(current_user["id"])
    try:
        result = generate_diagnostic(answers=answers)
    except ValueError as e:
        raise HTTPException(400, str(e))
    increment_question_count(current_user["id"])
    return result


# ─── Score ────────────────────────────────────────────────────────────────────

@router.get("/score/questions")
def score_questions():
    from api.features.score import get_score_questions
    return {"questions": get_score_questions()}


@router.post("/score/evaluate")
def score_evaluate(body: dict):
    from api.features.score import calculate_score
    answers = body.get("answers", [])
    if isinstance(answers, dict):
        answers = [{"question_id": i + 1, "answer": v} for i, (k, v) in enumerate(answers.items())]
    if not isinstance(answers, list):
        raise HTTPException(400, "answers doit être une liste.")
    try:
        return calculate_score(answers=answers)
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(400, str(e))


# ─── Legal Response ───────────────────────────────────────────────────────────

@router.post("/response/generate")
@limiter.limit("5/minute")
def response_generate(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Génère une réponse à un courrier juridique reçu."""
    from api.features.legal_response import generate_response
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    received_text = body.get("received_text", "") or body.get("received_letter", "") or body.get("letter_text", "")
    user_context = body.get("user_context") or body.get("tone")
    if len(received_text.strip()) < 20:
        raise HTTPException(400, "Le courrier est trop court (minimum 20 caractères).")
    check_quota(current_user["id"])
    try:
        result = generate_response(received_text=received_text, user_context=user_context)
    except ValueError as e:
        raise HTTPException(400, str(e))
    increment_question_count(current_user["id"])
    return result


# ─── Contracts ────────────────────────────────────────────────────────────────

@router.get("/contracts/templates")
def contracts_list(
    category: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
):
    from api.features.contracts import list_templates
    templates = list_templates(category=category, region=region)
    return {"templates": templates, "total": len(templates)}


@router.get("/contracts/{template_id}")
def contracts_get(template_id: str):
    from api.features.contracts import get_template
    template = get_template(template_id)
    if not template:
        raise HTTPException(404, "Template introuvable.")
    return template


@router.post("/contracts/{template_id}/generate")
def contracts_generate(
    template_id: str,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.contracts import generate_contract_html
    html = generate_contract_html(template_id=template_id, variables=body.get("variables", {}))
    return {"html": html, "template_id": template_id}


# ─── Compliance ───────────────────────────────────────────────────────────────

@router.get("/compliance/questions")
def compliance_questions():
    from api.features.compliance import get_compliance_questions
    return {"questions": get_compliance_questions()}


@router.post("/compliance/audit")
@limiter.limit("3/minute")
def compliance_audit(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.compliance import generate_compliance_audit
    answers = body.get("answers", [])
    if not answers or len(answers) < 5:
        raise HTTPException(400, "Minimum 5 réponses requises.")
    try:
        return generate_compliance_audit(answers=answers, company_type=body.get("company_type", "independant"))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Audit Entreprise ─────────────────────────────────────────────────────────

@router.get("/audit/questions")
def audit_questions(company_type: str = Query(default="srl")):
    from api.features.audit_entreprise import get_audit_questions, get_company_types, get_audit_categories
    return {
        "questions": get_audit_questions(company_type),
        "company_types": get_company_types(),
        "categories": get_audit_categories(),
    }


@router.post("/audit/generate", response_model=AuditResponse)
@limiter.limit("3/minute")
def audit_generate(
    request: Request,
    body: AuditRequest,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.audit_entreprise import generate_audit_report
    from api.stripe_billing import check_quota, is_beta_active
    from api.database import get_subscription, increment_question_count

    check_quota(current_user["id"])
    if not is_beta_active():
        sub = get_subscription(current_user["id"])
        plan = sub.get("plan", "free") if sub else "free"
        if plan in ("free", "basic"):
            raise HTTPException(403, "L'audit entreprise est réservé aux plans Business, Firm et Enterprise.")

    result = generate_audit_report(
        answers=[{"question_id": a.question_id, "answer": a.answer} for a in body.answers],
        company_type=body.company_type,
        company_name=body.company_name or "",
        sector=body.sector or "",
        employees=body.employees or 0,
    )
    increment_question_count(current_user["id"])
    return AuditResponse(**result)


@router.get("/audit/history")
def audit_history(current_user: Annotated[dict, Depends(_get_current_user)]):
    from api.database import get_audit_reports
    reports = get_audit_reports(current_user["id"])
    return {"reports": reports, "total": len(reports)}


# ─── Defend ───────────────────────────────────────────────────────────────────

@router.get("/defend/categories")
def defend_categories():
    from api.features.defend import get_defend_categories
    return {"categories": get_defend_categories()}


@router.post("/defend/detect")
def defend_detect(body: dict):
    from api.features.defend import detect_situation_type
    description = body.get("description", "")
    if len(description.strip()) < 10:
        raise HTTPException(400, "Description trop courte")
    return detect_situation_type(description)


@router.post("/defend/analyze", response_model=DefendResponse)
@limiter.limit("5/minute")
def defend_analyze(
    request: Request,
    body: DefendRequest,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.defend import analyze_and_generate
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    check_quota(current_user["id"])
    try:
        result = analyze_and_generate(
            description=body.description,
            category=body.category,
            region=body.region,
            user_name=body.user_name or "",
            user_address=body.user_address or "",
            photos_base64=body.photos_base64 or [],
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        log.error(f"Defend error: {e}")
        raise HTTPException(500, "Erreur lors de l'analyse.")

    increment_question_count(current_user["id"])
    sources = [SourceDoc(**s) for s in result.get("sources", [])]
    laws = [{"article": l.get("article", ""), "content": l.get("content", ""), "source": l.get("source")} for l in result.get("applicable_law", [])]

    return DefendResponse(
        detection=result.get("detection", {}),
        situation_analysis=result.get("situation_analysis", ""),
        applicable_law=laws,
        contestation_possible=result.get("contestation_possible", False),
        success_probability=result.get("success_probability", "indeterminee"),
        document_type=result.get("document_type", "contestation"),
        document_text=result.get("document_text", ""),
        recipient=result.get("recipient"),
        deadline=result.get("deadline"),
        next_steps=result.get("next_steps", []),
        cost_estimate=result.get("cost_estimate"),
        sources=sources,
        generated_at=result.get("generated_at", ""),
    )


@router.post("/defend/checklist")
@limiter.limit("10/minute")
def defend_checklist(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.defend import analyze_checklist
    from api.stripe_billing import check_quota
    check_quota(current_user["id"])
    try:
        return analyze_checklist(
            category=body.get("category", "amende"),
            answers=body.get("answers", {}),
            region=body.get("region"),
            extra_description=body.get("description", ""),
            photos_base64=body.get("photos", []),
            tone=body.get("tone", "formel"),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        log.error(f"/defend/checklist error: {e}")
        raise HTTPException(500, "Erreur lors de l'analyse")


@router.post("/defend/regenerate-letter")
@limiter.limit("10/minute")
def defend_regenerate_letter(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.defend import generate_letter, TONE_INSTRUCTIONS
    from api.stripe_billing import check_quota
    check_quota(current_user["id"])
    tone = body.get("tone", "formel")
    if tone not in TONE_INSTRUCTIONS:
        raise HTTPException(400, f"Ton invalide. Options : {list(TONE_INSTRUCTIONS.keys())}")
    try:
        letter = generate_letter(body.get("description", ""), body.get("vices_str", ""), body.get("legal_context", ""), tone=tone)
        return {"letter": letter, "tone": tone}
    except Exception as e:
        log.error(f"/defend/regenerate-letter error: {e}")
        raise HTTPException(500, "Erreur lors de la génération")


@router.post("/defend/scan-amende")
@limiter.limit("5/minute")
def defend_scan_amende(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.defend import scan_amende
    from api.stripe_billing import check_quota
    check_quota(current_user["id"])
    photos = body.get("photos", [])
    if not photos:
        raise HTTPException(400, "Au moins une photo est requise")
    try:
        return scan_amende(photos_base64=photos, category=body.get("category", "amende"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        log.error(f"/defend/scan-amende error: {e}")
        raise HTTPException(500, "Erreur lors du scan")


# ─── Alerts ───────────────────────────────────────────────────────────────────

@router.get("/alerts/domains")
def alerts_domains():
    from api.features.alerts import get_alert_domains
    return {"domains": get_alert_domains()}


@router.post("/alerts/preferences")
def alerts_save_preferences(
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.database import update_alert_preferences
    return update_alert_preferences(
        user_id=current_user["id"],
        domains=body.get("domains", []),
        frequency=body.get("frequency"),
        enabled=body.get("enabled"),
    )


@router.get("/alerts/feed")
def alerts_feed(
    current_user: Annotated[dict, Depends(_get_current_user)],
    domains: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
):
    from api.features.alerts import get_alert_feed
    if domains:
        domain_list = [d.strip() for d in domains.split(",")]
    else:
        try:
            from api.database import get_alert_preferences
            prefs = get_alert_preferences(current_user["id"])
            domain_list = prefs.get("domains", []) if isinstance(prefs, dict) else []
        except Exception:
            domain_list = []
    if not domain_list:
        domain_list = ["travail", "fiscal", "bail"]
    try:
        feed = get_alert_feed(domains=domain_list, limit=limit)
    except Exception:
        feed = []
    return {"alerts": feed, "total": len(feed)}


# ─── Litigation ───────────────────────────────────────────────────────────────

@router.get("/litigation/stages")
def litigation_stages():
    from api.features.litigation import get_stages
    return {"stages": get_stages()}


@router.post("/litigation/start")
@limiter.limit("5/minute")
def litigation_start(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.litigation import start_litigation
    try:
        return start_litigation(
            creditor_name=body.get("creditor_name", ""),
            debtor_name=body.get("debtor_name", ""),
            amount=body.get("amount", 0),
            invoice_number=body.get("invoice_number", ""),
            due_date=body.get("due_date", ""),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Match ────────────────────────────────────────────────────────────────────

@router.post("/match/find")
def match_find(
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.match import find_matching_lawyers
    try:
        return find_matching_lawyers(
            description=body.get("description", ""),
            city=body.get("city"),
            language=body.get("language", "fr"),
            budget=body.get("budget"),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Emergency ────────────────────────────────────────────────────────────────

@router.get("/emergency/categories")
def emergency_categories():
    from api.features.emergency import get_categories
    return {"categories": get_categories()}


@router.post("/emergency/request")
def emergency_request(
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.emergency import create_emergency_request, EMERGENCY_PRICE_CENTS
    try:
        result = create_emergency_request(
            user_id=current_user["id"],
            category=body.get("category", "autre"),
            description=body.get("description", ""),
            phone=body.get("phone", ""),
            city=body.get("city", ""),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        import stripe as _stripe
        from api.stripe_billing import FRONTEND_URL
        session = _stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": EMERGENCY_PRICE_CENTS,
                    "product_data": {"name": "Lexavo Emergency — Avocat en 2h"},
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{FRONTEND_URL}/emergency/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/emergency/cancel",
            metadata={
                "lexavo_user_id": str(current_user["id"]),
                "lexavo_type": "emergency",
                "emergency_id": str(result["id"]),
            },
        )
        result["checkout_url"] = session.url
        result["stripe_session_id"] = session.id
    except Exception as e:
        log.error(f"Emergency checkout error: {e}")
        result["checkout_url"] = None
        result["stripe_session_id"] = None
    return result


# ─── Proof ────────────────────────────────────────────────────────────────────

@router.post("/proof/create")
def proof_create(
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.database import create_proof_case
    title = body.get("title", "")
    if not title or len(title.strip()) < 3:
        raise HTTPException(400, "Le titre du dossier doit contenir au moins 3 caractères.")
    return create_proof_case(user_id=current_user["id"], title=title.strip(), description=body.get("description", ""))


@router.get("/proof/cases")
def proof_list(current_user: Annotated[dict, Depends(_get_current_user)]):
    from api.database import list_proof_cases
    cases = list_proof_cases(current_user["id"])
    return {"cases": cases, "total": len(cases)}


@router.post("/proof/{case_id}/add-entry")
def proof_add_entry(
    case_id: int,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.database import get_proof_case, add_proof_entry
    case = get_proof_case(case_id)
    if not case:
        raise HTTPException(404, "Dossier de preuves introuvable.")
    if case["user_id"] != current_user["id"]:
        raise HTTPException(403, "Accès refusé à ce dossier.")
    return add_proof_entry(case_id=case_id, entry_type=body.get("type", "note"), content=body.get("content", ""), metadata=body.get("metadata"))


@router.get("/proof/{case_id}/entries")
def proof_entries(
    case_id: int,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.database import get_proof_case, list_proof_entries
    case = get_proof_case(case_id)
    if not case:
        raise HTTPException(404, "Dossier de preuves introuvable.")
    if case["user_id"] != current_user["id"]:
        raise HTTPException(403, "Accès refusé.")
    entries = list_proof_entries(case_id)
    return {"entries": entries, "total": len(entries)}


# ─── Heritage ─────────────────────────────────────────────────────────────────

@router.post("/heritage/guide")
@limiter.limit("10/minute")
def heritage_guide(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.heritage import generate_heritage_guide
    from api.stripe_billing import check_quota
    check_quota(current_user["id"])
    relationship = _normalize_rel(body.get("relationship") or body.get("lien_parente") or "direct_line")
    try:
        return generate_heritage_guide(
            region=body.get("region", ""),
            relationship=relationship,
            has_testament=body.get("has_testament", False),
            has_real_estate=body.get("has_real_estate", False),
            estimated_value=body.get("estimated_value", 0),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Fiscal ───────────────────────────────────────────────────────────────────

@router.post("/fiscal/ask")
@limiter.limit("5/minute")
def fiscal_ask(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.features.fiscal import ask_fiscal
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    check_quota(current_user["id"])
    try:
        result = ask_fiscal(question=body.get("question", ""), photos_base64=body.get("photos_base64") or [])
        increment_question_count(current_user["id"])
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Newsletter ───────────────────────────────────────────────────────────────

@router.get("/newsletter/preview")
def newsletter_preview(week: int = Query(default=1, ge=1, le=52)):
    from api.features.newsletter import generate_newsletter_html
    html = generate_newsletter_html(week_num=week)
    return HTMLResponse(content=html, status_code=200)


@router.post("/newsletter/subscribe")
def newsletter_subscribe(body: dict):
    from api.database import subscribe_newsletter
    import re
    email = body.get("email", "").strip().lower()
    domains = body.get("domains", [])
    if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        raise HTTPException(400, "Adresse email invalide.")
    if not isinstance(domains, list):
        domains = []
    result = subscribe_newsletter(email=email, domains=domains)
    if not result:
        raise HTTPException(409, "Email déjà inscrit.")
    return {"status": "subscribed", "email": result["email"], "domains": result["domains"], "confirmed": result["confirmed"], "message": "Inscription enregistrée. Consultez vos emails pour confirmer."}


@router.get("/newsletter/unsubscribe")
def newsletter_unsubscribe(token: str = Query(...)):
    from api.database import unsubscribe_newsletter
    success = unsubscribe_newsletter(token=token)
    if success:
        html = """<!DOCTYPE html><html><body style="font-family:Arial;text-align:center;padding:60px">
        <h2 style="color:#1C2B3A">Vous êtes désinscrit(e)</h2>
        <p>Vous ne recevrez plus la newsletter Lexavo.</p>
        <a href="https://lexavo.be" style="color:#E85D26">Retourner sur Lexavo →</a>
        </body></html>"""
        return HTMLResponse(content=html, status_code=200)
    raise HTTPException(404, "Token de désinscription inconnu ou déjà utilisé.")


# ─── Notifications ────────────────────────────────────────────────────────────

@router.post("/notifications/register")
def notifications_register(
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.database import save_push_token
    token = body.get("token", "").strip()
    if not token:
        raise HTTPException(400, "Token push manquant.")
    save_push_token(user_id=current_user["id"], token=token)
    return {"status": "registered", "token": token}


@router.post("/notifications/preferences")
def notifications_preferences(
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    from api.database import update_push_preferences
    token = body.get("token", "").strip()
    preferences = body.get("preferences", {})
    if not isinstance(preferences, dict):
        raise HTTPException(400, "Préférences invalides.")
    update_push_preferences(user_id=current_user["id"], token=token, preferences=preferences)
    return {"status": "updated", "preferences": preferences}


# ─── Billing cancel/restore (hors prefix /billing) ───────────────────────────

@router.post("/billing/cancel")
def billing_cancel(current_user: Annotated[dict, Depends(_get_current_user)]):
    from api.stripe_billing import cancel_subscription
    return cancel_subscription(current_user["id"])


@router.post("/billing/restore")
def billing_restore(current_user: Annotated[dict, Depends(_get_current_user)]):
    from api.stripe_billing import restore_subscription
    return restore_subscription(current_user["id"])
