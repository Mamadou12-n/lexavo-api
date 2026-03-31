"""
Humanizer — Post-processing anti-patterns IA pour les reponses juridiques.
Supprime les tics d'ecriture IA (em dash, rule of three, sycophancy, etc.)
tout en preservant les references juridiques (ECLI, articles, dates).
"""

import re
from typing import List, Tuple


# ─── Patterns a corriger ──────────────────────────────────────────────────

# Mots et expressions typiques de l'IA a remplacer
AI_WORDS = {
    "Il est important de noter que ": "",
    "Il convient de souligner que ": "",
    "Il est crucial de ": "Il faut ",
    "Il est essentiel de ": "Il faut ",
    "Il est fondamental de ": "Il faut ",
    "En ce qui concerne ": "Pour ",
    "Dans le cadre de ": "Pour ",
    "En effet, ": "",
    "Par ailleurs, ": "",
    "De plus, ": "",
    "En outre, ": "",
    "Ainsi, ": "",
    "Par conséquent, ": "",
    "En conclusion, ": "",
    "En résumé, ": "",
    "Force est de constater que ": "",
    "Il y a lieu de ": "Il faut ",
    "Il apparaît que ": "",
    "Il ressort que ": "",
    "À cet égard, ": "",
    "En l'espèce, ": "",
    "Dès lors, ": "",
}

# Patterns de debut de phrase a supprimer
AI_STARTERS = [
    r"^Bien sûr[,!] ",
    r"^Certainement[,!] ",
    r"^Absolument[,!] ",
    r"^Excellente question[,!] ",
    r"^Bonne question[,!] ",
    r"^C'est une question (très )?pertinente[,!.] ",
    r"^Voici (un aperçu|une analyse|les éléments)[^.]*[.:] ",
    r"^Je serais ravi de ",
    r"^N'hésitez pas à ",
    r"^J'espère que (cela|cette réponse) ",
]

# Patterns de fin a supprimer
AI_CLOSERS = [
    r"\s*N.h[ée]sitez pas [àa] me poser d.autres questions[^.]*[.!]*\s*$",
    r"\s*J.esp[èe]re que (cela|cette r[ée]ponse) vous (aide|sera utile)[.!]*\s*$",
    r"\s*Si vous avez (d.autres|des) questions[^.]*[.!]*\s*$",
    r"\s*Je reste [àa] votre disposition[^.]*[.!]*\s*$",
    r"\s*Souhaitez-vous que j.approfondisse[^.]*[.!?]*\s*$",
    r"\s*Voulez-vous que je d[ée]veloppe[^.]*[.!?]*\s*$",
    r"\s*N.h[ée]sitez pas [àa] me poser d.autres questions[^!.]*[!.]*",
]


