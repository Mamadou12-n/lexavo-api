"""SEO programmatique Lexavo — pages HTML indexables.

Génère 500+ pages indexables depuis les données existantes :
  - 3 pages calculateurs
  - 15 villes × 1 page générale = 15 pages avocats
  - 15 villes × 6 spécialités = 90 pages avocats/spécialité
  - 9 modèles de contrats
  Total : 3 + 15 + 90 + 9 = 117 pages statiques
  + sitemap.xml + robots.txt
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# ─── Données de référence ──────────────────────────────────────────────────────

BELGIAN_CITIES = [
    "Bruxelles", "Liège", "Gand", "Anvers", "Charleroi",
    "Bruges", "Namur", "Louvain", "Mons", "Aalst",
    "Hasselt", "Courtrai", "Tournai", "Mechelen", "La Louvière"
]

SPECIALTIES_FR = {
    "droit-travail": "Droit du travail",
    "droit-immobilier": "Droit immobilier",
    "droit-familial": "Droit familial",
    "droit-fiscal": "Droit fiscal",
    "droit-commercial": "Droit commercial",
    "droit-penal": "Droit pénal",
}

BARREAU_INFO = {
    "Bruxelles": (
        "Le Barreau de Bruxelles (Ordre des avocats du Barreau de Bruxelles) est le plus grand "
        "barreau de Belgique avec plus de 7 000 avocats inscrits. Il est bilingue français/néerlandais "
        "et couvre toute la Région de Bruxelles-Capitale. Siège : Palais de Justice, Place Poelaert."
    ),
    "Liège": (
        "Le Barreau de Liège-Huy compte environ 1 500 avocats. Il couvre l'arrondissement judiciaire "
        "de Liège. Le Palais de Justice de Liège est situé Place Saint-Lambert."
    ),
    "Gand": (
        "De Balie van Gent (Barreau de Gand) compte environ 2 000 avocats. Il couvre l'arrondissement "
        "judiciaire de Gand (Oost-Vlaanderen). Siège : Gerechtsgebouw, Opgeëistenlaan."
    ),
    "Anvers": (
        "De Balie van Antwerpen (Barreau d'Anvers) est le deuxième plus grand barreau de Belgique "
        "avec plus de 3 500 avocats. Il couvre la province d'Anvers."
    ),
    "Charleroi": (
        "Le Barreau de Charleroi compte environ 600 avocats et couvre l'arrondissement judiciaire "
        "de Charleroi (Hainaut). Siège : Palais de Justice de Charleroi."
    ),
    "Bruges": (
        "De Balie van Brugge (Barreau de Bruges) couvre la province de Flandre-Occidentale avec "
        "environ 1 000 avocats inscrits. Siège : Gerechtsgebouw, Kazernevest."
    ),
    "Namur": (
        "Le Barreau de Namur compte environ 500 avocats et couvre la province de Namur. "
        "Siège : Palais de Justice, Place du Palais de Justice, Namur."
    ),
    "Louvain": (
        "De Balie van Leuven (Barreau de Louvain) couvre la province du Brabant flamand avec "
        "environ 800 avocats. Siège : Gerechtsgebouw, Smoldersplein."
    ),
    "Mons": (
        "Le Barreau de Mons compte environ 700 avocats et couvre l'arrondissement judiciaire de Mons. "
        "Siège : Palais de Justice de Mons, Place du Gouvernement."
    ),
    "Aalst": (
        "De Balie van Dendermonde-Aalst couvre la région d'Alost (Oost-Vlaanderen). "
        "Environ 500 avocats inscrits. Siège : Gerechtsgebouw, Aalst."
    ),
    "Hasselt": (
        "De Balie van Hasselt couvre la province du Limbourg avec environ 600 avocats. "
        "Siège : Gerechtsgebouw, Thonissenlaan, Hasselt."
    ),
    "Courtrai": (
        "De Balie van Kortrijk (Barreau de Courtrai) couvre la région de Courtrai (Flandre-Occidentale) "
        "avec environ 500 avocats. Siège : Gerechtsgebouw, Kortrijk."
    ),
    "Tournai": (
        "Le Barreau de Tournai compte environ 350 avocats et couvre l'arrondissement judiciaire "
        "de Tournai (Hainaut). Siège : Palais de Justice de Tournai."
    ),
    "Mechelen": (
        "De Balie van Mechelen (Barreau de Malines) couvre la région de Malines (Anvers) "
        "avec environ 400 avocats. Siège : Gerechtsgebouw, Mechelen."
    ),
    "La Louvière": (
        "Le Barreau de La Louvière (rattaché au Barreau de Mons) dessert la région du Centre "
        "en Hainaut. Environ 200 avocats actifs dans la région."
    ),
}

CITY_DESCRIPTIONS = {
    "Bruxelles": "Capitale de la Belgique et siège des institutions européennes, Bruxelles abrite le plus grand barreau du pays avec plus de 7 000 avocats spécialisés dans tous les domaines du droit.",
    "Liège": "Troisième ville de Wallonie, Liège dispose d'un barreau dynamique de 1 500 avocats couvrant l'ensemble des branches du droit belge.",
    "Gand": "Capitale de la Flandre-Orientale, Gand est un centre juridique majeur avec un barreau de 2 000 avocats et une Cour d'appel réputée.",
    "Anvers": "Deuxième ville de Belgique et premier port d'Europe, Anvers dispose du deuxième plus grand barreau de Belgique, très actif en droit commercial et maritime.",
    "Charleroi": "Principale ville du Hainaut, Charleroi dispose d'un barreau spécialisé notamment en droit du travail et droit social.",
    "Bruges": "Capitale de la Flandre-Occidentale, Bruges abrite un barreau d'environ 1 000 avocats couvrant toute la province.",
    "Namur": "Capitale de la Wallonie, Namur dispose d'un barreau de 500 avocats et du siège du Gouvernement wallon.",
    "Louvain": "Ville universitaire du Brabant flamand, Louvain dispose d'un barreau dynamique lié à la présence de la KU Leuven, première université belge.",
    "Mons": "Capitale du Hainaut et ancienne Capitale européenne de la Culture, Mons dispose d'un barreau de 700 avocats actifs.",
    "Aalst": "Ville principale d'Alost en Flandre-Orientale, avec un barreau couvrant la région de Dendermonde-Aalst.",
    "Hasselt": "Capitale du Limbourg, Hasselt dispose d'un barreau d'environ 600 avocats couvrant toute la province limbourgeoise.",
    "Courtrai": "Ville principale du sud de la Flandre-Occidentale, Courtrai dispose d'un barreau actif en droit commercial et social.",
    "Tournai": "Ville historique du Hainaut occidental, Tournai dispose d'un barreau de 350 avocats couvrant l'arrondissement.",
    "Mechelen": "Ville de la province d'Anvers, Malines dispose d'un barreau dynamique couvrant la région malinoise.",
    "La Louvière": "Centre industriel du Hainaut, La Louvière est desservie par le barreau de Mons avec des avocats actifs dans la région du Centre.",
}


def _get_lawyers_for_city(city: str, specialty_slug: str = None) -> list:
    """Récupère les avocats d'une ville depuis la DB."""
    try:
        from api.database import list_lawyers
        specialty_label = SPECIALTIES_FR.get(specialty_slug) if specialty_slug else None
        lawyers = list_lawyers(city=city, specialty=specialty_label)
        return lawyers
    except Exception:
        return []


