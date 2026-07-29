"""Boundary-date and unknown-propagation tests for the deterministic rule engine."""
from datetime import date

from app.services.fisheries_rules.engine import check_confirmed_catch


def test_real_date_29_july_closure_not_active():
    check = check_confirmed_catch("octopus_cyanea", None, date(2026, 7, 29))
    assert check.status != "closed_season"


def test_boundary_day_before_closure():
    assert check_confirmed_catch("octopus_cyanea", None, date(2026, 8, 14)).status != "closed_season"


def test_boundary_first_day_of_closure():
    check = check_confirmed_catch("octopus_cyanea", None, date(2026, 8, 15))
    assert check.status == "closed_season"
    assert check.rule == "R-OCT-CLOSE-2016"
    assert check.source_id == "S1"
    assert check.verification_status == "provisional"
    assert "official fisheries notice" in (check.note or "")


def test_boundary_last_day_of_closure():
    assert check_confirmed_catch("octopus_cyanea", None, date(2026, 10, 15)).status == "closed_season"


def test_boundary_day_after_closure():
    assert check_confirmed_catch("octopus_cyanea", None, date(2026, 10, 16)).status != "closed_season"


def test_simulated_september_date_shows_closure():
    assert check_confirmed_catch("octopus_cyanea", None, date(2026, 9, 1)).status == "closed_season"


def test_historical_january_rule_not_evaluated():
    """The Jan-Mar window is a historical note only and must never trigger."""
    assert check_confirmed_catch("octopus_cyanea", None, date(2026, 2, 1)).status != "closed_season"


def test_missing_minimum_size_source_returns_unknown():
    check = check_confirmed_catch("lethrinus_nebulosus", 35.0, date(2026, 7, 29))
    assert check.status == "unknown"
    assert "official fisheries notice" in (check.note or "")


def test_missing_measurement_returns_unknown_for_size_species():
    assert check_confirmed_catch("siganus_sutor", None, date(2026, 7, 29)).status == "unknown"


def test_unlisted_species_returns_unknown():
    assert check_confirmed_catch("nonexistent_species", 40.0, date(2026, 7, 29)).status == "unknown"
