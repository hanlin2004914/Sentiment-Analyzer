import streamlit as st
import requests
import json
import time
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score


# -------------------------
# CONFIG
# -------------------------

MCP_URL = "http://127.0.0.1:8000/tools/get_wsj_titles"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"

LABELS = ["negative", "neutral", "positive"]


# -------------------------
# API CALLS
# -------------------------

def fetch_articles(n):
    res = requests.post(MCP_URL, json={"limit": n})

    if res.status_code != 200:
        st.error("Failed to fetch articles")
        return []

    return res.json().get("titles", [])


def predict(text):
    prompt = f"""
Classify sentiment.

Text: {text}

Return JSON:
{{"label":"negative|neutral|positive"}}
"""

    res = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    try:
        return json.loads(res.json()["response"])["label"]
    except:
        return "UNKNOWN"


# -------------------------
# UI
# -------------------------

st.set_page_config(page_title="AI Benchmark Dashboard", layout="wide")

st.title("📊 AI Agent Benchmark Dashboard")

tab1, tab2, tab3 = st.tabs(["🔍 Live Predictions", "🧪 Benchmark", "⚙️ Settings"])


# -------------------------
# TAB 1: LIVE
# -------------------------

with tab1:
    st.subheader("Fetch and classify live news")

    n = st.slider("Number of articles", 1, 20, 5)

    if st.button("Fetch Articles"):
        st.session_state["articles"] = fetch_articles(n)

    articles = st.session_state.get("articles", [])

    for article in articles:
        col1, col2 = st.columns([4, 1])

        with col1:
            st.write(article)

        with col2:
            if st.button("Predict", key=article):
                label = predict(article)
                st.success(label)


# -------------------------
# TAB 2: BENCHMARK
# -------------------------

with tab2:
    st.subheader("Run quick benchmark")

    run_n = st.slider("Benchmark size", 5, 50, 10)

    if st.button("Run Benchmark"):
        titles = fetch_articles(run_n)

        results = []
        y_true = []
        y_pred = []

        progress = st.progress(0)

        for i, t in enumerate(titles):
            start = time.time()
            pred = predict(t)
            latency = time.time() - start

            results.append({
                "text": t,
                "prediction": pred,
                "latency": latency
            })

            # fake labels for demo (replace with real dataset later)
            gold = "neutral"
            y_true.append(gold)
            y_pred.append(pred)

            progress.progress((i + 1) / run_n)

        df = pd.DataFrame(results)

        st.dataframe(df)

        # metrics
        try:
            acc = accuracy_score(y_true, y_pred)
            f1 = f1_score(y_true, y_pred, average="macro")

            st.metric("Accuracy", round(acc, 3))
            st.metric("F1 Score", round(f1, 3))
        except:
            st.warning("Not enough valid predictions for metrics")


# -------------------------
# TAB 3: SETTINGS
# -------------------------

with tab3:
    st.subheader("Configuration")

    st.write("MCP Server:", MCP_URL)
    st.write("Model:", MODEL)

    st.info("Make sure Ollama + MCP server are running")

    st.code("""
# Start MCP server
uvicorn main:app --reload

# Start Ollama
ollama serve
""")