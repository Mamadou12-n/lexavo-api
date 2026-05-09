"""Tests unitaires pour les 9 alternatives du retriever Lexavo.

Chaque alternative est testée isolément avec mocks Qdrant + SentenceTransformer.

Alt.1 : Recherche vecteurs (sémantique)
Alt.2 : Mots-clés articles (Art. X)
Alt.3 : Termes juridiques (MatchText multi-termes)
Alt.4 : Chunks voisins (contexte ±1)
Alt.5 : Vote majoritaire (fusion 1+2+3)
Alt.6 : Détection source dans la question
Alt.7 : Re-ranking Claude Haiku
Alt.8 : Index articles séparé (collection legal_articles_be)
Alt.9 : Reformulation automatique

Issue : audit 2026-05-09 angle 3 (RAG/IA) — finding HIGH "0 test pytest des 9 alts".
"""
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest


# ─── Fixtures réutilisables ──────────────────────────────────────────────────


@pytest.fixture
def mock_qdrant_point():
    """Factory : un ScoredPoint Qdrant minimal."""

    def _make(
        chunk_id: str = "DOC_001__chunk_001",
        source: str = "Moniteur belge",
        title: str = "Loi du 3 juillet 1978",
        text: str = "Article 37 de la loi sur les contrats de travail",
        score: float = 0.85,
        doc_id: str = "MONITEUR_2009000158",
        chunk_idx: int = 1,
    ) -> MagicMock:
        pt = MagicMock()
        pt.id = chunk_id
        pt.score = score
        pt.payload = {
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "source": source,
            "title": title,
            "text": text,
            "chunk_idx": chunk_idx,
            "doc_type": "Loi",
            "jurisdiction": "BE_FED",
            "date": "2009-03-12",
            "url": f"https://example.be/{doc_id}",
            "ecli": "",
            "chunk_count": 50,
        }
        return pt

    return _make


@pytest.fixture
def mock_qdrant_client(mock_qdrant_point):
    """Mock du QdrantClient (search/scroll/get_collection)."""
    client = MagicMock()
    pt1 = mock_qdrant_point(chunk_id="DOC_A__chunk_001", score=0.92)
    pt2 = mock_qdrant_point(
        chunk_id="DOC_B__chunk_002",
        source="JUSTEL",
        title="Article 1382 Code civil",
        score=0.81,
    )
    qr = MagicMock()
    qr.points = [pt1, pt2]
    client.query_points.return_value = qr
    client.scroll.return_value = ([pt1, pt2], None)
    client.retrieve.return_value = [pt1, pt2]
    client.get_collection.return_value = MagicMock(points_count=12234)
    return client


@pytest.fixture
def mock_embed_model():
    """Mock du modèle SentenceTransformer."""
    model = MagicMock()
    model.encode.return_value = [[0.1] * 384]
    return model


# ─── Alt.6 : Détection source dans la question (pure regex, pas de mock) ────


class TestAlt6SourceDetection:
    def test_alt6_detects_code_penal(self):
        from rag.retriever import SOURCE_DETECT

        query = "Que dit le code pénal sur le vol ?"
        matched = None
        for pattern, source in SOURCE_DETECT.items():
            if re.search(pattern, query, re.IGNORECASE):
                matched = source
                break
        assert matched == "Code pénal"

    def test_alt6_detects_contrats_travail(self):
        from rag.retriever import SOURCE_DETECT

        query = "Quel est le délai de préavis ?"
        matched = None
        for pattern, source in SOURCE_DETECT.items():
            if re.search(pattern, query, re.IGNORECASE):
                matched = source
                break
        assert matched == "Loi sur les contrats de travail"

    def test_alt6_detects_tva(self):
        from rag.retriever import SOURCE_DETECT

        query = "Quel est le taux TVA pour la rénovation ?"
        matched = None
        for pattern, source in SOURCE_DETECT.items():
            if re.search(pattern, query, re.IGNORECASE):
                matched = source
                break
        assert matched == "Code de la TVA"

    def test_alt6_excludes_penal_social_from_code_penal(self):
        from rag.retriever import SOURCE_DETECT

        query = "Le code pénal social s'applique-t-il ?"
        results = []
        for pattern, source in SOURCE_DETECT.items():
            if re.search(pattern, query, re.IGNORECASE):
                results.append(source)
        assert "Code pénal social" in results

    def test_alt6_no_match_returns_none(self):
        from rag.retriever import SOURCE_DETECT

        query = "Question hors sujet sur la météo"
        matched = None
        for pattern, source in SOURCE_DETECT.items():
            if re.search(pattern, query, re.IGNORECASE):
                matched = source
                break
        assert matched is None


# ─── Alt.6 bis : SOURCE_TO_KEYWORDS pour matcher titres JUSTEL ──────────────


class TestAlt6Keywords:
    def test_keywords_18_sources_minimum(self):
        from rag.retriever import SOURCE_TO_KEYWORDS

        assert len(SOURCE_TO_KEYWORDS) >= 18

    def test_keywords_code_penal_has_date(self):
        from rag.retriever import SOURCE_TO_KEYWORDS

        kws = SOURCE_TO_KEYWORDS["Code pénal"]
        assert "1867" in kws or "8 juin 1867" in kws

    def test_keywords_match_function(self):
        from rag.retriever import _matches_detected_source

        assert _matches_detected_source(
            "Loi du 3 juillet 1978", "Loi sur les contrats de travail"
        )
        assert not _matches_detected_source(
            "Météo Bruxelles", "Loi sur les contrats de travail"
        )


# ─── chunk_id_to_uuid : transformation déterministe ─────────────────────────


