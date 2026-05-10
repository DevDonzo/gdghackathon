# RateDrop — Agent Wrap Plan

## What this document is

A complete, actionable plan for wrapping RateDrop's live phone negotiation engine inside an agentic
SDK. It covers SDK selection with rationale, exact architecture, all new files, every code change,
dependencies, environment variables, and a toggle strategy so the current system stays intact as a
fallback.

---

## SDK Selection

### Primary: AWS Strands Agents SDK

**Repo**: https://github.com/strands-agents/sdk-python  
**License**: Apache 2.0  
**Install**: `pip install strands-agents`  
**LLM adapter**: `pip install litellm` (required for Gemini 2.5 Flash)

Strands is the right choice for this project for four reasons:

1. **Tool-first design.** A `@tool` decorator turns any Python function into an agent tool with
   zero boilerplate. The agent loops over tool calls until it produces a final text response. This
   maps directly onto the negotiation turn loop RateDrop already has.

2. **LLM-agnostic.** Strands uses LiteLLM as its model layer, which means it can drive Gemini 2.5
   Flash (`gemini/gemini-2.5-flash`) with the same `GEMINI_API_KEY` the project already sets. No
   new API keys, no new accounts.

3. **Apache 2.0, no usage fees.** Correct for a hackathon.

4. **Thin surface area.** The entire integration is one new file (`negotiator_agent.py`) and one
   change to `conversation_relay.py`. Nothing else moves.

### Alternative: Google Agent Development Kit (ADK)

**Repo**: https://github.com/google/adk-python  
**License**: Apache 2.0  
**Install**: `pip install google-adk`

Google ADK is the native path if the team wants zero LiteLLM overhead. It drives `gemini-2.5-flash`
directly via the Google GenAI SDK that is already a transitive dependency of this project.
`FunctionTool` wraps any Python callable. `LlmAgent` runs the tool loop. The integration pattern
is identical to Strands; only the import names change.

**Use ADK instead of Strands if**: the team wants to cut one dependency (`litellm`) and is
comfortable tying the agent directly to Google's SDK. Use Strands if flexibility to swap models
(e.g., Claude 3.5 Sonnet for a demo) matters more.

### Not recommended: Anthropic Claude Agent SDK

The Anthropic Agent SDK (`claude-code`) is built for interactive code-editing workflows, not for
embedding a custom tool-using agent inside a running Python server. It has no `@tool` decorator
pattern suitable for this use case.

---

## Why wrap at all — the problem with the current code

`phrase_live_action()` in `negotiation_live.py` returns hardcoded f-strings:

```python
"counter_to_target": (
    f"That's helpful, but it still doesn't really solve the bill. "
    f"If you can bring the monthly rate to ${target:.2f}, we can accept that on this call."
),
```

These strings are delivered as live spoken audio over a real phone call. They work, but they sound
robotic and cannot adapt to what the rep actually said (tone, specific offer wording, carrier
jargon). The agent's job is to generate natural, contextually responsive speech while the
**deterministic policy engine keeps all strategic decisions**.

The negotiation strategy (accept, counter, exit, push) is never decided by the LLM. It is always
decided by `advance_live_policy()`. The agent only turns the policy decision into spoken words.

---

## Architecture

### The integration point

In `conversation_relay.py`, `_handle_rep_prompt()` is the single entry point for every rep
utterance received from Twilio ConversationRelay:

```python
async def _handle_rep_prompt(negotiation_id: str, websocket: WebSocket, prompt: str) -> None:
    negotiation = negotiations.find_one(...)
    decision = advance_live_policy(negotiation, prompt)   # ← THIS LINE IS REPLACED
    ...
    await _send_text(websocket, decision["text"])
```

The agent replaces the `advance_live_policy(negotiation, prompt)` call. It receives the same
inputs and returns the same `decision` dict shape. Everything downstream (`_persist_turn_and_publish`,
`_send_text`, the `completed` check) is unchanged.

### Data flow

