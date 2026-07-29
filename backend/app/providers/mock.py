"""Deterministic offline mock provider.

Fully offline, repeatable (seeded by image hash + note keywords), and always
labelled: real_inference=False, mode='mock'. Never presented as Gemma.
"""
from __future__ import annotations

import time

from app.core.limitations import MOCK_DISCLOSURE
from app.providers.base import ProviderResult
from app.tools.registry import ToolContext, execute

WEATHER_WORDS = ("weather", "lamer", "sea", "wave", "houle", "swell", "vag", "letan", "meteo", "vent", "wind")
DECLARATION_WORDS = ("declaration", "deklarasion", "declare", "deklare", "receipt", "resi")
LOG_WORDS = ("log", "record", "anrezistre", "save", "note sa", "met dan zistwar")


def _intent_from_note(note: str | None, has_image: bool) -> str:
    text = (note or "").lower()
    if any(w in text for w in WEATHER_WORDS) and not has_image:
        return "weather_query"
    if any(w in text for w in DECLARATION_WORDS):
        return "make_declaration"
    if any(w in text for w in LOG_WORDS):
        return "log_catch"
    if has_image:
        return "identify_catch"
    return "other"


def analyse(image_sha: str | None, note: str | None, language: str,
            candidates: list[dict], ctx: ToolContext) -> ProviderResult:
    start = time.monotonic()
    res = ProviderResult(mode="mock", provider_name="deterministic-mock", model="none",
                         real_inference=False, disclosures=[MOCK_DISCLOSURE])
    res.intent = _intent_from_note(note, has_image=image_sha is not None)

    if res.intent == "weather_query":
        data, trace = execute("get_marine_conditions", {}, ctx)
        res.function_trace.append(trace)
        wave = data.get("wave_height_m")
        swell = data.get("swell_height_m")
        res.reply = (f"Current conditions near the fallback location: waves about {wave} m, "
                     f"swell about {swell} m. This is informational only — check official advisories.")
        res.reply_morisyen = (f"Kondision lamer aster: vag apepre {wave} m, houle apepre {swell} m. "
                              "Sa zis lenformasion — verifie bilten ofisiel avan sorti.")
        res.recommended_next_step = "none"
    elif res.intent == "identify_catch" and candidates:
        # Deterministic pick: keyword match first, else image-hash seeded choice.
        text = (note or "").lower()
        pick = None
        for c in candidates:
            if any(k.lower() in text for k in (c.get("morisyen", ""), c["english"].split()[0].lower()) if k):
                pick = c
                break
        if pick is None:
            seed = int((image_sha or "0")[:8], 16)
            pick = candidates[seed % len(candidates)]
            res.confidence_label = "low"
        else:
            res.confidence_label = "medium"
        res.species_id = pick["species_id"]
        res.visible_characteristics = pick.get("visible_characteristics", [])[:3]
        res.reply = (f"This may be {pick['english']} ({pick['scientific']}). Please confirm or correct "
                     "the species, then enter the measured length with a ruler.")
        res.reply_morisyen = (f"Kitfwa sa se {pick['morisyen']} ({pick['english']}). Silvouple konfirm ouswa "
                              "koriz lespes, apre met longer mezire avek enn regleman.")
        res.recommended_next_step = "confirm_species"
    elif res.intent == "make_declaration":
        res.reply = "I can prepare a declaration draft from your recent catches. It will be sent to a MOCK demonstration endpoint only."
        res.reply_morisyen = "Mo kapav prepar enn brouyon deklarasion ar to bann lapes resan. Li pou al zis lor enn sistem DEMONSTRASION (MOCK)."
        res.recommended_next_step = "none"
    elif res.intent == "log_catch":
        res.reply = "Tell me the confirmed species and measured length, and I will record the catch."
        res.reply_morisyen = "Dir mwa lespes konfirme ek longer mezire, mo pou anrezistre lapes la."
        res.recommended_next_step = "enter_measurement"
    else:
        res.reply = "I can help with catch photos, marine conditions, your catch log and declarations."
        res.reply_morisyen = "Mo kapav ed twa ar foto lapes, kondision lamer, to zistwar lapes ek deklarasion."
        res.recommended_next_step = "none"

    res.latency_ms = int((time.monotonic() - start) * 1000)
    return res
