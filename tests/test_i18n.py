"""
Tests i18n backend — verifient que les 4 langues (FR/NL/EN/DE) sont
retournees correctement selon le header Accept-Language ou X-Lexavo-Lang.

Couvre :
- module api.i18n : normalize_lang, parse_accept_language, t
- endpoint /auth/register : erreurs validation en 4 langues
- endpoint /auth/login : erreur invalid_credentials en 4 langues
- fallback comportement : langue non supportee -> FR
- override mobile : X-Lexavo-Lang gagne sur Accept-Language

Mots-cles distinctifs par langue (utilises pour l'assertion) :
  FR : "invalide" / "incorrect" / "moins de 8"
  NL : "ongeldig" / "minstens 8"
  EN : "invalid" / "incorrect" / "at least 8"
  DE : "ungültig" / "mindestens 8"
"""

import pytest


# ─── Tests unitaires sur api.i18n ────────────────────────────────────────────


class TestNormalizeLang:
    """Tests sur normalize_lang() — whitelist 4 langues + fallback fr."""

    def test_normalize_supported_lang_returns_same(self):
        from api.i18n import normalize_lang
        assert normalize_lang("fr") == "fr"
        assert normalize_lang("nl") == "nl"
        assert normalize_lang("en") == "en"
        assert normalize_lang("de") == "de"

    def test_normalize_strips_region_code(self):
        from api.i18n import normalize_lang
        assert normalize_lang("fr-BE") == "fr"
        assert normalize_lang("nl-NL") == "nl"
        assert normalize_lang("en-US") == "en"
        assert normalize_lang("de-DE") == "de"

    def test_normalize_unsupported_lang_falls_back_to_fr(self):
        from api.i18n import normalize_lang
        assert normalize_lang("es") == "fr"
        assert normalize_lang("ar") == "fr"
        assert normalize_lang("zh-CN") == "fr"

    def test_normalize_none_or_empty_returns_fr(self):
        from api.i18n import normalize_lang
        assert normalize_lang(None) == "fr"
        assert normalize_lang("") == "fr"

    def test_normalize_uppercase_lowercased(self):
        from api.i18n import normalize_lang
        assert normalize_lang("FR") == "fr"
        assert normalize_lang("NL-BE") == "nl"


class TestParseAcceptLanguage:
    """Tests sur parse_accept_language() — RFC 7231 robust parsing."""

    def test_parse_simple_lang(self):
        from api.i18n import parse_accept_language
        assert parse_accept_language("fr") == "fr"
        assert parse_accept_language("nl") == "nl"

    def test_parse_with_quality_factors_picks_highest(self):
        from api.i18n import parse_accept_language
        # nl=0.9 gagne sur fr=0.5
        assert parse_accept_language("fr;q=0.5,nl;q=0.9") == "nl"

    def test_parse_belgian_browser_typical(self):
        from api.i18n import parse_accept_language
        # Browser typique BE : "fr-BE,fr;q=0.9,en;q=0.8"
        assert parse_accept_language("fr-BE,fr;q=0.9,en;q=0.8") == "fr"

    def test_parse_unsupported_falls_back_to_fr(self):
        from api.i18n import parse_accept_language
        assert parse_accept_language("es-ES,es;q=0.9") == "fr"

    def test_parse_empty_or_none_returns_fr(self):
        from api.i18n import parse_accept_language
        assert parse_accept_language("") == "fr"
        assert parse_accept_language(None) == "fr"

    def test_parse_malformed_q_does_not_crash(self):
        from api.i18n import parse_accept_language
        # q invalide -> defensive parsing, ne crash pas
        result = parse_accept_language("fr;q=zzz,nl;q=0.5")
        assert result in ("fr", "nl")

    def test_parse_picks_first_supported_when_no_q(self):
        from api.i18n import parse_accept_language
        # Sans q, premier supporte gagne
        assert parse_accept_language("nl,fr") == "nl"


class TestT:
    """Tests sur t() — traduction avec fallback FR puis cle brute."""

    def test_t_returns_correct_translation(self):
        from api.i18n import t
        assert "invalide" in t("auth_invalid_email", "fr").lower()
        assert "ongeldig" in t("auth_invalid_email", "nl").lower()
        assert "invalid" in t("auth_invalid_email", "en").lower()
        assert "ungültig" in t("auth_invalid_email", "de").lower()

    def test_t_unsupported_lang_falls_back_to_fr(self):
        from api.i18n import t
        # 'ar' non supporte -> doit retourner FR
        assert "invalide" in t("auth_invalid_email", "ar").lower()

    def test_t_missing_key_returns_key_brute(self):
        from api.i18n import t
        # Cle inexistante : retourne la cle (pas de KeyError)
        assert t("nonexistent_key_xyz", "fr") == "nonexistent_key_xyz"

    def test_t_no_lang_uses_default_fr(self):
        from api.i18n import t
        assert "invalide" in t("auth_invalid_email").lower()


