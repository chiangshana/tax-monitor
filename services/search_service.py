from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Dict, List
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests


class SearchService:
    def search(
        self,
        keywords: List[str],
        user_prompt: str = None,
        mode: str = "auto",
        date_range: str = "1m",
        start_date: str = None,
        end_date: str = None,
        max_results: int = 10,
        candidate_urls: List[str] = None
    ) -> List[Dict]:
        query = " ".join(keywords)
        candidate_urls = candidate_urls or []

        if mode == "manual" and candidate_urls:
            return [
                {
                    "title": url,
                    "url": url,
                    "snippet": user_prompt or "",
                    "source": "manual",
                    "published_at": None,
                    "relevance_score": 1.0
                }
                for url in candidate_urls[:max_results]
            ]

        window = self._resolve_date_window(date_range, start_date, end_date)
        results = self._search_google_news_rss(query=query, window=window, max_results=max_results)
        return self._rank_results(results, keywords=keywords, user_prompt=user_prompt)

    def _search_google_news_rss(self, query: str, window: Dict[str, datetime], max_results: int) -> List[Dict]:
        when_clause = self._build_google_news_when(window)
        full_query = f"{query} {when_clause}".strip()
        url = f"https://news.google.com/rss/search?q={quote_plus(full_query)}&hl=en-US&gl=US&ceid=US:en"

        response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        root = ET.fromstring(response.text)
        items = []
        for item in root.findall(".//item"):
            pub_date = item.findtext("pubDate")
            normalized_date = None
            if pub_date:
                try:
                    normalized_date = parsedate_to_datetime(pub_date).isoformat()
                except Exception:
                    normalized_date = pub_date
            items.append({
                "title": item.findtext("title", default=""),
                "url": item.findtext("link", default=""),
                "snippet": item.findtext("description", default=""),
                "source": "google_news_rss",
                "published_at": normalized_date,
                "relevance_score": 0.0
            })
            if len(items) >= max_results:
                break
        return items

    def _rank_results(self, results: List[Dict], keywords: List[str], user_prompt: str = None) -> List[Dict]:
        prompt_terms = (user_prompt or "").lower().split()

        for result in results:
            haystack = " ".join([
                result.get("title", ""),
                result.get("snippet", "")
            ]).lower()
            keyword_hits = sum(2 for keyword in keywords if keyword.lower() in haystack)
            prompt_hits = sum(1 for term in prompt_terms if term in haystack)
            freshness_bonus = 0.0
            if result.get("published_at"):
                freshness_bonus = 0.5
            result["relevance_score"] = round(keyword_hits + prompt_hits + freshness_bonus, 2)

        return sorted(results, key=lambda item: item["relevance_score"], reverse=True)

    def _resolve_date_window(self, date_range: str, start_date: str = None, end_date: str = None) -> Dict[str, datetime]:
        now = datetime.utcnow()
        mapping = {
            "7d": timedelta(days=7),
            "1m": timedelta(days=30),
            "3m": timedelta(days=90),
            "6m": timedelta(days=180),
            "1y": timedelta(days=365)
        }

        if date_range == "custom" and start_date and end_date:
            return {
                "start": datetime.fromisoformat(start_date),
                "end": datetime.fromisoformat(end_date)
            }

        delta = mapping.get(date_range, timedelta(days=30))
        return {"start": now - delta, "end": now}

    def _build_google_news_when(self, window: Dict[str, datetime]) -> str:
        start = window["start"]
        end = window["end"]
        delta_days = max((end - start).days, 1)
        if delta_days <= 7:
            return "when:7d"
        if delta_days <= 30:
            return "when:30d"
        if delta_days <= 90:
            return "when:90d"
        if delta_days <= 180:
            return "when:180d"
        return "when:365d"
