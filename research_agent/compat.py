"""Compatibility patches for CrewAI 1.15.x + Groq.

Patch 1 - cache_breakpoint (see below).
Patch 2 - automatic retry when Groq's free-tier tokens-per-minute limit is hit.

Problem: CrewAI adds an Anthropic-only marker key ("cache_breakpoint") to the
messages it sends. Anthropic understands it; Groq rejects it with:
    'messages.0': property 'cache_breakpoint' is unsupported
This is a known upstream bug (crewAIInc/crewAI issue #5886). Until it is fixed,
we (1) stop the marker being added and (2) strip it right before sending.
Each step is independent and fails silently, so a future CrewAI fix won't break us.
"""

import asyncio
import functools
import re
import sys
import threading
import time

_KEY = "cache_breakpoint"
_FLAG = "_research_agent_patched"


def _strip(messages):
    """Return a copy of `messages` without the cache_breakpoint key."""
    if not isinstance(messages, list):
        return messages
    return [
        {k: v for k, v in m.items() if k != _KEY} if isinstance(m, dict) else m
        for m in messages
    ]


# ---------------------------------------------------------------- rate limits
_MAX_ATTEMPTS = 6
_MAX_WAIT = 75.0  # seconds; longer waits usually mean a DAILY limit, so give up
_state = threading.local()


def _is_retryable(exc: Exception) -> bool:
    text = str(exc)
    return (
        "RateLimitError" in type(exc).__name__
        or "rate_limit_exceeded" in text
        or "tool_use_failed" in text  # model emitted a badly formed tool call
    )


def _wait_seconds(exc: Exception) -> float:
    """Read Groq's 'Please try again in 13.9s' hint (also handles 1m5s / 850ms)."""
    if "tool_use_failed" in str(exc):
        return 1.0  # no need to wait; just ask the model again
    m = re.search(r"try again in (?:(\d+)m)?\s*([\d.]+)(ms|s)", str(exc))
    if not m:
        return 15.0
    minutes = int(m.group(1) or 0)
    value = float(m.group(2)) / (1000 if m.group(3) == "ms" else 1)
    return minutes * 60 + value + 1.0


def _with_retry(fn):
    """Retry `fn` when Groq says 'rate limit', waiting as long as Groq asks."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if getattr(_state, "active", False):  # already inside a retrying call
            return fn(*args, **kwargs)
        _state.active = True
        try:
            for attempt in range(1, _MAX_ATTEMPTS + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    if not _is_retryable(exc) or attempt == _MAX_ATTEMPTS:
                        raise
                    wait = _wait_seconds(exc)
                    if wait > _MAX_WAIT:
                        raise
                    time.sleep(wait)
        finally:
            _state.active = False

    setattr(wrapper, _FLAG, True)
    return wrapper


def _patch_retry() -> None:
    from crewai.llm import LLM

    original = getattr(LLM, "call", None)
    if original is not None and not getattr(original, _FLAG, False):
        LLM.call = _with_retry(original)


# ------------------------------------------------------- cache_breakpoint bug

def _disable_marker_injection() -> None:
    """Replace mark_cache_breakpoint() with a no-op everywhere it was imported."""
    import crewai.llms.cache  # noqa: F401  (make sure the module is loaded)

    def _noop(msg, *args, **kwargs):
        return msg

    for name, module in list(sys.modules.items()):
        if name.startswith("crewai") and hasattr(module, "mark_cache_breakpoint"):
            setattr(module, "mark_cache_breakpoint", _noop)


def _patch_crewai_llm() -> None:
    """Strip the marker from the parameters CrewAI hands to LiteLLM."""
    from crewai.llm import LLM

    original = getattr(LLM, "_prepare_completion_params", None)
    if original is None or getattr(original, _FLAG, False):
        return

    @functools.wraps(original)
    def patched(self, *args, **kwargs):
        params = original(self, *args, **kwargs)
        if isinstance(params, dict) and "messages" in params:
            params["messages"] = _strip(params["messages"])
        return params

    setattr(patched, _FLAG, True)
    LLM._prepare_completion_params = patched


def _patch_litellm() -> None:
    """Last line of defence: strip the marker inside litellm.completion itself."""
    import litellm

    for name in ("completion", "acompletion"):
        original = getattr(litellm, name, None)
        if original is None or getattr(original, _FLAG, False):
            continue

        if asyncio.iscoroutinefunction(original):
            @functools.wraps(original)
            async def wrapper(*args, __orig=original, **kwargs):
                if "messages" in kwargs:
                    kwargs["messages"] = _strip(kwargs["messages"])
                return await __orig(*args, **kwargs)
        else:
            @functools.wraps(original)
            def wrapper(*args, __orig=original, **kwargs):
                if "messages" in kwargs:
                    kwargs["messages"] = _strip(kwargs["messages"])
                return __orig(*args, **kwargs)

            wrapper = _with_retry(wrapper)

        setattr(wrapper, _FLAG, True)
        setattr(litellm, name, wrapper)


def apply_groq_patches() -> None:
    for step in (_disable_marker_injection, _patch_crewai_llm, _patch_litellm, _patch_retry):
        try:
            step()
        except Exception:  # never let a compatibility helper crash the app
            pass