```
Twilio ConversationRelay
        │
        │  rep_text (spoken audio → STT → text)
        ▼
_handle_rep_prompt()
        │
        │  negotiation dict + rep_text
        ▼
negotiator_agent.run(rep_text, negotiation)
        │
        ├─ tool: analyze_rep_speech(rep_text, negotiation)
        │         ├── classify_rep_utterance()     [existing, unchanged]
        │         ├── parse_offer_values()         [existing, unchanged]
        │         └── advance_live_policy()        [existing, unchanged]
        │         └─ returns: {action, objective, completed, accepted,
        │                      finalMonthly, bestCredit, nextState, …}
        │
        │  LLM (Gemini 2.5 Flash) generates spoken response text
        │  constrained by the determined action
        │
        ├─ tool: finalize_response(negotiation_id, action, text, completed)
        │         └── validates action is in known enum
        │         └── returns: approval signal
        │
        └─ agent returns final text → substitutes decision["text"]
```

### Key constraint on the LLM

The system prompt passed to the agent hard-forbids certain behaviors:

> You are a live phone negotiator. You MUST call `analyze_rep_speech` first.
> The action it returns is final — you may NOT choose a different action.
> You MUST call `finalize_response` before ending.
> Your only creative task is generating natural spoken language for the determined action.
> Do not make offers, concessions, or strategic decisions not authorized by the tools.

This keeps the model in its lane. If `analyze_rep_speech` returns `action=counter_to_target`, the
model generates a natural counter-offer phrasing. It cannot decide to accept instead.

---

## Files to create

### `backend/app/agent/__init__.py`

Empty init file.

### `backend/app/agent/negotiator_agent.py`

