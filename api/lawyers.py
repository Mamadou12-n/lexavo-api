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
    existing = count_lawyers()
    if existing >= 25:
        return 0  # deja peuple avec les 25 avocats

    # 25 avocats couvrant les 11 barreaux principaux et les 15 branches du droit
    # Donnees de demonstration — les emails @lexavo-demo.be ne sont pas reels
    demo_lawyers = [
        # ── Bruxelles (4 avocats) ────────────────────────────────────────
        {"name": "Me Sophie Vandenberghe", "bar": "Barreau de Bruxelles",
         "specialties": ["droit du travail", "droit commercial"],
         "email": "s.vandenberghe@lexavo-demo.be", "phone": "+32 2 512 34 56",
         "city": "Bruxelles", "rating": 4.7, "verified": True,
         "description": "Avocate au Barreau de Bruxelles depuis 2010. Droit du travail et commercial. Restructurations, licenciements, conventions collectives."},
        {"name": "Me Jean-Pierre Lambert", "bar": "Barreau de Bruxelles",
         "specialties": ["droit administratif", "droit de l'environnement"],
         "email": "jp.lambert@lexavo-demo.be", "phone": "+32 2 513 67 89",
         "city": "Bruxelles", "rating": 4.6, "verified": True,
         "description": "Avocat specialise en droit administratif et environnemental. Permis d'urbanisme, recours au Conseil d'Etat, contentieux IBGE."},
        {"name": "Me Amina Belhaj", "bar": "Barreau de Bruxelles",
         "specialties": ["droit des etrangers", "droits fondamentaux"],
         "email": "a.belhaj@lexavo-demo.be", "phone": "+32 2 514 23 45",
         "city": "Bruxelles", "rating": 4.9, "verified": True,
         "description": "Avocate specialisee en droit des etrangers et droits fondamentaux. Asile, regroupement familial, recours CCE, CEDH."},
        {"name": "Me Thomas Willems", "bar": "Barreau de Bruxelles",
         "specialties": ["propriete intellectuelle", "droit europeen"],
         "email": "t.willems@lexavo-demo.be", "phone": "+32 2 515 89 01",
         "city": "Bruxelles", "rating": 4.4, "verified": True,
         "description": "Avocat specialise en propriete intellectuelle et droit europeen. Brevets, marques, droit d'auteur, contentieux CJUE."},
        # ── Anvers (3 avocats) ───────────────────────────────────────────
        {"name": "Me Marc De Smedt", "bar": "Balie van Antwerpen",
         "specialties": ["droit fiscal", "droit commercial"],
         "email": "m.desmedt@lexavo-demo.be", "phone": "+32 3 233 45 67",
         "city": "Anvers", "rating": 4.5, "verified": True,
         "description": "Advocaat — fiscaal recht en handelsrecht. Bijstand aan KMO's bij fiscale geschillen, btw-procedures en internationale structuren."},
        {"name": "Me Lies Van Damme", "bar": "Balie van Antwerpen",
         "specialties": ["droit familial", "droit civil"],
         "email": "l.vandamme@lexavo-demo.be", "phone": "+32 3 234 56 78",
         "city": "Anvers", "rating": 4.7, "verified": True,
         "description": "Advocaat familierecht en burgerlijk recht. Echtscheiding, onderhoudsgeld, erfrecht, aansprakelijkheid."},
        {"name": "Me Koen Peeters", "bar": "Balie van Antwerpen",
         "specialties": ["droit penal", "droit de la securite sociale"],
         "email": "k.peeters@lexavo-demo.be", "phone": "+32 3 235 67 89",
         "city": "Anvers", "rating": 4.3, "verified": True,
         "description": "Advocaat strafrecht en socialezekerheidsrecht. Bijstand bij verhoor, correctionele zaken, sociale fraude."},
        # ── Liege (2 avocats) ────────────────────────────────────────────
        {"name": "Me Isabelle Moreau", "bar": "Barreau de Liege",
         "specialties": ["droit familial", "droit immobilier"],
         "email": "i.moreau@lexavo-demo.be", "phone": "+32 4 222 56 78",
         "city": "Liege", "rating": 4.8, "verified": True,
         "description": "Avocate en droit de la famille et immobilier. Divorce, garde d'enfants, successions, baux. Mediatrice agreee."},
        {"name": "Me Philippe Franssen", "bar": "Barreau de Liege",
         "specialties": ["droit du travail", "droit de la securite sociale"],
         "email": "p.franssen@lexavo-demo.be", "phone": "+32 4 223 67 89",
         "city": "Liege", "rating": 4.5, "verified": True,
         "description": "Avocat en droit social. Licenciements, accidents du travail, ONEM, INAMI, pensions, allocations familiales."},
        # ── Gand (2 avocats) ─────────────────────────────────────────────
        {"name": "Me Pieter Claessens", "bar": "Balie van Gent",
         "specialties": ["droit penal", "droit du travail"],
         "email": "p.claessens@lexavo-demo.be", "phone": "+32 9 225 67 89",
         "city": "Gand", "rating": 4.3, "verified": True,
         "description": "Advocaat strafrecht en sociaal recht. Politieverhoren, correctionele en assisenzaken, sociaal strafrecht."},
        {"name": "Me Eva De Wit", "bar": "Balie van Gent",
         "specialties": ["droit de l'environnement", "droit administratif"],
         "email": "e.dewit@lexavo-demo.be", "phone": "+32 9 226 78 90",
         "city": "Gand", "rating": 4.6, "verified": True,
         "description": "Advocaat milieurecht en bestuursrecht. VLAREM-vergunningen, bodemsanering, Raad van State."},
        # ── Namur (2 avocats) ────────────────────────────────────────────
        {"name": "Me Catherine Dupont", "bar": "Barreau de Namur",
         "specialties": ["droit immobilier", "droit fiscal"],
         "email": "c.dupont@lexavo-demo.be", "phone": "+32 81 22 78 90",
         "city": "Namur", "rating": 4.6, "verified": True,
         "description": "Avocate en droit immobilier et fiscal. Ventes, copropriete, baux commerciaux, urbanisme, droits d'enregistrement."},
        {"name": "Me Francois Bodart", "bar": "Barreau de Namur",
         "specialties": ["droit civil", "droit commercial"],
         "email": "f.bodart@lexavo-demo.be", "phone": "+32 81 23 89 01",
         "city": "Namur", "rating": 4.4, "verified": True,
         "description": "Avocat en droit civil et commercial. Contrats, responsabilite, recouvrement de creances, droit des societes."},
        # ── Charleroi (2 avocats) ────────────────────────────────────────
        {"name": "Me Nadia Ferrara", "bar": "Barreau de Charleroi",
         "specialties": ["droit penal", "droit familial"],
         "email": "n.ferrara@lexavo-demo.be", "phone": "+32 71 31 45 67",
         "city": "Charleroi", "rating": 4.5, "verified": True,
         "description": "Avocate en droit penal et familial. Defense correctionnelle, violences conjugales, protection de la jeunesse."},
        {"name": "Me Youssef El Amrani", "bar": "Barreau de Charleroi",
         "specialties": ["droit des etrangers", "droit du travail"],
         "email": "y.elamrani@lexavo-demo.be", "phone": "+32 71 32 56 78",
         "city": "Charleroi", "rating": 4.4, "verified": True,
         "description": "Avocat en droit des etrangers et droit social. Regularisation, permis de travail, sejour, recours CCE."},
        # ── Bruges (2 avocats) ───────────────────────────────────────────
        {"name": "Me Jan Vermeersch", "bar": "Balie van Brugge",
         "specialties": ["droit commercial", "marches publics"],
         "email": "j.vermeersch@lexavo-demo.be", "phone": "+32 50 33 45 67",
         "city": "Bruges", "rating": 4.5, "verified": True,
         "description": "Advocaat handelsrecht en overheidsopdrachten. Aanbestedingen, concessies, PPP-contracten."},
        {"name": "Me Sofie Maes", "bar": "Balie van Brugge",
         "specialties": ["droit immobilier", "droit de l'environnement"],
         "email": "s.maes@lexavo-demo.be", "phone": "+32 50 34 56 78",
         "city": "Bruges", "rating": 4.6, "verified": True,
         "description": "Advocaat vastgoedrecht en milieurecht. Bouwvergunningen, appartementsrecht, VLAREM."},
        # ── Mons (2 avocats) ─────────────────────────────────────────────
        {"name": "Me Claire Henrard", "bar": "Barreau de Mons",
         "specialties": ["droit familial", "droit civil"],
         "email": "c.henrard@lexavo-demo.be", "phone": "+32 65 33 67 89",
         "city": "Mons", "rating": 4.7, "verified": True,
         "description": "Avocate en droit familial et civil. Divorce, liquidation de regime matrimonial, adoptions, tutelle."},
        {"name": "Me Olivier Delattre", "bar": "Barreau de Mons",
         "specialties": ["droit fiscal", "droit des societes"],
         "email": "o.delattre@lexavo-demo.be", "phone": "+32 65 34 78 90",
         "city": "Mons", "rating": 4.3, "verified": True,
         "description": "Avocat fiscaliste. Impots des societes, TVA, controles fiscaux, rulings, planification successorale."},
        # ── Louvain (2 avocats) ──────────────────────────────────────────
        {"name": "Me Anna Declercq", "bar": "Balie van Leuven",
         "specialties": ["propriete intellectuelle", "droit europeen"],
         "email": "a.declercq@lexavo-demo.be", "phone": "+32 16 22 45 67",
         "city": "Louvain", "rating": 4.8, "verified": True,
         "description": "Advocaat IP en Europees recht. Octrooien, databankenrecht, GDPR, procedures voor het EUIPO en CJUE."},
        {"name": "Me Bart Janssens", "bar": "Balie van Leuven",
         "specialties": ["droit administratif", "marches publics"],
         "email": "b.janssens@lexavo-demo.be", "phone": "+32 16 23 56 78",
         "city": "Louvain", "rating": 4.4, "verified": True,
         "description": "Advocaat bestuursrecht en overheidsopdrachten. Stedenbouw, onteigening, Raad van State, Raad voor Vergunningsbetwistingen."},
        # ── Hasselt (1 avocat) ───────────────────────────────────────────
        {"name": "Me Lien Hermans", "bar": "Balie van Limburg",
         "specialties": ["droit du travail", "droit de la securite sociale"],
         "email": "l.hermans@lexavo-demo.be", "phone": "+32 11 22 67 89",
         "city": "Hasselt", "rating": 4.5, "verified": True,
         "description": "Advocaat arbeidsrecht en sociale zekerheid. Ontslag, arbeidsongevallen, werkloosheid, pensioenen."},
        # ── Eupen (1 avocat — communaute germanophone) ───────────────────
        {"name": "Me Klaus Schmitz", "bar": "Anwaltskammer Eupen",
         "specialties": ["droit civil", "droit familial"],
         "email": "k.schmitz@lexavo-demo.be", "phone": "+32 87 55 34 56",
         "city": "Eupen", "rating": 4.4, "verified": True,
         "description": "Rechtsanwalt fur Zivilrecht und Familienrecht. Scheidung, Erbrecht, Vertragsrecht. Deutschsprachige Gemeinschaft Belgiens."},
        # ── Tournai (1 avocat) ───────────────────────────────────────────
        {"name": "Me Lucie Lefevre", "bar": "Barreau du Hainaut",
         "specialties": ["droit penal", "droits fondamentaux"],
         "email": "l.lefevre@lexavo-demo.be", "phone": "+32 69 22 45 67",
         "city": "Tournai", "rating": 4.6, "verified": True,
         "description": "Avocate penaliste et droits fondamentaux. Defense en assises, detention preventive, droits des detenus, CEDH."},
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
