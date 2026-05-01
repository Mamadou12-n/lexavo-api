"""Calculateurs de droits belges — logique mathematique pure (zero API).

Sources legales :
- Preavis : CCT n109 du CNT (30/01/2014) + Loi Peeters (26/12/2013)
- Pension alimentaire : Bareme Renard (methode doctrinale de reference)
- Succession : Code des droits de succession (3 regions)
"""


def calculate_notice_period(years: int, monthly_salary: float) -> dict:
    """Calcule le preavis de licenciement (CCT n109)."""
    if years < 0:
        raise ValueError("L'anciennete ne peut pas etre negative")

    if years == 0:
        weeks = 1
    elif years <= 3:
        weeks = 2 + (years * 4)
    elif years <= 4:
        weeks = 15
    elif years <= 5:
        weeks = 18
    elif years <= 6:
        weeks = 21
    elif years <= 7:
        weeks = 24
    elif years <= 8:
        weeks = 27
    elif years <= 9:
        weeks = 30
    elif years <= 10:
        weeks = 33
    elif years <= 15:
        weeks = 33 + (years - 10) * 3
    elif years <= 20:
        weeks = 48 + (years - 15) * 3
    else:
        weeks = 63 + (years - 20) * 3

    indemnity = round(monthly_salary * (weeks / 4.33), 2)

    return {
        "result": indemnity,
        "unit": "€ (indemnité compensatoire)",
        "details": {"weeks": weeks, "months": round(weeks / 4.33, 1), "monthly_salary": monthly_salary, "years_service": years},
        "legal_basis": "CCT n°109 du CNT — Art. 37/2 Loi du 3 juillet 1978",
        "disclaimer": "Estimation indicative. Consultez votre secrétariat social.",
    }


def calculate_alimony_renard(
    income_high: float, income_low: float, children: int = 0
) -> dict:
    """Calcule la pension alimentaire selon le bareme Renard."""
    if income_high < income_low:
        income_high, income_low = income_low, income_high

    base = (income_high - income_low) / 3
    child_supplement = base * 0.10 * children
    monthly_amount = round(base + child_supplement, 2)

    cap = income_high / 3
    if monthly_amount > cap:
        monthly_amount = round(cap, 2)

    formula = "Bareme Renard : (revenus eleves - revenus faibles) / 3"
    return {
        "result": monthly_amount,
        "unit": "€/mois",
        "details": {"annual_amount": round(monthly_amount * 12, 2), "income_high": income_high, "income_low": income_low, "children": children, "formula": formula},
        "legal_basis": "Méthode Renard — Art. 301 §3 Code civil belge",
        "disclaimer": "Estimation selon la méthode Renard. Le juge reste souverain.",
    }


SUCCESSION_RATES = {
    "bruxelles": {
        "direct_line": [
            (50000, 0.03), (100000, 0.08), (175000, 0.09),
            (250000, 0.18), (500000, 0.24), (float("inf"), 0.30),
        ],
        "siblings": [
            (12500, 0.20), (25000, 0.25), (50000, 0.30),
            (100000, 0.40), (175000, 0.55), (250000, 0.60), (float("inf"), 0.65),
        ],
        "others": [
            (50000, 0.40), (75000, 0.55), (175000, 0.65), (float("inf"), 0.80),
        ],
    },
    "wallonie": {
        "direct_line": [
            (12500, 0.03), (25000, 0.04), (50000, 0.05), (100000, 0.07),
            (150000, 0.10), (200000, 0.14), (250000, 0.18),
            (500000, 0.24), (float("inf"), 0.30),
        ],
        "siblings": [
            (12500, 0.20), (25000, 0.25), (75000, 0.35),
            (175000, 0.50), (float("inf"), 0.65),
        ],
        "others": [
            (12500, 0.25), (25000, 0.30), (75000, 0.40),
            (175000, 0.55), (float("inf"), 0.70),
        ],
    },
    "flandre": {
        "direct_line": [
            (50000, 0.03), (250000, 0.09), (float("inf"), 0.27),
        ],
        "siblings": [
            (35000, 0.25), (75000, 0.30), (float("inf"), 0.55),
        ],
        "others": [
            (35000, 0.25), (75000, 0.45), (float("inf"), 0.55),
        ],
    },
}


