"""Lexavo Litiges Pro — Recouvrement d'impayes automatise.
Facture impayee -> sequence rappel -> mise en demeure -> recommandation."""

import logging
from typing import Optional
from datetime import datetime, timedelta

log = logging.getLogger("litigation")

LITIGATION_STAGES = [
    {"stage": 1, "name": "rappel_amiable", "label": "Rappel amiable", "delay_days": 15, "description": "Premier rappel courtois de paiement"},
    {"stage": 2, "name": "rappel_ferme", "label": "Rappel ferme", "delay_days": 30, "description": "Second rappel avec mention des interets de retard"},
    {"stage": 3, "name": "mise_en_demeure", "label": "Mise en demeure", "delay_days": 45, "description": "Mise en demeure formelle par recommande"},
    {"stage": 4, "name": "recouvrement", "label": "Recouvrement", "delay_days": 60, "description": "Procedure IOS ou mise en relation avocat"},
]


def get_stages() -> list:
    return LITIGATION_STAGES


def start_litigation(
    creditor_name: str, debtor_name: str, amount: float,
    invoice_number: str, due_date: str, mock: bool = False,
) -> dict:
    if amount <= 0:
        raise ValueError("Le montant doit etre positif")
    if len(creditor_name.strip()) < 2:
        raise ValueError("Nom du creancier requis")

    today = datetime.now()

    stages_timeline = []
    for stage in LITIGATION_STAGES:
        stage_date = today + timedelta(days=stage["delay_days"])
        stages_timeline.append({
            **stage,
            "scheduled_date": stage_date.strftime("%Y-%m-%d"),
            "status": "pending",
        })
    stages_timeline[0]["status"] = "active"

    # Generate first reminder letter
    reminder = f"""Madame, Monsieur,

Sauf erreur de notre part, nous constatons que la facture {invoice_number} d'un montant de {amount:.2f} EUR, dont l'echeance etait fixee au {due_date}, demeure impayee a ce jour.

Nous vous saurions gre de bien vouloir proceder au reglement de cette somme dans les meilleurs delais.

A defaut de paiement dans les 15 jours, nous nous verrons contraints d'entamer les demarches prevues par la loi, notamment l'application d'interets de retard conformement a la Loi du 2 aout 2002 concernant la lutte contre le retard de paiement dans les transactions commerciales.

Veuillez agreer, Madame, Monsieur, l'expression de nos salutations distinguees.

{creditor_name}"""

    return {
        "litigation_id": f"LIT-{today.strftime('%Y%m%d')}-{hash(invoice_number) % 10000:04d}",
        "creditor": creditor_name,
        "debtor": debtor_name,
        "amount": amount,
        "invoice_number": invoice_number,
        "due_date": due_date,
        "current_stage": "rappel_amiable",
        "stages": stages_timeline,
        "current_letter": reminder,
        "legal_basis": "Loi du 2 aout 2002 (retard de paiement transactions commerciales)",
        "disclaimer": "Modeles de lettres type. Ne constituent pas un acte d'huissier.",
    }
