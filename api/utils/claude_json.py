"""Helper mutualisé pour extraire du JSON depuis les réponses Claude.

Gère les cas :
- JSON nu : {"key": "value"}
- Array nu : [{"key": "value"}]
- Wrapped dans code fence : ```json {...} ```
- Texte parasite avant/après le JSON
"""

from __future__ import annotations

import json
import re
import logging

log = logging.getLogger(__name__)

# Regex : cherche le premier bloc JSON objet ou array, en tenant compte des imbrications
_RE_OBJECT = re.compile(r'\{[\s\S]*\}')
_RE_ARRAY  = re.compile(r'\[[\s\S]*\]')
_RE_FENCE  = re.compile(r'```(?:json)?\s*([\s\S]*?)\s*```')


def extract_json(text: str, *, array: bool = False) -> dict | list | None:
    """Extrait le premier objet (ou array) JSON depuis une réponse Claude.

    Args:
        text:  Texte brut retourné par Claude.
        array: True pour extraire un array JSON plutôt qu'un objet.

    Returns:
        dict ou list parsé, ou None si aucun JSON valide trouvé.
    """
    if not text:
        return None

    # 1. Essayer d'abord un code fence ```json ... ```
    fence_match = _RE_FENCE.search(text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Chercher le pattern brut (objet ou array selon le mode)
    pattern = _RE_ARRAY if array else _RE_OBJECT
    raw_match = pattern.search(text)
    if raw_match:
        try:
            return json.loads(raw_match.group())
        except json.JSONDecodeError:
            pass

    return None


def extract_json_object(text: str) -> dict | None:
    """Extrait un objet JSON depuis une réponse Claude. Retourne None si absent."""
    result = extract_json(text, array=False)
    if result is None or not isinstance(result, dict):
        return None
    return result


def extract_json_array(text: str) -> list | None:
    """Extrait un array JSON depuis une réponse Claude. Retourne None si absent."""
    result = extract_json(text, array=True)
    if result is None or not isinstance(result, list):
        return None
    return result
