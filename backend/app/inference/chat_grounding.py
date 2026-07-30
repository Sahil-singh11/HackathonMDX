"""Retrieval grounding for the conversational assistant.

THE RULE THIS FILE ENFORCES: the assistant must never answer a Mauritian
fisheries question from the model's training data. Gemma has read the open web;
it has not read the current Mauritian gazette, and a plausible-sounding invented
size limit is the single most damaging thing this product could output.

So every chat turn is retrieved against the app's own regulatory files first,
and whatever matched is injected verbatim into the prompt. The system
instruction then forbids answering from anything else. Two independent controls,
because either one alone has been observed to fail.

The same retrieval doubles as the answer itself when no model runs — no key
configured, hosted Gemma down, or the fisher is on a boat with no signal. That
path calls nothing and invents nothing: it reads rules out of the JSON and says
where each one came from. It is the honest degradation, not an error state.

Retrieval is keyword-based, not embedding-based, and deliberately so: the
catalogue already ships hand-written `keywords` per species covering Morisyen,
French and English (octopus / ourite / poulpe), the corpus is a handful of
species and rules, and a deterministic matcher is auditable in a way a
similarity score is not. This mirrors `frontend/src/assistant/grounding.ts`,
which does the same job for the fully offline on-device path.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

from app.core.config import get_settings
from app.core.limitations import RULE_VERIFY_NOTICE
from app.services.fisheries_rules.engine import load_rules
from app.services.species.retrieval import load_catalogue

Topic = str | None

# Topic cues in the three languages a fisher may type into this box.
# Deliberately generous: a false positive costs a wasted retrieval, a false
# negative wrongly tells the fisher we have nothing.
SIZE_CUES = ("size", "length", "minimum", "undersized", "small", "cm", "measure", "how long",
             "groser", "longer", "tipti", "mezir", "mantle", "mantel",
             "taille", "longueur", "petit", "mesure", "combien")
SEASON_CUES = ("season", "closed", "closure", "ban", "allowed", "month", "open", "period",
               "sezon", "ferme", "fermtir", "kan", "permet", "mwa", "ouver",
               "saison", "fermeture", "quand", "mois", "interdit", "autorise")
DECLARATION_CUES = ("declaration", "declare", "submit", "report", "form", "paperwork",
                    "ministry", "permit", "licence", "license",
                    "deklarasion", "deklar", "soumet", "rapor", "formil", "minister",
                    "declaration", "declarer", "soumettre", "rapport", "formulaire")
MARINE_CUES = ("weather", "wave", "waves", "swell", "wind", "sea state", "conditions", "forecast",
               "sea", "rough", "calm", "tide",
               "lamer", "vag", "divan", "kondision", "previzion", "gro lamer",
               "meteo", "vague", "houle", "vent", "mer")

MONTHS = ("", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December")

DECLARATION_CONTEXT = """- Completing a declaration in this app (process, not regulation):
  1. Record each catch as it is landed: photo, the fisher confirms the species, enter the measured length. Works offline; records queue on the device.
  2. Before the period ends, check the catch log: confirm everything synced and correct any wrong species.
  3. Choose the period on the Declaration page and review the record count, species breakdown and total.
  4. Submit and keep the reference number and printable summary.
  IMPORTANT: the submission in this app is SIMULATED. It is not a real government filing, and the receipt says so."""


@dataclass
class Grounding:
    """What the app's own data has to say about one question."""

    covered: bool
    topic: Topic = None
    species: list[dict] = field(default_factory=list)
    rules: list[dict] = field(default_factory=list)
    #: Verbatim block injected into the model prompt. Empty when nothing matched.
    context: str = ""
    cited_rules: list[str] = field(default_factory=list)


def _normalise(text: str) -> str:
    """Fold accents and punctuation so 'déclaration' matches the 'deklarasion' cues."""
    folded = unicodedata.normalize("NFD", text.lower())
    folded = "".join(c for c in folded if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9\s]", " ", folded)


def _has_cue(haystack: str, cues: tuple[str, ...]) -> bool:
    return any(_normalise(cue) in haystack for cue in cues)


@lru_cache
def _sources() -> dict:
    path = get_settings().data_dir / "rules" / "source_register.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("sources", {})


def match_species(question: str) -> list[dict]:
    """Species whose name, scientific name or keywords appear in the question."""
    q = _normalise(question)
    hits = []
    for sp in load_catalogue():
        terms = [sp.get("english", ""), sp.get("morisyen", ""), sp.get("scientific", "")]
        terms += list(sp.get("keywords", []))
        for term in terms:
            t = _normalise(str(term)).strip()
            if len(t) <= 2:
                continue
            # Word boundaries, so a short Morisyen name does not match inside an
            # unrelated word. Multi-word terms tolerate any run of whitespace.
            pattern = r"\s+".join(re.escape(part) for part in t.split())
            if re.search(rf"\b{pattern}\b", q):
                hits.append(sp)
                break
    return hits


