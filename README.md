# 🔎 AI Research Agent

A single-agent research assistant. Give it a topic; it searches the web and writes a structured Markdown report.

**Stack:** [CrewAI](https://docs.crewai.com) · [Groq](https://console.groq.com) (`openai/gpt-oss-120b`) · DuckDuckGo (`ddgs`) · [Streamlit](https://streamlit.io)


## Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then put your GROQ_API_KEY inside
streamlit run app.py
```

Use **Python 3.11 or 3.12** (CrewAI supports 3.10 to 3.13).

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub (never commit `.env` or `secrets.toml`).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **Create app** → pick your repo, branch `main`, main file `app.py`.
3. Under **Advanced settings** choose **Python 3.12** and paste in Secrets:
   ```toml
   GROQ_API_KEY = "your_groq_api_key_here"
   ```
4. Click **Deploy**.
