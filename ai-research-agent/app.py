"""Streamlit front-end for the AI Research Agent."""

import os
import re
import time
from datetime import date

import streamlit as st
from dotenv import load_dotenv

from research_agent import DEPTH_PRESETS, run_research

load_dotenv()  # reads .env when running locally; harmless on Streamlit Cloud

st.set_page_config(page_title="AI Research Agent", page_icon="🔎", layout="wide")


def get_api_key() -> str:
    """Streamlit secrets first (cloud), then environment / .env (local)."""
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.getenv("GROQ_API_KEY", "")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50] or "report"


# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = get_api_key()
    if not api_key:
        api_key = st.text_input("Groq API key", type="password", help="Get a free key at console.groq.com")
    else:
        st.success("Groq API key loaded", icon="🔑")

    depth = st.radio(
        "Research depth",
        list(DEPTH_PRESETS),
        index=1,
        help="Deeper = more searches and a longer report (slower, uses more tokens).",
    )
    st.divider()
    st.caption("Built with CrewAI · Groq (gpt-oss-120b) · DuckDuckGo · Streamlit")

# ---------- Main ----------
st.title("🔎 AI Research Agent")
st.write("Enter any topic. A single AI agent will search the web and write a structured report.")

topic = st.text_input(
    "Research topic",
    placeholder="e.g. Solid-state batteries for electric vehicles",
)

if st.button("Generate report", type="primary", disabled=not topic.strip()):
    if not api_key:
        st.error("Please add your Groq API key in the sidebar.")
    else:
        start = time.time()
        try:
            with st.status("Agent is researching. This can take 30-90 seconds…", expanded=True) as status:
                st.write("🔍 Searching the web and analysing sources…")
                report = run_research(topic.strip(), api_key, depth)
                status.update(label=f"Report ready in {time.time() - start:.0f}s", state="complete", expanded=False)
            st.session_state["report"] = report
            st.session_state["topic"] = topic.strip()
        except Exception as exc:
            st.error(f"Something went wrong: {exc}")
            st.info("Common causes: invalid API key, Groq rate limit (wait a minute and retry), or a DuckDuckGo throttle.")

# Show the last report (kept in session_state so it survives reruns, e.g. after clicking Download)
if "report" in st.session_state:
    st.divider()
    st.download_button(
        "⬇️ Download report (.md)",
        data=st.session_state["report"],
        file_name=f"{slugify(st.session_state['topic'])}-{date.today()}.md",
        mime="text/markdown",
    )
    st.markdown(st.session_state["report"])