def detect_topic(question: str) -> Topic:
    q = _normalise(question)
    if _has_cue(q, DECLARATION_CUES):
        return "declaration"
    if _has_cue(q, SEASON_CUES):
        return "season"
    if _has_cue(q, SIZE_CUES):
        return "size"
    if _has_cue(q, MARINE_CUES):
        return "marine"
    return None


def _mmdd(value: str) -> str:
    try:
        month, day = (int(x) for x in value.split("-"))
        return f"{day} {MONTHS[month]}"
    except (ValueError, IndexError):
        return value


def _species_name(species_id: str) -> str:
    for sp in load_catalogue():
        if sp["species_id"] == species_id:
            return f"{sp['english']} ({sp['morisyen']}, {sp['scientific']})"
    return species_id


def _rule_to_context(rule: dict) -> str:
    """One rule rendered verbatim and attributed. Never paraphrased, never summarised."""
    lines = [f"- Species: {_species_name(rule['species_id'])}",
             f"  Rule {rule['rule_id']} ({rule['rule_type']})"]
    if rule["rule_type"] in ("seasonal_closure", "historical_note"):
        lines.append(f"  Closed from {_mmdd(rule.get('closed_from', ''))} "
                     f"to {_mmdd(rule.get('closed_to', ''))}")
    if rule.get("minimum_length_cm") is not None:
        lines.append(f"  Minimum {rule['minimum_length_cm']} cm, measured as: "
                     f"{rule.get('measurement', 'unspecified')}")
    elif rule["rule_type"] == "minimum_size":
        lines.append("  No verified minimum size recorded for this species.")
    lines.append(f"  Verification status: {rule.get('verification_status', 'unavailable')}")
    if rule.get("note"):
        lines.append(f"  Note: {rule['note']}")
    if rule.get("scope_note"):
        lines.append(f"  Scope: {rule['scope_note']}")
    src = _sources().get(rule.get("source_id", ""))
    if src:
        lines.append(f"  Source {rule['source_id']}: {src.get('title', '')}")
    return "\n".join(lines)


def retrieve(question: str) -> Grounding:
    """Retrieve the app's own data for one question.

    Coverage rules:
      - a named species is always covered; we can cite its rules even when the
        honest answer is "no verified rule exists for it"
      - a declaration question is covered by the process text
      - a size or season question with no species named is covered by every rule
        of that type, so "what are the closed seasons?" works
      - a sea-conditions question is covered only in the sense that we know where
        the real numbers live; no rule text applies
    """
    matched = match_species(question)
    topic = detect_topic(question)

    if topic == "declaration":
        return Grounding(covered=True, topic=topic, context=DECLARATION_CONTEXT)

    all_rules = load_rules()
    relevant: list[dict] = []
    if matched:
        ids = {s["species_id"] for s in matched}
        relevant = [r for r in all_rules if r["species_id"] in ids]
        if topic == "size":
            narrowed = [r for r in relevant if r["rule_type"] == "minimum_size"]
        elif topic == "season":
            narrowed = [r for r in relevant
                        if r["rule_type"] in ("seasonal_closure", "historical_note")]
        else:
            narrowed = relevant
        # A species with no rule of the asked-for type still gets its full set,
        # so the answer can be "no size rule, but there is a closure" rather
        # than going silent on the closure.
        relevant = narrowed or relevant
    elif topic == "size":
        relevant = [r for r in all_rules if r["rule_type"] == "minimum_size"]
    elif topic == "season":
        relevant = [r for r in all_rules
                    if r["rule_type"] in ("seasonal_closure", "historical_note")]

    covered = bool(matched or relevant or topic == "marine")

    blocks = [_rule_to_context(r) for r in relevant]
    if matched:
        blocks.append("Species details:\n" + "\n".join(
            f"- {s['english']} ({s['morisyen']}, {s['scientific']}) — habitat: {s.get('habitat', 'unrecorded')}"
            for s in matched))
    if topic == "marine":
        blocks.append("- Sea conditions are not in this rules data. Live wave, swell and sea "
                      "temperature figures come from the get_marine_conditions function and "
                      "from the app's Sea conditions page.")

    return Grounding(covered=covered, topic=topic, species=matched, rules=relevant,
                     context="\n".join(blocks),
                     cited_rules=[r["rule_id"] for r in relevant])


# --------------------------------------------------------------------------
# Deterministic answers — used whenever no model runs.
#
# These are assembled from the rule fields, not written as prose about them, so
# a figure in an answer here is a figure that is in the JSON. Short by design:
# this is the version a fisher reads when the connection has already failed
# once, and the Fishing rules page holds the full text.
# --------------------------------------------------------------------------

