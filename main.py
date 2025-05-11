from flask import Flask, render_template, request, jsonify
import requests
import json
from googlesearch import search as google_search
from os import getenv

app = Flask(__name__)

def generate_queries(problem: str) -> list[str]:
    """Generate 3 search queries from a problem statement using Gemini API directly."""
    api_key = getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY environment variable not set.")

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    prompt = f"""
    Convert this problem description into 3 optimal web search queries.
    Prioritize: error types (if technical), key terms, and context.
    Return ONLY the queries, one per line:

    Problem: {problem}
    """

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(endpoint, headers=headers, data=json.dumps(payload))

    if response.status_code != 200:
        raise Exception(f"Gemini API error: {response.text}")

    data = response.json()
    text_response = data["candidates"][0]["content"]["parts"][0]["text"]
    queries = text_response.strip().split("\n")
    return [q.strip() for q in queries if q.strip()][:3]


def enhance_query(base_query: str, includes: str, excludes: str, site: str) -> str:
    """Enhance the query with includes, excludes, and site focus."""
    if includes:
        include_keywords = [kw.strip() for kw in includes.split(",") if kw.strip()]
        for kw in include_keywords:
            base_query += f' "{kw}"'

    if excludes:
        exclude_items = [item.strip() for item in excludes.split(",") if item.strip()]
        for item in exclude_items:
            if "." in item:
                base_query += f" -site:{item}"
            else:
                base_query += f" -{item}"

    if site:
        domain = site.strip()
        if not domain.startswith("site:"):
            domain = f"site:{domain}"
        base_query = f"{domain} {base_query}"

    return base_query


def search_queries(queries: list[str], max_results: int = 5, includes: str = "", excludes: str = "", site: str = "") -> list[dict]:
    """Search each query using Google and return structured results."""
    results = []
    for query in queries:
        enhanced_query = enhance_query(query, includes, excludes, site)
        try:
            search_results = list(google_search(enhanced_query, num_results=max_results))
            results.append({
                "query": enhanced_query,
                "results": [{"url": url} for url in search_results]
            })
        except Exception as e:
            results.append({
                "query": enhanced_query,
                "error": str(e)
            })
    return results


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def handle_search():
    data = request.get_json()
    problem = data.get("problem", "")
    includes = data.get("includes", "")
    excludes = data.get("excludes", "")
    site = data.get("site", "")

    try:
        queries = generate_queries(problem)
        search_results = search_queries(queries, includes=includes, excludes=excludes, site=site)
        return jsonify({
            "success": True,
            "results": search_results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


if __name__ == "__main__":
    port = int(getenv("PORT") or "5000")
    app.run(host="0.0.0.0", port=port)
