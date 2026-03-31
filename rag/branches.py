"""
Detection de branche juridique + configuration par branche.
Detecte la branche du droit a partir de la question de l'utilisateur,
puis fournit le prompt systeme, les sources prioritaires et les keywords.
"""

import re
from typing import Dict, List, Optional, Tuple


# ─── Configuration par branche ─────────────────────────────────────────────

BRANCHES = {
    "droit_travail": {
        "label": "Droit du travail",
        "keywords": [
            "licenciement", "contrat de travail", "preavis", "motif grave",
            "convention collective", "salaire", "cct", "bien-etre au travail",
            "temps de travail", "vacances annuelles", "protection contre le licenciement",
            "discrimination", "harcelement", "delegation syndicale", "conseil d'entreprise",
            "reglement de travail", "clause de non-concurrence", "periode d'essai",
            "travail a temps partiel", "interim", "detachement", "onem", "chomage technique",
            "preavis", "indemnite de rupture", "faute grave",
        ],
        "source_filter": ["Moniteur belge", "Juridat", "CNT", "CCE", "Conseil d'État"],
        "top_k": 8,
        "system_prompt_extra": (
            "Tu es specialise en droit du travail belge. "
            "Legislation de reference : Loi du 3 juillet 1978 (contrats de travail), "
            "Loi du 5 decembre 1968 (CCT), Loi du 4 aout 1996 (bien-etre), "
            "Loi du 26 decembre 2013 (statut unique). "
            "Distingue ouvriers et employes (ancien regime) vs statut unique (nouveau regime). "
            "Cite les CCT du CNT quand pertinent."
        ),
    },
    "droit_familial": {
        "label": "Droit familial",
        "keywords": [
            "divorce", "pension alimentaire", "autorite parentale", "hebergement",
            "filiation", "adoption", "regime matrimonial", "cohabitation legale",
            "obligation alimentaire", "mediation familiale", "protection de la jeunesse",
            "tutelle", "administration provisoire", "consentement mutuel",
            "desunion irremédiable", "liquidation-partage", "garde des enfants",
            "mariage", "separation de fait",
        ],
        "source_filter": ["Juridat", "Moniteur belge", "Cour constitutionnelle", "HUDOC"],
        "top_k": 6,
        "system_prompt_extra": (
            "Tu es specialise en droit familial belge. "
            "Legislation : Code civil Livre 1 (personnes), Livre 2.3 (relations familiales), "
            "Loi du 27 avril 2007 (divorce), art. 1475-1479 CC (cohabitation legale). "
            "Ne jamais inventer de montants de pension alimentaire. "
            "Toujours recommander la consultation d'un avocat pour les situations familiales."
        ),
    },
    "droit_fiscal": {
        "label": "Droit fiscal",
        "keywords": [
            "impot", "tva", "ipp", "isoc", "precompte", "droits de succession",
            "droits d'enregistrement", "declaration fiscale", "taxe",
            "revenus", "deduction", "reduction d'impot", "regime fiscal",
            "ruling", "abus fiscal", "prix de transfert", "contribution",
            "precompte mobilier", "precompte immobilier", "precompte professionnel",
            "spf finances", "exercice d'imposition",
        ],
        "source_filter": ["SPF Finances", "Moniteur belge", "Juridat", "Conseil d'État", "Cour constitutionnelle"],
        "top_k": 8,
        "system_prompt_extra": (
            "Tu es specialise en droit fiscal belge. "
            "Legislation : CIR 92 (impots sur les revenus), Code TVA, "
            "Code des droits d'enregistrement, Code des droits de succession. "
            "Distingue federal (IPP, ISOC, TVA) vs regional (droits enregistrement, succession). "
            "Les montants indexes changent chaque annee — toujours preciser l'exercice d'imposition."
        ),
    },
    "droit_penal": {
        "label": "Droit penal",
        "keywords": [
            "infraction", "delit", "crime", "peine", "detention", "casier judiciaire",
            "plainte", "parquet", "instruction", "tribunal correctionnel", "cour d'assises",
            "detention preventive", "mandat d'arret", "probation",
            "surveillance electronique", "recidive", "prescription penale",
            "constitution de partie civile", "presomption d'innocence",
            "internement", "mediation penale", "code penal",
        ],
        "source_filter": ["Juridat", "Moniteur belge", "Cour constitutionnelle", "HUDOC", "Conseil d'État"],
        "top_k": 6,
        "system_prompt_extra": (
            "Tu es specialise en droit penal belge. "
            "Legislation : Code penal (1867), nouveau Code penal Livre 1 (2024), "
            "Code d'instruction criminelle, Loi du 20 juillet 1990 (detention preventive), "
            "Loi Franchimont du 12 mars 1998 (droits de la defense). "
            "Attention : le nouveau Code penal Livre 1 entre en vigueur progressivement. "
            "Ne jamais affirmer qu'un fait est une infraction sans citer le texte legal."
        ),
    },
    "droit_civil": {
        "label": "Droit civil",
        "keywords": [
            "contrat", "obligation", "responsabilite civile", "dommage",
            "vice de consentement", "nullite", "resolution", "resiliation",
            "force majeure", "imprevision", "garantie", "surete",
            "succession", "donation", "testament", "reserve hereditaire",
            "prescription", "propriete", "servitude",
            "enrichissement sans cause", "code civil",
        ],
        "source_filter": ["Juridat", "Moniteur belge", "Cour constitutionnelle"],
        "top_k": 6,
        "system_prompt_extra": (
            "Tu es specialise en droit civil belge. "
            "Legislation : nouveau Code civil — Livre 3 (biens, 2020), Livre 4 (successions, 2017), "
            "Livre 5 (obligations, 2022), Livre 8 (preuve, 2019). "
            "Distingue ancien Code civil vs nouveau Code civil. "
            "Le Livre 6 (responsabilite extracontractuelle) n'est pas encore adopte."
        ),
    },
    "droit_administratif": {
        "label": "Droit administratif",
        "keywords": [
            "conseil d'etat", "conseil d etat", "recours en annulation", "suspension", "extreme urgence",
            "acte administratif", "motivation formelle", "fonction publique",
            "urbanisme", "permis d'urbanisme", "permis d urbanisme", "tutelle administrative",
            "autorite administrative", "principe de legalite", "audi alteram partem",
            "retrait d'acte", "responsabilite de l'etat", "responsabilite de l etat", "fonctionnaire",
            "recours", "annulation",
        ],
        "source_filter": ["Conseil d'État", "Moniteur belge", "Bruxelles", "Codex Vlaanderen", "GalliLex", "WalLex"],
        "top_k": 8,
        "system_prompt_extra": (
            "Tu es specialise en droit administratif belge. "
            "Legislation : Lois coordonnees sur le Conseil d'Etat (AR 12 janvier 1973), "
            "Loi du 29 juillet 1991 (motivation formelle), Loi du 11 avril 1994 (publicite). "
            "Distingue les trois Regions pour l'urbanisme et la tutelle. "
            "Les arrets du CE ont le format : arret n. XXX.XXX du JJ/MM/AAAA."
        ),
    },
    "droit_commercial": {
        "label": "Droit commercial",
        "keywords": [
            "societe", "csa", "srl", "sa", "faillite", "insolvabilite",
            "reorganisation judiciaire", "pratiques du marche", "concurrence",
            "abus de position dominante", "clause abusive", "droit bancaire",
            "marches financiers", "responsabilite des administrateurs",
            "code de droit economique", "cde", "entreprise",
        ],
        "source_filter": ["Moniteur belge", "Juridat", "FSMA", "EUR-Lex", "Cour constitutionnelle"],
        "top_k": 6,
        "system_prompt_extra": (
            "Tu es specialise en droit commercial et des societes belge. "
            "Legislation : CSA (Loi du 23 mars 2019), CDE (Code de droit economique), "
            "Livre XX CDE (insolvabilite). "
            "Le CSA a remplace le Code des societes depuis le 1er mai 2019. "
            "Attention a la numerotation specifique du CSA (art. 5:153 CSA)."
        ),
    },
    "droit_immobilier": {
        "label": "Droit immobilier",
        "keywords": [
            "bail", "location", "copropriete", "syndic", "vente immobiliere",
            "compromis de vente", "acte authentique", "permis de construire",
            "certificat peb", "cadastre", "precompte immobilier", "hypotheque",
            "emphyteose", "superficie", "usufruit", "expropriation",
            "loyer", "locataire", "proprietaire", "bail commercial",
            "assemblee generale des coproprietaires", "charges communes",
            "bail d habitation", "etat des lieux", "garantie locative",
        ],
        "source_filter": ["Moniteur belge", "Bruxelles", "Codex Vlaanderen", "WalLex", "GalliLex", "Juridat"],
        "top_k": 8,
        "system_prompt_extra": (
            "Tu es specialise en droit immobilier belge. "
            "Le bail d'habitation est entierement regionalise depuis 2014. "
            "Wallonie : Decret du 15 mars 2018. Bruxelles : Ordonnance du 27 juillet 2017. "
            "Flandre : Decret du 9 novembre 2018. "
            "Toujours demander ou preciser la Region concernee."
        ),
    },
    "droit_environnement": {
        "label": "Droit de l'environnement",
        "keywords": [
            "permis d'environnement", "pollution", "dechets", "recyclage",
            "eau", "eaux usees", "sol contamine", "natura 2000", "biodiversite",
            "climat", "gaz a effet de serre", "certificat vert",
            "nuisances sonores", "qualite de l'air", "evaluation des incidences",
            "permis unique", "vlarem",
        ],
        "source_filter": ["Codex Vlaanderen", "WalLex", "Bruxelles", "Moniteur belge", "EUR-Lex", "Conseil d'État"],
        "top_k": 8,
        "system_prompt_extra": (
            "Tu es specialise en droit de l'environnement belge. "
            "Matiere presque entierement regionalisee. "
            "Flandre : VLAREM I et II. Wallonie : Code de l'environnement. "
            "Bruxelles : Ordonnance du 5 juin 1997 (permis d'environnement). "
            "Toujours identifier la Region avant de repondre."
        ),
    },
    "droit_propriete_intellectuelle": {
        "label": "Propriete intellectuelle",
        "keywords": [
            "marque", "brevet", "droit d'auteur", "contrefacon", "boip",
            "dessin et modele", "secret d'affaires", "licence", "copyright",
            "propriete intellectuelle", "droits voisins", "nom de domaine",
        ],
        "source_filter": ["Moniteur belge", "EUR-Lex", "Juridat", "Cour constitutionnelle"],
        "top_k": 6,
        "system_prompt_extra": (
            "Tu es specialise en propriete intellectuelle belge et Benelux. "
            "Legislation : CDE Livre XI (PI), Convention Benelux PI (2005), "
            "Loi du 28 mars 1984 (brevets). "
            "Distingue marque Benelux (BOIP) vs marque UE (EUIPO). "
            "Le brevet unitaire europeen est en vigueur depuis juin 2023."
        ),
    },
    "droit_securite_sociale": {
        "label": "Securite sociale",
        "keywords": [
            "securite sociale", "chomage", "allocations de chomage", "onem",
            "inami", "incapacite de travail", "pension", "pension de retraite",
            "allocations familiales", "accident du travail", "maladie professionnelle",
            "cotisations sociales", "onss", "independant", "cpas",
            "revenu d'integration", "mutuelle", "fedris",
        ],
        "source_filter": ["Moniteur belge", "CCE", "Juridat", "Cour constitutionnelle", "Conseil d'État"],
        "top_k": 8,
        "system_prompt_extra": (
            "Tu es specialise en droit de la securite sociale belge. "
            "Trois regimes : salaries, independants, fonctionnaires. "
            "Allocations familiales regionalisees depuis 2019 : "
            "Flandre (Groeipakket), Wallonie (AVIQ), Bruxelles (Iriscare). "
            "Les montants sont indexes et changent regulierement — toujours signaler la date."
        ),
    },
    "droit_etrangers": {
        "label": "Droit des etrangers",
        "keywords": [
            "sejour", "titre de sejour", "visa", "regroupement familial",
            "asile", "refugie", "protection subsidiaire", "cgra",
            "office des etrangers", "expulsion", "regularisation",
            "article 9bis", "article 9ter", "nationalite belge",
            "permis unique", "carte bleue europeenne", "etranger",
            "centre ferme", "detention administrative",
        ],
        "source_filter": ["Moniteur belge", "Conseil d'État", "HUDOC", "EUR-Lex", "Cour constitutionnelle", "Juridat"],
        "top_k": 8,
        "system_prompt_extra": (
            "Tu es specialise en droit des etrangers et de l'asile en Belgique. "
            "Legislation : Loi du 15 decembre 1980 (sejour), AR du 8 octobre 1981, "
            "Code de la nationalite belge (Loi du 28 juin 1984). "
            "La CEDH (art. 3, 5, 8) et le droit UE sont centraux. "
            "Les conditions changent frequemment — toujours verifier la date."
        ),
    },
    "droit_fondamentaux": {
        "label": "Droits fondamentaux",
        "keywords": [
            "droits fondamentaux", "constitution", "cedh", "charte des droits fondamentaux",
            "discrimination", "liberte d'expression", "liberte expression", "vie privee", "rgpd",
            "protection des donnees", "egalite", "apd", "droit a la vie",
            "proces equitable", "article 6", "article 8", "recours effectif",
            "cour constitutionnelle", "question prejudicielle",
            "droits de l'homme", "non-discrimination",
        ],
        "source_filter": ["HUDOC", "EUR-Lex", "Cour constitutionnelle", "Moniteur belge", "APD", "Juridat"],
        "top_k": 8,
        "system_prompt_extra": (
            "Tu es specialise en droits fondamentaux. "
            "Sources principales : Constitution belge, CEDH, Charte UE, RGPD. "
            "Distingue CEDH (Strasbourg) vs CJUE (Luxembourg) vs Cour constitutionnelle (Bruxelles). "
            "L'APD rend des decisions en matiere RGPD."
        ),
    },
    "droit_marches_publics": {
        "label": "Marches publics",
        "keywords": [
            "marche public", "adjudication", "procedure negociee", "appel d'offres",
            "cahier des charges", "soumission", "pouvoir adjudicateur",
            "concession", "ppp", "procedure ouverte", "procedure restreinte",
            "standstill", "critere d'attribution", "critere de selection",
            "sous-traitance", "penalites",
        ],
        "source_filter": ["Moniteur belge", "Conseil d'État", "EUR-Lex", "Juridat", "Cour constitutionnelle"],
        "top_k": 8,
        "system_prompt_extra": (
            "Tu es specialise en droit des marches publics belge. "
            "Legislation : Loi du 17 juin 2016 (marches publics), "
            "AR du 18 avril 2017 (passation secteurs classiques), "
            "AR du 14 janvier 2013 (regles generales d'execution). "
            "Les seuils europeens changent tous les deux ans."
        ),
    },
    "droit_europeen": {
        "label": "Droit europeen",
        "keywords": [
            "droit europeen", "union europeenne", "cjue", "directive", "reglement europeen",
            "marche interieur", "aides d'etat", "libre circulation",
            "question prejudicielle cjue", "tfue", "tue", "transposition",
            "ai act", "dsa", "dma", "rgpd", "primauté",
        ],
        "source_filter": ["EUR-Lex", "HUDOC", "Cour constitutionnelle", "Moniteur belge", "Conseil d'État"],
        "top_k": 8,
        "system_prompt_extra": (
            "Tu es specialise en droit de l'Union europeenne applique en Belgique. "
            "Distingue reglements (directement applicables) vs directives (transposition). "
            "Ne pas confondre CJUE (Luxembourg) et CEDH (Strasbourg). "
            "EUR-Lex est la source principale (5,239 docs dans la base)."
        ),
    },
}


