"""Lexavo Heritage — Guide succession personnalise par region.
Deces d'un proche -> guide etape par etape selon region et situation."""

import logging
from typing import Optional

log = logging.getLogger("heritage")

HERITAGE_STEPS_COMMON = [
    {"step": 1, "title": "Deces et formalites immediates", "deadline": "24-48h", "actions": ["Obtenir l'acte de deces a la commune", "Contacter la banque du defunt (comptes geles)", "Prevenir l'employeur si applicable"]},
    {"step": 2, "title": "Choix successoral", "deadline": "3 mois", "actions": ["Accepter la succession purement et simplement", "Accepter sous benefice d'inventaire", "Renoncer a la succession (si dettes > actif)"]},
    {"step": 3, "title": "Declaration de succession", "deadline": "4 mois (Flandre) / 4 mois (Wallonie/Bruxelles)", "actions": ["Etablir l'inventaire des biens et dettes", "Deposer la declaration au bureau Securite juridique", "Payer les droits de succession"]},
    {"step": 4, "title": "Partage", "deadline": "Variable", "actions": ["Partage amiable entre heritiers", "Partage judiciaire si desaccord", "Intervention notariale obligatoire pour les immeubles"]},
]

REGIONAL_SPECIFICS = {
    "bruxelles": {
        "authority": "SPF Finances — Bureau Securite juridique de Bruxelles",
        "deadline_declaration": "4 mois (deces en Belgique), 5 mois (deces en Europe), 6 mois (hors Europe)",
        "exemptions": ["Logement familial : abattement de 25.000 EUR pour le conjoint survivant"],
        "rates_info": "Tranches progressives de 3% a 30% en ligne directe",
    },
    "wallonie": {
        "authority": "SPF Finances — Bureau Securite juridique wallon",
        "deadline_declaration": "4 mois (idem Bruxelles)",
        "exemptions": ["Logement familial : exemption totale pour le conjoint survivant (sous conditions)"],
        "rates_info": "Tranches progressives de 3% a 30% en ligne directe",
    },
    "flandre": {
        "authority": "Vlaamse Belastingdienst (VLABEL)",
        "deadline_declaration": "4 mois",
        "exemptions": ["Gezinswoning : vrijstelling voor langstlevende partner", "Forfaitaire aftrek huisraad: 20.000 EUR"],
        "rates_info": "Drie schijven: 3%, 9%, 27% in rechte lijn",
    },
}


def generate_heritage_guide(
    region: str, relationship: str = "direct_line",
    has_testament: bool = False, has_real_estate: bool = False,
    estimated_value: float = 0, mock: bool = False,
) -> dict:
    region = region.lower()
    if region not in REGIONAL_SPECIFICS:
        raise ValueError("Region inconnue. Utilisez bruxelles, wallonie ou flandre.")

    regional = REGIONAL_SPECIFICS[region]

    # Calculate estimated duties
    from api.features.calculators import calculate_succession_duties
    duties = None
    if estimated_value > 0:
        duties = calculate_succession_duties(region=region, amount=estimated_value, relationship=relationship)

    guide = {
        "region": region,
        "relationship": relationship,
        "steps": HERITAGE_STEPS_COMMON,
        "regional_info": regional,
        "has_testament": has_testament,
        "has_real_estate": has_real_estate,
        "notes": [],
    }

    if has_testament:
        guide["notes"].append("Un testament existe — le notaire doit l'ouvrir et verifier sa validite.")
    else:
        guide["notes"].append("Pas de testament — la succession legale s'applique (Code civil, art. 731 et suivants).")

    if has_real_estate:
        guide["notes"].append("Biens immobiliers presents — l'intervention d'un notaire est OBLIGATOIRE pour le partage.")

    if duties:
        guide["estimated_duties"] = duties

    guide["disclaimer"] = "Guide informatif. Les successions necessitent l'intervention d'un notaire."

    # Cles attendues par le frontend mobile
    guide["model"] = "local"

    # summary — combine les notes en texte lisible
    if not guide.get("summary"):
        parts = [f"Succession en region {region.capitalize()}."]
        parts.extend(guide.get("notes", []))
        parts.append(f"Autorite competente : {regional.get('authority', 'N/A')}.")
        parts.append(f"Delai de declaration : {regional.get('deadline_declaration', 'N/A')}.")
        guide["summary"] = " ".join(parts)

    # succession_duties et effective_rate depuis estimated_duties
    if duties and isinstance(duties, dict):
        guide["succession_duties"] = duties.get("total_duties", duties.get("duties", 0))
        if estimated_value > 0 and guide["succession_duties"]:
            guide["effective_rate"] = (guide["succession_duties"] / estimated_value) * 100
        else:
            guide["effective_rate"] = 0.0
    elif duties and isinstance(duties, (int, float)):
        guide["succession_duties"] = duties
        guide["effective_rate"] = (duties / estimated_value * 100) if estimated_value > 0 else 0.0
    else:
        guide["succession_duties"] = None
        guide["effective_rate"] = None

    # applicable_rates depuis regional_info
    if not guide.get("applicable_rates"):
        guide["applicable_rates"] = None
        rates_info = regional.get("rates_info", "")
        if rates_info:
            guide["legal_basis"] = rates_info
        else:
            guide["legal_basis"] = None

    return guide
