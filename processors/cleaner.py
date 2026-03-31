"""
Processor / Cleaner — Normalisation des données juridiques
Phase 1 : Nettoyage et structuration avant indexation RAG.

Prend les JSON bruts des scrapers et produit des documents propres.
"""

import json
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    OUTPUT_DIR, JURIDAT_DIR, EURLEX_DIR, HUDOC_DIR, MONITEUR_DIR,
    CONSCONST_DIR, CONSEIL_ETAT_DIR, CCE_DIR, CNT_DIR, JUSTEL_DIR,
    APD_DIR, GALLILEX_DIR, FSMA_DIR, WALLEX_DIR, CCREK_DIR, CHAMBRE_DIR,
    CODEX_VL_DIR, BRUXELLES_DIR,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cleaner")

# ─── Format normalisé pour TOUS les documents ─────────────────────────────────

@dataclass
class LegalDocument:
    """
    Format unique pour tous les documents juridiques.
    Compatible avec LlamaIndex / Qdrant pour l'indexation RAG.
    """
    doc_id: str           # Identifiant unique
    source: str           # HUDOC | EUR-Lex | Juridat | Moniteur
    doc_type: str         # JUDGMENT | LEGISLATION | REGULATION | DECREE
    jurisdiction: str     # CJEU | ECHR | CASS_BE | CONST_BE | etc.
    country: str          # BE | EU
    language: str         # fr | nl | de | en
    title: str
    date: str             # YYYY-MM-DD
    url: str
    ecli: str             # European Case Law Identifier si disponible
    full_text: str        # Texte complet nettoyé
    summary: str          # Résumé (premier paragraphe significatif)
    keywords: List[str]   # Mots-clés extraits
    legal_domains: List[str]  # Branches du droit
    char_count: int       # Longueur du texte
    is_valid: bool        # Passe les contrôles de qualité


def clean_text(text: str) -> str:
    """
    Nettoie un texte juridique brut.
    - Supprime les artefacts HTML
    - Normalise les espaces et retours à la ligne
    - Supprime les caractères non-imprimables
    """
    if not text:
        return ""

    # Supprimer balises HTML résiduelles
    text = re.sub(r"<[^>]+>", " ", text)

    # Décoder entités HTML communes
    replacements = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&nbsp;": " ", "&quot;": '"', "&apos;": "'",
        "&#160;": " ", "&#8211;": "–", "&#8212;": "—",
    }
    for entity, char in replacements.items():
        text = text.replace(entity, char)

    # Normaliser les espaces multiples
    text = re.sub(r"[ \t]+", " ", text)

    # Normaliser les sauts de ligne multiples (max 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Supprimer caractères de contrôle (sauf newlines et tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    return text.strip()


def extract_ecli(text: str) -> str:
    """
    Extrait le numéro ECLI depuis un texte.
    Format ECLI : ECLI:PAYS:COUR:ANNÉE:NUMERO
    Exemples :
        ECLI:BE:CASS:2023:ARR.20230101.1
        ECLI:EU:C:2023:100
        ECLI:ECHR:2023:1234
    """
    pattern = r"ECLI:[A-Z]{2}:[A-Z]+:\d{4}:[A-Z0-9._-]+"
    match = re.search(pattern, text)
    return match.group(0) if match else ""