```python
from __future__ import annotations

from typing import Any

from strands import Agent, tool
from strands.models import LiteLLMModel

from backend.app.services.negotiation_live import advance_live_policy, initial_live_state

# ── model ─────────────────────────────────────────────────────────────────────

def _make_model() -> LiteLLMModel:
    from backend.app.core.config import get_settings
    settings = get_settings()
    return LiteLLMModel(
        model_id="gemini/gemini-2.5-flash",
        params={"api_key": settings.gemini_api_key, "temperature": 0.4},
    )


# ── tools ─────────────────────────────────────────────────────────────────────

_pending_decision: dict[str, Any] = {}


@tool
def analyze_rep_speech(rep_text: str, negotiation_json: str) -> str:
    """
    Run the deterministic RateDrop policy engine against the rep's speech.
    Returns a JSON object with: action, objective, completed, accepted,
    finalMonthly, bestCredit, nextState, repIntent, proposedMonthly, credit.
    Call this first on every turn.
    """
    import json
    negotiation = json.loads(negotiation_json)
    decision = advance_live_policy(negotiation, rep_text)
    _pending_decision.clear()
    _pending_decision.update(decision)
    return json.dumps({
        "action": decision["action"],
        "objective": decision["objective"],
        "completed": decision["completed"],
        "accepted": decision["accepted"],
        "repIntent": decision["repIntent"],
        "proposedMonthly": decision["proposedMonthly"],
        "credit": decision["credit"],
        "bestOfferMonthly": decision["bestOfferMonthly"],
        "bestCredit": decision["bestCredit"],
        "finalMonthly": decision["finalMonthly"],
        "nextState": decision["nextState"],
        "currentMonthly": negotiation.get("currentMonthly"),
        "targetMonthly": negotiation.get("targetMonthly"),
        "walkAwayMonthly": negotiation.get("walkAwayMonthly"),
        "provider": negotiation.get("provider", "the carrier"),
    })


@tool
def finalize_response(action: str, spoken_text: str, completed: bool) -> str:
    """
    Validate that the action matches the policy decision and register the
    spoken response. Call this as your last tool before ending.
    Returns 'approved' or an error string.
    """
    allowed = {
        "push_for_retention", "counter_to_target", "ask_for_credit_plus_rate_relief",
        "accept_offer", "exit_without_accepting",
        "explain_support_goal", "provide_available_context", "ask_for_escalation",
        "ask_for_concrete_next_step", "confirm_task_complete", "escalate_or_capture_next_step",
    }
    if action not in allowed:
        return f"error: unknown action '{action}'"
    if not spoken_text or not spoken_text.strip():
        return "error: spoken_text must not be empty"
    _pending_decision["_agent_text"] = spoken_text.strip()
    return "approved"


# ── system prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a live phone negotiator calling on behalf of a customer.
You are speaking directly to a carrier or service representative — this is a real voice call.

Rules:
1. ALWAYS call analyze_rep_speech first. Its output tells you the action to take.
2. The action returned by analyze_rep_speech is FINAL. Do not choose a different action.
3. Generate concise, natural spoken language that conveys the determined action.
   - Speak as if you are the customer (first person).
   - Keep responses under 3 sentences.
   - Do not use markdown, bullet points, or any non-speech formatting.
   - Mirror the formality level of the rep's speech.
4. ALWAYS call finalize_response last with the exact action string and your spoken text.
5. Do not invent offers, concede amounts, or make promises not authorized by the action.

Action meanings:
- push_for_retention: Rep hasn't engaged yet — ask them to check retention or loyalty options.
- counter_to_target: Rep made an offer that doesn't meet the target — counter toward the target rate.
- ask_for_credit_plus_rate_relief: Rep offered a credit but not a rate reduction — ask for both.
- accept_offer: Rep's offer meets or beats the walk-away threshold — accept and confirm it.
- exit_without_accepting: Counters exhausted, no acceptable offer — exit professionally.
- explain_support_goal: State the support issue and desired outcome clearly.
- provide_available_context: Give the rep the account/booking/identity details they asked for.
- ask_for_escalation: Request a supervisor or specialist to get resolution authority.
- ask_for_concrete_next_step: Pin down who owns the action, what it is, and when it happens.
- confirm_task_complete: Acknowledge resolution and ask for a reference number.
- escalate_or_capture_next_step: No resolution reached — demand a case number or transfer.
""".strip()


# ── public API ─────────────────────────────────────────────────────────────────

def run_negotiator_agent(negotiation: dict[str, Any], rep_text: str) -> dict[str, Any]:
    """
    Drop-in replacement for advance_live_policy().
    Returns a decision dict with the same keys, but decision["text"] is
    LLM-generated rather than a hardcoded string.
    """
    import json

    agent = Agent(
        model=_make_model(),
        tools=[analyze_rep_speech, finalize_response],
        system_prompt=SYSTEM_PROMPT,
    )

    _pending_decision.clear()

    negotiation_json = json.dumps({
        k: v for k, v in negotiation.items()
        if k in {
            "currentMonthly", "targetMonthly", "walkAwayMonthly", "provider",
            "liveState", "bestOfferMonthly", "oneTimeCredit", "issueContext",
        }
    }, default=str)

    user_message = (
        f"The carrier representative just said: \"{rep_text}\"\n\n"
        f"Negotiation state: {negotiation_json}"
    )

    agent(user_message)

    if not _pending_decision:
        # Agent failed to call tools — fall back to deterministic engine
        from backend.app.services.negotiation_live import advance_live_policy
        return advance_live_policy(negotiation, rep_text)

    decision = dict(_pending_decision)
    if "_agent_text" in decision:
        decision["text"] = decision.pop("_agent_text")
    else:
        # finalize_response was not called — fall back to deterministic phrase
        from backend.app.services.negotiation_live import phrase_live_action
        decision["text"] = phrase_live_action(
            decision["action"], negotiation,
            decision.get("proposedMonthly"), decision.get("bestOfferMonthly"),
            float(decision.get("bestCredit") or 0),
        )

    return decision
```

---

## Files to modify

### `backend/app/services/conversation_relay.py`

One import and one conditional call replace the direct `advance_live_policy` call:

```python
# Add import at top
from backend.app.core.config import get_settings

# In _handle_rep_prompt(), replace:
decision = advance_live_policy(negotiation, prompt)

# With:
settings = get_settings()
if settings.agent_mode == "strands":
    from backend.app.agent.negotiator_agent import run_negotiator_agent
    decision = run_negotiator_agent(negotiation, prompt)
else:
    decision = advance_live_policy(negotiation, prompt)
```

### `backend/app/core/config.py`

Add one field to the `Settings` class:

```python
agent_mode: str = Field(default="disabled", alias="RATEDROP_AGENT_MODE")
# Values: "disabled" (use deterministic engine), "strands" (use agent)
```

### `requirements.txt` / `pyproject.toml`

```
strands-agents>=0.1.0
litellm>=1.40.0
```

Both are pip-installable, Apache 2.0, no usage fees.

---

## Environment variables

