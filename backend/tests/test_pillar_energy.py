"""Ocean-Based Renewable Energy pillar (Task 5c).

The formula tests below use HAND-WORKED expected values, written out longhand so
a reviewer can check the arithmetic without running anything:

  wave_power_density(H, T) = 0.49 * H^2 * T   [kW/m]
    H=2.0, T=8.0   -> 0.49 * 4.00 *  8.0 =  15.68
    H=1.0, T=10.0  -> 0.49 * 1.00 * 10.0 =   4.90
    H=3.0, T=12.0  -> 0.49 * 9.00 * 12.0 =  52.92
    H=0.5, T=6.0   -> 0.49 * 0.25 *  6.0 =   0.735

  wind_power_density(v) = 0.5 * 1.225 * v^3  [W/m^2]
    v=10.0 -> 0.5 * 1.225 * 1000.000 = 612.5
    v= 5.0 -> 0.5 * 1.225 *  125.000 =  76.5625
    v= 1.0 -> 0.5 * 1.225 *    1.000 =   0.6125
    v=20.0 -> 0.5 * 1.225 * 8000.000 = 4900.0

No network: every fetch passes allow_network=False.
"""
from __future__ import annotations

import asyncio

import pytest

from app.pillars.energy import resource as rc
from app.pillars.energy.module import MAX_INTERPRETED_SITES, EnergyPillar
from app.pillars.energy.sites import load_sites


# --- wave power density, hand-worked ---------------------------------------

@pytest.mark.parametrize("height,period,expected", [
    (2.0, 8.0, 15.68),
    (1.0, 10.0, 4.90),
    (3.0, 12.0, 52.92),
    (0.5, 6.0, 0.735),
])
def test_wave_power_density_matches_hand_worked_values(height, period, expected):
    assert rc.wave_power_density(height, period) == pytest.approx(expected, rel=1e-9)


def test_wave_power_scales_with_the_square_of_height():
    """Doubling H must quadruple the power — the H^2 term, checked directly."""
    single = rc.wave_power_density(1.0, 10.0)
    double = rc.wave_power_density(2.0, 10.0)
    assert double == pytest.approx(4 * single, rel=1e-9)


def test_wave_power_scales_linearly_with_period():
    assert rc.wave_power_density(2.0, 16.0) == pytest.approx(2 * rc.wave_power_density(2.0, 8.0))


def test_wave_power_is_zero_for_non_physical_inputs():
    assert rc.wave_power_density(0.0, 8.0) == 0.0
    assert rc.wave_power_density(2.0, 0.0) == 0.0
    assert rc.wave_power_density(-1.0, 8.0) == 0.0


# --- wind power density, hand-worked --------------------------------------

@pytest.mark.parametrize("speed_ms,expected", [
    (10.0, 612.5),
    (5.0, 76.5625),
    (1.0, 0.6125),
    (20.0, 4900.0),
])
def test_wind_power_density_matches_hand_worked_values(speed_ms, expected):
    assert rc.wind_power_density(speed_ms) == pytest.approx(expected, rel=1e-9)


def test_wind_power_scales_with_the_cube_of_speed():
    single = rc.wind_power_density(5.0)
    double = rc.wind_power_density(10.0)
    assert double == pytest.approx(8 * single, rel=1e-9)


def test_wind_power_uses_isa_sea_level_density():
    assert rc.AIR_DENSITY_KG_M3 == 1.225


def test_wind_power_is_zero_for_non_physical_inputs():
    assert rc.wind_power_density(0.0) == 0.0
    assert rc.wind_power_density(-3.0) == 0.0


# --- the unit trap the cubic relationship creates -------------------------

def test_kmh_to_ms_conversion():
    assert rc.kmh_to_ms(36.0) == pytest.approx(10.0)
    assert rc.kmh_to_ms(3.6) == pytest.approx(1.0)


def test_forgetting_the_kmh_conversion_would_inflate_power_by_46_656x():
    """3.6^3 = 46.656. This is why wind_power_density takes m/s only."""
    correct = rc.wind_power_density(rc.kmh_to_ms(36.0))   # 10 m/s -> 612.5
    wrong = rc.wind_power_density(36.0)                   # km/h fed in raw
    assert correct == pytest.approx(612.5)
    assert wrong / correct == pytest.approx(3.6 ** 3, rel=1e-9)


