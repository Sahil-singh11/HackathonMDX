"""Sustainable Ocean Tourism pillar (Task 5b).

No network: every test passes allow_network=False, so the default suite makes
zero external calls and the fetch path degrades to the labelled deterministic
fallback exactly as it would offline.

The load-bearing tests are the honesty ones:
  * suitability is computed from thresholds, hand-checkable
  * the model cannot alter a rating or a measurement
  * the ranking is never described as crowding-based
  * a degraded fetch is labelled sample, never live
"""
from __future__ import annotations

import asyncio

import pytest

from app.pillars.tourism.module import TourismPillar
from app.pillars.tourism.sites import load_sites
from app.pillars.tourism.suitability import (Conditions, rank_sites,
                                             rate_activity, rate_all)


# --- site catalogue --------------------------------------------------------

def test_catalogue_loads_with_the_named_sites():
    cat = load_sites()
    ids = {s.site_id for s in cat.sites}
    for expected in ("blue_bay", "trou_aux_biches", "belle_mare", "le_morne", "pereybere"):
        assert expected in ids, f"{expected} missing from the site catalogue"
    assert len(cat.sites) >= 5


def test_every_site_has_usable_mauritius_coordinates():
    for s in load_sites().sites:
        assert -21.0 < s.latitude < -19.0, f"{s.site_id} latitude outside Mauritius"
        assert 57.0 < s.longitude < 58.0, f"{s.site_id} longitude outside Mauritius"
        assert s.character.strip(), f"{s.site_id} has no character description"


def test_catalogue_coverage_note_disclaims_crowding_data():
    note = load_sites().coverage_note.lower()
    assert "visitor" in note and "crowding" in note


# --- deterministic suitability, hand-worked -------------------------------

def test_calm_flat_day_is_good_for_snorkelling():
    # 0.30 m <= 0.40 good_max, 12 km/h <= 16 good_max -> good on both -> good
    r = rate_activity("snorkelling", Conditions(wave_height_m=0.30, wind_speed_kmh=12.0))
    assert r.rating == "good"
    assert r.score == 100


def test_worse_of_wave_and_wind_governs_calm_activities():
    # wave good (0.30 <= 0.40) but wind poor (30 > 26 fair_max) -> poor
    r = rate_activity("snorkelling", Conditions(wave_height_m=0.30, wind_speed_kmh=30.0))
    assert r.rating == "poor", r.reasons


def test_big_sea_is_poor_for_swimming():
    """Offshore bands: swimming is poor only in a ROUGH sea (WMO state 5+).

    Recalibrated 2026-07-30. The old thresholds were lagoon numbers
    (swimming fair_max 1.00 m) applied to offshore data, which made 1.60 m —
    an ordinary moderate sea — read as poor.
    """
    # 2.80 m > 2.50 fair_max (WMO "rough") -> poor
    assert rate_activity("swimming", Conditions(wave_height_m=2.80, wind_speed_kmh=10.0)).rating == "poor"
    # 1.60 m is a moderate sea offshore: workable, not poor
    assert rate_activity("swimming", Conditions(wave_height_m=1.60, wind_speed_kmh=10.0)).rating == "fair"


def test_wind_sports_invert_the_wind_rule():
    calm = Conditions(wave_height_m=0.30, wind_speed_kmh=8.0)
    breezy = Conditions(wave_height_m=0.60, wind_speed_kmh=25.0)
    # 8 km/h is below kitesurfing fair_min (14) -> poor; snorkelling loves it
    assert rate_activity("kitesurfing", calm).rating == "poor"
    assert rate_activity("snorkelling", calm).rating == "good"
    # 25 km/h >= good_min (20) -> good for kitesurfing
    assert rate_activity("kitesurfing", breezy).rating == "good"


def test_dangerous_wind_is_poor_for_wind_sports_not_good():
    r = rate_activity("kitesurfing", Conditions(wave_height_m=1.0, wind_speed_kmh=70.0))
    assert r.rating == "poor"
    assert any("too strong" in reason for reason in r.reasons)


