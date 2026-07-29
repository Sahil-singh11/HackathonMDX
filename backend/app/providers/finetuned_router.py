"""FineTunedE2BRouterProvider — optional specialised router.

Scope (deliberately narrow):
  - Morisyen intent classification
  - allow-listed function selection
  - argument generation
  - offline / edge structured routing

NOT its responsibility, ever:
  - authoritative fish identification
  - legal decisions
  - verified measurement
  - marine safety advice
  - official ministry submission

Hosted `gemma-4-26b-a4b-it` keeps catch-image understanding; the deterministic rules
engine keeps every legality decision.

This provider stays DISABLED unless a tuned adapter is present *and* it passed the Step-3
acceptance gate. `readiness()` reports why it is unavailable rather than silently
degrading, and the dispatcher never selects it by default.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.prompts.compact_router_v1 import (ALLOWED_INTENTS, COMPACT_ROUTER_PROMPT,
                                           COMPACT_ROUTER_VERSION, ROUTABLE_TOOLS)

BASE_MODEL = "google/gemma-4-E2B-it"

# Written by the Kaggle run and copied in by scripts/kaggle_download_ai_outputs.ps1.
# Newest first: readiness reports the LATEST gate decision (v2), falling back to v1
# only if no v2 outputs exist locally.
ADAPTER_DIRNAMES = ("e2b_router_v2", "e2b_router")
GATE_FILE = "evaluation_metrics.json"


class RouterUnavailable(Exception):
    """Raised when routing is requested but no accepted adapter is loaded."""


@dataclass
class RouterStatus:
    available: bool
    reason: str
    adapter_path: str | None = None
    base_model: str = BASE_MODEL
    compact_prompt_version: str = COMPACT_ROUTER_VERSION
    gate_passed: bool | None = None
    intent_accuracy: float | None = None
    tool_accuracy: float | None = None
    improvement_pp: float | None = None
    real_inference: bool = False
    simulated: bool = False

    def as_dict(self) -> dict:
        return {
            "provider_name": "finetuned-e2b-router",
            "available": self.available,
            "reason": self.reason,
            "base_model": self.base_model,
            "adapter_path": self.adapter_path,
            "compact_prompt_version": self.compact_prompt_version,
            "gate_passed": self.gate_passed,
            "intent_accuracy": self.intent_accuracy,
            "tool_accuracy": self.tool_accuracy,
            "improvement_pp": self.improvement_pp,
            "real_inference": self.real_inference,
            "simulated": self.simulated,
            "scope": ["intent_classification", "function_selection", "argument_generation",
                      "offline_routing"],
            "never_responsible_for": ["authoritative_species_identification", "legal_decisions",
                                      "verified_measurement", "marine_safety",
                                      "official_ministry_submission"],
        }


def _adapter_dir() -> Path:
    base = get_settings().storage_dir.parent / "kaggle" / "outputs"
    for name in ADAPTER_DIRNAMES:
        if (base / name).exists():
            return base / name
    return base / ADAPTER_DIRNAMES[0]


def readiness() -> RouterStatus:
    """Why the router is or is not usable. Never raises."""
    d = _adapter_dir()
    if not d.exists():
        return RouterStatus(False, "no adapter downloaded; run scripts/kaggle_download_ai_outputs.ps1")

    weights = list(d.rglob("adapter_model.safetensors")) + list(d.rglob("adapter_model.bin"))
    if not weights:
        return RouterStatus(False, f"no adapter weights found under {d}", adapter_path=str(d))

    gate_files = list(d.rglob(GATE_FILE))
    if not gate_files:
        return RouterStatus(False, "adapter present but no evaluation_metrics.json — "
                                   "the acceptance gate was never evaluated",
                            adapter_path=str(d))

    try:
        metrics = json.loads(gate_files[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return RouterStatus(False, f"unreadable metrics ({type(e).__name__})", adapter_path=str(d))

    # v2 metrics carry gate_a/gate_b; v1 carries only acceptance_gate. The router may
    # only be enabled by an explicit pre-registered gate pass (A or B).
    gate = metrics.get("gate_a") or metrics.get("acceptance_gate") or {}
    gate_b = metrics.get("gate_b") or {}
    tuned = metrics.get("tuned_internal") or {}
    untuned = metrics.get("untuned_internal") or {}
    accepted = bool(gate.get("ACCEPTED")) or bool(gate_b.get("ACCEPTED"))
    improvement = None
    if tuned.get("intent_accuracy") is not None and untuned.get("intent_accuracy") is not None:
        improvement = round(100 * (tuned["intent_accuracy"] - untuned["intent_accuracy"]), 1)

    if not accepted:
        failed = [k for k, v in gate.items() if k != "ACCEPTED" and v is False]
        return RouterStatus(
            False,
            "adapter REJECTED by the pre-registered acceptance gate: " + (", ".join(failed) or "see report"),
            adapter_path=str(d), gate_passed=False,
            intent_accuracy=tuned.get("intent_accuracy"),
            tool_accuracy=tuned.get("tool_accuracy"), improvement_pp=improvement)

    return RouterStatus(True, "adapter present and accepted", adapter_path=str(d),
                        gate_passed=True, intent_accuracy=tuned.get("intent_accuracy"),
                        tool_accuracy=tuned.get("tool_accuracy"), improvement_pp=improvement,
                        real_inference=True)


def build_messages(user_text: str, available_tools: list[str] | None = None) -> list[dict]:
    """Exactly the format the adapter was trained on — same frozen compact prompt."""
    tools = available_tools or list(ROUTABLE_TOOLS)
    return [
        {"role": "system", "content": COMPACT_ROUTER_PROMPT},
        {"role": "user", "content": f"Tools available: {', '.join(tools)}\n\n"
                                    f"Fisher message: {user_text}"},
    ]


def validate_route(raw: dict | None) -> dict:
    """Server-side validation of a routing decision. The adapter is never trusted blindly.

    Anything outside the frozen vocabularies is dropped, exactly as with the hosted
    provider: an unknown intent becomes `other`, an unknown tool becomes None.
    """
    from app.tools.registry import REGISTRY

    if not isinstance(raw, dict):
        return {"intent": "other", "tool": None, "arguments": {},
                "needs_more_information": True, "rejected": ["unparseable"]}

    rejected: list[str] = []
    intent = raw.get("intent")
    if intent not in ALLOWED_INTENTS:
        rejected.append(f"intent:{intent!r}")
        intent = "other"

    tool = raw.get("tool")
    if tool is not None and (tool not in ROUTABLE_TOOLS or tool not in REGISTRY):
        rejected.append(f"tool:{tool!r}")
        tool = None

    args = raw.get("arguments")
    if not isinstance(args, dict):
        args = {}

    return {
        "intent": intent,
        "tool": tool,
        "arguments": args,
        "needs_more_information": bool(raw.get("needs_more_information")),
        "rejected": rejected,
    }


def route(user_text: str, available_tools: list[str] | None = None) -> dict:
    """Route one message. Raises RouterUnavailable unless an accepted adapter is loaded.

    Deliberately refuses rather than falling back silently: a caller that wanted the
    fine-tuned router must know it did not get it.
    """
    status = readiness()
    if not status.available:
        raise RouterUnavailable(status.reason)
    raise RouterUnavailable(
        "adapter accepted but local inference is not wired up in this environment "
        "(no local GPU); use the hosted provider or run routing on Kaggle")
