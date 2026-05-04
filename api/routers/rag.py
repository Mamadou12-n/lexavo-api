"""Router RAG — /ask, /ask/stream, /search, /branches."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Annotated

from api.models import (
    AskRequest, AskResponse, SourceDoc,
    SearchRequest, SearchResponse, SearchResult,
)
from api.auth import get_current_user as _get_current_user
from api.routers.deps import get_api_key, limiter

log = logging.getLogger("api.rag")

router = APIRouter(tags=["rag"])


@router.post("/ask", response_model=AskResponse)
@limiter.limit("10/minute")
def ask_endpoint(
    request: Request,
    body: AskRequest,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Endpoint principal : question juridique → réponse RAG avec détection de branche."""
    from rag.pipeline import ask
    from rag.indexer_qdrant import get_index_stats as _qdrant_stats
    from api.stripe_billing import check_quota
    from api.database import (
        increment_question_count, create_conversation,
        list_messages, create_message, get_conversation_by_id,
    )
    import json

    _qstats = _qdrant_stats()
    if _qstats.get("status") != "ok":
        raise HTTPException(
            status_code=503,
            detail=f"Qdrant indisponible: {_qstats.get('error', 'unknown')}. "
                   "Lance les containers : docker compose up -d qdrant ollama.",
        )

    check_quota(current_user["id"])

    conversation_id = body.conversation_id
    history = None

    if conversation_id:
        conv = get_conversation_by_id(conversation_id)
        if not conv or conv["user_id"] != current_user["id"]:
            raise HTTPException(404, "Conversation non trouvée.")
        prev_messages = list_messages(conversation_id)
        if prev_messages:
            history = [{"role": m["role"], "content": m["content"]} for m in prev_messages]
    else:
        title = body.question[:60] + ("..." if len(body.question) > 60 else "")
        conv = create_conversation(current_user["id"], title)
        conversation_id = conv["id"]

    enriched_question = body.question
    if body.photos_base64:
        try:
            from api.utils.ocr import extract_text_from_base64_list
            ocr_text = extract_text_from_base64_list(body.photos_base64)
            if ocr_text:
                enriched_question = f"{body.question}\n\n[Texte extrait des photos jointes]\n{ocr_text}"
        except Exception as e:
            log.warning(f"OCR photos /ask ignoré : {e}")

    try:
        result = ask(
            question=enriched_question,
            top_k=body.top_k,
            source_filter=body.source_filter,
            model=body.model,
            anthropic_api_key=api_key,
            branch=body.branch,
            region=body.region,
            history=history,
            language=body.language,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Index indisponible : {str(e)}.")
    except Exception as e:
        log.error(f"Erreur pipeline RAG : {e}")
        raise HTTPException(status_code=500, detail=str(e))

    increment_question_count(current_user["id"])

    sources_list = result.get("sources", [])
    create_message(conversation_id, "user", body.question)
    create_message(conversation_id, "assistant", result["answer"], json.dumps(sources_list, default=str))

    sources = [
        SourceDoc(
            doc_id=s.get("doc_id", ""),
            source=s.get("source", ""),
            title=s.get("title", ""),
            date=s.get("date", ""),
            ecli=s.get("ecli", ""),
            url=s.get("url", ""),
            similarity=s.get("similarity", 0.0),
        )
        for s in sources_list
    ]

    return AskResponse(
        answer=result["answer"],
        sources=sources,
        chunks_used=result["chunks_used"],
        model=result["model"],
        branch=result.get("branch"),
        branch_label=result.get("branch_label"),
        branch_confidence=result.get("branch_confidence", 0.0),
        conversation_id=conversation_id,
    )


@router.post("/ask/stream")
@limiter.limit("10/minute")
def ask_stream_endpoint(
    request: Request,
    body: AskRequest,
    api_key: Annotated[str, Depends(get_api_key)],
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Streaming SSE de la réponse RAG. Format : data: <chunk>\\n\\n | data: [DONE]{json}\\n\\n"""
    from rag.pipeline import ask_stream
    from rag.indexer_qdrant import get_index_stats as _qdrant_stats
    from api.stripe_billing import check_quota
    from api.database import (
        increment_question_count, create_conversation,
        list_messages, create_message, get_conversation_by_id,
    )

    _qstats = _qdrant_stats()
    if _qstats.get("status") != "ok":
        raise HTTPException(status_code=503, detail=f"Qdrant indisponible: {_qstats.get('error', 'unknown')}")

    check_quota(current_user["id"])

    conversation_id = body.conversation_id
    history = None

    if conversation_id:
        conv = get_conversation_by_id(conversation_id)
        if not conv or conv["user_id"] != current_user["id"]:
            raise HTTPException(404, "Conversation non trouvée.")
        prev_messages = list_messages(conversation_id)
        if prev_messages:
            history = [{"role": m["role"], "content": m["content"]} for m in prev_messages]
    else:
        title = body.question[:60] + ("..." if len(body.question) > 60 else "")
        conv = create_conversation(current_user["id"], title)
        conversation_id = conv["id"]

    enriched_question = body.question
    if body.photos_base64:
        try:
            from api.utils.ocr import extract_text_from_base64_list
            ocr_text = extract_text_from_base64_list(body.photos_base64)
            if ocr_text:
                enriched_question = f"{body.question}\n\n[Texte extrait des photos jointes]\n{ocr_text}"
        except Exception as e:
            log.warning(f"OCR photos /ask/stream ignoré : {e}")

    full_answer_parts: list[str] = []

    def event_generator():
        import json
        try:
            for chunk in ask_stream(
                question=enriched_question,
                top_k=body.top_k,
                source_filter=body.source_filter,
                model=body.model,
                anthropic_api_key=api_key,
                branch=body.branch,
                region=body.region,
                history=history,
                language=body.language,
            ):
                if chunk.startswith("data: [DONE]"):
                    metadata_json = chunk[len("data: [DONE]"):-2]
                    try:
                        metadata = json.loads(metadata_json)
                        sources_list = metadata.get("sources", [])
                        full_answer = "".join(full_answer_parts)
                        increment_question_count(current_user["id"])
                        create_message(conversation_id, "user", body.question)
                        create_message(conversation_id, "assistant", full_answer, json.dumps(sources_list, default=str))
                        metadata["conversation_id"] = conversation_id
                    except Exception:
                        metadata = {"conversation_id": conversation_id}
                    yield f"data: [DONE]{json.dumps(metadata, default=str)}\n\n"
                else:
                    text_part = chunk[6:].replace("\\n", "\n")
                    full_answer_parts.append(text_part)
                    yield chunk
        except Exception as e:
            log.error(f"Erreur streaming RAG : {e}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/branches")
def branches_list():
    """Liste les 15 branches du droit disponibles avec détection automatique."""
    from rag.branches import list_branches
    branches = list_branches()
    return {"branches": branches, "total": len(branches)}


@router.post("/search", response_model=SearchResponse)
@limiter.limit("20/minute")
def search_endpoint(request: Request, body: SearchRequest):
    """Recherche vectorielle seule (sans appel LLM)."""
    from rag.retriever import retrieve
    from rag.indexer_qdrant import get_index_stats as _qdrant_stats

    _qstats = _qdrant_stats()
    if _qstats.get("status") != "ok":
        raise HTTPException(status_code=503, detail=f"Qdrant indisponible: {_qstats.get('error', 'unknown')}.")

    try:
        chunks = retrieve(query=body.query, top_k=body.top_k, source_filter=body.source_filter)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Index indisponible : {str(e)}")

    results = [
        SearchResult(
            doc_id=c.get("doc_id", ""),
            source=c.get("source", ""),
            doc_type=c.get("doc_type", ""),
            jurisdiction=c.get("jurisdiction", ""),
            title=c.get("title", ""),
            date=c.get("date", ""),
            url=c.get("url", ""),
            ecli=c.get("ecli", ""),
            chunk_text=c.get("chunk_text", ""),
            similarity=c.get("similarity", 0.0),
            score=c.get("score", 0.0),
        )
        for c in chunks
    ]

    return SearchResponse(query=body.query, results=results, total=len(results))