def humanize(text: str) -> str:
    """
    Applique le post-processing humanizer sur une reponse.
    Preserve les references juridiques (ECLI, articles, numeros d'arret).
    """
    if not text or not text.strip():
        return text

    # 1. Proteger les references juridiques avant modification
    protected, placeholders = _protect_legal_refs(text)

    # 2. Supprimer les starters IA
    for pattern in AI_STARTERS:
        protected = re.sub(pattern, "", protected, flags=re.IGNORECASE)

    # 3. Supprimer les closers IA
    for pattern in AI_CLOSERS:
        protected = re.sub(pattern, "", protected, flags=re.IGNORECASE)

    # 4. Remplacer les mots/expressions IA
    for ai_word, replacement in AI_WORDS.items():
        protected = protected.replace(ai_word, replacement)
        # Version sans accents aussi
        protected = protected.replace(ai_word.lower(), replacement.lower())

    # 5. Reduire les em dashes excessifs (garder max 1 par paragraphe)
    protected = _reduce_em_dashes(protected)

    # 6. Supprimer le gras excessif dans les listes (garder si c'est un titre de source)
    protected = _reduce_bold(protected)

    # 7. Restaurer les references juridiques
    result = _restore_legal_refs(protected, placeholders)

    # 8. Nettoyer les espaces multiples et lignes vides
    result = re.sub(r"  +", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = result.strip()

    return result


def _protect_legal_refs(text: str) -> Tuple[str, dict]:
    """
    Remplace temporairement les references juridiques par des placeholders
    pour eviter qu'elles soient modifiees par le humanizer.
    Ordre : bloc Sources d'abord (integralite), puis references individuelles dans le reste.
    """
    placeholders = {}
    counter = 0

    # 1. Bloc "Sources :" en fin de reponse — proteger integralement EN PREMIER
    sources_match = re.search(r"(\n\n?Sources?\s*:.*)", text, re.DOTALL | re.IGNORECASE)
    if sources_match:
        key = f"__LEGAL_REF_{counter}__"
        placeholders[key] = sources_match.group()
        text = text.replace(sources_match.group(), key, 1)
        counter += 1

    # 2. ECLI (dans le corps du texte, pas dans Sources qui est deja protege)
    for match in re.finditer(r"ECLI:[A-Z]{2}:[A-Z.]+:\d{4}:[A-Z0-9._-]+", text):
        key = f"__LEGAL_REF_{counter}__"
        placeholders[key] = match.group()
        text = text.replace(match.group(), key, 1)
        counter += 1

    # 3. References d'articles (art. 5:153 CSA, art. 1382 CC, etc.)
    for match in re.finditer(r"[Aa]rt(?:icle)?\.?\s*\d+(?:[:./]\d+)*(?:\s*(?:du|de la|des|CC|CSA|CDE|CIR|TFUE|TUE|CEDH|Constitution))?", text):
        key = f"__LEGAL_REF_{counter}__"
        placeholders[key] = match.group()
        text = text.replace(match.group(), key, 1)
        counter += 1

    # 4. Dates de lois (Loi du 3 juillet 1978, AR du 18 avril 2017, etc.)
    for match in re.finditer(r"(?:Loi|AR|Décret|Ordonnance|Directive|Règlement)\s+(?:du|n[°o.])\s+\d{1,2}\s+\w+\s+\d{4}", text):
        key = f"__LEGAL_REF_{counter}__"
        placeholders[key] = match.group()
        text = text.replace(match.group(), key, 1)
        counter += 1

    # 5. Numeros d'arret du CE (n. 123.456 ou n° 123.456)
    for match in re.finditer(r"n[°o.]\s*\d{3}[.]\d{3}", text):
        key = f"__LEGAL_REF_{counter}__"
        placeholders[key] = match.group()
        text = text.replace(match.group(), key, 1)
        counter += 1

    # 6. References numerotees [1], [2], etc. (citations dans le corps)
    for match in re.finditer(r"\[\d+\]", text):
        key = f"__LEGAL_REF_{counter}__"
        placeholders[key] = match.group()
        text = text.replace(match.group(), key, 1)
        counter += 1

    return text, placeholders


def _restore_legal_refs(text: str, placeholders: dict) -> str:
    """Restaure les references juridiques protegees."""
    for key, value in placeholders.items():
        text = text.replace(key, value)
    return text


def _reduce_em_dashes(text: str) -> str:
    """Reduit les em dashes excessifs — garde max 1 par paragraphe."""
    paragraphs = text.split("\n\n")
    result = []
    for para in paragraphs:
        dash_count = para.count(" — ") + para.count(" – ")
        if dash_count > 1:
            parts = re.split(r" [—–] ", para)
            if len(parts) > 2:
                rebuilt = parts[0] + " — " + ", ".join(parts[1:])
                result.append(rebuilt)
            else:
                result.append(para)
        else:
            result.append(para)
    return "\n\n".join(result)


def _reduce_bold(text: str) -> str:
    """Reduit le gras excessif — garde le gras uniquement pour les titres de sources."""
    # Compter les occurrences de **...**
    bold_count = len(re.findall(r"\*\*[^*]+\*\*", text))
    if bold_count > 3:
        # Trop de gras — supprimer sauf dans les lignes Sources/References
        lines = text.split("\n")
        result = []
        for line in lines:
            if re.match(r"^(Sources?|Références?|Note)\s*:", line, re.IGNORECASE):
                result.append(line)  # Garder tel quel
            else:
                result.append(re.sub(r"\*\*([^*]+)\*\*", r"\1", line))
        return "\n".join(result)
    return text
