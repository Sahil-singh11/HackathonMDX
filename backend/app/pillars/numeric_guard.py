"""Number firewall: the model may describe already-computed figures, never invent one.

WHY THIS EXISTS. Every pillar narrative prompt already TELLS the model "use only
the figures supplied, never add or alter a number" — see the RULES block in
energy/module.py, tourism/module.py and transport/brief.py. That is a prompt
instruction, not an enforcement mechanism: the existing `_LyingProvider` test
fixture proves a model CAN ignore it ("Wave power here is actually 9999 kW/m").
`narrative.py`'s `prose_or_empty` and transport's `narrative_is_grounded` catch a
refusal wearing a JSON costume and an invented vessel identifier, but neither
one reads the prose for a fabricated figure — transport's own docstring says so
plainly: "a model can describe a busy approach as quiet and this returns True."

This module closes that specific gap: it extracts every number the narrative
states and checks each one against the numbers the caller actually put in the
prompt. A number that cannot be traced back to the input is not describing a
computed figure — it is either fabricated or a computation the model is not
authorised to perform. Either way, the honest thing to do is a stated reject and
a fall back to the mechanical summary, never a guess at which reading was
intended.

WHAT THIS DOES NOT DO. It cannot judge whether the model's *qualitative* framing
of a grounded number is fair (e.g. calling 1.46 m "modest" vs "significant") —
that is the same limitation `narrative_is_grounded` already discloses, and nobody
in this codebase claims otherwise. It also is not a units checker: "15.68" passes
whether the surrounding word is "kW/m" or something else, because the RULES text
already tells the model which unit belongs to which figure, and this firewall's
job is only "was this NUMBER given to you."

USAGE. Build `source_text` from exactly the FACTS block handed to the model —
not the full prompt, which also contains instructional numbers ("two or three
sentences") that are not data and must not silently become an allow-list.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

# Cardinals only, zero through twenty — matches the scope the model is asked to
# respect. Deliberately excludes ordinals ("first", "second", "2nd"): those are
# never numeric CLAIMS about a figure, so they are simply never extracted as
# numbers in the first place, rather than being extracted and then allow-listed.
_WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20,
}
_WORD_RE = re.compile(r"\b(" + "|".join(_WORD_NUMBERS) + r")\b", re.IGNORECASE)

# Digit tokens: optional sign, digits with optional thousands commas, optional
# decimal part. The lookbehind/lookahead exclude a digit run glued to letters on
# either side ("1st", "M2", "10am", "co2") so those are never torn apart into a
# bare number — they were never a numeric CLAIM to begin with.
_DIGIT_RE = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w])")


def extract_numbers(text: str | None) -> list[float]:
    """Every value a reader would recognise as a number: digit tokens and the
    cardinal words zero..twenty. Order is not meaningful; duplicates are kept
    (a repeated number is still one legitimate value seen twice)."""
    if not text:
        return []
    out: list[float] = []
    for token in _DIGIT_RE.findall(text):
        cleaned = token.replace(",", "")
        try:
            out.append(float(cleaned))
        except ValueError:  # pragma: no cover - regex should not admit this
            continue
    for match in _WORD_RE.findall(text):
        out.append(float(_WORD_NUMBERS[match.lower()]))
    return out


@dataclass
class GroundingResult:
    ok: bool
    reason: str = ""
    offending: list[float] = field(default_factory=list)


def check_numeric_grounding(
    output_text: str,
    source_text: str,
    *,
    rel_tolerance: float = 0.05,
    abs_tolerance: float = 0.1,
    allowed_years: frozenset[int] = frozenset(),
) -> GroundingResult:
    """Does every number in `output_text` trace back to a number actually shown
    in `source_text` (within a rounding tolerance), or to an explicitly-passed
    year?

    Tolerance is `max(abs_tolerance, rel_tolerance * |source_value|)` per
    candidate match, so a small figure (1.46 m) tolerates ~0.1 of rounding
    while a large one (612.5 W/m2) tolerates ~5% — enough to absorb the model
    restating "about 15.7" for a computed 15.68, not enough to let a
    fabricated order-of-magnitude figure (9999 for a real value of 15.68)
    through by accident.
    """
    allowed = extract_numbers(source_text)
    offending: list[float] = []
    for n in extract_numbers(output_text):
        if n in allowed_years:
            continue
        if any(abs(n - a) <= max(abs_tolerance, rel_tolerance * abs(a)) for a in allowed):
            continue
        offending.append(n)

    if offending:
        shown = ", ".join(f"{o:g}" for o in offending[:5])
        more = f" (+{len(offending) - 5} more)" if len(offending) > 5 else ""
        return GroundingResult(
            False,
            f"narrative stated number(s) not traceable to the supplied figures: {shown}{more}",
            offending,
        )
    return GroundingResult(True)


# --------------------------------------------------------------------- stats

class NumericGuardStats:
    """In-process counters for the demo claim this exists to support: 'the
    model attempted to introduce an unsourced figure N times and was blocked
    every time.' Deliberately in-memory only (same lifetime contract as the
    rate limiters in app.core.ratelimit) — a hackathon demo process, not a
    durability guarantee. Reset alongside everything else via /api/demo/reset.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._checked = 0
        self._rejected = 0
        self._reasons: dict[str, int] = {}

    def record(self, result: GroundingResult, *, pillar_id: str) -> None:
        with self._lock:
            self._checked += 1
            if not result.ok:
                self._rejected += 1
                key = f"{pillar_id}: {result.reason.split(':')[0].strip()}"
                self._reasons[key] = self._reasons.get(key, 0) + 1

    def reset(self) -> None:
        with self._lock:
            self._checked = 0
            self._rejected = 0
            self._reasons = {}

    def snapshot(self) -> dict:
        with self._lock:
            checked, rejected = self._checked, self._rejected
            reasons = dict(self._reasons)
        return {
            "narratives_checked": checked,
            "narratives_rejected": rejected,
            "rejection_rate_pct": round(100 * rejected / checked, 1) if checked else 0.0,
            "rejection_reasons": reasons,
            "note": (
                "In-memory since last restart/demo-reset. A rejection means a model "
                "stated a number that could not be traced to the figures it was given; "
                "the pillar fell back to figures-only or a mechanical summary rather "
                "than render it."
            ),
        }


stats = NumericGuardStats()


def guarded(text: str | None, source_text: str, *, pillar_id: str,
           rel_tolerance: float = 0.05, abs_tolerance: float = 0.1,
           allowed_years: frozenset[int] = frozenset()) -> str:
    """Convenience wrapper for pillar call sites: check, record to `stats`, and
    return the narrative when grounded or "" when not (never raises — the same
    fail-open-to-empty contract as narrative.prose_or_empty)."""
    if not text:
        return ""
    result = check_numeric_grounding(
        text, source_text, rel_tolerance=rel_tolerance,
        abs_tolerance=abs_tolerance, allowed_years=allowed_years,
    )
    stats.record(result, pillar_id=pillar_id)
    return text if result.ok else ""
