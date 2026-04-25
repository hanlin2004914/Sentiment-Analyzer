from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os

app = FastAPI()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")


class ArticleRequest(BaseModel):
    limit: int = 5


@app.get("/")
def root():
    return {"status": "MCP server running"}


@app.post("/tools/get_wsj_titles")
def get_wsj_titles(req: ArticleRequest):
    url = "https://newsapi.org/v2/everything"

    params = {
        "q": "Wall Street Journal",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": req.limit,
        "apiKey": NEWS_API_KEY
    }

    res = requests.get(url, params=params)

    if res.status_code != 200:
        return {"error": res.text}

    data = res.json()
    articles = data.get("articles", [])

    titles = [a["title"] for a in articles if "title" in a]

    return {
        "titles": titles,
        "count": len(titles)
    }