def calculate_succession_duties(
    region: str, amount: float, relationship: str = "direct_line"
) -> dict:
    """Calcule les droits de succession par region belge."""
    region = region.lower().replace("e\u0300", "e").replace("e\u0302", "e")
    # Normalize common variants
    if region in ("bxl", "brux"):
        region = "bruxelles"
    elif region in ("wal", "wall"):
        region = "wallonie"
    elif region in ("vl", "fla", "vlaanderen"):
        region = "flandre"

    if region not in SUCCESSION_RATES:
        raise ValueError(f"Region inconnue : {region}. Utilisez bruxelles, wallonie ou flandre.")
    if relationship not in ("direct_line", "siblings", "others"):
        raise ValueError("Relation : direct_line, siblings, others")

    rates = SUCCESSION_RATES[region][relationship]

    total_duty = 0.0
    remaining = amount
    breakdown = []

    prev_limit = 0
    for limit, rate in rates:
        taxable = min(remaining, limit - prev_limit)
        if taxable <= 0:
            break
        duty = taxable * rate
        total_duty += duty
        breakdown.append({
            "from": prev_limit,
            "to": prev_limit + taxable,
            "rate": f"{rate*100:.0f}%",
            "duty": round(duty, 2),
        })
        remaining -= taxable
        prev_limit = limit

    effective_rate = (total_duty / amount * 100) if amount > 0 else 0

    return {
        "result": round(total_duty, 2),
        "unit": "€ de droits de succession",
        "details": {"net_amount": round(amount - total_duty, 2), "effective_rate": f"{effective_rate:.1f}%", "region": region, "relationship": relationship, "amount": amount, "breakdown": breakdown},
        "legal_basis": f"Code des droits de succession — Région de {region.capitalize()}",
        "disclaimer": "Estimation indicative. Les exemptions et abattements spécifiques ne sont pas inclus.",
    }


# ─── Indexation loyer ─────────────────────────────────────────────────────────
# Indice santé Belgique : (loyer_base × indice_nouveau) / indice_depart
# Source : SPF Économie — Statbel (https://statbel.fgov.be)

def calculate_indexation_loyer(
    loyer_base: float,
    indice_depart: float,
    indice_nouveau: float,
    region: str = "bruxelles",
) -> dict:
    """Calcule le loyer indexé selon l'indice santé belge.

    Formule légale : loyer_indexé = loyer_base × (indice_nouveau / indice_depart)
    Référence : Loi du 20 février 1991, art. 1728bis Code civil ; bail régional.
    """
    if loyer_base <= 0:
        raise ValueError("Loyer de base requis (> 0)")
    if indice_depart <= 0 or indice_nouveau <= 0:
        raise ValueError("Indices santé requis (> 0)")

    loyer_indexe = round(loyer_base * (indice_nouveau / indice_depart), 2)
    augmentation = round(loyer_indexe - loyer_base, 2)
    pct = round((augmentation / loyer_base) * 100, 2) if loyer_base else 0.0

    region_n = (region or "bruxelles").lower()
    legal_refs = {
        "bruxelles": "Code bruxellois du logement — art. 224 ; Loi 20/02/1991.",
        "wallonie": "Code wallon du logement — art. 13 ; Loi 20/02/1991.",
        "flandre": "Vlaamse Wooncode — Woninghuurdecreet 09/11/2018.",
    }

    return {
        "result": loyer_indexe,
        "unit": "€/mois (loyer indexé)",
        "details": {
            "loyer_base": loyer_base,
            "indice_depart": indice_depart,
            "indice_nouveau": indice_nouveau,
            "augmentation": augmentation,
            "pourcentage": f"{pct}%",
            "region": region_n,
            "formula": "loyer_base × (indice_nouveau / indice_depart)",
        },
        "legal_basis": legal_refs.get(region_n, legal_refs["bruxelles"]),
        "disclaimer": "Estimation indicative. L'indexation suppose une clause d'indexation au bail et ne s'applique qu'à la date anniversaire.",
    }
