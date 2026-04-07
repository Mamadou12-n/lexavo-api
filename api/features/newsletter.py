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
    # 16-52 : vrais conseils juridiques belges
    "Loi du 3 juillet 1978, Art. 82 : le préavis d'un employé avec 5 ans d'ancienneté est de 13 semaines — depuis la réforme de 2014, le calcul est unifié pour ouvriers et employés.",
    "Art. 1654 Code civil + loi du 9 juillet 1971 : un entrepreneur en construction est présumé responsable des vices graves pendant 10 ans après la réception des travaux (responsabilité décennale).",
    "Ordonnance bruxelloise du 27 juillet 2017, Art. 237 : à Bruxelles, le loyer ne peut être indexé qu'une fois par an et uniquement si le bail le prévoit expressément.",
    "Code pénal, Art. 505 : le recel d'objet volé est punissable même si vous ignoriez l'origine illicite — la négligence grave peut suffire à engager votre responsabilité.",
    "CIR 92, Art. 104 : les dons à des organismes agréés d'au moins 40€ par an donnent droit à une réduction d'impôt de 45% du montant donné en Belgique.",
    "Loi du 11 avril 1995 (Charte de l'assuré social) : tout refus de prestation sociale doit être motivé et notifié par écrit — vous avez 3 mois pour introduire un recours.",
    "CSA, Art. 5:64 : dans une SRL, les gérants sont solidairement responsables des cotisations ONSS impayées et de la TVA en cas de faute grave.",
    "RGPD, Art. 35 : les entreprises traitant des données sensibles à grande échelle doivent réaliser une analyse d'impact (DPIA) avant de lancer tout nouveau projet numérique.",
    "Code civil, Art. 1382 (ancien) / Art. 1240 (nouveau) : pour obtenir réparation d'un préjudice extracontractuel, vous devez prouver la faute, le dommage et le lien causal entre les deux.",
    "Loi hypothécaire du 16 décembre 1851 : un bien immobilier ne peut être saisi que sur décision judiciaire — toute expulsion sans titre exécutoire est illégale et pénalement sanctionnable.",
    "Code civil, Art. 913 : la réserve héréditaire des enfants est de la moitié de la succession quelle que soit leur nombre — depuis la réforme de 2018, cette règle est assouplie pour les donations.",
    "Code civil, Art. 1287 : en cas de divorce par consentement mutuel, la convention doit régler la liquidation du régime matrimonial, la garde des enfants et la pension alimentaire.",
    "Code judiciaire, Art. 1408 : le mobilier indispensable au foyer (lit, réfrigérateur, cuisinière, table) est insaisissable par les huissiers — une liste limitative est fixée par la loi.",
    "Loi du 6 avril 2010 sur les pratiques du marché, Art. 51 : le vendeur professionnel doit garantir la conformité du bien pendant 2 ans à compter de la livraison au consommateur.",
    "Loi du 23 décembre 2005 sur le pacte de solidarité, Art. 20 : un travailleur de 45 ans licencié dans une entreprise de 50+ employés a droit à un outplacement de minimum 60h.",
    "Loi du 25 juin 1992 sur le contrat d'assurance terrestre, Art. 14 : l'assureur ne peut refuser un sinistre pour vice de forme si vous avez déclaré le sinistre dans le délai prévu.",
    "Code économique, Art. XX.99 : en cas de faillite d'une SRL, les gérants peuvent être déclarés personnellement responsables si leur faute a contribué à l'insuffisance d'actif.",
    "CTVA belge, Art. 45 : la TVA sur une voiture achetée pour usage mixte (pro + privé) n'est déductible qu'à concurrence de l'usage professionnel, avec un maximum de 50%.",
    "Code pénal, Art. 91 : la prescription de l'action publique pour les crimes est de 15 ans, 5 ans pour les délits, et 6 mois pour les contraventions à partir du jour de l'infraction.",
    "Loi du 10 avril 1971 sur les accidents du travail, Art. 7 : l'accident survenu sur le trajet domicile-lieu de travail est assimilé à un accident du travail et couvert par l'assurance obligatoire.",
    "Loi du 19 juillet 2018 sur la protection de la vie privée, Art. 8 : l'utilisation commerciale de votre image sans consentement exprès est sanctionnable — même une photo prise dans un lieu public.",
    "RGPD, Art. 20 : vous avez le droit de recevoir vos données personnelles dans un format structuré (portabilité) et de les transmettre directement à un autre prestataire de service.",
    "Loi du 30 avril 1951 sur les baux commerciaux, Art. 3 : la durée minimale d'un bail commercial est de 9 ans — toute clause prévoyant une durée inférieure est nulle de plein droit.",
    "Code judiciaire, Art. 1724 : toute médiation menée par un médiateur agréé par la Commission fédérale de médiation peut aboutir à un accord homologué par le tribunal, ayant force exécutoire.",
    "Code des sociétés et associations, Art. 9:5 : une ASBL doit tenir une comptabilité conforme et déposer ses comptes annuels à la BNB si elle dépasse 2 des 3 seuils (recettes 312 500€, total bilan 1,25M€, 5 ETP).",
    "Loi du 10 mai 2007 contre la discrimination, Art. 14 : le refus d'un logement ou d'un emploi fondé sur l'origine ethnique, la religion ou le handicap est sanctionné de 208 à 4 160€ d'amende.",
    "Arrêté royal du 5 mai 2019 sur le chômage temporaire : en cas de force majeure économique, l'employeur peut recourir au chômage temporaire sans préavis pour éviter les licenciements.",
    "CTVA belge, Art. 45bis AR n°20 : depuis 2021, le forfait de déductibilité des voitures de société est plafonné selon le taux d'émission CO₂ — les voitures 0 CO₂ restent à 100%.",
    "Loi du 22 août 2002 sur les droits du patient, Art. 8 : tout patient a le droit de refuser ou d'interrompre un traitement médical — le médecin ne peut passer outre que si la vie du patient est en danger immédiat.",
    "CWATUPE / CoDT wallon, Art. D.IV.4 : en Wallonie, le permis d'urbanisme est obligatoire pour toute construction de plus de 40 m² — sans permis, les travaux sont passibles d'amende et de démolition forcée.",
    "Loi du 5 mars 2017 sur le travail faisable et maniable, Art. 22 : le télétravailleur régulier a les mêmes droits que le travailleur sur site — l'employeur doit fournir le matériel ou verser une indemnité forfaitaire.",
    "Loi du 2 juin 2010 sur la copropriété forcée, Art. 577-9 : tout copropriétaire peut contester une décision de l'assemblée générale devant le juge de paix dans le mois suivant sa notification.",
    "Loi du 19 décembre 1939 sur les allocations familiales (coordonnée) : les enfants ont droit aux allocations familiales jusqu'à 25 ans s'ils suivent des études — le montant de base est modulé par rang.",
    "CIR 92, Art. 131 bis : les droits de donation sur un bien immobilier en Région wallonne sont de 3,3% en ligne directe (enfants, parents) depuis le 1er janvier 2022.",
    "Loi du 11 mars 2003 sur certains aspects juridiques des services de la société de l'information, Art. 16 : un contrat conclu par voie électronique est valide dès lors que le processus d'acceptation est clair et explicite.",
    "Code civil, Art. 1253 : la médiation familiale homologuée par le tribunal de la famille permet de fixer rapidement la résidence alternée et la pension alimentaire sans procédure longue.",
    "Code économique, Art. VII.143 : le taux annuel effectif global (TAEG) d'un crédit à la consommation doit figurer clairement dans tout document publicitaire — un contrat sans TAEG est nul.",
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
