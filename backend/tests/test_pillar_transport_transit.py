"""Transit-window assessment — the deterministic core of the repointed transport pillar.

These thresholds are the whole honesty basis of the approach brief: the page
prints them and claims every band comes from them, so they are worth pinning
against hand-worked values rather than trusting.

The pillar previously led with SYNTHETIC AIS vessels. It now leads with live
Open-Meteo sea state, and this module is what turns that reading into guidance —
so a silent change here would silently change what the app tells a fisher.
"""
from __future__ import annotations

from app.pillars.transport import transit


def _marine(wave=None, period=None, swell=None, swell_period=None, sst=None):
    return {
        "wave_height_m": wave, "wave_period_s": period,
        "swell_height_m": swell, "swell_period_s": swell_period,
        "sea_surface_temperature_c": sst,
    }


def _wind(speed=None, gusts=None):
    return {"wind_speed_kmh": speed, "wind_gusts_kmh": gusts}


def _band_for(window, craft_substring):
    return next(c for c in window.crafts if craft_substring in c.craft)


# --------------------------------------------------------------------- bands

def test_calm_sea_is_good_for_both_craft_classes():
    w = transit.assess(_marine(wave=0.8), _wind(speed=15.0, gusts=20.0))
    assert _band_for(w, "Small open craft").overall == "good"
    assert _band_for(w, "Commercial vessel").overall == "good"


def test_the_two_craft_classes_are_judged_on_DIFFERENT_thresholds():
    """The point of having two classes at all.

    1.8 m is past the small-craft 'good' ceiling (1.25 m) but well inside the
    commercial one (2.5 m). If both ever return the same band for this reading,
    the class distinction has stopped meaning anything.
    """
    w = transit.assess(_marine(wave=1.8), _wind(speed=20.0, gusts=25.0))
    assert _band_for(w, "Small open craft").overall == "moderate"
    assert _band_for(w, "Commercial vessel").overall == "good"


def test_wave_height_above_the_moderate_ceiling_is_poor():
    w = transit.assess(_marine(wave=2.4), _wind(speed=10.0, gusts=12.0))
    assert _band_for(w, "Small open craft").overall == "poor"


def test_a_calm_sea_under_a_gale_is_not_a_good_window():
    """Weakest link. Wind must be able to veto an otherwise fine sea state."""
    w = transit.assess(_marine(wave=0.5), _wind(speed=60.0, gusts=80.0))
    small = _band_for(w, "Small open craft")
    assert small.overall == "poor"
    assert "wind" in small.limiting_factor


def test_gusts_govern_over_mean_wind_when_both_are_known():
    """A boat is knocked down by the gust, not by the ten-minute mean.

    Mean 25 km/h is inside the small-craft 'good' ceiling (28); a 40 km/h gust
    is 'moderate' (<= 46). The gust must be the one that decides.
    """
    w = transit.assess(_marine(wave=0.5), _wind(speed=25.0, gusts=40.0))
    small = _band_for(w, "Small open craft")
    assert small.wind_band == "moderate"
    assert small.overall == "moderate"


def test_a_known_bad_reading_still_reports_poor_when_the_other_is_missing():
    """`poor` outranks `unknown`: if the sea is known to be poor, saying so is
    both safe and more useful than refusing to answer."""
    w = transit.assess(_marine(wave=3.5), _wind(speed=None, gusts=None))
    assert _band_for(w, "Small open craft").overall == "poor"


def test_boundary_values_are_inclusive_of_the_better_band():
    """Exactly at a threshold is the SAFER band, not the worse one — the
    thresholds_note printed on the page says '<=', so this pins that wording."""
    w = transit.assess(_marine(wave=transit.SMALL_CRAFT_WAVE_M["good"]), _wind(speed=1.0, gusts=1.0))
    assert _band_for(w, "Small open craft").wave_band == "good"


# ------------------------------------------------------- missing data honesty

def test_a_missing_reading_is_unknown_and_never_treated_as_calm():
    """The failure this guards: defaulting a missing wave height to 0 would
    report a dangerous sea as 'good'."""
    w = transit.assess(_marine(wave=None), _wind(speed=10.0, gusts=12.0))
    small = _band_for(w, "Small open craft")
    assert small.wave_band == "unknown"
    assert small.overall == "unknown"
    assert w.incomplete is True


def test_a_complete_reading_is_not_flagged_incomplete():
    w = transit.assess(_marine(wave=1.0), _wind(speed=10.0, gusts=12.0))
    assert w.incomplete is False


def test_mean_wind_is_used_when_gusts_are_absent():
    w = transit.assess(_marine(wave=0.5), _wind(speed=55.0, gusts=None))
    small = _band_for(w, "Small open craft")
    assert small.wind_band == "poor"
    # The limiting-factor text must not claim gusts it never had.
    assert "gusts" not in small.limiting_factor


# ------------------------------------------------------------- long swell flag

def test_long_swell_is_flagged_when_period_and_height_both_qualify():
    w = transit.assess(
        _marine(wave=1.0, swell=1.4, swell_period=13.0), _wind(speed=10.0, gusts=12.0))
    assert w.long_swell_flag is True
    assert "13.0 s" in w.long_swell_note


def test_a_long_period_with_negligible_height_is_not_flagged():
    """A 14 s period on 0.2 m of swell is not a heave anybody feels."""
    w = transit.assess(
        _marine(wave=1.0, swell=0.2, swell_period=14.0), _wind(speed=10.0, gusts=12.0))
    assert w.long_swell_flag is False
    assert w.long_swell_note == ""


def test_short_period_swell_is_not_flagged_however_big():
    w = transit.assess(
        _marine(wave=1.0, swell=2.0, swell_period=6.0), _wind(speed=10.0, gusts=12.0))
    assert w.long_swell_flag is False


# ------------------------------------------------------------- transparency

def test_every_craft_states_the_thresholds_it_was_judged_against():
    """The page prints these so a reader can disagree with the bands. An empty
    or vague note would make the numbers unfalsifiable."""
    w = transit.assess(_marine(wave=1.0), _wind(speed=10.0, gusts=12.0))
    for craft in w.crafts:
        assert "m wave" in craft.thresholds_note
        assert "km/h wind" in craft.thresholds_note
        assert craft.limiting_factor


def test_readings_are_passed_through_unaltered():
    """This module must never adjust a measurement — it only bands them."""
    w = transit.assess(
        _marine(wave=1.37, period=11.7, swell=1.22, swell_period=9.8, sst=25.1),
        _wind(speed=14.1, gusts=27.4))
    assert (w.wave_height_m, w.wave_period_s) == (1.37, 11.7)
    assert (w.swell_height_m, w.swell_period_s) == (1.22, 9.8)
    assert (w.wind_speed_kmh, w.wind_gusts_kmh) == (14.1, 27.4)
    assert w.sea_surface_temperature_c == 25.1
