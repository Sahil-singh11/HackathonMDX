"""Number firewall (Task 2 of the pillar-backend work list).

The claim across the pillars is that the model can never turn its own prose
into a figure. Before this module that was enforced by prompt instruction
only — `prose_or_empty` and `narrative_is_grounded` catch a refusal-as-JSON
and an invented vessel identifier, but neither reads the prose for a
fabricated NUMBER. These tests prove the new check does, using the exact
fabrication already on record in this codebase's own test fixture
(test_pillar_energy.py's `_LyingProvider`: "Wave power here is actually 9999
kW/m and wind power is 88888 W/m2").
"""
from __future__ import annotations

from app.pillars.numeric_guard import (GroundingResult, NumericGuardStats,
                                       check_numeric_grounding, extract_numbers,
                                       guarded)

# --- extract_numbers ---------------------------------------------------

def test_extracts_plain_integers_and_decimals():
    assert extract_numbers("wave 1.46 m, swell 1.32 m at 10.15 s") == [1.46, 1.32, 10.15]


def test_extracts_negative_numbers():
    assert extract_numbers("delta of -3.5 units") == [-3.5]


def test_extracts_thousands_commas():
    assert extract_numbers("1,200 vessels") == [1200.0]


def test_extracts_cardinal_words_up_to_twenty():
    assert extract_numbers("twelve vessels are tracked, nine under way, two at anchor") == [12.0, 9.0, 2.0]


def test_does_not_extract_ordinal_words():
    """Ordinals describe position, not a figure — never treated as a number."""
    assert extract_numbers("the first and second candidate sites") == []


def test_does_not_tear_a_number_out_of_a_glued_token():
    """1st / M2 / 10am / co2 are not numeric claims about a figure."""
    assert extract_numbers("ranked 1st, measured in W/m2, seen at 10am, plus co2") == []


def test_empty_and_none_are_safe():
    assert extract_numbers("") == []
    assert extract_numbers(None) == []


def test_repeated_numbers_are_each_kept():
    assert extract_numbers("1.46 m and again 1.46 m") == [1.46, 1.46]


# --- check_numeric_grounding -------------------------------------------

FACTS = (
    "Significant wave height: 1.46 m\n"
    "Wave period (as supplied): 10.15 s\n"
    "Wind at 10 m: 36.0 km/h = 10.0 m/s\n"
    "COMPUTED wave power density: 15.68 kW/m\n"
    "COMPUTED wind power density: 612.5 W/m2\n"
    "All sites by wave power: se_coast_offshore=15.68 kW/m, south_coast_offshore=4.90 kW/m"
)


def test_narrative_that_only_restates_the_facts_is_grounded():
    text = (
        "This site shows a strong wave resource at 15.68 kW/m, ahead of "
        "south_coast_offshore at 4.90 kW/m. Wind power density is 612.5 W/m2 "
        "from a 10.0 m/s breeze at 10 m."
    )
    result = check_numeric_grounding(text, FACTS)
    assert result.ok is True
    assert result.offending == []


def test_minor_rounding_is_tolerated():
    """The model may write 'about 15.7' for a computed 15.68 without being
    treated as fabrication — restating with reasonable rounding is not the
    failure mode this firewall exists to catch."""
    text = "Wave power here is about 15.7 kW/m, roughly 4.9 kW/m ahead of the weakest site."
    result = check_numeric_grounding(text, FACTS)
    assert result.ok is True


def test_fabricated_large_figure_is_rejected():
    """The exact adversarial example already on record in this codebase
    (test_pillar_energy.py::_LyingProvider). prose_or_empty alone does NOT
    catch this — the text is syntactically ordinary prose, not JSON/an
    envelope — which is precisely the gap this module closes."""
    text = ("Wave power here is actually 9999 kW/m and wind power is 88888 W/m2. "
            "This is a bankable yield assessment and the site is surveyed.")
    result = check_numeric_grounding(text, FACTS)
    assert result.ok is False
    assert 9999.0 in result.offending
    assert 88888.0 in result.offending
    assert "not traceable" in result.reason


def test_fabricated_figure_close_in_magnitude_is_still_rejected():
    """Tolerance must not be so loose that a wrong-but-plausible-looking
    number slips through: 25.0 is nowhere near the real 15.68 (>5% relative,
    >0.1 absolute), even though it is the same order of magnitude."""
    text = "Wave power density here is 25.0 kW/m."
    result = check_numeric_grounding(text, FACTS)
    assert result.ok is False
    assert 25.0 in result.offending


def test_years_are_rejected_unless_explicitly_allowed():
    """A blanket 'any 4-digit number is a year' rule would let 9999-style
    fabrications hide as a year. Years must be explicitly, narrowly opted in."""
    text = "Conditions were measured in 2026."
    assert check_numeric_grounding(text, FACTS).ok is False
    assert check_numeric_grounding(text, FACTS, allowed_years=frozenset({2026})).ok is True


def test_empty_output_has_nothing_to_reject():
    result = check_numeric_grounding("", FACTS)
    assert result.ok is True
    assert result.offending == []


# --- guarded() wrapper + stats -----------------------------------------

def test_guarded_returns_text_when_grounded_and_empty_when_not(monkeypatch):
    import app.pillars.numeric_guard as ng

    fresh_stats = NumericGuardStats()
    monkeypatch.setattr(ng, "stats", fresh_stats)

    ok_text = "Wave power here is 15.68 kW/m."
    bad_text = "Wave power here is 9999 kW/m."

    assert guarded(ok_text, FACTS, pillar_id="energy") == ok_text
    assert guarded(bad_text, FACTS, pillar_id="energy") == ""
    assert guarded(None, FACTS, pillar_id="energy") == ""

    snap = fresh_stats.snapshot()
    assert snap["narratives_checked"] == 2  # None short-circuits before recording
    assert snap["narratives_rejected"] == 1
    assert snap["rejection_reasons"]  # keyed by pillar_id, populated


def test_stats_snapshot_reports_zero_before_any_check():
    stats = NumericGuardStats()
    snap = stats.snapshot()
    assert snap == {
        "narratives_checked": 0,
        "narratives_rejected": 0,
        "rejection_rate_pct": 0.0,
        "rejection_reasons": {},
        "note": snap["note"],
    }


def test_stats_reset_clears_counts():
    stats = NumericGuardStats()
    stats.record(GroundingResult(False, "narrative stated number(s) not traceable: 9999"), pillar_id="energy")
    assert stats.snapshot()["narratives_rejected"] == 1
    stats.reset()
    assert stats.snapshot() == {
        "narratives_checked": 0, "narratives_rejected": 0,
        "rejection_rate_pct": 0.0, "rejection_reasons": {},
        "note": stats.snapshot()["note"],
    }
