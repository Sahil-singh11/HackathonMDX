"""Transport schema for native structured output.

WHY THIS EXISTS
---------------
`GemmaStructuredAnalysis` (app.schemas.gemma_gate) pins two invariants with
`Literal[True]`: `species_confirmation_required` and `measured_size_required`.
That is correct for the application boundary — the model must not be able to
lower them — but google-genai 2.14.0 cannot convert it into a response schema:

    ValueError: Literal values must be strings.

So the wire format needs a model built only from constructs the API handles
well: string enums, a flat nested object, bounded lists, explicit required
fields, no unions beyond `X | None`, no dicts, no recursion.

The two pinned booleans are simply ABSENT from the transport model. They are not
negotiable, so there is nothing for the model to say about them — they are
re-asserted during conversion. This is a transport difference, not a contract
change: the accepted public enum values are unchanged, and
`to_application_model()` is a deterministic, tested conversion into the frozen
application shape.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Deliberately re-declared as plain string Literals rather than imported aliases:
# the SDK schema converter reads these annotations directly, and these values
# must stay identical to the frozen contract in app.schemas.analysis.
TransportIntent = Literal["identify_catch", "weather_query", "log_catch", "make_declaration", "other"]
TransportConfidence = Literal["low", "medium", "high"]
TransportNextStep = Literal["confirm_species", "retake_photo", "enter_measurement", "none"]


class TransportSpeciesSuggestion(BaseModel):
    """One level of nesting only; every field nullable because 'unknown' is valid."""

    species_id: str | None = Field(
        default=None, description="Must be one of the supplied candidate species_id values, or null if unsure.")
    morisyen: str | None = Field(default=None, description="Morisyen (Mauritian Creole) name, or null.")
    english: str | None = Field(default=None, description="English common name, or null.")
    scientific: str | None = Field(default=None, description="Scientific name, or null.")


class GemmaTransportAnalysis(BaseModel):
    """What the model is asked to emit. Converted, never returned directly."""

    intent: TransportIntent = Field(description="The fisher's intent.")
    species_suggestion: TransportSpeciesSuggestion = Field(
        description="Suggested species. Use nulls when the evidence is insufficient.")
    # Bounds are load-bearing, not decoration: they become `maxItems`/`maxLength` in the
    # emitted JSON schema. Without them this model sometimes keeps extending the string and
    # array fields until it hits the output ceiling (observed: 1024 tokens, ~40-49 s,
    # truncated mid-object).
    visible_characteristics: list[str] = Field(
        default_factory=list, max_length=3,
        description="At most 3 short visible features actually observed.")
    confidence_label: TransportConfidence = Field(description="Confidence in the species suggestion.")
    estimated_size_unverified_cm: float | None = Field(
        default=None, description="Rough size estimated from the image only. Never a measurement. Null if unclear.")
    reply: str = Field(max_length=220, description="Short practical reply in English, max 25 words.")
    reply_morisyen: str = Field(
        max_length=220, description="Short practical reply in Morisyen (Mauritian Creole), max 25 words.")
    recommended_next_step: TransportNextStep = Field(description="The single next action for the fisher.")
    requested_function: str | None = Field(
        default=None, description="Name of an offered function to call, or null.")
    limitations: list[str] = Field(
        default_factory=list, max_length=2, description="At most 2 short caveats about this analysis.")


def to_application_model(transport: GemmaTransportAnalysis, allowed_ids: set[str]):
    """Deterministically convert transport -> frozen application model.

    Re-asserts the non-negotiable invariants and re-applies the allow-lists. The
    model's output cannot influence `species_confirmation_required` or
    `measured_size_required` because they never crossed the wire.
    """
    from app.schemas.gemma_gate import GemmaStructuredAnalysis
    from app.tools.registry import REGISTRY

    sug = transport.species_suggestion
    species_id = sug.species_id if sug.species_id in allowed_ids else None
    return GemmaStructuredAnalysis(
        intent=transport.intent,
        species_suggestion={
            "species_id": species_id,
            # A name without an allow-listed id would be an unbacked claim.
            "morisyen": sug.morisyen if species_id else None,
            "english": sug.english if species_id else None,
            "scientific": sug.scientific if species_id else None,
        },
        visible_characteristics=[str(c) for c in transport.visible_characteristics][:8],
        confidence_label=transport.confidence_label,
        species_confirmation_required=True,
        estimated_size_unverified_cm=transport.estimated_size_unverified_cm,
        measured_size_required=True,
        reply=str(transport.reply or "")[:1200],
        reply_morisyen=str(transport.reply_morisyen or "")[:1200],
        recommended_next_step=transport.recommended_next_step,
        requested_function=(transport.requested_function
                            if transport.requested_function in REGISTRY else None),
        limitations=[str(x) for x in transport.limitations][:8],
    )