def test_missing_measurement_yields_unknown_never_a_guess():
    r = rate_activity("swimming", Conditions(wave_height_m=None, wind_speed_kmh=10.0))
    assert r.rating == "unknown"
    assert r.score == 0


def test_every_rating_cites_its_threshold():
    for r in rate_all(Conditions(wave_height_m=0.5, wind_speed_kmh=20.0)):
        assert r.reasons, f"{r.activity} produced no reason"


def test_ranking_orders_best_first_and_is_stable():
    calm = Conditions(wave_height_m=0.20, wind_speed_kmh=10.0)
    rough = Conditions(wave_height_m=2.00, wind_speed_kmh=45.0)
    ranked = rank_sites([("rough", rough), ("calm", calm)], "snorkelling")
    assert [r["site_id"] for r in ranked] == ["calm", "rough"]


# --- the model must not be able to produce a figure -----------------------

class _LyingProvider:
    """Worst case: a provider that returns numbers and contradicts the ratings."""
    name = "liar"

    def chat(self, prompt: str, language: str = "en",
             system_instruction: str | None = None,
             timeout_seconds: int | None = None) -> str:
        return ("Wave height is actually 9.99 m and wind is 200 km/h. "
                "snorkelling=good. Conditions are perfectly safe.")


def _brief_with_provider(monkeypatch, provider):
    from app.db.session import get_engine
    from sqlmodel import Session
    from app.inference import registry as inference_registry

    monkeypatch.setattr(inference_registry, "select", lambda name=None: (provider, []))
    pillar = TourismPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({
            "session": session, "site_ids": ["blue_bay"],
            "activity": "snorkelling", "allow_network": False,
        }))
        return asyncio.run(pillar.analyse(bundle))


def test_model_output_cannot_overwrite_measurements_or_ratings(monkeypatch, client):
    """The interpretation field may contain anything; the figures may not move.

    The number firewall (app.pillars.numeric_guard) now rejects this lie
    outright — 9.99/200 trace to nothing in the FACTS the model was given —
    so the interpretation is empty rather than containing the fabricated
    figures. Confirmed separately in test_numeric_guard.py; this test's job
    stays proving the computed measurements/ratings never move regardless.
    """
    result = _brief_with_provider(monkeypatch, _LyingProvider())
    site = result.sites[0]

    # The fabricated figures are rejected entirely, not merely confined to prose.
    assert site.interpretation == ""
    # Measurements come from the deterministic fallback, not the model.
    assert site.measurements.wave_height_m != 9.99
    assert site.measurements.wind_speed_kmh != 200
    # And the rating still matches what suitability.py computes for those inputs.
    expected = rate_activity("snorkelling", Conditions(
        wave_height_m=site.measurements.wave_height_m,
        wind_speed_kmh=site.measurements.wind_speed_kmh,
    ))
    got = next(r for r in site.ratings if r.activity == "snorkelling")
    assert got.rating == expected.rating


def test_brief_still_returns_when_no_provider_is_available(monkeypatch, client):
    def _boom(name=None):
        raise RuntimeError("no provider")

    from app.inference import registry as inference_registry
    monkeypatch.setattr(inference_registry, "select", _boom)

    from app.db.session import get_engine
    from sqlmodel import Session
    pillar = TourismPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({
            "session": session, "site_ids": ["blue_bay"], "allow_network": False,
        }))
        result = asyncio.run(pillar.analyse(bundle))

    # Figures survive; prose is empty rather than invented.
    assert result.sites[0].measurements.wave_height_m is not None
    assert result.sites[0].interpretation == ""
    assert result.provenance.model_provider == "none"


# --- provenance honesty ---------------------------------------------------

