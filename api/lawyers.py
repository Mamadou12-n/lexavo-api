"""
Lawyer marketplace logic for Lexavo.
Handles listing, filtering, and seeding demo lawyers.
"""

from typing import Optional

from fastapi import HTTPException, status

import logging

from api.database import (
    list_lawyers as db_list_lawyers,
    get_lawyer_by_id as db_get_lawyer,
    create_lawyer as db_create_lawyer,
    count_lawyers,
    _get_conn, USE_PG,
)

log = logging.getLogger("lawyers")


def _purge_duplicate_lawyers():
    """Remove duplicate lawyers keeping the lowest id for each email."""
    conn = _get_conn()
    try:
        if USE_PG:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM lawyers WHERE id NOT IN (
                    SELECT MIN(id) FROM lawyers GROUP BY email
                );
            """)
        else:
            conn.execute("""
                DELETE FROM lawyers WHERE id NOT IN (
                    SELECT MIN(id) FROM lawyers GROUP BY email
                );
            """)
        conn.commit()
        remaining = count_lawyers()
        log.info(f"Purged duplicate lawyers, {remaining} remaining")
    finally:
        conn.close()


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
    existing = count_lawyers()

    # Purger tous les avocats si plus de 5 (migration vers 5 demo)
    if existing > 5:
        from api.database import _get_conn, _execute
        conn = _get_conn()
        _execute(conn, "DELETE FROM lawyers")
        conn.commit()
        conn.close()
        existing = 0

    if existing >= 5:
        return 0  # deja peuple

    # 5 avocats couvrant les 5 grandes villes et specialites principales
    # Donnees de demonstration — les emails @lexavo-demo.be ne sont pas reels
    demo_lawyers = [
        {"name": "Me Sophie Vandenberghe", "bar": "Barreau de Bruxelles",
         "specialties": ["droit du travail", "droit commercial"],
         "email": "s.vandenberghe@lexavo-demo.be", "phone": "+32 2 512 34 56",
         "city": "Bruxelles", "rating": 4.7, "verified": True,
         "description": "Avocate au Barreau de Bruxelles depuis 2010. Droit du travail et commercial. Restructurations, licenciements, conventions collectives."},
        {"name": "Me Marc De Smedt", "bar": "Balie van Antwerpen",
         "specialties": ["droit fiscal", "droit commercial"],
         "email": "m.desmedt@lexavo-demo.be", "phone": "+32 3 233 45 67",
         "city": "Anvers", "rating": 4.5, "verified": True,
         "description": "Advocaat fiscaal recht en handelsrecht. Bijstand aan KMO's bij fiscale geschillen, btw-procedures en internationale structuren."},
        {"name": "Me Isabelle Moreau", "bar": "Barreau de Liege",
         "specialties": ["droit familial", "droit immobilier"],
         "email": "i.moreau@lexavo-demo.be", "phone": "+32 4 222 56 78",
         "city": "Liege", "rating": 4.8, "verified": True,
         "description": "Avocate en droit de la famille et immobilier. Divorce, garde d'enfants, successions, baux. Mediatrice agreee."},
        {"name": "Me Pieter Claessens", "bar": "Balie van Gent",
         "specialties": ["droit penal", "droit du travail"],
         "email": "p.claessens@lexavo-demo.be", "phone": "+32 9 225 67 89",
         "city": "Gand", "rating": 4.3, "verified": True,
         "description": "Advocaat strafrecht en sociaal recht. Politieverhoren, correctionele en assisenzaken, sociaal strafrecht."},
        {"name": "Me Catherine Dupont", "bar": "Barreau de Namur",
         "specialties": ["droit immobilier", "droit fiscal"],
         "email": "c.dupont@lexavo-demo.be", "phone": "+32 81 22 78 90",
         "city": "Namur", "rating": 4.6, "verified": True,
         "description": "Avocate en droit immobilier et fiscal. Ventes, copropriete, baux commerciaux, urbanisme, droits d'enregistrement."},
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
