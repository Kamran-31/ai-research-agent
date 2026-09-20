"""Tools the agent can call. Here: a free DuckDuckGo web search (no API key)."""

from crewai.tools import tool
from ddgs import DDGS

MAX_RESULTS = 4
SNIPPET_CHARS = 250  # keep snippets short so we stay inside Groq's token limits


@tool("DuckDuckGo Search")
def web_search(query: str) -> str:
    """Search the web with DuckDuckGo.

    Always call this with a "query" argument: a focused search phrase (3-10 words).
    Output: a numbered list of results with title, URL and a short snippet.
    """
    try:
        results = DDGS().text(query, max_results=MAX_RESULTS)
    except Exception as exc:  # network errors, rate limits, etc.
        return f"Search failed ({exc}). Try a different or shorter query."

    if not results:
        return "No results found. Try rephrasing the query."

    lines = []
    for i, r in enumerate(results, start=1):
        snippet = (r.get("body") or "")[:SNIPPET_CHARS]
        lines.append(f"[{i}] {r.get('title', 'Untitled')}\nURL: {r.get('href', '')}\n{snippet}")
    return "\n\n".join(lines)
