"""Central configuration. Change models / presets here, not in the logic files."""

import os

# Turn off CrewAI's anonymous telemetry (keeps the app quiet and faster on cloud).
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

# CrewAI reaches Groq through LiteLLM: "groq/" (provider) + Groq's own model ID.
# Groq's model ID is "openai/gpt-oss-120b", so the full string has two slashes.
MODEL_NAME = "groq/openai/gpt-oss-120b"
TEMPERATURE = 0.3

# How thorough the agent should be for each option shown in the UI.
DEPTH_PRESETS = {
    "Quick":    {"searches": 3, "words": "500-700"},
    "Standard": {"searches": 5, "words": "900-1200"},
    "Deep":     {"searches": 8, "words": "1500-2000"},
}