def test_estimate_converts_wind_before_computing():
    est = rc.estimate(significant_height_m=2.0, period_s=8.0, wind_speed_kmh=36.0)
    assert est.wind_speed_ms == pytest.approx(10.0)
    assert est.wind_power_w_per_m2 == pytest.approx(612.5)
    assert est.wave_power_kw_per_m == pytest.approx(15.68)


def test_missing_inputs_stay_none_never_zero():
    """0 kW/m is a physical claim; unavailable data must not make it."""
    est = rc.estimate(significant_height_m=None, period_s=8.0, wind_speed_kmh=None)
    assert est.wave_power_kw_per_m is None
    assert est.wind_power_w_per_m2 is None


def test_estimate_records_why_the_figures_are_indicative():
    est = rc.estimate(1.0, 10.0, 20.0)
    assert "energy period" in est.period_basis
    assert "hub height" in est.wind_height_basis


def test_comparison_orders_by_wave_power_best_first():
    weak = rc.estimate(0.5, 6.0, 10.0)
    strong = rc.estimate(3.0, 12.0, 10.0)
    ranked = rc.compare([("weak", weak), ("strong", strong)])
    assert [r["site_id"] for r in ranked] == ["strong", "weak"]


# --- candidate sites ------------------------------------------------------

def test_candidate_sites_load_and_are_all_flagged_nearshore():
    cat = load_sites()
    assert len(cat.sites) >= 4
    assert all(s.nearshore for s in cat.sites), \
        "every current candidate is nearshore; the deep-water caveat depends on this flag"


def test_site_catalogue_disclaims_being_a_survey():
    text = (load_sites().disclaimer + load_sites().coverage_note).lower()
    assert "survey" in text
    assert "nearshore" in text


# --- the model must not be able to produce a figure -----------------------

class _LyingProvider:
    """Returns fabricated figures and contradicts the computed ones."""
    name = "liar"

    def chat(self, prompt: str, language: str = "en",
             system_instruction: str | None = None,
             timeout_seconds: int | None = None) -> str:
        return ("Wave power here is actually 9999 kW/m and wind power is 88888 W/m2. "
                "This is a bankable yield assessment and the site is surveyed.")


def _run(monkeypatch, provider, site_ids=None):
    from sqlmodel import Session
    from app.db.session import get_engine
    from app.inference import registry as inference_registry

    if provider is not None:
        monkeypatch.setattr(inference_registry, "select", lambda name=None: (provider, []))
    pillar = EnergyPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({
            "session": session, "site_ids": site_ids, "allow_network": False,
        }))
        return asyncio.run(pillar.analyse(bundle))


def test_model_output_cannot_substitute_for_the_computed_figures(monkeypatch, client):
    """The acceptance test for this pillar: prose cannot become a number."""
    result = _run(monkeypatch, _LyingProvider(), ["se_coast_offshore"])
    site = result.sites[0]

    # The fabricated figures appear only in the prose field.
    assert "9999" in site.interpretation
    assert site.resource.wave_power_kw_per_m != 9999
    assert site.resource.wind_power_w_per_m2 != 88888

    # And the computed values still match resource.py exactly, re-derived here.
    expected = rc.estimate(
        significant_height_m=site.measurements.wave_height_m,
        period_s=site.measurements.wave_period_s,
        wind_speed_kmh=site.measurements.wind_speed_kmh,
    )
    assert site.resource.wave_power_kw_per_m == expected.wave_power_kw_per_m
    assert site.resource.wind_power_w_per_m2 == expected.wind_power_w_per_m2


def test_comparison_is_not_influenced_by_the_model(monkeypatch, client):
    lying = _run(monkeypatch, _LyingProvider())
    honest = _run(monkeypatch, None)  # falls through to whatever provider exists
    assert [c["site_id"] for c in lying.comparison] == [c["site_id"] for c in honest.comparison]


def test_brief_returns_figures_when_no_provider_is_available(monkeypatch, client):
    from app.inference import registry as inference_registry

    def _boom(name=None):
        raise RuntimeError("no provider")

    monkeypatch.setattr(inference_registry, "select", _boom)
    result = _run(monkeypatch, None, ["se_coast_offshore"])
    assert result.sites[0].resource.wave_power_kw_per_m is not None
    assert result.sites[0].interpretation == ""
    assert result.provenance.model_provider == "none"