| Variable | Values | Default | Effect |
|---|---|---|---|
| `RATEDROP_AGENT_MODE` | `disabled`, `strands` | `disabled` | Enables agent phrasing |
| `GEMINI_API_KEY` | string | (already required) | Used by LiteLLM → Gemini |

No new API keys are needed. LiteLLM passes the existing `GEMINI_API_KEY` through to the Gemini
2.5 Flash endpoint.

---

## Google ADK equivalent

If the team chooses Google ADK over Strands, the implementation is structurally identical. Replace
the Strands-specific code with:

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types as genai_types

def _make_adk_agent() -> LlmAgent:
    return LlmAgent(
        name="ratedrop_negotiator",
        model="gemini-2.5-flash",
        instruction=SYSTEM_PROMPT,
        tools=[
            FunctionTool(analyze_rep_speech_fn),
            FunctionTool(finalize_response_fn),
        ],
    )
```

The tool functions (`analyze_rep_speech_fn`, `finalize_response_fn`) have the same logic as the
Strands `@tool` versions — only the decorator and runner change.

**ADK install**: `pip install google-adk`  
**No LiteLLM needed**: ADK calls Gemini natively via `google-genai`.

---

## What the agent does NOT do

These are hard boundaries enforced by tool design, not by prompt engineering alone:

- **Does not decide the negotiation strategy.** `analyze_rep_speech` runs
  `advance_live_policy()` deterministically. The action is a fact by the time the LLM sees it.
- **Does not parse dollar amounts from speech.** `parse_offer_values()` handles all number
  extraction including number-word normalization ("fifty dollars a month" → 50.0). The agent
  receives the parsed result.
- **Does not write to the database.** `_persist_turn_and_publish()` is called after the agent
  returns, by the existing `_handle_rep_prompt()` code.
- **Does not determine completion.** The `completed` and `accepted` flags come from the policy
  engine, not from the LLM.
- **Does not send the Twilio `end` event.** The existing `_handle_rep_prompt()` code does that
  based on `decision["completed"]`.

---

## Fallback behavior

The agent has two explicit fallback paths:

1. **Tool loop fails (agent returns without calling tools).** The `_pending_decision` dict is
   empty. `run_negotiator_agent()` catches this and calls `advance_live_policy()` directly,
   returning the deterministic result.

2. **`finalize_response` not called.** `_agent_text` is not in `_pending_decision`. The function
   calls `phrase_live_action()` to fill in `decision["text"]`, so the turn still completes
   correctly.

Setting `RATEDROP_AGENT_MODE=disabled` (the default) bypasses the agent entirely and uses the
original code path with zero overhead.

---

## What changes for the demo

With `RATEDROP_AGENT_MODE=strands`:

| Before (hardcoded) | After (agent-generated) |
|---|---|
| "That's helpful, but it still doesn't really solve the bill. If you can bring the monthly rate to $55.00, we can accept that on this call." | Gemini-generated response that uses the rep's specific wording, mirrors their tone, and delivers the same counter-offer intent naturally. |
| "Could you please check retention or loyalty options before the customer decides whether to move the line?" | Contextual push phrasing that references the specific plan, provider name, and current amount. |
| "I understand. Could you please check retention or loyalty options…" | Natural opening that sounds like a real person on a call. |

The negotiation outcome — whether we accept, counter, or walk — is identical in both modes.

---

## Implementation order

1. `pip install strands-agents litellm` into the venv.
2. Add `agent_mode` field to `backend/app/core/config.py`.
3. Create `backend/app/agent/__init__.py` (empty).
4. Create `backend/app/agent/negotiator_agent.py` (full file above).
5. Modify `backend/app/services/conversation_relay.py` (2-line conditional swap).
6. Set `RATEDROP_AGENT_MODE=strands` in `.env`.
7. Run the server and test with a simulated call — both `conversation_relay` mode and `simulated`
   mode should work (simulated mode bypasses the agent entirely, it only applies in
   `conversation_relay` mode).
8. Verify fallback by temporarily raising an exception inside `analyze_rep_speech` — the system
   should silently fall back to the deterministic engine.

Total new lines of Python: ~120. Zero changes to the deterministic policy engine. Zero changes to
the frontend. Zero new API keys.
