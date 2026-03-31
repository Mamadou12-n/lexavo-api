"""Lexavo Newsletter — Génération automatique de newsletter juridique belge."""

import secrets
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

log = logging.getLogger("newsletter")

# ─── 52 Tips juridiques belges (semaine 1 à 52) ──────────────────────────────

WEEKLY_TIPS: List[str] = [
    # 1-15 : tips réels
    "Art. 1647 Code civil : vice caché → vous disposez d'1 an à partir de la découverte pour agir en garantie.",
    "CCT n°109 : chaque année d'ancienneté = 3 semaines de préavis supplémentaires pour les ouvriers et employés.",
    "RGPD Art. 17 : le droit à l'effacement de vos données peut être exercé par simple email à l'entreprise concernée.",
    "Art. 3 de la loi du 21 mars 1991 : le consommateur dispose de 14 jours pour se rétracter d'un achat à distance.",
    "Art. 1654 Code civil : si votre vendeur connaissait le vice caché, il peut être condamné à des dommages et intérêts en plus du remboursement.",
    "CCT n°17 : les heures supplémentaires doivent être payées avec un surtaux de 50% (ou 100% la nuit et le dimanche).",
    "Art. 1724 Code civil : en cas de réparations urgentes, le locataire est obligé de les tolérer même pendant le bail.",
    "Loi du 4 août 1992 sur le crédit hypothécaire : le droit de remboursement anticipé est légalement garanti, avec une indemnité maximale de 3 mois d'intérêts.",
    "Art. 2262bis Code civil : la prescription générale en matière civile est de 10 ans, mais attention aux prescriptions spéciales plus courtes.",
    "Art. 3 Loi 14/07/1991 sur les pratiques commerciales : une publicité mensongère peut être sanctionnée par le tribunal de l'entreprise.",
    "Code des sociétés et associations (CSA), Art. 2:5 : la SRL peut être constituée par une seule personne physique, avec un capital minimum librement fixé.",
    "Art. 1375 Code civil : l'enrichissement sans cause oblige à restituer ce dont on s'est enrichi injustement aux dépens d'autrui.",
    "TVA belge, Art. 42 CTVA : les travaux de rénovation d'un logement de plus de 10 ans bénéficient du taux réduit de 6% sous conditions.",
    "Loi du 8 juillet 1976 sur les CPAS : toute personne en situation précaire peut demander un revenu d'intégration sociale (RIS) à son CPAS.",
    "Art. 63/7 du Code de la nationalité belge : après 5 ans de résidence légale ininterrompue, vous pouvez demander la nationalité belge.",
    # 16-52 : placeholders
    "Tip 16 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 17 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 18 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 19 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 20 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 21 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 22 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 23 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 24 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 25 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 26 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 27 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 28 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 29 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 30 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 31 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 32 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 33 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 34 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 35 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 36 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 37 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 38 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 39 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 40 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 41 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 42 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 43 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 44 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 45 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 46 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 47 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 48 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 49 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 50 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 51 — Droit belge : restez informé avec Lexavo chaque semaine.",
    "Tip 52 — Droit belge : restez informé avec Lexavo chaque semaine.",
]

# Vérification : 52 tips exactement
assert len(WEEKLY_TIPS) == 52, f"Il faut 52 tips, {len(WEEKLY_TIPS)} trouvés"

# ─── 5 Questions fréquentes avec réponses ────────────────────────────────────