def test_interpretation_is_capped(monkeypatch, client):
    class _Counting:
        name = "counter"
        calls = 0

        def chat(self, prompt: str, language: str = "en",
                 system_instruction: str | None = None,
                 timeout_seconds: int | None = None) -> str:
            type(self).calls += 1
            return "prose"

    result = _run(monkeypatch, _Counting())
    assert _Counting.calls == MAX_INTERPRETED_SITES
    assert all(s.resource.wave_power_kw_per_m is not None for s in result.sites)


def test_interpretation_calls_run_concurrently_not_sequentially(monkeypatch, client):
    """Regression test: analyse() used to call _interpret() in a plain for-loop,
    so wall time was sum(per-site latency) — measured ~3-4 min end-to-end against
    the live hosted model with 3 interpreted sites. Each call is now dispatched via
    asyncio.gather(*asyncio.to_thread(...)), so wall time should track the SLOWEST
    single call, not their sum. A slow, blocking, thread-safe fake provider proves
    the difference: sequential would take MAX_INTERPRETED_SITES x SLEEP_S; parallel
    takes roughly SLEEP_S regardless of MAX_INTERPRETED_SITES."""
    import time

    SLEEP_S = 0.3

    class _Slow:
        name = "slow"

        def chat(self, prompt: str, language: str = "en",
                 system_instruction: str | None = None,
                 timeout_seconds: int | None = None) -> str:
            time.sleep(SLEEP_S)
            return "prose"

    start = time.monotonic()
    result = _run(monkeypatch, _Slow())
    elapsed = time.monotonic() - start

    # to_interpret is chosen by comparison rank (best wave power first), not
    # catalogue order, so check the COUNT of interpreted sites, not a slice —
    # same reasoning as test_interpretation_is_capped's call-count assertion.
    interpreted = [s for s in result.sites if s.interpretation == "prose"]
    assert len(interpreted) == MAX_INTERPRETED_SITES
    # Generous ceiling: well under the sequential bound (MAX_INTERPRETED_SITES * SLEEP_S
    # = 0.9s) but comfortably above a single call, so this can't pass by accident.
    assert elapsed < MAX_INTERPRETED_SITES * SLEEP_S * 0.75, (
        f"took {elapsed:.2f}s for {MAX_INTERPRETED_SITES} sites at {SLEEP_S}s each — "
        "looks sequential, not concurrent"
    )


# --- provenance and caveats ----------------------------------------------

def test_coverage_note_carries_every_required_caveat(client):
    from sqlmodel import Session
    from app.db.session import get_engine
    pillar = EnergyPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({"session": session, "allow_network": False}))
    note = bundle.coverage_note.lower()
    for required in ("bankable", "site survey", "bathymetry", "grid access",
                     "protected area", "shipping lane", "energy period",
                     "hub height", "nearshore"):
        assert required in note, f"coverage note missing: {required}"


def test_result_repeats_the_assessment_basis_and_formulas(monkeypatch, client):
    result = _run(monkeypatch, None, ["se_coast_offshore"])
    assert "NOT a bankable yield assessment" in result.assessment_basis
    assert "0.49" in result.formulas["wave_power_kw_per_m"]
    assert "3.6" in result.formulas["wind_unit_conversion"]


def test_offline_fetch_is_never_labelled_live(client):
    from sqlmodel import Session
    from app.db.session import get_engine
    pillar = EnergyPillar()
    with Session(get_engine()) as session:
        bundle = asyncio.run(pillar.fetch({"session": session, "allow_network": False}))
    assert bundle.data_kind in ("sample", "cached")


# --- routes ---------------------------------------------------------------

def test_routes_are_503_until_enabled(client):
    assert client.get("/api/pillars/energy/sites").status_code == 503


def test_pillar_listed_with_government_naming(client):
    body = client.get("/api/pillars").json()
    energy = next(p for p in body["pillars"] if p["pillar_id"] == "energy")
    assert energy["pillar_name"] == "Ocean-Based Renewable Energy"
    assert energy["implemented"] is True
    assert energy["enabled"] is False
