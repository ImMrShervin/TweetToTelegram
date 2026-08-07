import re
from typing import Any, Dict, List, Optional



import requests

import config

URL_RE = re.compile(
    r"https?://(?:www\.)?(?:twitter\.com|x\.com|fxtwitter\.com|vxtwitter\.com|nitter\.[^/]+)/"
    r"(?P<user>[A-Za-z0-9_]+)/status(?:es)?/(?P<id>\d+)",
    re.I,
)


class TweetError(Exception):
    pass


def parse_url(text: str) -> Optional[Dict[str, str]]:
    m = URL_RE.search(text or "")
    if not m:
        return None
    return {"user": m.group("user"), "id": m.group("id")}


def _get_json(url: str) -> Dict[str, Any]:
    r = requests.get(url, timeout=20, headers={"User-Agent": "TweetShotBot/1.0"})
    r.raise_for_status()
    return r.json()


def fetch(url_or_text: str) -> Dict[str, Any]:

    parsed = parse_url(url_or_text)
    if not parsed:
        raise TweetError("لینک توییت معتبر نیست.")
    tid, user = parsed["id"], parsed["user"]

    last_err: Optional[Exception] = None
    for base in (config.TWEET_API, config.TWEET_API_FALLBACK):
        if not base:
            continue
        try:
            if "fxtwitter" in base:
                data = _get_json(f"{base.rstrip('/')}/status/{tid}")
                return _from_fx(data)
            data = _get_json(f"{base.rstrip('/')}/{user}/status/{tid}")
            return _from_vx(data)
        except Exception as e:
            last_err = e
    raise TweetError(f"دریافت اطلاعات توییت ناموفق بود: {last_err}")


def _media_list(items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    out = []
    for m in items or []:
        kind = m.get("type") or "photo"
        thumb = m.get("thumbnail_url") or m.get("url") or ""
        out.append(
            {
                "type": "video" if kind in ("video", "gif", "animated_gif") else "photo",
                "url": m.get("url", ""),
                "thumb": thumb,
            }
        )
    return out


def _from_fx(data: Dict[str, Any]) -> Dict[str, Any]:
    t = data.get("tweet") or {}
    if not t:
        raise TweetError("پاسخ وب‌سرویس خالی بود.")
    a = t.get("author") or {}
    media = t.get("media") or {}
    all_media = media.get("all") or []
    quote = t.get("quote")
    return {
        "id": str(t.get("id", "")),
        "url": t.get("url", ""),
        "text": t.get("text", "") or "",
        "lang": t.get("lang", ""),
        "created_at": t.get("created_at", ""),
        "author": {
            "name": a.get("name", ""),
            "screen_name": a.get("screen_name", ""),
            "avatar": a.get("avatar_url", ""),
            "verified": bool(a.get("is_verified") or a.get("verified")),
        },
        "stats": {
            "likes": t.get("likes", 0) or 0,
            "retweets": t.get("retweets", 0) or 0,
            "replies": t.get("replies", 0) or 0,
            "views": t.get("views", 0) or 0,
        },
        "media": _media_list(all_media),
        "video_url": next((m["url"] for m in _media_list(all_media) if m["type"] == "video"), ""),
        "quote": (
            {
                "name": (quote.get("author") or {}).get("name", ""),
                "screen_name": (quote.get("author") or {}).get("screen_name", ""),
                "text": quote.get("text", ""),
            }
            if quote
            else None
        ),
    }


def _from_vx(data: Dict[str, Any]) -> Dict[str, Any]:
    media = data.get("media_extended") or []
    norm = [
        {
            "type": "video" if (m.get("type") in ("video", "gif")) else "photo",
            "url": m.get("url", ""),
            "thumb": m.get("thumbnail_url") or m.get("url", ""),
        }
        for m in media
    ]
    return {
        "id": str(data.get("tweetID", "")),
        "url": data.get("tweetURL", ""),
        "text": data.get("text", "") or "",
        "lang": "",
        "created_at": data.get("date", ""),
        "author": {
            "name": data.get("user_name", ""),
            "screen_name": data.get("user_screen_name", ""),
            "avatar": data.get("user_profile_image_url", ""),
            "verified": False,
        },
        "stats": {
            "likes": data.get("likes", 0) or 0,
            "retweets": data.get("retweets", 0) or 0,
            "replies": data.get("replies", 0) or 0,
            "views": 0,
        },
        "media": norm,
        "video_url": next((m["url"] for m in norm if m["type"] == "video"), ""),
        "quote": None,
    }
