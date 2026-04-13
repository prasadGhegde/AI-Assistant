from __future__ import annotations

import calendar
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

import feedparser
import requests
from bs4 import BeautifulSoup

from .config import AppConfig
from .models import RawItem
from .quality import NewsQualityFilter
from .utils import clean_text, load_json, stable_id


class NewsCollector:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.quality_filter = NewsQualityFilter(config)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "MorningBriefs/0.1 local briefing bot "
                    "(personal use; contact owner from local machine)"
                )
            }
        )

    def collect(self) -> Tuple[List[RawItem], List[str]]:
        manifest = load_json(self.config.sources_path, default={})
        collected_at = datetime.now(timezone.utc).isoformat()
        items: List[RawItem] = []
        warnings: List[str] = []

        for category, sources in manifest.items():
            for source in sources:
                try:
                    items.extend(self._collect_source(category, source, collected_at))
                except Exception as exc:
                    warnings.append(
                        f"Failed to collect {source.get('name', source.get('url'))}: {exc}"
                    )

        deduped = self._dedupe(items)
        return deduped, warnings

    def _collect_source(
        self, category: str, source: Dict[str, Any], collected_at: str
    ) -> List[RawItem]:
        if source.get("kind") != "rss":
            return []
        response = self.session.get(
            source["url"], timeout=self.config.fetch_timeout
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        entries = parsed.entries[: self.config.max_items_per_source]
        output = []
        for entry in entries:
            headline = clean_text(entry.get("title", ""), 220)
            url = entry.get("link", "")
            if not headline or not url:
                continue
            published_dt = self._entry_datetime(entry)
            excerpt = clean_text(
                entry.get("summary")
                or entry.get("description")
                or entry.get("subtitle")
                or "",
                520,
            )
            if not excerpt:
                excerpt = self._page_excerpt(url)
            freshness_hours = self._freshness_hours(published_dt)
            item = RawItem(
                id=stable_id(category, source.get("name", ""), headline, url),
                category=category,
                source_name=source.get("name", "Unknown source"),
                source_url=source.get("url", ""),
                headline=headline,
                url=url,
                excerpt=excerpt,
                published_at=published_dt.isoformat() if published_dt else None,
                collected_at=collected_at,
                tags=list(source.get("tags", [])),
                source_weight=float(source.get("source_weight", 1.0)),
                freshness_hours=freshness_hours,
            )
            output.append(self.quality_filter.apply(item))
        return output

    def _entry_datetime(self, entry: Dict[str, Any]) -> Optional[datetime]:
        for parsed_key in ("published_parsed", "updated_parsed", "created_parsed"):
            parsed = entry.get(parsed_key)
            if parsed:
                return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
        for text_key in ("published", "updated", "created"):
            value = entry.get(text_key)
            if not value:
                continue
            try:
                dt = parsedate_to_datetime(value)
            except (TypeError, ValueError):
                continue
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        return None

    def _freshness_hours(self, published_dt: Optional[datetime]) -> Optional[float]:
        if published_dt is None:
            return None
        now = datetime.now(timezone.utc)
        delta = now - published_dt.astimezone(timezone.utc)
        return round(max(delta.total_seconds() / 3600.0, 0.0), 2)

    def _page_excerpt(self, url: str) -> str:
        try:
            response = self.session.get(url, timeout=min(self.config.fetch_timeout, 8))
            response.raise_for_status()
        except Exception:
            return ""
        soup = BeautifulSoup(response.text, "html.parser")
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return clean_text(meta["content"], 420)
        paragraphs = [clean_text(p.get_text(" "), 220) for p in soup.find_all("p")[:4]]
        paragraphs = [paragraph for paragraph in paragraphs if paragraph]
        return clean_text(" ".join(paragraphs), 420)

    def _dedupe(self, items: List[RawItem]) -> List[RawItem]:
        by_url: Dict[str, RawItem] = {}
        for item in items:
            key = item.url.split("?")[0].rstrip("/")
            existing = by_url.get(key)
            if existing is None or (
                item.quality_score + item.source_weight
                > existing.quality_score + existing.source_weight
            ):
                by_url[key] = item
        return list(by_url.values())