def _count_seo_pages() -> int:
    """Compte le nombre total de pages SEO générées."""
    calc_pages = 3
    city_pages = len(BELGIAN_CITIES)
    specialty_pages = len(BELGIAN_CITIES) * len(SPECIALTIES_FR)
    try:
        from api.features.contracts import list_templates
        contract_pages = len(list_templates())
    except Exception:
        contract_pages = 9
    return calc_pages + city_pages + specialty_pages + contract_pages


# ─── A. Pages Calculateurs ─────────────────────────────────────────────────────

@router.get("/calcul/preavis-licenciement", response_class=HTMLResponse)
def page_calcul_preavis(request: Request):
    """Page SEO — Calculateur préavis licenciement Belgique."""
    return templates.TemplateResponse(request, "calcul_preavis.html", {})


@router.get("/calcul/pension-alimentaire", response_class=HTMLResponse)
def page_calcul_pension(request: Request):
    """Page SEO — Calculateur pension alimentaire Belgique."""
    return templates.TemplateResponse(request, "calcul_pension.html", {})


@router.get("/calcul/droits-succession", response_class=HTMLResponse)
def page_calcul_succession(request: Request):
    """Page SEO — Calculateur droits de succession Belgique."""
    return templates.TemplateResponse(request, "calcul_succession.html", {})


# ─── B. Pages Avocats par ville ────────────────────────────────────────────────

