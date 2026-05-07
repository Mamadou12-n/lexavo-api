"""Simulations realistes Lexavo - bypass Claude API (mock=True direct)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("LEXAVO_JWT_SECRET", "test-simulation-secret-key-very-long")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-mock-key")
os.environ.setdefault("RATELIMIT_ENABLED", "0")

from fastapi.testclient import TestClient
from api.main import app
from api.database import init_db

init_db()
client = TestClient(app)
PASSED = 0
FAILED = 0
FAILS = []

def check(label, cond, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print("  [PASS] " + label + (" -- " + detail if detail else ""))
    else:
        FAILED += 1
        FAILS.append(label + (" -- " + detail if detail else ""))
        print("  [FAIL] " + label + (" -- " + detail if detail else ""))

def signup(email, password="Password123", name="Test", lang="fr"):
    r = client.post("/auth/register", json={"email": email, "password": password, "name": name, "language": lang})
    if r.status_code not in (200, 201):
        r = client.post("/auth/login", json={"email": email, "password": password})
    j = r.json()
    token = j.get("token") or j.get("access_token")
    assert token, "Pas de token : " + str(r.status_code)
    return {"Authorization": "Bearer " + token}

def section(title):
    print("\n" + "="*70)
    print("  " + title)
    print("="*70)

def persona_1_marie():
    section("PERSONA 1 - Marie, locataire bruxelloise")
    h = signup("marie.dupont+sim1@lexavo.be", name="Marie")
    check("Signup + login Marie", "Authorization" in h)
    r = client.get("/billing/quota/status", headers=h)
    check("GET /billing/quota/status 200", r.status_code == 200, "status=" + str(r.status_code))
    data = r.json()
    check("Quota warning_level=none", data.get("warning_level") == "none")
    check("Quota fields complets", all(k in data for k in ("plan", "warning_level", "next_reset")))
    try:
        from api.features.diagnostic import generate_diagnostic
        result = generate_diagnostic(answers=[
            {"question_id": 1, "answer": "Logement/Bail"},
            {"question_id": 2, "answer": "Litige en cours"},
            {"question_id": 3, "answer": "1 a 6 mois"},
        ], mock=True)
        check("Diagnostic mock dict", isinstance(result, dict))
        check("Diagnostic branch immobilier", result.get("branch_detected") == "droit_immobilier")
    except Exception as e:
        check("Diagnostic mock", False, str(e)[:80])
    try:
        from api.features.legal_response import generate_response
        resp = generate_response(received_text="Madame, vous etes redevable de 1234 EUR. Huissier Dupont. " * 2, user_context="Locataire", mock=True)
        check("LegalResponse mock", "response_letter" in resp or "response_text" in resp)
        check("LegalResponse disclaimer", "disclaimer" in resp)
    except Exception as e:
        check("LegalResponse mock", False, str(e)[:80])
    me = client.get("/auth/me", headers=h)
    check("/auth/me retourne user", me.status_code == 200)

def persona_2_jean():
    section("PERSONA 2 - Jean, electricien independant")
    h = signup("jean.martin+sim2@lexavo.be", name="Jean")
    check("Signup + login Jean", "Authorization" in h)
    try:
        from api.features.shield import analyze_contract_text as analyze_contract
        contract = "CONTRAT entre ALPHA SRL et Jean. Article 1: prix 12500 EUR. Article 2: penalites 5%/jour. " * 5
        res = analyze_contract(text=contract, contract_type="sous_traitance", region="bruxelles", mock=True)
        check("Shield mock dict", isinstance(res, dict))
        check("Shield verdict valide", res.get("verdict") in ("vert", "orange", "rouge", "green", "yellow", "red"), "verdict=" + str(res.get("verdict")))
        check("Shield score numerique", isinstance(res.get("score"), (int, float)))
    except Exception as e:
        check("Shield mock", False, str(e)[:80])
    try:
        from api.features.decode import decode_document
        res = decode_document(text="SPF FINANCES Avis exercice 2025. Cotisation 8456 EUR, solde 5456 EUR du 30 avril 2026.", mock=True)
        check("Decode plain_language", "plain_language" in res)
        check("Decode key_points liste", isinstance(res.get("key_points"), list))
    except Exception as e:
        check("Decode mock", False, str(e)[:80])
    try:
        from api.features.fiscal import ask_fiscal
        res = ask_fiscal(question="Frais voiture deductibles ?", mock=True)
        check("Fiscal answer", "answer" in res)
        check("Fiscal disclaimer", "disclaimer" in res)
    except Exception as e:
        check("Fiscal mock", False, str(e)[:80])

def persona_3_sophie():
    section("PERSONA 3 - Sophie, etudiante droit")
    h = signup("sophie.lefebvre+sim3@lexavo.be", name="Sophie")
    check("Signup + login Sophie", "Authorization" in h)
    try:
        from api.features.heritage import generate_heritage_guide
        res = generate_heritage_guide(relationship="conjoint_survivant", region="bruxelles", mock=True)
        check("Heritage mock", isinstance(res, dict))
    except Exception as e:
        check("Heritage mock", False, str(e)[:80])

def paywall_simulation():
    section("PAYWALL PROGRESSIF - 0% -> 50% -> 80% -> 100%")
    h = signup("paywall+sim4@lexavo.be", name="Paywall")
    me = client.get("/auth/me", headers=h)
    user_id = me.json().get("id")
    check("User ID", user_id is not None)
    from api.database import _get_conn, _execute, USE_PG
    conn = _get_conn()
    PH = "%s" if USE_PG else "?"
    cases = [(0, "none"), (24, "none"), (25, "soft"), (39, "soft"), (40, "hard"), (49, "hard"), (50, "blocked"), (60, "blocked")]
    for used, expected in cases:
        try:
            _execute(conn, "UPDATE subscriptions SET questions_used = " + PH + " WHERE user_id = " + PH, (used, user_id))
            if hasattr(conn, "commit"):
                conn.commit()
        except Exception as e:
            check("Paywall " + str(used) + " DB", False, str(e)[:60])
            continue
        r = client.get("/billing/quota/status", headers=h)
        real = r.json().get("warning_level", "?")
        check("Paywall " + str(used) + "/50 -> " + expected, real == expected, "real=" + real)

def rgpd_simulation():
    section("RGPD - Art.17 + Art.20")
    h = signup("rgpd+sim5@lexavo.be", name="RGPD")
    check("Signup OK", "Authorization" in h)
    r = client.get("/account/export", headers=h)
    check("GET /account/export 200", r.status_code == 200, "status=" + str(r.status_code))
    if r.status_code == 200:
        d = r.json()
        check("Export donnees", any(k in d for k in ("user", "profile", "email", "id")))
    r = client.delete("/account", headers=h)
    check("DELETE /account 204", r.status_code == 204, "status=" + str(r.status_code))
    r = client.get("/auth/me", headers=h)
    check("Apres delete 401", r.status_code == 401, "status=" + str(r.status_code))

def security_simulation():
    section("SECURITE - SSRF lms + lockout")
    signup("lockout+sim7@lexavo.be", name="Lock")  # Creer user AVANT lockout pour eviter 429 sur signup
    h = signup("sec+sim6@lexavo.be", name="Sec")
    ssrf = ["http://169.254.169.254/", "https://169.254.169.254/", "http://localhost:5432/", "https://127.0.0.1/", "https://10.0.0.1/"]
    blocked = 0
    for url in ssrf:
        r = client.post("/student/lms/connect", headers=h, json={"site_url": url, "username": "x", "password": "x"})
        if r.status_code in (400, 422):
            blocked += 1
    check("SSRF " + str(blocked) + "/" + str(len(ssrf)) + " bloquees", blocked >= 4)
    locked_at = None
    for i in range(7):
        r = client.post("/auth/login", json={"email": "lockout+sim7@lexavo.be", "password": "Wrong" + str(i)})
        if r.status_code in (423, 429) and locked_at is None:
            locked_at = i + 1
            break
    check("Lockout apres 4-7 fails", locked_at is not None and 4 <= locked_at <= 7, "locked_at=" + str(locked_at))

def headers_simulation():
    section("SECURITE - Headers HTTP")
    r = client.get("/health")
    check("X-Frame-Options DENY", r.headers.get("X-Frame-Options") == "DENY")
    check("HSTS present", "Strict-Transport-Security" in r.headers)
    check("Referrer-Policy", "Referrer-Policy" in r.headers)
    check("Permissions-Policy", "Permissions-Policy" in r.headers)
    check("CSP", "Content-Security-Policy" in r.headers)

def bola_simulation():
    section("BOLA - Isolation conversations")
    h_a = signup("alice+sim8@lexavo.be", name="Alice")
    h_b = signup("bob+sim9@lexavo.be", name="Bob")
    r = client.post("/conversations", headers=h_a, json={"title": "Conv Alice"})
    check("Alice cree conv", r.status_code in (200, 201), "status=" + str(r.status_code))
    conv_id = r.json().get("id") if r.status_code in (200, 201) else None
    if conv_id:
        r = client.get("/conversations/" + str(conv_id), headers=h_b)
        check("BOLA Bob bloque", r.status_code in (403, 404), "status=" + str(r.status_code))

def main():
    persona_1_marie()
    persona_2_jean()
    persona_3_sophie()
    paywall_simulation()
    rgpd_simulation()
    security_simulation()
    headers_simulation()
    bola_simulation()
    section("RECAP FINAL")
    total = PASSED + FAILED
    pct = 100 * PASSED // max(total, 1)
    print("\n  TOTAL : " + str(PASSED) + "/" + str(total) + " tests passes (" + str(pct) + "%)")
    print("  Echecs : " + str(FAILED))
    if FAILS:
        print("\n  Liste des echecs :")
        for f in FAILS:
            print("    - " + f)

if __name__ == "__main__":
    main()
