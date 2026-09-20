"""Compatibility patch for CrewAI 1.15.x + Groq.

Problem: CrewAI adds an Anthropic-only marker key ("cache_breakpoint") to the
messages it sends. Anthropic understands it; Groq rejects it with:
    'messages.0': property 'cache_breakpoint' is unsupported
This is a known upstream bug (crewAIInc/crewAI issue #5886). Until it is fixed,
we (1) stop the marker being added and (2) strip it right before sending.
Each step is independent and fails silently, so a future CrewAI fix won't break us.
"""

import asyncio
import functools
import sys

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

        setattr(wrapper, _FLAG, True)
        setattr(litellm, name, wrapper)


def apply_groq_patches() -> None:
    for step in (_disable_marker_injection, _patch_crewai_llm, _patch_litellm):
        try:
            step()
        except Exception:  # never let a compatibility helper crash the app
            pass