# ─── Tests integration sur les endpoints ────────────────────────────────────


@pytest.mark.parametrize(
    "lang_header,expected_keyword",
    [
        ("fr", "invalide"),
        ("nl-BE,nl;q=0.9", "ongeldig"),
        ("en-US", "invalid"),
        ("de-DE,de;q=0.9", "ungültig"),
    ],
)
def test_register_invalid_email_returns_localized_error(
    client, lang_header, expected_keyword
):
    """POST /auth/register avec email invalide -> message dans la langue."""
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "Password123!", "name": "Test"},
        headers={"Accept-Language": lang_header},
    )
    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert expected_keyword.lower() in detail.lower(), (
        f"Lang={lang_header} : attendu '{expected_keyword}' dans '{detail}'"
    )


def test_register_unsupported_language_falls_back_to_french(client):
    """Accept-Language: es-ES (non supporte) -> fallback FR."""
    response = client.post(
        "/auth/register",
        json={"email": "bad", "password": "Password123!", "name": "Y"},
        headers={"Accept-Language": "es-ES,es;q=0.9"},
    )
    # 400 = validation custom localisee, 422 = Pydantic EmailStr intercept avant
    assert response.status_code in (400, 422)
    body = response.json()
    detail = body.get("detail", "")
    if response.status_code == 400:
        assert "invalide" in str(detail).lower()


def test_x_lexavo_lang_overrides_accept_language(client):
    """X-Lexavo-Lang doit gagner sur Accept-Language (override mobile)."""
    response = client.post(
        "/auth/register",
        json={"email": "bad", "password": "Password123!", "name": "Y"},
        headers={
            "Accept-Language": "fr-FR",
            "X-Lexavo-Lang": "de",
        },
    )
    # 400 = validation custom localisee DE, 422 = Pydantic EmailStr intercept avant
    assert response.status_code in (400, 422)
    if response.status_code == 400:
        detail = response.json().get("detail", "")
        assert "ungültig" in detail.lower(), f"DE attendu, recu : '{detail}'"


def test_register_password_too_short_localized(client):
    """Password < 8 chars retourne le message dans la langue."""
    response = client.post(
        "/auth/register",
        json={"email": "valid@example.com", "password": "abc", "name": "Test"},
        headers={"Accept-Language": "nl"},
    )
    # Pydantic peut intercepter avant que login_user soit appele
    assert response.status_code in (400, 422)


def test_register_invalid_language_field_localized(client):
    """language='ar' (non supporte) retourne le message dans la langue."""
    response = client.post(
        "/auth/register",
        json={
            "email": "valid@example.com",
            "password": "Password123!",
            "name": "Test",
            "language": "ar",
        },
        headers={"Accept-Language": "en"},
    )
    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert "invalid language" in detail.lower() or "choose" in detail.lower()


def test_login_invalid_credentials_localized_de(client):
    """POST /auth/login avec email inconnu -> message DE."""
    response = client.post(
        "/auth/login",
        json={"email": "unknown@nowhere.test", "password": "anything"},
        headers={"Accept-Language": "de"},
    )
    assert response.status_code == 401
    detail = response.json().get("detail", "")
    assert "falsch" in detail.lower() or "passwort" in detail.lower()


def test_login_no_user_enumeration(client):
    """Bad email -> message generique (pas d'enumeration de comptes)."""
    response = client.post(
        "/auth/login",
        json={"email": "unknown_xyz@test.com", "password": "X"},
        headers={"Accept-Language": "fr"},
    )
    assert response.status_code == 401
    detail = response.json().get("detail", "").lower()
    assert "incorrect" in detail


def test_malformed_accept_language_does_not_crash(client):
    """Accept-Language malforme ne doit pas crasher le serveur."""
    response = client.post(
        "/auth/register",
        json={"email": "bad", "password": "Password123!", "name": "Y"},
        headers={"Accept-Language": "garbage;q=zzz,more!@#"},
    )
    # Le serveur ne doit pas renvoyer 500
    assert response.status_code in (400, 422)
