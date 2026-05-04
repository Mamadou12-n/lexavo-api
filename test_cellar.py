"""Test CELLAR XHTML pour législation EU."""
import requests
from SPARQLWrapper import SPARQLWrapper, JSON as SJ

TARGET_CELEX = "32016R0679"  # RGPD

sparql = SPARQLWrapper("https://publications.europa.eu/webapi/rdf/sparql")
sparql.setReturnFormat(SJ)
sparql.setTimeout(30)

q = (
    "PREFIX cdm: <http://publications.europa.eu/ontology/cdm#> "
    "SELECT ?work ?celex WHERE { "
    "?work cdm:resource_legal_id_celex ?celex . "
    "FILTER(CONTAINS(STR(?celex), '" + TARGET_CELEX + "')) "
    "} LIMIT 5"
)
sparql.setQuery(q)
result = sparql.query().convert()
bindings = result.get("results", {}).get("bindings", [])
print(f"SPARQL results: {len(bindings)}")
for b in bindings:
    work_uri = b.get("work", {}).get("value", "")
    celex = b.get("celex", {}).get("value", "")
    print(f"  celex={celex} | work={work_uri}")
    if work_uri:
        uuid = work_uri.split("/")[-1]
        url = f"https://publications.europa.eu/resource/cellar/{uuid}"
        for accept in ["application/xhtml+xml", "application/pdf"]:
            try:
                r = requests.get(url, headers={"Accept": accept, "Accept-Language": "fr"},
                                 timeout=20, allow_redirects=True)
                ct = r.headers.get("Content-Type", "?")[:60]
                print(f"    [{accept}] {r.status_code} len={len(r.text)} ct={ct}")
            except Exception as e:
                print(f"    [{accept}] ERR: {e}")