_T = {
    "no_data": {
        "en": ("I do not have that in the app's rules data, so I will not guess at it. "
               "Open the Fishing rules page — it holds every rule this app has, and it works "
               "with no signal."),
        "mfe": ("Mo pena sa dan bann regleman ki dan app la, alor mo pa pou devine. "
                "Ouver paz Regleman lapes — li ena tou bann regleman ki app la kone, ek li "
                "marse san rezo."),
    },
    "marine": {
        "en": ("I cannot reach the live sea forecast right now. Open the Sea conditions page for "
               "the latest figures the app has stored, and check the official marine advisory "
               "before you go out."),
        "mfe": ("Mo pa kapav gagn previzion lamer la aster. Ouver paz Kondision lamer pou bann "
                "dernie sif ki app la finn garde, ek verifie bilten ofisiel avan ou sorti."),
    },
    "declaration": {
        "en": ("Record each catch as you land it, check the log before the period ends, then pick "
               "the period on the Declaration page and submit. The submission in this app is "
               "simulated — it is not a real government filing."),
        "mfe": ("Anrezistre sak lapes kan ou debark li, verifie ou zournal avan lafin peryod, "
                "apre swazir peryod lor paz Deklarasion ek soumet. Soumision dan app la zis enn "
                "simulasion — li pa enn vre depo ar gouvernman."),
    },
    "verify": {"en": RULE_VERIFY_NOTICE, "mfe": "Verifie avek dernie lavi ofisiel lapes avan pran desizion."},
    "provisional": {
        "en": "Rules marked provisional have been read from the published text but not confirmed as still in force.",
        "mfe": "Bann regleman make provizwar finn lir dan text ofisiel me pa ankor konfirme ki zot ankor an viger.",
    },
}


def _rule_sentence(rule: dict) -> str:
    """One English sentence of fact per rule. Figures come straight from the JSON."""
    name = _species_name(rule["species_id"])
    status = rule.get("verification_status", "unavailable")
    rid = rule["rule_id"]

    if rule["rule_type"] == "seasonal_closure":
        return (f"{name}: a closed season is recorded from {_mmdd(rule.get('closed_from', ''))} "
                f"to {_mmdd(rule.get('closed_to', ''))} ({rid}, {status}).")
    if rule["rule_type"] == "historical_note":
        return (f"{name}: a past closure from {_mmdd(rule.get('closed_from', ''))} to "
                f"{_mmdd(rule.get('closed_to', ''))} is on record as historical and not in force ({rid}).")
    if rule["rule_type"] == "minimum_size":
        if rule.get("minimum_length_cm") is None:
            return f"{name}: no verified minimum size is recorded ({rid}, {status})."
        measurement = rule.get("measurement", "total_length_cm")
        if measurement != "total_length_cm":
            return (f"{name}: the recorded minimum is {rule['minimum_length_cm']} cm measured on "
                    f"{measurement.replace('_cm', '').replace('_', ' ')}, not total length, so a "
                    f"total-length measurement cannot decide it ({rid}, {status}).")
        return (f"{name}: the recorded minimum length is {rule['minimum_length_cm']} cm "
                f"({rid}, {status}).")
    return f"{name}: rule {rid} is on record ({status})."


def deterministic_reply(grounding: Grounding, language: str) -> str:
    """Answer with no model at all. Never invents; says plainly when it has nothing."""
    lang = "mfe" if language == "mfe" else "en"

    if grounding.topic == "declaration":
        return _T["declaration"][lang]
    if not grounding.covered or (not grounding.rules and not grounding.species):
        return _T["marine"][lang] if grounding.topic == "marine" else _T["no_data"][lang]

    if not grounding.rules:
        names = ", ".join(f"{s['english']} ({s['morisyen']})" for s in grounding.species)
        body = (f"No rule is recorded in this app for {names}. That means no rule was found, "
                f"not that none exists.")
    elif not grounding.species:
        # A size or season question that named no species we hold. Listing our
        # rules without saying whose they are reads as an answer about the
        # species the fisher asked about, which it is not.
        held = ", ".join(sorted({_species_name(r["species_id"]).split(" (")[0]
                                 for r in grounding.rules}))
        body = (f"I did not recognise a species in that question. This app holds rules for "
                f"{held} only, and nothing else. ")
        body += " ".join(_rule_sentence(r) for r in grounding.rules[:2])
    else:
        # Cap at three so the answer stays readable on a phone; the Fishing
        # rules page is where the full set lives.
        body = " ".join(_rule_sentence(r) for r in grounding.rules[:3])
        if len(grounding.rules) > 3:
            body += f" {len(grounding.rules) - 3} further rules are listed on the Fishing rules page."

    tail = _T["verify"][lang]
    if any(r.get("verification_status") == "provisional" for r in grounding.rules):
        tail = f"{_T['provisional'][lang]} {tail}"
    return f"{body} {tail}"