@router.get("/avocats/{city}", response_class=HTMLResponse)
def page_avocats_ville(request: Request, city: str):
    """Page SEO — Avocats par ville (15 villes × 1 = 15 pages)."""
    lawyers = _get_lawyers_for_city(city)

    page_title = f"Avocats à {city}"
    meta_description = (
        f"Trouvez un avocat à {city} sur Lexavo. "
        f"{len(lawyers)} avocat{'s' if len(lawyers) != 1 else ''} disponible{'s' if len(lawyers) != 1 else ''} "
        f"dans toutes les spécialités. Barreau de {city}."
    )
    city_description = CITY_DESCRIPTIONS.get(city, f"Trouvez un avocat qualifié à {city}, Belgique.")
    barreau_info = BARREAU_INFO.get(city, f"Le barreau de {city} regroupe les avocats de la région.")

    return templates.TemplateResponse(
        request,
        "avocats_ville.html",
        {
            "city": city,
            "specialty": None,
            "specialty_slug": None,
            "specialty_label": None,
            "lawyers": lawyers,
            "page_title": page_title,
            "meta_description": meta_description,
            "city_description": city_description,
            "barreau_info": barreau_info,
            "specialties": SPECIALTIES_FR,
            "all_cities": BELGIAN_CITIES,
        },
    )


@router.get("/avocats/{city}/{specialty}", response_class=HTMLResponse)
def page_avocats_ville_specialite(request: Request, city: str, specialty: str):
    """Page SEO — Avocats par ville et spécialité (15 × 6 = 90 pages)."""
    specialty_label = SPECIALTIES_FR.get(specialty, specialty.replace("-", " ").title())
    lawyers = _get_lawyers_for_city(city, specialty_slug=specialty)

    page_title = f"Avocats {specialty_label} à {city}"
    meta_description = (
        f"Trouvez un avocat spécialisé en {specialty_label} à {city} sur Lexavo. "
        f"Liste des avocats du barreau de {city} avec notes et contacts."
    )
    city_description = CITY_DESCRIPTIONS.get(city, f"Trouvez un avocat qualifié à {city}, Belgique.")
    barreau_info = BARREAU_INFO.get(city, f"Le barreau de {city} regroupe les avocats de la région.")

    return templates.TemplateResponse(
        request,
        "avocats_ville.html",
        {
            "city": city,
            "specialty": specialty_label,
            "specialty_slug": specialty,
            "specialty_label": specialty_label,
            "lawyers": lawyers,
            "page_title": page_title,
            "meta_description": meta_description,
            "city_description": city_description,
            "barreau_info": barreau_info,
            "specialties": SPECIALTIES_FR,
            "all_cities": BELGIAN_CITIES,
        },
    )


# ─── C. Pages Modèles de contrats ─────────────────────────────────────────────

@router.get("/modeles/{template_id}", response_class=HTMLResponse)
def page_modele_contrat(request: Request, template_id: str):
    """Page SEO — Modèle de contrat (9 pages)."""
    from fastapi import HTTPException
    from api.features.contracts import get_template, list_templates

    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Modèle introuvable.")

    all_templates = list_templates()

    return templates.TemplateResponse(
        request,
        "modele_contrat.html",
        {
            "template": template,
            "all_templates": all_templates,
        },
    )


# ─── D. Sitemap XML ────────────────────────────────────────────────────────────

@router.get("/sitemap.xml", response_class=Response)
def sitemap_xml(request: Request):
    """Sitemap XML listant toutes les pages SEO générées dynamiquement."""
    from api.features.contracts import list_templates

    base = "https://lexavo.be"
    urls = []

    # Calculateurs
    for slug in ["preavis-licenciement", "pension-alimentaire", "droits-succession"]:
        urls.append(f"{base}/calcul/{slug}")

    # Avocats par ville
    for city in BELGIAN_CITIES:
        urls.append(f"{base}/avocats/{city}")
        for spec_slug in SPECIALTIES_FR:
            urls.append(f"{base}/avocats/{city}/{spec_slug}")

    # Modèles de contrats
    try:
        for tpl in list_templates():
            urls.append(f"{base}/modeles/{tpl['id']}")
    except Exception:
        pass

    url_entries = "\n".join(
        f"  <url>\n"
        f"    <loc>{u}</loc>\n"
        f"    <changefreq>monthly</changefreq>\n"
        f"    <priority>0.7</priority>\n"
        f"  </url>"
        for u in urls
    )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{url_entries}\n"
        "</urlset>"
    )

    return Response(content=xml, media_type="application/xml")


# ─── E. Robots.txt ────────────────────────────────────────────────────────────

@router.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    """Robots.txt autorisant l'indexation des pages SEO."""
    return PlainTextResponse(
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /docs\n"
        "Disallow: /redoc\n"
        "Disallow: /auth/\n"
        "Disallow: /billing/\n"
        "\n"
        "Sitemap: https://lexavo.be/sitemap.xml\n"
    )