def detect_branch(question: str) -> Tuple[Optional[str], float]:
    """
    Detecte la branche du droit la plus pertinente pour une question.

    Returns:
        (branch_key, confidence) — branch_key est None si aucune branche detectee.
        confidence est entre 0.0 et 1.0.
    """
    question_lower = _normalize(question)

    scores: Dict[str, int] = {}
    for branch_key, config in BRANCHES.items():
        score = 0
        for kw in config["keywords"]:
            kw_normalized = _normalize(kw)
            if kw_normalized in question_lower:
                # Mots plus longs = plus specifiques = plus de poids
                weight = 2 if len(kw_normalized) > 12 else 1
                score += weight
        if score > 0:
            scores[branch_key] = score

    if not scores:
        return None, 0.0

    best = max(scores, key=scores.get)
    max_score = scores[best]

    # Confidence basee sur le nombre de keywords matches
    # 1 match = 0.3, 2 = 0.5, 3+ = 0.7+, 5+ = 0.9+
    confidence = min(0.3 + (max_score - 1) * 0.15, 1.0)

    return best, round(confidence, 2)


def get_branch_config(branch_key: str) -> Optional[Dict]:
    """Retourne la configuration complete d'une branche."""
    return BRANCHES.get(branch_key)


def get_branch_prompt(branch_key: str) -> str:
    """Retourne le complement de prompt systeme pour une branche."""
    config = BRANCHES.get(branch_key)
    if not config:
        return ""
    return config.get("system_prompt_extra", "")


def get_branch_sources(branch_key: str) -> Optional[List[str]]:
    """Retourne le source_filter pour une branche."""
    config = BRANCHES.get(branch_key)
    if not config:
        return None
    return config.get("source_filter")


def get_branch_top_k(branch_key: str) -> int:
    """Retourne le top_k recommande pour une branche."""
    config = BRANCHES.get(branch_key)
    if not config:
        return 6
    return config.get("top_k", 6)


def list_branches() -> List[Dict]:
    """Liste toutes les branches disponibles avec leur label."""
    return [
        {"key": key, "label": config["label"]}
        for key, config in BRANCHES.items()
    ]


def _normalize(text: str) -> str:
    """Normalise le texte pour la detection (minuscules, accents simplifies, apostrophes)."""
    text = text.lower()
    # Remplacements d'accents courants pour matcher les keywords sans accents
    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "ù": "u", "û": "u", "ü": "u",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "ç": "c",
    }
    for accent, plain in replacements.items():
        text = text.replace(accent, plain)
    # Normaliser les apostrophes typographiques
    text = text.replace("\u2019", "'")  # ' → '
    text = text.replace("\u2018", "'")  # ' → '
    return text
