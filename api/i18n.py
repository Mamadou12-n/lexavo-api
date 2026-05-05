"""
api/i18n.py — Backend i18n pour Lexavo (FR/NL/EN/DE).

Refocalisation 2026-05-05 : 4 langues supportees (BE officielles + EN).
Le client envoie son Accept-Language ou prefere la valeur stockee
dans le profil utilisateur. La fonction `get_lang(request)` parse le
header de maniere robuste et tombe en `fr` par defaut.

Usage typique :

    from fastapi import Depends
    from api.i18n import get_lang, t

    @router.post("/auth/register")
    def register(payload: RegisterRequest, lang: str = Depends(get_lang)):
        if not payload.email or "@" not in payload.email:
            raise HTTPException(400, t("auth_invalid_email", lang))

Ne jamais utiliser de f-string sur les cles : `t(key, lang)` retourne
toujours une string deterministe sans interpolation cote module.
"""

from __future__ import annotations

from typing import Final
from fastapi import Request


SUPPORTED_LANGS: Final[tuple[str, ...]] = ("fr", "nl", "en", "de")
DEFAULT_LANG: Final[str] = "fr"


# ─── Dictionnaire d'erreurs ─────────────────────────────────────────────────
# Cles flat (pas de nesting) pour rester compatibles avec un fallback simple.
# Toute cle ajoutee ici DOIT exister dans les 4 langues.

_MESSAGES: Final[dict[str, dict[str, str]]] = {
    # Auth — register
    "auth_invalid_email": {
        "fr": "Adresse email invalide.",
        "nl": "Ongeldig e-mailadres.",
        "en": "Invalid email address.",
        "de": "Ungültige E-Mail-Adresse.",
    },
    "auth_password_too_short": {
        "fr": "Le mot de passe doit contenir au moins 8 caractères.",
        "nl": "Het wachtwoord moet minstens 8 tekens bevatten.",
        "en": "Password must contain at least 8 characters.",
        "de": "Das Passwort muss mindestens 8 Zeichen enthalten.",
    },
    "auth_name_too_short": {
        "fr": "Le nom doit contenir au moins 2 caractères.",
        "nl": "De naam moet minstens 2 tekens bevatten.",
        "en": "Name must contain at least 2 characters.",
        "de": "Der Name muss mindestens 2 Zeichen enthalten.",
    },
    "auth_invalid_language": {
        "fr": "Langue invalide. Choisissez parmi : fr, nl, en, de.",
        "nl": "Ongeldige taal. Kies uit: fr, nl, en, de.",
        "en": "Invalid language. Choose from: fr, nl, en, de.",
        "de": "Ungültige Sprache. Wählen Sie aus: fr, nl, en, de.",
    },
    "auth_email_taken": {
        "fr": "Un compte existe déjà avec cet email.",
        "nl": "Er bestaat al een account met dit e-mailadres.",
        "en": "An account already exists with this email.",
        "de": "Es existiert bereits ein Konto mit dieser E-Mail-Adresse.",
    },
    # Auth — login
    "auth_invalid_credentials": {
        "fr": "Email ou mot de passe incorrect.",
        "nl": "E-mailadres of wachtwoord onjuist.",
        "en": "Incorrect email or password.",
        "de": "E-Mail oder Passwort falsch.",
    },
    "auth_account_locked": {
        "fr": "Compte temporairement verrouillé après plusieurs échecs. Réessayez dans 15 minutes.",
        "nl": "Account tijdelijk vergrendeld na meerdere mislukkingen. Probeer het over 15 minuten opnieuw.",
        "en": "Account temporarily locked after multiple failures. Try again in 15 minutes.",
        "de": "Konto vorübergehend gesperrt nach mehreren Fehlversuchen. Versuchen Sie es in 15 Minuten erneut.",
    },
    # Auth — reset password
    "auth_invalid_token": {
        "fr": "Token invalide ou expiré.",
        "nl": "Ongeldig of verlopen token.",
        "en": "Invalid or expired token.",
        "de": "Ungültiges oder abgelaufenes Token.",
    },
    # Push notifications (cf. api/push.py)
    "push_new_answer_title": {
        "fr": "Nouvelle réponse",
        "nl": "Nieuw antwoord",
        "en": "New answer",
        "de": "Neue Antwort",
    },
    "push_new_answer_body": {
        "fr": "Votre question juridique a été analysée.",
        "nl": "Uw juridische vraag is geanalyseerd.",
        "en": "Your legal question has been analyzed.",
        "de": "Ihre Rechtsfrage wurde analysiert.",
    },
    "push_beta_ending_j30_title": {
        "fr": "Votre beta se termine dans 30 jours",
        "nl": "Uw beta eindigt over 30 dagen",
        "en": "Your beta ends in 30 days",
        "de": "Ihre Beta endet in 30 Tagen",
    },
    "push_beta_ending_j30_body": {
        "fr": "Bloquez votre tarif fondateur 3,99€/mois à vie.",
        "nl": "Reserveer uw oprichterstarief van €3,99/maand voor het leven.",
        "en": "Lock in your founder price of €3.99/month forever.",
        "de": "Sichern Sie sich den Gründerpreis von 3,99 €/Monat lebenslang.",
    },
    "push_beta_ending_j7_title": {
        "fr": "Plus que 7 jours de beta",
        "nl": "Nog 7 dagen beta",
        "en": "Only 7 days of beta left",
        "de": "Nur noch 7 Tage Beta",
    },
    "push_beta_ending_j7_body": {
        "fr": "Activez Particulier avant la fin de la beta.",
        "nl": "Activeer Particulier vóór het einde van de beta.",
        "en": "Activate Individual before the beta ends.",
        "de": "Aktivieren Sie Privat vor dem Beta-Ende.",
    },

    # Generic
    "internal_error": {
        "fr": "Une erreur interne est survenue. Veuillez réessayer.",
        "nl": "Er is een interne fout opgetreden. Probeer het opnieuw.",
        "en": "An internal error occurred. Please try again.",
        "de": "Ein interner Fehler ist aufgetreten. Bitte erneut versuchen.",
    },
}


