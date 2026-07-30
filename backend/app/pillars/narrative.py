"""Is a model's output usable prose, or is it a refusal wearing a JSON costume?

WHY THIS EXISTS. `chat()` injects the catch-assistant system instruction unless a
caller overrides it. That instruction scopes the model to fishers and orders it to
"always produce valid structured output matching the requested JSON schema". Asked
for an ocean-tourism brief or an offshore-energy note under that instruction, the
live hosted model refuses AND wraps the refusal in the fisheries envelope:

    ```json
    {"intent": "other",
     "reply": "I am sorry, I can only help with identifying and logging fish
               catches. I cannot assist with ocean-energy analysis.",
     "reply_morisyen": "..."}
    ```

Measured 30 Jul 2026 on 2 of 8 tourism sites and on the energy assessments. Both
rendered that JSON to the user as the site's written brief — a chatbot refusal
presented as analysis.

The primary fix is a scoped `system_instruction` per pillar, so the model is asked
the right question in the first place. This module is the second line: even with
the right instruction a model may still return an envelope or a code block, and
prose is what these fields promise. An envelope is a FAILED narrative, not a
narrative, so it becomes an empty string — a state every pillar schema and every
surface already handles honestly.

`transport/brief.py:narrative_is_grounded` does the same job plus MMSI checks and
predates this module; it is intentionally left alone rather than refactored mid-
hackathon. This is the shared version for pillars that need no identifier check.
"""
from __future__ import annotations

import json

# Keys of the fisheries assistant's structured envelope. Kept in sync with
# transport/brief.py's _ENVELOPE_MARKERS by intent, not by import, because that
# one also guards MMSIs and the two can diverge without breaking each other.
_ENVELOPE_MARKERS = ('"intent"', '"reply_morisyen"', '"reply"', '"call"')


def is_prose(text: str | None) -> bool:
    """True when `text` looks like prose a human asked for.

    Deliberately narrow — it rejects a structural signature, not a topic:

    1. empty or whitespace
    2. a fenced code block or a bare JSON object/array
    3. text carrying the fisheries envelope's own keys

    Ordinary prose that happens to contain a brace still passes, because the
    marker test requires a quoted key followed by a colon.
    """
    if not text or not text.strip():
        return False
    stripped = text.strip()
    if stripped.startswith("```") or stripped.startswith("{") or stripped.startswith("["):
        return False
    return not any(f"{m}:" in stripped.replace('" :', '":') for m in _ENVELOPE_MARKERS)


#: Phrases that mark a reply as a refusal rather than an answer. A refusal is a
#: failed narrative: rendering "I can only help with fish catches" under an
#: ocean-energy heading is worse than rendering nothing, because it looks like
#: the pillar's own conclusion.
_REFUSAL_MARKERS = (
    "i am sorry", "i'm sorry", "i cannot", "i can not", "i can't",
    "i am unable", "i'm unable", "only help with", "only assist with",
    "outside my scope", "not able to assist",
)


def _looks_like_refusal(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in _REFUSAL_MARKERS)


def salvage_reply(text: str | None, *, language: str = "en") -> str:
    """Best-effort prose from a model response, including a wrapped envelope.

    Order of attempts:

    1. Already prose -> return it.
    2. A fenced or bare JSON envelope -> parse it and take the reply field for
       `language` (`reply_morisyen` for 'mfe', else `reply`). This is the case
       that was rendering on screen verbatim, fences and `intent` field
       included.
    3. Anything left, or a reply that is a REFUSAL, or a missing field -> "",
       so the caller falls back to its mechanical summary.

    A refusal is dropped even when it parses cleanly. It is a real model
    response, but it is not an answer to the question the page is asking, and
    presenting it as the analysis would be an overclaim about what we know.
    """
    if not text or not text.strip():
        return ""
    stripped = text.strip()

    if is_prose(stripped):
        return "" if _looks_like_refusal(stripped) else stripped

    # Strip a ```json ... ``` fence if there is one, then try to parse.
    body = stripped
    if body.startswith("```"):
        body = body.split("\n", 1)[-1] if "\n" in body else body[3:]
        if body.rstrip().endswith("```"):
            body = body.rstrip()[:-3]
    body = body.strip()

    try:
        parsed = json.loads(body)
    except (ValueError, TypeError):
        return ""
    if not isinstance(parsed, dict):
        return ""

    key = "reply_morisyen" if language == "mfe" else "reply"
    reply = parsed.get(key) or parsed.get("reply") or ""
    if not isinstance(reply, str) or not reply.strip():
        return ""
    reply = reply.strip()
    # `intent` and `call` are never rendered — only the reply text, and only
    # when it is an actual answer.
    return "" if _looks_like_refusal(reply) else reply


def prose_or_empty(text: str | None) -> str:
    """`text` when it is usable prose, otherwise "".

    Returning "" rather than raising is deliberate: a brief without a sentence is
    valid and already rendered honestly, while a hard failure would take the
    deterministic figures down with it. The figures are the part that matters.
    """
    return salvage_reply(text)
