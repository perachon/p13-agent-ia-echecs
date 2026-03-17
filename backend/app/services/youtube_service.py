from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class YouTubeVideo:
    video_id: str
    title: str
    channel_title: str | None
    published_at: str | None
    url: str
    thumbnail_url: str | None


class YouTubeService:
    def __init__(self) -> None:
        self._timeout = httpx.Timeout(settings.http_timeout_seconds)

    def search_videos(self, query: str, max_results: int = 5) -> list[YouTubeVideo]:
        if not settings.youtube_api_key:
            raise RuntimeError("YouTube API key not configured (set YOUTUBE_API_KEY)")

        q = query.strip()
        if not q:
            return []

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "key": settings.youtube_api_key,
            "part": "snippet",
            "type": "video",
            "q": q,
            "maxResults": max(1, min(int(max_results), 25)),
            "regionCode": settings.youtube_region_code,
            "relevanceLanguage": settings.youtube_relevance_language,
            "safeSearch": "none",
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RuntimeError("YouTube request timed out") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            # Common: 400 (bad request), 403 (quota/forbidden), 429 (rate limit)
            raise RuntimeError(f"YouTube request failed: {status}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError("YouTube request failed") from exc

        data: dict[str, Any] = resp.json()
        items = data.get("items", []) or []

        results: list[YouTubeVideo] = []
        for item in items:
            id_obj = item.get("id") or {}
            snippet = item.get("snippet") or {}

            video_id = id_obj.get("videoId")
            if not video_id:
                continue

            title = snippet.get("title") or ""
            channel_title = snippet.get("channelTitle")
            published_at = snippet.get("publishedAt")

            thumbs = snippet.get("thumbnails") or {}
            thumbnail_url = None
            for key in ("high", "medium", "default"):
                t = thumbs.get(key)
                if isinstance(t, dict) and t.get("url"):
                    thumbnail_url = t["url"]
                    break

            results.append(
                YouTubeVideo(
                    video_id=video_id,
                    title=title,
                    channel_title=channel_title,
                    published_at=published_at,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    thumbnail_url=thumbnail_url,
                )
            )

        return results
