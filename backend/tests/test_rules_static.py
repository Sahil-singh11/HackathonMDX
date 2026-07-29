"""GET /api/rules/static — the offline assistant's freshness/source endpoint.

Reads local JSON only; no network, so it is safe in the default suite.
"""


def test_returns_all_three_datasets(client):
    r = client.get("/api/rules/static")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"rules", "catalogue", "sources", "rules_version"}
    assert body["rules"]["rules"], "rule list must not be empty"
    assert body["catalogue"]["species"], "species catalogue must not be empty"
    assert body["sources"]["sources"], "source register must not be empty"


def test_rules_version_matches_the_rules_payload(client):
    """The assistant compares its bundled rules_version against this field, so a
    mismatch here would silently disable stale-bundle detection."""
    body = client.get("/api/rules/static").json()
    assert body["rules_version"] == body["rules"]["rules_version"]


def test_rules_are_served_verbatim_with_their_attribution(client):
    """The UI renders notes and scope_notes verbatim (CLAUDE.md honesty rule 4),
    so the endpoint must not strip or summarise them."""
    rules = client.get("/api/rules/static").json()["rules"]["rules"]
    octopus_min = next(r for r in rules if r["rule_id"] == "R-OCT-MINSIZE-2016")
    assert octopus_min["measurement"] == "mantle_length_cm"
    assert octopus_min["minimum_length_cm"] == 7
    assert octopus_min["verification_status"] == "provisional"
    assert "scope_note" in octopus_min and octopus_min["scope_note"]
    assert "mantle" in octopus_min["note"].lower()


def test_no_api_key_material_in_response(client):
    r = client.get("/api/rules/static")
    assert "AIza" not in r.text
