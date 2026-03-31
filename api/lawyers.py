"""
Lawyer marketplace logic for Lexavo.
Handles listing, filtering, and seeding demo lawyers.
"""

from typing import Optional

from fastapi import HTTPException, status

from api.database import (
    list_lawyers as db_list_lawyers,
    get_lawyer_by_id as db_get_lawyer,
    create_lawyer as db_create_lawyer,
    count_lawyers,
)


def list_lawyers(
    city: Optional[str] = None,
    specialty: Optional[str] = None,
    language: Optional[str] = None,
) -> list:
    """List lawyers with optional filters. Returns list of lawyer dicts."""
    return db_list_lawyers(city=city, specialty=specialty, language=language)


def get_lawyer(lawyer_id: int) -> dict:
    """Get a single lawyer by ID. Raises 404 if not found."""
    lawyer = db_get_lawyer(lawyer_id)
    if not lawyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Avocat #{lawyer_id} introuvable.",
        )
    return lawyer


def seed_demo_lawyers() -> int:
    """Seed 5 fictional but realistic Belgian lawyers.
    Uses real barreaux and realistic specialties.
    Returns number of lawyers seeded.
    Only seeds if the lawyers table is empty.
    """
    if count_lawyers() > 0:
        return 0

    demo_lawyers = [
        {
            "name": "Me Sophie Vandenberghe",
            "bar": "Barreau de Bruxelles",
            "specialties": ["droit du travail", "droit commercial"],
            "email": "s.vandenberghe@lexavo-demo.be",
            "phone": "+32 2 512 34 56",
            "city": "Bruxelles",
            "description": (
                "Avocate au Barreau de Bruxelles depuis 2010, spécialisée en droit du travail "
                "et droit commercial. Accompagne les entreprises et les travailleurs dans leurs "
                "litiges individuels et collectifs. Expérience en restructurations, licenciements "
                "et négociations de conventions collectives."
            ),
            "rating": 4.7,
            "verified": True,
        },
        {
            "name": "Me Marc De Smedt",
            "bar": "Balie van Antwerpen",
            "specialties": ["droit fiscal", "droit commercial"],
            "email": "m.desmedt@lexavo-demo.be",
            "phone": "+32 3 233 45 67",
            "city": "Anvers",
            "description": (
                "Advocaat aan de Balie van Antwerpen. Gespecialiseerd in fiscaal recht en "
                "handelsrecht. Bijstand aan KMO's en particulieren bij fiscale geschillen, "
                "controles en bezwaarschriften. Ruime ervaring met btw-procedures en "
                "internationale fiscale structuren."
            ),
            "rating": 4.5,
            "verified": True,
        },
        {
            "name": "Me Isabelle Moreau",
            "bar": "Barreau de Liège",
            "specialties": ["droit familial", "droit immobilier"],
            "email": "i.moreau@lexavo-demo.be",
            "phone": "+32 4 222 56 78",
            "city": "Liège",
            "description": (
                "Avocate au Barreau de Liège, spécialisée en droit de la famille et droit "
                "immobilier. Intervient en matière de divorce, garde d'enfants, pensions "
                "alimentaires, successions et baux. Médiatrice agréée en matières familiales."
            ),
            "rating": 4.8,
            "verified": True,
        },
        {
            "name": "Me Pieter Claessens",
            "bar": "Balie van Gent",
            "specialties": ["droit pénal", "droit du travail"],
            "email": "p.claessens@lexavo-demo.be",
            "phone": "+32 9 225 67 89",
            "city": "Gand",
            "description": (
                "Advocaat aan de Balie van Gent. Gespecialiseerd in strafrecht en sociaal recht. "
                "Bijstand bij politieverhoren, correctionale zittingen en assisen. Verdediging "
                "bij misdrijven tegen personen, vermogensdelicten en drugsdelicten. Eveneens "
                "actief in sociaal strafrecht."
            ),
            "rating": 4.3,
            "verified": True,
        },
        {
            "name": "Me Catherine Dupont",
            "bar": "Barreau de Namur",
            "specialties": ["droit immobilier", "droit fiscal"],
            "email": "c.dupont@lexavo-demo.be",
            "phone": "+32 81 22 78 90",
            "city": "Namur",
            "description": (
                "Avocate au Barreau de Namur depuis 2008. Pratique axée sur le droit immobilier "
                "(ventes, copropriété, baux commerciaux, urbanisme) et le droit fiscal "
                "(impôts des sociétés, plus-values immobilières, droits d'enregistrement). "
                "Conseil aux promoteurs et investisseurs immobiliers."
            ),
            "rating": 4.6,
            "verified": True,
        },
    ]

    seeded = 0
    for lawyer in demo_lawyers:
        try:
            result = db_create_lawyer(**lawyer)
            if result:
                seeded += 1
        except Exception:
            continue

    return seeded