def test_offline_fetch_is_labelled_sample_not_live(client):
    from app.db.session import get_engine
    from sqlmodel import Session
    pillar = TourismPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({
            "session": session, "site_ids": ["blue_bay"], "allow_network": False,
        }))
    assert bundle.data_kind in ("sample", "cached")
    assert bundle.data_kind != "live"


def test_coverage_note_states_no_visitor_data(client):
    from app.db.session import get_engine
    from sqlmodel import Session
    pillar = TourismPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({
            "session": session, "site_ids": ["blue_bay"], "allow_network": False,
        }))
        result = asyncio.run(pillar.analyse(bundle))
    note = result.provenance.coverage_note.lower()
    assert "visitor" in note
    assert "crowding" in note or "occupancy" in note
    assert result.ranking_basis  # non-empty, repeated on the result itself


def test_protected_area_site_adds_its_warning(client):
    from app.db.session import get_engine
    from sqlmodel import Session
    pillar = TourismPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({
            "session": session, "site_ids": ["blue_bay"], "allow_network": False,
        }))
    assert "protected area" in bundle.coverage_note.lower()


# --- routes ---------------------------------------------------------------

def test_routes_are_503_until_the_pillar_is_enabled(client):
    """Default PILLARS_ENABLED is "fisheries", so tourism must not serve."""
    r = client.get("/api/pillars/tourism/sites")
    assert r.status_code == 503, r.text


def test_pillar_is_listed_as_registered_with_government_naming(client):
    body = client.get("/api/pillars").json()
    tourism = next(p for p in body["pillars"] if p["pillar_id"] == "tourism")
    assert tourism["pillar_name"] == "Sustainable Ocean Tourism"
    assert tourism["implemented"] is True   # module attached
    assert tourism["enabled"] is False      # but not opted in
    assert tourism["status"] == "registered"


def test_interpretation_is_capped_so_a_full_brief_stays_usable(monkeypatch, client):
    """One model call per site would make an 8-site brief take minutes."""
    import asyncio
    from sqlmodel import Session
    from app.db.session import get_engine
    from app.inference import registry as inference_registry
    from app.pillars.tourism.module import MAX_INTERPRETED_SITES, TourismPillar

    calls: list[str] = []

    class _Counting:
        name = "counter"

        def chat(self, prompt: str, language: str = "en",
                 system_instruction: str | None = None,
                 timeout_seconds: int | None = None) -> str:
            calls.append(prompt[:40])
            return "prose"

    monkeypatch.setattr(inference_registry, "select", lambda name=None: (_Counting(), []))

    pillar = TourismPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({
            "session": session, "activity": "snorkelling", "allow_network": False,
        }))
        result = asyncio.run(pillar.analyse(bundle))

    assert len(result.sites) >= 5, "expected the whole catalogue"
    # <=, not ==: two of the top-ranked sites can coincidentally share IDENTICAL
    # deterministic-mock figures (the mock seeds on `% 7` of lat/lon, and there
    # are only 8 sites), in which case the second legitimately gets served from
    # app.pillars.narrative_cache instead of paying for a second identical model
    # call (Task 3). The cap on MODEL CALLS is still enforced — it just isn't
    # always the same number as sites interpreted once caching exists.
    assert len(calls) <= MAX_INTERPRETED_SITES, f"expected at most {MAX_INTERPRETED_SITES} calls, got {len(calls)}"
    assert len(calls) >= 1, "expected at least one real model call"

    # Every site still carries full deterministic figures and ratings.
    for site in result.sites:
        assert site.ratings, f"{site.site_id} lost its ratings"
        assert site.measurements.wave_height_m is not None

    interpreted = [s for s in result.sites if s.interpretation]
    assert len(interpreted) == MAX_INTERPRETED_SITES