def extract_date(text: str, existing_date: str = "") -> str:
    """
    Extrait et normalise une date depuis un texte juridique.
    Retourne au format YYYY-MM-DD.
    """
    if existing_date and re.match(r"\d{4}-\d{2}-\d{2}", existing_date):
        return existing_date

    # Formats détectés : 01/01/2023, 1 janvier 2023, 2023-01-01
    patterns = [
        (r"(\d{1,2})[./](\d{1,2})[./](\d{4})", lambda m: f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"),
        (r"(\d{4})-(\d{2})-(\d{2})", lambda m: m.group(0)),
    ]

    mois_fr = {
        "janvier": "01", "février": "02", "mars": "03", "avril": "04",
        "mai": "05", "juin": "06", "juillet": "07", "août": "08",
        "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12",
    }

    # Format "1 janvier 2023"
    for mois_nom, mois_num in mois_fr.items():
        match = re.search(rf"(\d{{1,2}})\s+{mois_nom}\s+(\d{{4}})", text, re.IGNORECASE)
        if match:
            return f"{match.group(2)}-{mois_num}-{int(match.group(1)):02d}"

    for pattern, formatter in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return formatter(match)
            except Exception:
                continue

    return ""


def extract_legal_domains(text: str) -> List[str]:
    """
    Détecte automatiquement les branches du droit concernées.
    Basé sur des mots-clés réels du droit belge.
    """
    text_lower = text.lower()

    domains = {
        "droit_civil": [
            "responsabilité civile", "contrat", "obligation", "propriété",
            "succession", "mariage", "divorce", "filiation", "bail"
        ],
        "droit_penal": [
            "infraction", "crime", "délit", "peine", "prison", "amende",
            "prévenu", "inculpé", "victime", "parquet", "ministère public"
        ],
        "droit_social": [
            "travail", "licenciement", "salaire", "syndicat", "grève",
            "chômage", "sécurité sociale", "accident de travail"
        ],
        "droit_administratif": [
            "conseil d'état", "permis d'urbanisme", "marché public",
            "acte administratif", "recours annulation", "fonctionnaire"
        ],
        "droit_constitutionnel": [
            "cour constitutionnelle", "droits fondamentaux", "liberté",
            "égalité", "constitution", "compétence fédérale", "autonomie"
        ],
        "droit_commercial": [
            "société", "faillite", "créancier", "concordat", "insolvabilité",
            "commerce", "entreprise", "actionnaire", "associé"
        ],
        "droit_fiscal": [
            "impôt", "tva", "taxe", "contribution", "fiscal", "précompte",
            "revenus", "déclaration fiscale"
        ],
        "droit_famille": [
            "adoption", "garde", "pension alimentaire", "autorité parentale",
            "cohabitation légale", "patrimoine"
        ],
        "droit_UE": [
            "cour de justice", "cjue", "directive", "règlement ue",
            "traité", "droit communautaire", "union européenne"
        ],
        "droits_fondamentaux_CEDH": [
            "cedh", "cour européenne", "droits de l'homme", "article 6",
            "article 8", "procès équitable", "torture"
        ],
    }

    detected = []
    for domain, keywords in domains.items():
        if any(kw in text_lower for kw in keywords):
            detected.append(domain)

    return detected


def extract_keywords(text: str, max_keywords: int = 20) -> List[str]:
    """
    Extrait les mots-clés juridiques significatifs.
    Méthode simple basée sur fréquence + liste de termes juridiques.
    """
    # Termes juridiques belges importants
    legal_terms = [
        "cassation", "appel", "tribunal", "cour", "jugement", "arrêt",
        "ordonnance", "requête", "citation", "défendeur", "demandeur",
        "intimé", "appelant", "préjudice", "dommages", "faute",
        "contrat", "obligations", "responsabilité", "prescription",
        "nullité", "résiliation", "indemnisation", "réparation",
        "loi", "article", "code civil", "code pénal", "procédure",
        "compétence", "juridiction", "irrecevabilité", "non-fondé",
    ]

    text_lower = text.lower()
    found = []

    for term in legal_terms:
        if term in text_lower:
            count = text_lower.count(term)
            found.append((term, count))

    # Trier par fréquence
    found.sort(key=lambda x: x[1], reverse=True)
    return [term for term, _ in found[:max_keywords]]


def extract_summary(text: str, max_chars: int = 500) -> str:
    """
    Extrait un résumé du texte (premier paragraphe significatif).
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    for para in paragraphs:
        # Ignorer les en-têtes courts
        if len(para) >= 100:
            return para[:max_chars] + ("..." if len(para) > max_chars else "")

    return text[:max_chars]


def is_valid_document(doc: LegalDocument) -> bool:
    """
    Vérifie qu'un document est suffisamment complet pour l'indexation RAG.
    Accepte les documents sans texte complet si le titre est présent (ex: HUDOC, EUR-Lex).
    """
    # Doit avoir soit un texte soit un titre
    if not doc.full_text and not doc.title:
        return False
    # Minimum 50 chars de contenu utile
    if doc.char_count < 50:
        return False
    return True


# ─── Convertisseurs par source ────────────────────────────────────────────────

def normalize_hudoc(raw: dict) -> Optional[LegalDocument]:
    """Convertit un document HUDOC brut en LegalDocument."""
    meta = raw.get("metadata", {})
    item_id = raw.get("item_id", "")

    full_text = raw.get("full_text", "") or ""
    title = meta.get("docname", "") or raw.get("title", "")

    if not full_text and not title:
        return None

    # Si pas de texte complet, construire un texte synthétique depuis les métadonnées
    if not full_text and title:
        conclusion  = meta.get("conclusion", "")
        appno       = meta.get("appno", "") or meta.get("extractedappno", "")
        respondent  = meta.get("respondent", "")
        violation   = meta.get("violation", "")
        importance  = meta.get("importance", "")
        collection  = raw.get("collection", "")

        parts = [f"Affaire : {title}"]
        if appno:
            parts.append(f"Requête n° {appno}")
        if respondent:
            parts.append(f"État défendeur : {respondent}")
        if collection:
            parts.append(f"Type : {collection}")
        if conclusion:
            parts.append(f"Conclusion : {conclusion}")
        if violation:
            parts.append(f"Violation : {'oui' if violation.lower() == 'yes' else 'non'}")
        if importance:
            level = {"1": "Grande Chambre", "2": "Chambre", "3": "Comité"}.get(str(importance), importance)
            parts.append(f"Importance : {level}")

        full_text = "\n".join(parts)

    text = clean_text(full_text)
    date_raw = meta.get("judgementdate", "") or meta.get("kpdate", "") or meta.get("decisiondate", "")
    date = extract_date(date_raw[:10] if date_raw else "")

    return LegalDocument(
        doc_id=f"HUDOC_{item_id.replace('/', '_')}",
        source="HUDOC",
        doc_type="JUDGMENT_ECHR",
        jurisdiction="ECHR",
        country="BE",
        language="fr" if "FRE" in str(meta.get("languageisocode", "")) else "en",
        title=clean_text(title),
        date=date,
        url=raw.get("url", f"https://hudoc.echr.coe.int/eng#{{item_id}}"),
        ecli=meta.get("ecli", "") or extract_ecli(text),
        full_text=text,
        summary=extract_summary(text),
        keywords=extract_keywords(text),
        legal_domains=extract_legal_domains(text),
        char_count=len(text),
        is_valid=len(text) >= 50 and bool(title),
    )


def _decode_celex(celex: str) -> str:
    """
    Décode un numéro CELEX en description lisible.
    Ex: 62023CJ0123 → 'Arrêt de la Cour C-123/23 (EUR-Lex)'
        32023R0001  → 'Règlement (UE) 2023/1 (EUR-Lex)'
    """
    import re as _re

    # Format jurisprudence : 6YYYYXT0123 (X=type institution, T=type affaire)
    m = _re.match(r"^6(\d{4})(C[JO]|TJ|CF)(\d{4})", celex)
    if m:
        year = m.group(1)
        inst = m.group(2)
        num  = int(m.group(3))
        inst_map = {"CJ": "Cour (C)", "CO": "Cour (ordonnance)", "TJ": "Tribunal (T)", "CF": "Tribunal de la fonction publique"}
        return f"Arrêt {inst_map.get(inst, inst)}-{num}/{year} (EUR-Lex CELEX {celex})"

    # Format législation : XYYYYTNNNNN
    m2 = _re.match(r"^3(\d{4})(R|L|D|E)(\d+)", celex)
    if m2:
        year = m2.group(1)
        typ  = m2.group(2)
        num  = int(m2.group(3))
        typ_map = {"R": "Règlement", "L": "Directive", "D": "Décision", "E": "Recommandation"}
        return f"{typ_map.get(typ, typ)} (UE) {year}/{num} (EUR-Lex CELEX {celex})"

    return f"Document EUR-Lex CELEX {celex}"


def normalize_eurlex(raw: dict) -> Optional[LegalDocument]:
    """Convertit un document EUR-Lex brut en LegalDocument."""
    import re as _re
    celex = raw.get("celex", "")
    full_text = raw.get("full_text", "") or ""
    title = raw.get("title", "") or ""
    doc_type = raw.get("type", "JUDGMENT_CJEU")

    if not celex:
        return None

    # Si pas de titre, le décoder depuis le CELEX
    if not title:
        title = _decode_celex(celex)

    # Si pas de texte complet, construire un texte synthétique depuis les métadonnées
    if not full_text:
        date = raw.get("date", "")
        url  = raw.get("url", "")
        parts = [title]
        if celex:
            parts.append(f"Référence CELEX : {celex}")
        if date:
            parts.append(f"Date : {date}")
        parts.append(f"Type : {doc_type}")
        if url:
            parts.append(f"Source : {url}")
        full_text = "\n".join(parts)

    text = clean_text(full_text)
    date = extract_date(raw.get("date", ""))

    safe_celex = _re.sub(r"[^a-zA-Z0-9._-]", "_", celex)

    return LegalDocument(
        doc_id=f"EURLEX_{safe_celex}",
        source="EUR-Lex",
        doc_type=doc_type,
        jurisdiction="CJEU",
        country="EU",
        language="fr",
        title=clean_text(title),
        date=date,
        url=raw.get("url", ""),
        ecli=extract_ecli(text),
        full_text=text,
        summary=extract_summary(text),
        keywords=extract_keywords(text),
        legal_domains=extract_legal_domains(text),
        char_count=len(text),
        is_valid=bool(celex),
    )


def normalize_juridat(raw: dict) -> Optional[LegalDocument]:
    """Convertit une décision Juridat brute en LegalDocument."""
    full_text = raw.get("full_text", "") or ""
    title = raw.get("title", "")
    url = raw.get("url", "")

    text = clean_text(full_text or title)
    date = extract_date(raw.get("date", ""), full_text[:500])

    # Déduire la juridiction depuis le titre
    jurisdiction = "BE_UNKNOWN"
    jur_map = {
        "cassation": "CASS_BE",
        "conseil d'état": "CONSEIL_ETAT_BE",
        "constitutionnelle": "CONST_BE",
        "appel": "APPEL_BE",
        "travail": "TRIB_TRAVAIL_BE",
    }
    title_lower = title.lower()
    for key, val in jur_map.items():
        if key in title_lower:
            jurisdiction = val
            break

    return LegalDocument(
        doc_id=f"JURIDAT_{re.sub(r'[^a-zA-Z0-9]', '_', url)[-50:]}",
        source="Juridat",
        doc_type="JUDGMENT_BE",
        jurisdiction=jurisdiction,
        country="BE",
        language="fr",
        title=clean_text(title),
        date=date,
        url=url,
        ecli=raw.get("ecli", "") or extract_ecli(text),
        full_text=text,
        summary=extract_summary(text),
        keywords=extract_keywords(text),
        legal_domains=extract_legal_domains(text),
        char_count=len(text),
        is_valid=len(text) >= 200,
    )


def normalize_consconst(raw: dict) -> Optional[LegalDocument]:
    """Convertit un arrêt de la Cour constitutionnelle belge en LegalDocument."""
    full_text = raw.get("full_text", "") or ""
    title = raw.get("title", "")
    if not full_text and not title:
        return None

    text = clean_text(full_text or title)
    date = extract_date(raw.get("date", ""), text[:300])

    num  = raw.get("arret_num", "")
    year = raw.get("arret_year", "")
    lang = raw.get("language", "fr")
    doc_id = raw.get("doc_id", f"CONSCONST_{year}_{num}_{lang.upper()}")

    return LegalDocument(
        doc_id=doc_id,
        source="Cour constitutionnelle",
        doc_type="Arrêt",
        jurisdiction="CONST_BE",
        country="BE",
        language=lang,
        title=clean_text(title or f"Arrêt n° {num}/{year} — Cour constitutionnelle"),
        date=date,
        url=raw.get("url", ""),
        ecli="",
        full_text=text,
        summary=extract_summary(text),
        keywords=extract_keywords(text),
        legal_domains=extract_legal_domains(text),
        char_count=len(text),
        is_valid=len(text) >= 100,
    )


def normalize_conseil_etat(raw: dict) -> Optional[LegalDocument]:
    """Convertit un arrêt du Conseil d'État belge en LegalDocument."""
    full_text = raw.get("full_text", "") or ""
    title = raw.get("title", "")
    if not full_text and not title:
        return None

    text = clean_text(full_text or title)
    date = extract_date(raw.get("date", ""), text[:300])

    arret_num = raw.get("arret_num", "")
    doc_id = raw.get("doc_id", f"CE_{arret_num}")

    return LegalDocument(
        doc_id=doc_id,
        source="Conseil d'État",
        doc_type="Arrêt",
        jurisdiction="CONSEIL_ETAT_BE",
        country="BE",
        language=raw.get("language", "fr"),
        title=clean_text(title or f"Arrêt n° {arret_num} — Conseil d'État"),
        date=date,
        url=raw.get("url", ""),
        ecli="",
        full_text=text,
        summary=extract_summary(text),
        keywords=extract_keywords(text),
        legal_domains=extract_legal_domains(text),
        char_count=len(text),
        is_valid=len(text) >= 200,
    )


def normalize_cce(raw: dict) -> Optional[LegalDocument]:
    """Convertit un arrêt CCE (Conseil du Contentieux des Étrangers) en LegalDocument."""
    full_text = raw.get("full_text", "") or ""
    title = raw.get("title", "")
    if not full_text and not title:
        return None

    text = clean_text(full_text or title)
    date = extract_date(raw.get("date", ""), text[:300])

    n    = raw.get("arret_num", "")
    lang = raw.get("language", "fr")
    doc_id = raw.get("doc_id", f"CCE_{n}_{lang.upper()}")

    return LegalDocument(
        doc_id=doc_id,
        source="CCE",
        doc_type="Arrêt",
        jurisdiction="CCE_BE",
        country="BE",
        language=lang,
        title=clean_text(title or f"Arrêt CCE n° {n}"),
        date=date,
        url=raw.get("url", ""),
        ecli="",
        full_text=text,
        summary=extract_summary(text),
        keywords=extract_keywords(text),
        legal_domains=["droit des étrangers", "droit_administratif"] + extract_legal_domains(text),
        char_count=len(text),
        is_valid=len(text) >= 100,
    )


def normalize_cnt(raw: dict) -> Optional[LegalDocument]:
    """Convertit une CCT du Conseil National du Travail en LegalDocument."""
    full_text = raw.get("full_text", "") or ""
    title = raw.get("title", "")
    if not full_text and not title:
        return None

    text = clean_text(full_text or title)
    date = extract_date(raw.get("date", ""), text[:500])

    num  = raw.get("cct_num", "")
    lang = raw.get("language", "fr")
    doc_id = raw.get("doc_id", f"CCT_{num:03d}_{lang.upper()}" if isinstance(num, int) else f"CCT_{num}_{lang.upper()}")

    return LegalDocument(
        doc_id=doc_id,
        source="CNT",
        doc_type="Convention collective de travail",
        jurisdiction="CNT_BE",
        country="BE",
        language=lang,
        title=clean_text(title or f"CCT n° {num}"),
        date=date,
        url=raw.get("url", ""),
        ecli="",
        full_text=text,
        summary=extract_summary(text),
        keywords=extract_keywords(text),
        legal_domains=["droit_social", "droit du travail"] + extract_legal_domains(text),
        char_count=len(text),
        is_valid=len(text) >= 100,
    )


def normalize_justel(raw: dict) -> Optional[LegalDocument]:
    """Convertit un texte coordonné JUSTEL en LegalDocument."""
    full_text = raw.get("full_text", "") or ""
    title = raw.get("title", "")
    numac = raw.get("numac", "")

    if not full_text and not title:
        return None

    text = clean_text(full_text or title)
    date = extract_date(
        raw.get("date_promulgation", "") or raw.get("date_publication", "") or raw.get("date_pub", ""),
        text[:300]
    )

    return LegalDocument(
        doc_id=f"JUSTEL_{numac}",
        source="JUSTEL",
        doc_type="Texte coordonné",
        jurisdiction="PARLEMENT_BE",
        country="BE",
        language="fr",
        title=clean_text(title),
        date=date,
        url=raw.get("url", raw.get("eli", "")),
        ecli="",
        full_text=text,
        summary=extract_summary(text),
        keywords=extract_keywords(text),
        legal_domains=extract_legal_domains(text),
        char_count=len(text),
        is_valid=len(text) >= 200 or bool(title),
    )


def normalize_moniteur(raw: dict) -> Optional[LegalDocument]:
    """Convertit un texte Moniteur belge brut en LegalDocument."""
    full_text = raw.get("full_text", "") or ""
    title = raw.get("title", "")
    numac = raw.get("numac", "")

    text = clean_text(full_text or title)
    date = extract_date(raw.get("date_publication", "") or raw.get("date_pub_raw", ""), text[:300])

    return LegalDocument(
        doc_id=f"MONITEUR_{numac}",
        source="Moniteur belge",
        doc_type=raw.get("doc_type", "LEGISLATION"),
        jurisdiction="PARLEMENT_BE",
        country="BE",
        language="fr",
        title=clean_text(title),
        date=date,
        url=raw.get("url", ""),
        ecli="",
        full_text=text,
        summary=extract_summary(text),
        keywords=extract_keywords(text),
        legal_domains=extract_legal_domains(text),
        char_count=len(text),
        is_valid=len(text) >= 200 or bool(title),
    )


# ─── Pipeline de traitement ───────────────────────────────────────────────────

def normalize_generic(raw: dict, source_name: str, doc_type_default: str,
                      jurisdiction: str, matiere_default: str) -> Optional[LegalDocument]:
    """
    Normaliseur générique pour les sources avec structure commune
    (APD, GalliLex, FSMA, WalLex, CCReK, Chambre).
    """
    full_text = raw.get("full_text", "") or ""
    title     = raw.get("title", "") or ""
    if not full_text and not title:
        return None

    text     = clean_text(full_text or title)
    date_raw = raw.get("date", "") or raw.get("date_pub", "") or raw.get("date_promulgation", "")
    date     = extract_date(date_raw, text[:300])

    doc_id   = raw.get("doc_id", f"{source_name.upper()}_{re.sub(r'[^a-zA-Z0-9]', '_', title[:40])}")
    doc_type = raw.get("doc_type", doc_type_default)
    language = raw.get("language", "fr")

    domains = extract_legal_domains(text)
    matiere = raw.get("matiere", matiere_default)
    if matiere and matiere not in domains:
        domains = [matiere] + domains

    return LegalDocument(
        doc_id=doc_id,
        source=source_name,
        doc_type=doc_type,
        jurisdiction=jurisdiction,
        country="BE",
        language=language,
        title=clean_text(title),
        date=date,
        url=raw.get("url", raw.get("pdf_url", "")),
        ecli="",
        full_text=text,
        summary=extract_summary(text),
        keywords=extract_keywords(text),
        legal_domains=domains,
        char_count=len(text),
        is_valid=len(text) >= 100 or bool(title),
    )


def normalize_apd(raw: dict) -> Optional[LegalDocument]:
    return normalize_generic(raw, "APD", "Décision RGPD", "APD_BE", "protection des données / RGPD")

def normalize_gallilex(raw: dict) -> Optional[LegalDocument]:
    return normalize_generic(raw, "GalliLex", "Texte normatif FWB", "FWB", "législation FWB")

def normalize_fsma(raw: dict) -> Optional[LegalDocument]:
    return normalize_generic(raw, "FSMA", "Décision FSMA", "FSMA_BE", "droit financier")

def normalize_wallex(raw: dict) -> Optional[LegalDocument]:
    return normalize_generic(raw, "WalLex", "Texte wallon", "PARLEMENT_WALLON", "législation wallonne")

def normalize_ccrek(raw: dict) -> Optional[LegalDocument]:
    return normalize_generic(raw, "Cour des comptes", "Publication", "CCREK_BE", "finances publiques")

def normalize_chambre(raw: dict) -> Optional[LegalDocument]:
    return normalize_generic(raw, "Chambre", "Document parlementaire", "CHAMBRE_BE", "législation fédérale")

def normalize_codex_vlaanderen(raw: dict) -> Optional[LegalDocument]:
    return normalize_generic(raw, "Codex Vlaanderen", raw.get("doc_type", "Vlaamse wetgeving"), "VLAAMS_PARLEMENT", raw.get("matiere", "Vlaamse wetgeving"))

def normalize_bruxelles(raw: dict) -> Optional[LegalDocument]:
    return normalize_generic(raw, "Bruxelles", raw.get("doc_type", "Ordonnance (Bruxelles)"), "PARLEMENT_BXL", raw.get("matiere", "législation bruxelloise"))


NORMALIZERS = {
    "hudoc":        (HUDOC_DIR,        normalize_hudoc),
    "eurlex":       (EURLEX_DIR,       normalize_eurlex),
    "juridat":      (JURIDAT_DIR,      normalize_juridat),
    "moniteur":     (MONITEUR_DIR,     normalize_moniteur),
    "consconst":    (CONSCONST_DIR,    normalize_consconst),
    "conseil_etat": (CONSEIL_ETAT_DIR, normalize_conseil_etat),
    "cce":          (CCE_DIR,          normalize_cce),
    "cnt":          (CNT_DIR,          normalize_cnt),
    "justel":       (JUSTEL_DIR,       normalize_justel),
    # Sources diverses
    "apd":          (APD_DIR,          normalize_apd),
    "gallilex":     (GALLILEX_DIR,     normalize_gallilex),
    "fsma":         (FSMA_DIR,         normalize_fsma),
    "wallex":       (WALLEX_DIR,       normalize_wallex),
    "ccrek":        (CCREK_DIR,        normalize_ccrek),
    "chambre":      (CHAMBRE_DIR,      normalize_chambre),
    # Couverture complète Belgique
    "codex_vlaanderen": (CODEX_VL_DIR,   normalize_codex_vlaanderen),
    "bruxelles":        (BRUXELLES_DIR,  normalize_bruxelles),
}


def process_all_sources(output_dir: Optional[Path] = None) -> Dict[str, int]:
    """
    Traite tous les documents bruts et produit les JSON normalisés.

    Returns:
        dict avec compte par source
    """
    out = output_dir or (OUTPUT_DIR / "normalized")
    out.mkdir(parents=True, exist_ok=True)

    stats = {}

    for source_name, (source_dir, normalizer) in NORMALIZERS.items():
        files = list(source_dir.glob("*.json"))
        log.info(f"Traitement {source_name}: {len(files)} fichiers bruts")

        valid = 0
        invalid = 0

        for json_file in files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)

                doc = normalizer(raw)
                if doc is None:
                    invalid += 1
                    continue

                doc.is_valid = is_valid_document(doc)
                if not doc.is_valid:
                    invalid += 1
                    continue

                # Sauvegarder le doc normalisé
                out_file = out / f"{doc.doc_id}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(asdict(doc), f, ensure_ascii=False, indent=2)

                valid += 1

            except Exception as e:
                log.warning(f"Erreur traitement {json_file.name}: {e}")
                invalid += 1

        stats[source_name] = {"valid": valid, "invalid": invalid, "total": len(files)}
        log.info(f"  {source_name}: {valid} valides, {invalid} invalides")

    return stats


if __name__ == "__main__":
    stats = process_all_sources()
    print("\n=== Résultats normalisation ===")
    for source, s in stats.items():
        print(f"  {source:12s} : {s['valid']:5d} valides / {s['total']:5d} total")
