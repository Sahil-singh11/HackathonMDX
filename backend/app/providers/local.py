"""Local (edge) provider gate.

'local' mode may only be reported after a real local Gemma model has loaded.
No model is bundled; until a team member runs a real quantised Gemma E2B/E4B
within the documented memory budget, this provider reports unavailable and the
caller falls back (with disclosure). Never simulates edge inference.
"""
from __future__ import annotations


class LocalUnavailable(Exception):
    pass


LOCAL_MODEL_LOADED = False  # flipped only by a real successful model load


def analyse(*args, **kwargs):
    raise LocalUnavailable(
        "No local Gemma model is loaded. Edge inference is only reported after a real local model run."
    )
