import os
import requests
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")

def serpapi_search(query: str, num_results: int = 3) -> List[Dict]:
    if not SERPAPI_KEY:
        raise RuntimeError("SERPAPI_API_KEY not set in environment")

    params = {
        "q": query,
        "engine": "google",
        "api_key": SERPAPI_KEY,
        "num": num_results
    }

    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=20
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("organic_results", [])[:num_results]:
            link = item.get("link") or item.get("url") or item.get("displayed_link")
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            if link:
                results.append({"title": title, "link": link, "snippet": snippet})
        return results

    except requests.exceptions.RequestException as e:
        print(f"Request error during SerpAPI search: {e}")
        return []
