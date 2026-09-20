"""AI Research Agent - a single CrewAI agent that researches a topic and writes a report."""

# Import config FIRST: it disables CrewAI telemetry before crewai is imported.
from . import config  # noqa: F401
from .config import DEPTH_PRESETS
from .crew import run_research

__all__ = ["DEPTH_PRESETS", "run_research"]