WEEKLY_QUESTIONS = [
    {
        "title": "Mon employeur peut-il lire mes emails professionnels ?",
        "answer": (
            "Oui, mais avec des limites strictes. L'employeur peut consulter les emails pro "
            "à condition d'en avoir informé le travailleur préalablement et par écrit. "
            "Les emails marqués 'privé' sont protégés et ne peuvent pas être lus. "
            "Une surveillance disproportionnée est sanctionnée."
        ),
        "legal_ref": "CCT n°81 du CNT · Loi du 13 juin 2005 sur les communications électroniques · Art. 8 CEDH",
    },
    {
        "title": "Quand le bail peut-il être résilié sans préavis ?",
        "answer": (
            "En Belgique, la résiliation sans préavis est possible uniquement en cas de faute "
            "grave du locataire (non-paiement répété, dégradations importantes, sous-location "
            "non autorisée) après mise en demeure restée sans effet, ou par accord amiable "
            "entre les parties."
        ),
        "legal_ref": "Loi du 20 février 1991 relative aux baux à loyer · Décret wallon du 15 mars 2018 · Ordonnance bruxelloise du 27 juillet 2017",
    },
    {
        "title": "Quelle est la prescription d'une facture impayée ?",
        "answer": (
            "La prescription d'une facture commerciale est de 5 ans en Belgique depuis la réforme "
            "du Code civil de 2018 (art. 2262bis → art. 8.13 nouveau Code civil). "
            "Pour les factures envers des consommateurs, le délai reste de 5 ans à partir de "
            "la date d'échéance."
        ),
        "legal_ref": "Art. 8.13 nouveau Code civil belge (loi du 13 avril 2019) · Art. 2262bis ancien Code civil",
    },
    {
        "title": "Mon employeur doit-il payer les heures supplémentaires ?",
        "answer": (
            "Oui. Les heures supplémentaires (au-delà de 9h/jour ou 40h/semaine) doivent être "
            "rémunérées avec un surtaux de 50%, ou 100% la nuit, le dimanche ou les jours fériés. "
            "L'employeur peut alternativement accorder un repos compensatoire équivalent sous "
            "conditions strictes."
        ),
        "legal_ref": "Art. 29 loi du 16 mars 1971 sur le travail · CCT n°17 du CNT",
    },
    {
        "title": "RGPD : qui est responsable si mes données sont volées ?",
        "answer": (
            "Le responsable du traitement (l'entreprise qui collecte vos données) est "
            "responsable en cas de violation, sauf s'il prouve avoir pris toutes les mesures "
            "techniques et organisationnelles appropriées. L'APD (Autorité de Protection des "
            "Données) peut infliger une amende jusqu'à 4% du chiffre d'affaires mondial."
        ),
        "legal_ref": "RGPD Art. 82 · Art. 83 · Loi belge du 30 juillet 2018 relative à la protection des personnes physiques",
    },
]


# ─── Fonction principale ──────────────────────────────────────────────────────

def generate_weekly_newsletter(week_num: int, domains: Optional[List[str]] = None) -> dict:
    """
    Génère le contenu complet d'une newsletter juridique belge hebdomadaire.

    Args:
        week_num: numéro de la semaine (1-52). Détermine le tip et la question.
        domains: liste des domaines d'alertes à inclure (ex: ['travail', 'fiscal']).

    Returns:
        dict avec subject, preheader, hero_title, weekly_tip, question, alerts, html_content, text_content.
    """
    if domains is None:
        domains = []

    # Sélection du tip (rotation 52 semaines, index 0-based)
    tip_index = (week_num - 1) % 52
    weekly_tip = WEEKLY_TIPS[tip_index]

    # Sélection de la question (rotation 5 questions)
    question = WEEKLY_QUESTIONS[(week_num - 1) % len(WEEKLY_QUESTIONS)]

    # Récupération des alertes depuis le module alerts
    from api.features.alerts import get_alert_feed
    alerts_raw = get_alert_feed(domains=domains if domains else [], limit=3)

    # Enrichissement des alertes avec un label lisible
    domain_labels = {
        "travail": "Droit du travail",
        "bail": "Droit du bail",
        "fiscal": "Droit fiscal",
        "famille": "Droit familial",
        "entreprise": "Droit des entreprises",
        "social": "Sécurité sociale",
        "immobilier": "Droit immobilier",
        "environnement": "Environnement",
    }

    alerts = []
    for a in alerts_raw[:3]:
        alerts.append({
            "domain": a.get("domain", ""),
            "domain_label": domain_labels.get(a.get("domain", ""), a.get("domain", "").capitalize()),
            "title": a.get("title", ""),
            "summary": a.get("summary", ""),
            "date": a.get("date", ""),
            "source": a.get("source", ""),
            "url": a.get("url", ""),
        })

    # Si pas d'alertes selon les domaines, on prend les 3 premières globalement
    if not alerts:
        from api.features.alerts import get_alert_feed as _feed
        for a in _feed(domains=[], limit=3):
            alerts.append({
                "domain": a.get("domain", ""),
                "domain_label": domain_labels.get(a.get("domain", ""), a.get("domain", "").capitalize()),
                "title": a.get("title", ""),
                "summary": a.get("summary", ""),
                "date": a.get("date", ""),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
            })

    subject = f"Lexavo — Votre veille juridique belge · Semaine {week_num}"
    preheader = f"{len(alerts)} actualité(s) juridique(s) + le tip de la semaine"
    hero_title = f"Semaine {week_num} : ce que la loi belge change pour vous"

    html_content = generate_newsletter_html(week_num=week_num, domains=domains)

    # Version texte brut
    text_lines = [
        f"LEXAVO — Semaine {week_num}",
        "=" * 40,
        "",
        "ACTUALITE JURIDIQUE",
    ]
    for a in alerts:
        text_lines.append(f"- [{a['domain_label']}] {a['title']} ({a['date']}, {a['source']})")
    text_lines += [
        "",
        "LE SAVIEZ-VOUS ?",
        weekly_tip,
        "",
        "QUESTION DE LA SEMAINE",
        question["title"],
        question["answer"],
        question["legal_ref"],
        "",
        "Accédez à Lexavo : https://lexavo.be",
        "Se désabonner : https://lexavo.be/newsletter/unsubscribe",
        "",
        "Ce contenu est fourni à titre informatif uniquement et ne constitue pas un avis juridique.",
    ]
    text_content = "\n".join(text_lines)

    return {
        "subject": subject,
        "preheader": preheader,
        "hero_title": hero_title,
        "weekly_tip": weekly_tip,
        "question": question,
        "alerts": alerts,
        "html_content": html_content,
        "text_content": text_content,
        "week_num": week_num,
    }