# ─── Helpers ────────────────────────────────────────────────────────────────


def normalize_lang(code: str | None) -> str:
    """Renvoie l'une des 4 langues supportees, ou DEFAULT_LANG en fallback."""
    if not code:
        return DEFAULT_LANG
    lower = str(code).strip().lower()[:2]
    return lower if lower in SUPPORTED_LANGS else DEFAULT_LANG


def parse_accept_language(header_value: str | None) -> str:
    """Parse un header Accept-Language RFC 7231 et retourne la meilleure
    langue supportee.

    Exemples :
        "fr-BE,fr;q=0.9,en;q=0.8"          -> "fr"
        "nl-NL,nl;q=0.9"                   -> "nl"
        "es-ES"                            -> "fr" (fallback, non supporte)
        ""                                 -> "fr"
        None                               -> "fr"

    Le parsing est defensif : on extrait la liste des langues, on prefere
    celles avec le plus haut q (defaut 1.0), et on garde la premiere
    supportee. Pas de dependance externe (langcodes/babel) : on reste leger.
    """
    if not header_value:
        return DEFAULT_LANG

    candidates: list[tuple[float, str]] = []
    for raw in header_value.split(","):
        part = raw.strip()
        if not part:
            continue
        # "fr-BE;q=0.9" -> ("fr-BE", q=0.9)
        if ";" in part:
            tag, *params = [p.strip() for p in part.split(";")]
            q = 1.0
            for p in params:
                if p.startswith("q="):
                    try:
                        q = float(p[2:])
                    except ValueError:
                        q = 0.0
            candidates.append((q, tag.lower()))
        else:
            candidates.append((1.0, part.lower()))

    # Tri descendant par q
    candidates.sort(key=lambda x: x[0], reverse=True)

    for _, tag in candidates:
        # "fr-be" -> "fr"
        primary = tag.split("-")[0]
        if primary in SUPPORTED_LANGS:
            return primary

    return DEFAULT_LANG


def get_lang(request: Request) -> str:
    """Dependency FastAPI : retourne la langue de la requete (4 supportees).

    Ordre de priorite :
        1. Header X-Lexavo-Lang (override explicite mobile)
        2. Header Accept-Language (RFC 7231)
        3. Default 'fr'
    """
    # Override mobile (le client peut forcer la langue stockee localement)
    explicit = request.headers.get("x-lexavo-lang")
    if explicit:
        return normalize_lang(explicit)

    return parse_accept_language(request.headers.get("accept-language"))


def t(key: str, lang: str | None = None) -> str:
    """Renvoie le message traduit, fallback FR puis cle brute si manquant.

    Le pattern de fallback est defensif : si la cle n'existe pas, on
    retourne la cle elle-meme pour debug rapide en dev (pas de KeyError
    en prod qui casserait le 400 -> 500).
    """
    safe_lang = normalize_lang(lang)
    entry = _MESSAGES.get(key)
    if entry is None:
        return key
    return entry.get(safe_lang) or entry.get(DEFAULT_LANG, key)
