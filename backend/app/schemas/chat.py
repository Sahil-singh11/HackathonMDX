"""Wire types for the conversational assistant (POST /api/ai/chat).

Separate from `analysis.py` on purpose. `AnalyseCatchResponse` is a catch
record's analysis and must stay that; a chat turn is prose plus the provenance
needed to judge it, and merging the two would put engineering telemetry into a
contract that officers read.

Every field here is safe to render. There is no prompt text, no chain of
thought, no API key, and — as in the console — argument NAMES only, never
argument values, because those can carry the fisher's own data.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analysis import ConsoleError, FunctionTraceEntry

# Bounded so a runaway client cannot push an unbounded transcript through the
# model. Twelve turns is roughly six exchanges, which is longer than any
# question a fisher has actually needed on a boat.
MAX_HISTORY_MESSAGES = 12
MAX_MESSAGE_CHARS = 1000


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_HISTORY_MESSAGES,
                                        description="Conversation so far, oldest first. "
                                                    "The last message must be from the fisher.")
    language: Literal["en", "mfe"] = "mfe"


class ChatResponse(BaseModel):
    reply: str = ""
    provider: str = ""
    model: str = ""
    #: False whenever the answer came from the deterministic grounded responder
    #: rather than a Gemma call. The UI must show this distinction, not hide it.
    real_inference: bool = False
    latency_ms: int = 0
    functions_called: list[str] = Field(default_factory=list)
    function_trace: list[FunctionTraceEntry] = Field(default_factory=list)
    #: Rule ids the deterministic responder answered from, so a fisher can check
    #: them in the Fishing rules page. Empty on a model-generated answer, whose
    #: grounding is the tool trace instead.
    cited_rules: list[str] = Field(default_factory=list)
    disclosures: list[str] = Field(default_factory=list)
    #: True when no model ran. Paired with a label the UI shows verbatim.
    grounded_only: bool = False
    grounded_label: str = ""
    controlled_error: ConsoleError | None = None