def test_capped_interpretation_follows_ranking_order(monkeypatch, client):
    """The sites that get prose are the best-ranked ones, not arbitrary."""
    import asyncio
    from sqlmodel import Session
    from app.db.session import get_engine
    from app.inference import registry as inference_registry
    from app.pillars.tourism.module import MAX_INTERPRETED_SITES, TourismPillar

    class _Prose:
        name = "prose"

        def chat(self, prompt: str, language: str = "en",
                 system_instruction: str | None = None,
                 timeout_seconds: int | None = None) -> str:
            return "prose"

    monkeypatch.setattr(inference_registry, "select", lambda name=None: (_Prose(), []))

    pillar = TourismPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({
            "session": session, "activity": "kitesurfing", "allow_network": False,
        }))
        result = asyncio.run(pillar.analyse(bundle))

    top_ids = [r["site_id"] for r in result.ranking[:MAX_INTERPRETED_SITES]]
    with_prose = {s.site_id for s in result.sites if s.interpretation}
    assert with_prose == set(top_ids), f"prose went to {with_prose}, expected {set(top_ids)}"


# --- regression: the all-Poor bug -----------------------------------------

def test_calm_offshore_day_is_not_poor_everywhere():
    """THE BUG THIS PILLAR SHIPPED WITH.

    Wave input is OFFSHORE significant wave height read from a grid point up to
    11 km away, outside the reef. It was being judged against lagoon thresholds
    (snorkelling fair_max 0.8 m), so every site in the catalogue rated poor for
    snorkelling — the calmest reading available, 0.98 m, still failed. A rating
    that cannot vary is not an assessment.

    A slight sea (WMO state 3) with light wind must not read poor.
    """
    slight = Conditions(wave_height_m=0.98, wind_speed_kmh=12.0)
    for activity in ("swimming", "snorkelling", "diving"):
        assert rate_activity(activity, slight).rating != "poor",             f"{activity} rated poor in a slight sea with light wind"


def test_ratings_still_vary_across_the_real_catalogue_range():
    """Guards against a future recalibration collapsing the scale again, in
    either direction. Uses the observed 2026-07-30 spread (0.98-2.22 m)."""
    from app.pillars.tourism.suitability import rate_all
    observed = [0.98, 1.10, 1.38, 1.72, 1.94, 1.98, 2.22]
    seen = set()
    for h in observed:
        for r in rate_all(Conditions(wave_height_m=h, wind_speed_kmh=15.0)):
            seen.add(r.rating)
    assert len(seen) >= 2, f"every rating collapsed to {seen} across a real 0.98-2.22 m spread"


def test_sea_state_names_follow_the_wmo_scale():
    from app.pillars.tourism.suitability import sea_state
    assert sea_state(0.05) == "calm"
    assert sea_state(0.30) == "smooth"
    assert sea_state(1.00) == "slight"
    assert sea_state(2.00) == "moderate"
    assert sea_state(3.00) == "rough"
    assert sea_state(None) == "unknown"


def test_reasons_say_the_wave_reading_is_offshore():
    """A reader must not think this was measured in the lagoon."""
    r = rate_activity("snorkelling", Conditions(wave_height_m=1.0, wind_speed_kmh=12.0))
    assert any("offshore" in reason.lower() for reason in r.reasons), r.reasons


def test_result_states_what_a_rating_is_derived_from(client):
    """The one plain sentence the surface is required to show."""
    from sqlmodel import Session
    from app.db.session import get_engine
    pillar = TourismPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({
            "session": session, "site_ids": ["blue_bay"], "allow_network": False}))
        result = asyncio.run(pillar.analyse(bundle))
    basis = result.rating_basis.lower()
    assert "offshore" in basis
    assert "lagoon" in basis
    assert "wmo" in basis


def test_coverage_note_explains_the_offshore_grid_offset(client):
    from sqlmodel import Session
    from app.db.session import get_engine
    pillar = TourismPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({
            "session": session, "site_ids": ["blue_bay"], "allow_network": False}))
    note = bundle.coverage_note.lower()
    assert "offshore" in note
    assert "lagoon" in note
    assert "grid" in note