def generate_newsletter_html(week_num: int, domains: Optional[List[str]] = None) -> str:
    """
    Rend le template Jinja2 de la newsletter pour la semaine donnée.

    Args:
        week_num: numéro de semaine (1-52).
        domains: domaines d'alertes à inclure.

    Returns:
        Chaîne HTML complète prête à envoyer.
    """
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError:
        log.warning("Jinja2 non disponible — retour HTML minimal.")
        return f"<html><body><h1>Lexavo — Semaine {week_num}</h1></body></html>"

    if domains is None:
        domains = []

    templates_dir = Path(__file__).parent.parent / "templates"

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
    )

    # Générer les données (en évitant la récursion : on calcule directement)
    tip_index = (week_num - 1) % 52
    weekly_tip = WEEKLY_TIPS[tip_index]
    question = WEEKLY_QUESTIONS[(week_num - 1) % len(WEEKLY_QUESTIONS)]

    from api.features.alerts import get_alert_feed
    alerts_raw = get_alert_feed(domains=domains if domains else [], limit=3)

    domain_labels = {
        "travail": "Droit du travail",
        "bail": "Droit du bail",
        "fiscal": "Droit fiscal",
        "famille": "Droit familial",
        "entreprise": "Droit des entreprises",
        "social": "Sécurité sociale",
        "immobilier": "Droit immobilier",
        "environnement": "Environnement",
    }

    alerts = []
    for a in alerts_raw[:3]:
        alerts.append({
            "domain": a.get("domain", ""),
            "domain_label": domain_labels.get(a.get("domain", ""), a.get("domain", "").capitalize()),
            "title": a.get("title", ""),
            "summary": a.get("summary", ""),
            "date": a.get("date", ""),
            "source": a.get("source", ""),
            "url": a.get("url", ""),
        })

    if not alerts:
        from api.features.alerts import get_alert_feed as _feed
        for a in _feed(domains=[], limit=3):
            alerts.append({
                "domain": a.get("domain", ""),
                "domain_label": domain_labels.get(a.get("domain", ""), a.get("domain", "").capitalize()),
                "title": a.get("title", ""),
                "summary": a.get("summary", ""),
                "date": a.get("date", ""),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
            })

    subject = f"Lexavo — Votre veille juridique belge · Semaine {week_num}"
    preheader = f"{len(alerts)} actualité(s) juridique(s) + le tip de la semaine"
    hero_title = f"Semaine {week_num} : ce que la loi belge change pour vous"

    template = env.get_template("newsletter_weekly.html")
    return template.render(
        subject=subject,
        preheader=preheader,
        hero_title=hero_title,
        week_num=week_num,
        alerts=alerts,
        weekly_tip=weekly_tip,
        question_title=question["title"],
        question_answer=question["answer"],
        question_legal_ref=question["legal_ref"],
    )
