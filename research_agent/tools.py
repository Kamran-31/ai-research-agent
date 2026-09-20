"""Tools the agent can call. Here: a free DuckDuckGo web search (no API key)."""

from crewai.tools import tool
from ddgs import DDGS

MAX_RESULTS = 4
SNIPPET_CHARS = 250  # keep snippets short so we stay inside Groq's token limits


@tool("DuckDuckGo Search")
def web_search(query: str = "", cursor: int = 0, id: int = 0) -> str:  # noqa: A002
    """Search the web with DuckDuckGo.

    Always pass a "query": a focused search phrase (3-10 words).
    The "cursor" and "id" arguments are ignored; never use them.
    Returns a list of results with title, URL and a short snippet.
    """
    query = (query or "").strip()
    if not query:
        return (
            "Error: no query was given. This tool cannot open pages by id. "
            "Call it again with a 'query' string, or write the report from the "
            "results you already have."
        )

    try:
        results = DDGS().text(query, max_results=MAX_RESULTS)
    except Exception as exc:  # network errors, rate limits, etc.
        return f"Search failed ({exc}). Try a different or shorter query."

    if not results:
        return "No results found. Try rephrasing the query."

    lines = []
    for r in results:
        snippet = (r.get("body") or "")[:SNIPPET_CHARS]
        lines.append(f"- {r.get('title', 'Untitled')}\n  URL: {r.get('href', '')}\n  {snippet}")
    return "\n".join(lines)
