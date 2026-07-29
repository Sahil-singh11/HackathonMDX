"""Route-specific generation profiles — set from Step-2 measurements, not from theory.

WHAT THE EXPERIMENTS ACTUALLY SHOWED (88 requests, docs/STRUCTURED_OUTPUT_REPORT.md)
-----------------------------------------------------------------------------------
The Step-2 hypothesis was that native structured output would beat prompt-instructed
JSON. It did not. On `gemma-4-26b-a4b-it`:

  config                              final valid   exact enums   intent   median   p90
  A prompt JSON + full prompt             100%         100%        100%    4 648ms  8 250ms
  F prompt JSON + MINIMAL thinking        100%         100%        100%    5 812ms  9 093ms
  E prompt JSON + compact prompt          100%         100%       53.8%    4 859ms  8 421ms
  B response_json_schema + MINIMAL       72.7%        59.1%         70%    5 233ms 53 530ms
  C response_json_schema + HIGH          59.1%        45.5%       87.5%   28 007ms 64 139ms

So: the control mechanism is kept, the full prompt is kept, and default thinking is kept.

Specific measured reasons:
- `response_json_schema` makes this model intermittently degenerate — it writes until the
  output ceiling (`finish_reason=MAX_TOKENS`, 1024 tokens, 26-57 s) or trips RECITATION.
  Adding `maxItems`/`maxLength` bounds to the schema reduced but did not remove it.
- `response_schema=<Pydantic>` is worse still: 32 768 tokens / ~12 min, or RECITATION.
- The COMPACT prompt halves prompt size but costs intent accuracy (100% -> 53.8%), because
  the intent and tool guidance it drops is load-bearing.
- `thinking_level=MINIMAL` is a real win in isolation (733 ms vs 11 483 ms on a bare
  prompt) but did not help end to end (F slower than A), so it is used only where it was
  measured to help: tool selection, which needs no deliberation.
- `max_output_tokens` counts hidden thinking tokens on this model. With default thinking,
  caps of 256/384/1024 all returned `finish_reason=MAX_TOKENS` with EMPTY text. A cap is
  therefore only set on the route that also pins thinking to MINIMAL.
- Image longest side: 768 px was *slower* (6 483 ms) than 1024/1280 (6 281 / 5 250 ms) and
  no more accurate. 1024 and 1280 produced byte-identical JPEGs for the demo fixtures
  (their longest side is already <=1024), so that comparison is inconclusive and the
  existing 1280 ceiling in the quality gate is left alone.
"""
from __future__ import annotations

from dataclasses import dataclass

THINKING_MINIMAL = "MINIMAL"
THINKING_HIGH = "HIGH"

# Measured truncation floor for the native-schema experiments: 512 truncated mid-object,
# 1024 completed. Only meaningful on a route that pins thinking to MINIMAL.
MIN_SAFE_OUTPUT_CAP = 1024


@dataclass(frozen=True)
class GenerationProfile:
    name: str
    thinking_level: str | None       # None = model default (measured fastest end to end)
    max_output_tokens: int | None    # None = uncapped; a cap also consumes thinking tokens
    compact_prompt: bool             # False = full SYSTEM_INSTRUCTION (protects intent accuracy)
    image_longest_side: int | None
    timeout_seconds: int
    structured: bool                 # True = ask for native structured output on this route

    def describe(self) -> dict:
        return {
            "name": self.name, "thinking_level": self.thinking_level,
            "max_output_tokens": self.max_output_tokens, "compact_prompt": self.compact_prompt,
            "image_longest_side": self.image_longest_side, "timeout_seconds": self.timeout_seconds,
            "structured": self.structured,
        }


# Turn 1: pick a function. Measured at ~1.4 s with MINIMAL thinking — the one route where
# MINIMAL clearly pays, because choosing an allow-listed tool needs no deliberation.
# Never structured: a response schema and a `function_call` part compete for the output.
FAST_TOOL_SELECTION = GenerationProfile(
    name="fast_tool_selection", thinking_level=THINKING_MINIMAL, max_output_tokens=None,
    compact_prompt=False, image_longest_side=None, timeout_seconds=45, structured=False)

# Text-only analysis. Config A settings: full prompt, default thinking, no cap.
FAST_INTENT = GenerationProfile(
    name="fast_intent", thinking_level=None, max_output_tokens=None,
    compact_prompt=False, image_longest_side=None, timeout_seconds=60, structured=False)

# Photo present — the quality-critical route. Median 7.3 s in config A.
IMAGE_SPECIES_ANALYSIS = GenerationProfile(
    name="image_species_analysis", thinking_level=None, max_output_tokens=None,
    compact_prompt=False, image_longest_side=1280, timeout_seconds=75, structured=False)

# Turn 2: fold a tool result into the final answer. Measured at ~3.9 s.
FINAL_TOOL_RESPONSE = GenerationProfile(
    name="final_tool_response", thinking_level=None, max_output_tokens=None,
    compact_prompt=False, image_longest_side=None, timeout_seconds=60, structured=False)

PROFILES = {p.name: p for p in (FAST_INTENT, FAST_TOOL_SELECTION, IMAGE_SPECIES_ANALYSIS, FINAL_TOOL_RESPONSE)}


def for_request(has_image: bool, stage: str) -> GenerationProfile:
    """Pick the profile for a request stage. Explicit, never inferred at call sites."""
    if stage == "tool_selection":
        return FAST_TOOL_SELECTION
    if stage == "final_tool_response":
        return FINAL_TOOL_RESPONSE
    return IMAGE_SPECIES_ANALYSIS if has_image else FAST_INTENT
