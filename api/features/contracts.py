"""Lexavo Bibliotheque de Contrats — Templates belges telechargeable en PDF.
Bail, contrat de travail, vente, pret, mise en demeure, CGV."""

import logging
from typing import Optional, List

log = logging.getLogger("contracts")

CONTRACT_TEMPLATES = {
    "bail_bruxelles": {
        "title": "Contrat de bail de residence principale — Region de Bruxelles-Capitale",
        "category": "bail",
        "region": "bruxelles",
        "legal_basis": "Code bruxellois du Logement (Ordonnance du 27 juillet 2017)",
        "price_cents": 500,
        "language": "fr",
        "variables": ["nom_bailleur", "nom_preneur", "adresse_bien", "loyer_mensuel", "date_debut", "duree_bail"],
    },
    "bail_wallonie": {
        "title": "Contrat de bail de residence principale — Region wallonne",
        "category": "bail",
        "region": "wallonie",
        "legal_basis": "Decret wallon du 15 mars 2018 relatif au bail d'habitation",
        "price_cents": 500,
        "language": "fr",
        "variables": ["nom_bailleur", "nom_preneur", "adresse_bien", "loyer_mensuel", "date_debut", "duree_bail"],
    },
    "bail_flandre": {
        "title": "Huurovereenkomst hoofdverblijfplaats — Vlaams Gewest",
        "category": "bail",
        "region": "flandre",
        "legal_basis": "Vlaams Woninghuurdecreet (9 november 2018)",
        "price_cents": 500,
        "language": "nl",
        "variables": ["naam_verhuurder", "naam_huurder", "adres_pand", "maandelijkse_huur", "startdatum", "duur_huur"],
    },
    "contrat_travail_cdi": {
        "title": "Contrat de travail a duree indeterminee",
        "category": "travail",
        "region": None,
        "legal_basis": "Loi du 3 juillet 1978 relative aux contrats de travail",
        "price_cents": 500,
        "language": "fr",
        "variables": ["nom_employeur", "nom_travailleur", "fonction", "salaire_brut", "date_debut", "lieu_travail"],
    },
    "mise_en_demeure": {
        "title": "Mise en demeure standard",
        "category": "recouvrement",
        "region": None,
        "legal_basis": "Art. 1139 et 1146 Code civil",
        "price_cents": 300,
        "language": "fr",
        "variables": ["nom_creancier", "nom_debiteur", "montant_du", "description_dette", "delai_jours"],
    },
    "vente_entre_particuliers": {
        "title": "Contrat de vente entre particuliers (bien meuble)",
        "category": "vente",
        "region": None,
        "legal_basis": "Art. 1582 et suivants Code civil",
        "price_cents": 500,
        "language": "fr",
        "variables": ["nom_vendeur", "nom_acheteur", "description_bien", "prix_vente", "date_livraison"],
    },
    "contrat_pret": {
        "title": "Contrat de pret entre particuliers",
        "category": "pret",
        "region": None,
        "legal_basis": "Art. 1892 et suivants Code civil",
        "price_cents": 500,
        "language": "fr",
        "variables": ["nom_preteur", "nom_emprunteur", "montant_pret", "taux_interet", "duree_mois", "modalites_remboursement"],
    },
    "cgv_independant": {
        "title": "Conditions Generales de Vente pour independants",
        "category": "commercial",
        "region": None,
        "legal_basis": "Code de droit economique, Livre VI",
        "price_cents": 900,
        "language": "fr",
        "variables": ["nom_entreprise", "numero_bce", "adresse_siege", "activite_principale", "conditions_paiement"],
    },
    "convention_cohabitation": {
        "title": "Convention de cohabitation legale",
        "category": "famille",
        "region": None,
        "legal_basis": "Art. 1477 et suivants Code civil",
        "price_cents": 500,
        "language": "fr",
        "variables": ["nom_partenaire_1", "nom_partenaire_2", "adresse_commune", "repartition_charges", "regime_biens"],
    },
}


def list_templates(category: Optional[str] = None, region: Optional[str] = None) -> list:
    """Liste les templates disponibles avec filtres optionnels."""
    results = []
    for key, template in CONTRACT_TEMPLATES.items():
        if category and template["category"] != category:
            continue
        if region and template.get("region") and template["region"] != region:
            continue
        results.append({
            "id": key,
            "title": template["title"],
            "category": template["category"],
            "region": template.get("region"),
            "legal_basis": template["legal_basis"],
            "price_cents": template["price_cents"],
            "language": template["language"],
            "variables": template["variables"],
        })
    return results


def get_template(template_id: str) -> Optional[dict]:
    """Recupere un template par ID."""
    template = CONTRACT_TEMPLATES.get(template_id)
    if not template:
        return None
    return {"id": template_id, **template}


def generate_contract_html(template_id: str, variables: dict) -> str:
    """Genere le HTML d'un contrat rempli.

    Args:
        template_id: ID du template
        variables: Dict des variables a remplir
    """
    template = CONTRACT_TEMPLATES.get(template_id)
    if not template:
        raise ValueError(f"Template inconnu : {template_id}")

    title = template["title"]
    legal_basis = template["legal_basis"]

    # Generer le HTML de base
    var_html = ""
    for var_name in template["variables"]:
        value = variables.get(var_name, f"[{var_name}]")
        label = var_name.replace("_", " ").capitalize()
        var_html += f"<p><strong>{label} :</strong> {value}</p>\n"

    html = f"""
    <h1>{title}</h1>
    <p><em>Base legale : {legal_basis}</em></p>
    <hr>
    <h2>Parties</h2>
    {var_html}
    <h2>Dispositions</h2>
    <p>Les conditions detaillees du contrat seront generees selon le type
    de contrat et les variables fournies.</p>
    <p><em>Document genere par Lexavo. A faire valider par un professionnel.</em></p>
    """
    return html


def generate_contract_pdf(template_id: str, variables: dict) -> bytes:
    """Genere le PDF d'un contrat rempli."""
    html = generate_contract_html(template_id, variables)
    from api.utils.pdf_gen import generate_pdf
    return generate_pdf(html, title=CONTRACT_TEMPLATES[template_id]["title"])