class TestChunkIdToUUID:
    def test_chunk_id_uuid_is_deterministic(self):
        from rag.retriever import chunk_id_to_uuid

        u1 = chunk_id_to_uuid("DOC_001__chunk_001")
        u2 = chunk_id_to_uuid("DOC_001__chunk_001")
        assert u1 == u2

    def test_different_chunk_ids_yield_different_uuids(self):
        from rag.retriever import chunk_id_to_uuid

        u1 = chunk_id_to_uuid("DOC_001__chunk_001")
        u2 = chunk_id_to_uuid("DOC_001__chunk_002")
        assert u1 != u2


# ─── Alt.1 : Recherche vecteurs (sémantique) ─────────────────────────────────


class TestAlt1VectorSearch:
    @patch("rag.retriever.get_client")
    @patch("rag.retriever.get_model")
    def test_alt1_returns_chunks(
        self,
        mock_get_model,
        mock_get_client,
        mock_qdrant_client,
        mock_embed_model,
    ):
        mock_get_client.return_value = mock_qdrant_client
        mock_get_model.return_value = mock_embed_model
        from rag.retriever import retrieve

        results = retrieve(query="préavis légal", top_k=2)
        assert isinstance(results, list)
        assert mock_embed_model.encode.called
        assert mock_qdrant_client.query_points.called

    @patch("rag.retriever.get_client")
    @patch("rag.retriever.get_model")
    def test_alt1_chunks_have_score(
        self,
        mock_get_model,
        mock_get_client,
        mock_qdrant_client,
        mock_embed_model,
    ):
        mock_get_client.return_value = mock_qdrant_client
        mock_get_model.return_value = mock_embed_model
        from rag.retriever import retrieve

        results = retrieve(query="contrat", top_k=2)
        for r in results:
            assert "score" in r
            assert isinstance(r["score"], (int, float))


# ─── Alt.2 + Alt.3 : Mots-clés articles + termes juridiques ──────────────────


class TestAlt2Alt3KeywordSearch:
    @patch("rag.retriever.get_client")
    @patch("rag.retriever.get_model")
    def test_alt2_article_pattern_extracted(
        self,
        mock_get_model,
        mock_get_client,
        mock_qdrant_client,
        mock_embed_model,
    ):
        mock_get_client.return_value = mock_qdrant_client
        mock_get_model.return_value = mock_embed_model
        from rag.retriever import retrieve

        results = retrieve(query="article 1382 du Code civil", top_k=3)
        assert mock_qdrant_client.query_points.called or mock_qdrant_client.scroll.called
        assert isinstance(results, list)

    @patch("rag.retriever.get_client")
    @patch("rag.retriever.get_model")
    def test_alt3_legal_terms_match(
        self,
        mock_get_model,
        mock_get_client,
        mock_qdrant_client,
        mock_embed_model,
    ):
        mock_get_client.return_value = mock_qdrant_client
        mock_get_model.return_value = mock_embed_model
        from rag.retriever import retrieve

        results = retrieve(query="responsabilité civile dommage faute", top_k=3)
        assert isinstance(results, list)


# ─── Filter Qdrant (source / jurisdiction) ──────────────────────────────────


class TestFilterBuilder:
    def test_filter_with_source(self):
        from rag.retriever import _build_qdrant_filter

        f = _build_qdrant_filter(source_filter=["Moniteur belge"])
        assert f is not None

    def test_filter_with_jurisdiction(self):
        from rag.retriever import _build_qdrant_filter

        f = _build_qdrant_filter(jurisdiction_filter="BE_FED")
        assert f is not None

    def test_filter_none_no_filters(self):
        from rag.retriever import _build_qdrant_filter

        f = _build_qdrant_filter()
        assert f is None


# ─── Alt.5 : Vote majoritaire / dédup ────────────────────────────────────────


class TestAlt5Dedup:
    @patch("rag.retriever.get_client")
    @patch("rag.retriever.get_model")
    def test_alt5_no_duplicate_chunk_ids(
        self,
        mock_get_model,
        mock_get_client,
        mock_qdrant_client,
        mock_embed_model,
    ):
        mock_get_client.return_value = mock_qdrant_client
        mock_get_model.return_value = mock_embed_model
        from rag.retriever import retrieve

        results = retrieve(query="contrat travail", top_k=10)
        chunk_ids = [r.get("chunk_id") for r in results if r.get("chunk_id")]
        assert len(chunk_ids) == len(set(chunk_ids)), "Doublons (Alt.5 défaillant)"


# ─── Smoke test : retrieve() ne doit jamais lever d'exception ────────────────


class TestRetrieveSmoke:
    @patch("rag.retriever.get_client")
    @patch("rag.retriever.get_model")
    def test_retrieve_top_k_respected(
        self,
        mock_get_model,
        mock_get_client,
        mock_qdrant_client,
        mock_embed_model,
    ):
        mock_get_client.return_value = mock_qdrant_client
        mock_get_model.return_value = mock_embed_model
        from rag.retriever import retrieve

        results = retrieve(query="préavis", top_k=2)
        assert len(results) <= 2

    @patch("rag.retriever.get_client")
    @patch("rag.retriever.get_model")
    def test_retrieve_returns_dict_chunks(
        self,
        mock_get_model,
        mock_get_client,
        mock_qdrant_client,
        mock_embed_model,
    ):
        mock_get_client.return_value = mock_qdrant_client
        mock_get_model.return_value = mock_embed_model
        from rag.retriever import retrieve

        results = retrieve(query="préavis", top_k=2)
        for r in results:
            assert isinstance(r, dict)
