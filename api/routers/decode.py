"""Router Decode — /decode/*."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from typing import Annotated

from api.auth import get_current_user as _get_current_user
from api.routers.deps import get_api_key, limiter

log = logging.getLogger("api.decode")

router = APIRouter(prefix="/decode", tags=["decode"])


@router.post("/analyze")
@limiter.limit("5/minute")
def decode_analyze(
    request: Request,
    body: dict,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Traduit un document administratif en langage clair."""
    from api.features.decode import decode_document
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    text = body.get("document_text") or body.get("text", "")
    if len(text.strip()) < 20:
        raise HTTPException(400, "Le document est trop court.")

    check_quota(current_user["id"])
    result = decode_document(text=text)
    increment_question_count(current_user["id"])
    return result


@router.post("/upload")
@limiter.limit("5/minute")
async def decode_upload(
    request: Request,
    file: UploadFile = File(...),
    api_key: Annotated[str, Depends(get_api_key)] = None,
    current_user: Annotated[dict, Depends(_get_current_user)] = None,
):
    """Upload un document admin (PDF/image) puis OCR puis traduction."""
    from api.utils.ocr import extract_text_from_image, extract_text_from_pdf
    from api.features.decode import decode_document
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    from api.security import validate_upload_mime

    check_quota(current_user["id"])
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Fichier trop volumineux (max 10 MB)")
    detected = validate_upload_mime(content, allowed={"pdf", "jpeg", "png"})

    text = extract_text_from_pdf(content) if detected == "pdf" else extract_text_from_image(content)
    if len(text.strip()) < 20:
        raise HTTPException(400, "Impossible d'extraire du texte.")

    result = decode_document(text=text)
    increment_question_count(current_user["id"])
    return {"extracted_text": text[:2000], "analysis": result}
