"""Routage intelligent des modèles Claude — optimisation coûts.

Règle : Haiku pour le simple, Sonnet pour l'analyse, Opus pour le complexe.
Le client ne choisit jamais — tout est automatique."""


def select_model(task_type: str, text_length: int = 0) -> str:
    HAIKU = "claude-haiku-4-5-20251001"
    SONNET = "claude-sonnet-4-6"
    OPUS = "claude-opus-4-6"

    routing = {
        # ─── Haiku (rapide, économique) ───────────────────
        "calculator":    HAIKU,   # Calculateurs (préavis, succession, pension)
        "simple_qa":     HAIKU,   # Questions simples / FAQ
        "translation":   HAIKU,   # Decode (traduction documents)
        "score":         HAIKU,   # Score juridique (évaluation simple)
        "quiz":          HAIKU,   # Quiz étudiants
        "flashcards":    HAIKU,   # Flashcards étudiants
        "alerts":        HAIKU,   # Alertes législatives

        # ─── Sonnet (qualité, équilibré) ──────────────────
        "analysis":      SONNET,  # Analyse générale
        "diagnostic":    SONNET,  # Diagnostic multi-branches
        "contract":      SONNET,  # Shield (analyse contrat)
        "defend":        SONNET,  # Defend (contestation + document)
        "fiscal":        SONNET,  # Copilote fiscal
        "response":      SONNET,  # Réponse à courrier juridique
        "heritage":      SONNET,  # Guide successoral
        "compliance":    SONNET,  # Audit conformité
        "litigation":    SONNET,  # Recouvrement impayés
        "match":         SONNET,  # Matching avocat
        "summary":       SONNET,  # Résumé étudiant

        # ─── Opus (très complexe, rare) ───────────────────
        "complex":       OPUS,    # Cas très complexes
        "audit":         OPUS,    # Audit entreprise 30 questions
        "emergency":     OPUS,    # Urgence juridique (précision max)
    }

    model = routing.get(task_type, SONNET)

    # Contrats longs → upgrade vers Opus
    if task_type == "contract" and text_length > 15000:
        model = OPUS

    # Defend avec description très longue → upgrade vers Opus
    if task_type == "defend" and text_length > 5000:
        model = OPUS

    return model
