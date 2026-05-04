"""Router Shield — /shield/*."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from typing import Annotated

from api.models import (
    ShieldAnalyzeRequest, ShieldAnalyzeResponse, ShieldClause,
    ShieldUploadResponse, SourceDoc,
)
from api.auth import get_current_user as _get_current_user
from api.routers.deps import get_api_key, limiter

log = logging.getLogger("api.shield")

router = APIRouter(prefix="/shield", tags=["shield"])


@router.post("/analyze", response_model=ShieldAnalyzeResponse)
@limiter.limit("5/minute")
def shield_analyze(
    request: Request,
    body: ShieldAnalyzeRequest,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Analyse un contrat et retourne le verdict feu tricolore."""
    from api.features.shield import analyze_contract_text
    from api.database import save_shield_analysis, increment_question_count
    from api.stripe_billing import check_quota
    import json as _json

    check_quota(current_user["id"])

    try:
        result = analyze_contract_text(
            text=body.contract_text,
            contract_type=body.contract_type,
            region=body.region,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Shield analysis error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse du contrat.")

    increment_question_count(current_user["id"])
    save_shield_analysis(
        user_id=current_user["id"],
        contract_type=result.get("contract_type_detected", "general"),
        verdict=result["verdict"],
        summary=result["summary"],
        clauses_json=_json.dumps(result.get("clauses", []), ensure_ascii=False),
        sources_json=_json.dumps(result.get("sources", []), ensure_ascii=False),
    )

    sources = [SourceDoc(**s) for s in result.get("sources", [])]
    return ShieldAnalyzeResponse(
        verdict=result["verdict"],
        score=result.get("score", 50),
        summary=result["summary"],
        clauses=[ShieldClause(**c) for c in result.get("clauses", [])],
        contract_type_detected=result.get("contract_type_detected"),
        region=result.get("region"),
        legal_sources=sources,
    )


@router.post("/upload", response_model=ShieldUploadResponse)
@limiter.limit("5/minute")
async def shield_upload(
    request: Request,
    file: UploadFile = File(..., description="Contrat PDF ou image (JPG/PNG)"),
    api_key: Annotated[str, Depends(get_api_key)] = None,
    current_user: Annotated[dict, Depends(_get_current_user)] = None,
):
    """Upload un contrat (PDF/image) puis OCR puis analyse Shield."""
    from api.utils.ocr import extract_text_from_image, extract_text_from_pdf
    from api.features.shield import analyze_contract_text
    from api.database import save_shield_analysis, increment_question_count
    from api.stripe_billing import check_quota
    from api.security import validate_upload_mime
    import json as _json

    check_quota(current_user["id"])
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Fichier trop volumineux (max 10 MB)")
    detected = validate_upload_mime(content, allowed={"pdf", "jpeg", "png"})

    text = extract_text_from_pdf(content) if detected == "pdf" else extract_text_from_image(content)
    if len(text.strip()) < 50:
        raise HTTPException(400, "Impossible d'extraire suffisamment de texte du document.")

    result = analyze_contract_text(text=text)
    increment_question_count(current_user["id"])
    save_shield_analysis(
        user_id=current_user["id"],
        contract_type=result.get("contract_type_detected", "general"),
        verdict=result["verdict"],
        summary=result["summary"],
        clauses_json=_json.dumps(result.get("clauses", []), ensure_ascii=False),
        sources_json=_json.dumps(result.get("sources", []), ensure_ascii=False),
    )

    sources = [SourceDoc(**s) for s in result.get("sources", [])]
    return ShieldUploadResponse(
        extracted_text=text[:2000],
        analysis=ShieldAnalyzeResponse(
            verdict=result["verdict"],
            summary=result["summary"],
            clauses=[ShieldClause(**c) for c in result.get("clauses", [])],
            contract_type_detected=result.get("contract_type_detected"),
            legal_sources=sources,
        ),
    )


@router.get("/history")
def shield_history(current_user: Annotated[dict, Depends(_get_current_user)]):
    """Historique des analyses Shield de l'utilisateur."""
    from api.database import list_shield_analyses
    import json as _json

    analyses = list_shield_analyses(current_user["id"])
    for a in analyses:
        a["clauses"] = _json.loads(a.get("clauses_json", "[]"))
        a["sources"] = _json.loads(a.get("sources_json", "[]"))
    return {"analyses": analyses, "total": len(analyses)}
