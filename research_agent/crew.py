"""Builds the single research agent and runs it."""

from crewai import Agent, Crew, LLM, Process, Task

from .compat import apply_groq_patches
from .config import DEPTH_PRESETS, MODEL_NAME, TEMPERATURE
from .tools import web_search

# Work around CrewAI sending a field ("cache_breakpoint") that Groq rejects.
apply_groq_patches()


def _build_agent(api_key: str, searches: int) -> Agent:
    llm = LLM(model=MODEL_NAME, api_key=api_key, temperature=TEMPERATURE)
    return Agent(
        role="Senior Research Analyst",
        goal="Produce accurate, well-structured research reports grounded in web sources.",
        backstory=(
            "You are a meticulous analyst. You search the web, cross-check claims "
            "across sources, and never invent facts or URLs. When sources disagree "
            "or information is thin, you say so plainly."
        ),
        tools=[web_search],
        llm=llm,
        allow_delegation=False,
        max_iter=searches + 4,  # safety cap so the agent cannot loop forever
        verbose=False,
    )


def _build_task(agent: Agent, searches: int, words: str) -> Task:
    # NOTE: "{topic}" is filled in by crew.kickoff(inputs={"topic": ...}).
    description = f"""Research the topic: {{topic}}

Process:
1. Run about {searches} different searches with the duckduckgo_search tool. Every call
   must include a "query" string. Cover different angles (background, current state,
   key players, recent developments, risks/debates).
2. Only use facts that appear in the search results. Never fabricate URLs.
3. Write the final report in Markdown, {words} words.

Required structure:
# <Report title>
## Executive Summary
## Key Findings  (bullet points)
## Detailed Analysis  (use sub-headings)
## Challenges & Open Questions
## Conclusion
## Sources  (a numbered list of the URLs you actually used)
"""
    return Task(
        description=description,
        expected_output="A complete, well-formatted Markdown research report with a Sources section.",
        agent=agent,
    )


def run_research(topic: str, api_key: str, depth: str = "Standard") -> str:
    """Research `topic` and return the report as a Markdown string."""
    preset = DEPTH_PRESETS[depth]
    agent = _build_agent(api_key, preset["searches"])
    task = _build_task(agent, preset["searches"], preset["words"])

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    result = crew.kickoff(inputs={"topic": topic})
    return result.raw
