#!/usr/bin/env python3
"""YouTube Data API v3 client for channel resolution and video listing."""

import argparse
import json
import sys
import re
from datetime import datetime, timezone

import requests

from file_utils import load_env, ensure_channel_dir, save_json, load_json

BASE_URL = "https://www.googleapis.com/youtube/v3"


def get_api_key():
    env = load_env()
    key = env["YOUTUBE_API_KEY"]
    if not key:
        print("Error: YOUTUBE_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)
    return key


def parse_channel_input(channel_input):
    """Extract channel identifier and type from various input formats."""
    channel_input = channel_input.strip().rstrip('/')

    # Full URL: https://www.youtube.com/@handle or /channel/ID or /c/name
    url_patterns = [
        (r'youtube\.com/@([\w.-]+)', 'handle'),
        (r'youtube\.com/channel/(UC[\w-]+)', 'id'),
        (r'youtube\.com/c/([\w.-]+)', 'username'),
        (r'youtube\.com/user/([\w.-]+)', 'username'),
        (r'youtube\.com/([\w.-]+)$', 'handle'),  # fallback for youtube.com/name
    ]

    for pattern, id_type in url_patterns:
        match = re.search(pattern, channel_input)
        if match:
            return match.group(1), id_type

    # Direct @handle
    if channel_input.startswith('@'):
        return channel_input[1:], 'handle'

    # Direct channel ID
    if channel_input.startswith('UC') and len(channel_input) == 24:
        return channel_input, 'id'

    # Assume it's a name/handle to search for
    return channel_input, 'search'


def resolve_channel(api_key, channel_input):
    """Resolve any channel input to channel info."""
    identifier, id_type = parse_channel_input(channel_input)

    params = {
        "key": api_key,
        "part": "snippet,contentDetails,statistics",
    }

    if id_type == 'handle':
        params["forHandle"] = identifier
    elif id_type == 'id':
        params["id"] = identifier
    elif id_type == 'username':
        params["forUsername"] = identifier
    else:
        # Search fallback
        search_params = {
            "key": api_key,
            "part": "snippet",
            "q": identifier,
            "type": "channel",
            "maxResults": 1,
        }
        resp = requests.get(f"{BASE_URL}/search", params=search_params)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            print(f"Error: No channel found for '{identifier}'", file=sys.stderr)
            sys.exit(1)
        params["id"] = items[0]["snippet"]["channelId"]

    resp = requests.get(f"{BASE_URL}/channels", params=params)
    resp.raise_for_status()
    items = resp.json().get("items", [])

    # If forHandle/forUsername failed, try search
    if not items and id_type in ('handle', 'username'):
        search_params = {
            "key": api_key,
            "part": "snippet",
            "q": identifier,
            "type": "channel",
            "maxResults": 1,
        }
        resp = requests.get(f"{BASE_URL}/search", params=search_params)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            print(f"Error: No channel found for '{identifier}'", file=sys.stderr)
            sys.exit(1)
        params.pop("forHandle", None)
        params.pop("forUsername", None)
        params["id"] = items[0]["snippet"]["channelId"]
        resp = requests.get(f"{BASE_URL}/channels", params=params)
        resp.raise_for_status()
        items = resp.json().get("items", [])

    if not items:
        print(f"Error: No channel found for '{channel_input}'", file=sys.stderr)
        sys.exit(1)

    ch = items[0]
    snippet = ch["snippet"]
    stats = ch["statistics"]
    uploads_playlist = ch["contentDetails"]["relatedPlaylists"]["uploads"]

    return {
        "channel_id": ch["id"],
        "title": snippet["title"],
        "handle": snippet.get("customUrl", ""),
        "description": snippet.get("description", ""),
        "subscriber_count": int(stats.get("subscriberCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "uploads_playlist_id": uploads_playlist,
        "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
    }


def parse_duration(duration_str):
    """Parse ISO 8601 duration (PT1H2M3S) to seconds."""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str or '')
    if not match:
        return 0
    h, m, s = (int(x) if x else 0 for x in match.groups())
    return h * 3600 + m * 60 + s


def format_duration(seconds):
    """Format seconds to HH:MM:SS or MM:SS."""
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def list_videos(api_key, uploads_playlist_id, channel_name, scope, include_shorts=False):
    """Fetch videos from a channel's uploads playlist with scope filtering."""
    scope_type = scope.get("type", "all")
    videos = []
    next_page = None
    page_count = 0

    # Handle video_ids scope — fetch specific videos directly by ID
    if scope_type == "video_ids":
        target_ids = scope.get("ids", [])
        if not target_ids:
            print("No video IDs provided", file=sys.stderr)
            return []

        # Fetch in batches of 50 (YouTube API limit)
        for i in range(0, len(target_ids), 50):
            batch = target_ids[i:i+50]
            resp = requests.get(f"{BASE_URL}/videos", params={
                "key": api_key,
                "id": ",".join(batch),
                "part": "snippet,contentDetails,statistics",
            })
            resp.raise_for_status()
            for item in resp.json().get("items", []):
                snippet = item["snippet"]
                dur_seconds = parse_duration(item["contentDetails"].get("duration", ""))
                stats = item.get("statistics", {})
                videos.append({
                    "video_id": item["id"],
                    "title": snippet["title"],
                    "published_at": snippet["publishedAt"],
                    "description": snippet.get("description", ""),
                    "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "duration_seconds": dur_seconds,
                    "duration": format_duration(dur_seconds),
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                })
            print(f"Fetched batch {i//50 + 1}: {len(batch)} IDs (total: {len(videos)})", file=sys.stderr)

        channel_dir = ensure_channel_dir(channel_name)
        save_json(channel_dir / "videos.json", videos)
        return videos

    # Parse scope parameters
    max_videos = scope.get("n") if scope_type == "last_n" else None
    after_date = None
    before_date = None
    keyword = scope.get("q", "").lower() if scope_type == "keyword" else None

    if scope_type == "date_range":
        if scope.get("after"):
            after_date = datetime.fromisoformat(scope["after"]).replace(tzinfo=timezone.utc)
        if scope.get("before"):
            before_date = datetime.fromisoformat(scope["before"]).replace(tzinfo=timezone.utc)

    while True:
        params = {
            "key": api_key,
            "playlistId": uploads_playlist_id,
            "part": "snippet,contentDetails",
            "maxResults": 50,
        }
        if next_page:
            params["pageToken"] = next_page

        resp = requests.get(f"{BASE_URL}/playlistItems", params=params)
        resp.raise_for_status()
        data = resp.json()
        page_count += 1

        # Get video IDs for this page to fetch durations and stats
        page_video_ids = []
        page_items = []
        for item in data.get("items", []):
            vid_id = item["contentDetails"]["videoId"]
            snippet = item["snippet"]
            published = snippet["publishedAt"]
            pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))

            # Date range filtering - skip if outside range
            if after_date and pub_dt < after_date:
                if scope_type == "date_range":
                    # Videos are in reverse chronological order, so we can stop
                    # Actually, playlist items are newest first, so if we're past the after_date, stop
                    continue
            if before_date and pub_dt > before_date:
                continue

            page_video_ids.append(vid_id)
            page_items.append({
                "video_id": vid_id,
                "title": snippet["title"],
                "published_at": published,
                "description": snippet.get("description", ""),
                "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            })

        # Fetch video details (duration, view count) in batches of 50
        if page_video_ids:
            details_resp = requests.get(f"{BASE_URL}/videos", params={
                "key": api_key,
                "id": ",".join(page_video_ids),
                "part": "contentDetails,statistics",
            })
            details_resp.raise_for_status()
            details_map = {}
            for item in details_resp.json().get("items", []):
                dur_seconds = parse_duration(item["contentDetails"].get("duration", ""))
                stats = item.get("statistics", {})
                details_map[item["id"]] = {
                    "duration_seconds": dur_seconds,
                    "duration": format_duration(dur_seconds),
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                }

            for v in page_items:
                detail = details_map.get(v["video_id"], {})
                v.update(detail)

        # Keyword filtering
        if keyword:
            page_items = [
                v for v in page_items
                if keyword in v["title"].lower() or keyword in v.get("description", "").lower()
            ]

        # Filter out Shorts (≤2 minutes) unless explicitly included
        if not include_shorts:
            page_items = [v for v in page_items if v.get("duration_seconds", 0) > 120]

        videos.extend(page_items)

        print(f"Fetched page {page_count}: {len(page_items)} videos (total: {len(videos)})", file=sys.stderr)

        # Check if we have enough for last_n
        if max_videos and len(videos) >= max_videos:
            videos = videos[:max_videos]
            break

        # Check for date_range early exit
        if scope_type == "date_range" and after_date and data.get("items"):
            last_published = data["items"][-1]["snippet"]["publishedAt"]
            last_dt = datetime.fromisoformat(last_published.replace("Z", "+00:00"))
            if last_dt < after_date:
                break

        next_page = data.get("nextPageToken")
        if not next_page:
            break

    # Save to channel dir
    channel_dir = ensure_channel_dir(channel_name)
    save_json(channel_dir / "videos.json", videos)

    return videos


def main():
    parser = argparse.ArgumentParser(description="YouTube API v3 client")
    parser.add_argument("--action", required=True, choices=["channel_info", "list_videos"])
    parser.add_argument("--channel", help="Channel URL, handle, or name")
    parser.add_argument("--channel_id", help="Channel ID")
    parser.add_argument("--uploads_playlist", help="Uploads playlist ID")
    parser.add_argument("--channel_name", help="Channel name for file storage")
    parser.add_argument("--scope", default='{"type": "all"}', help="Scope JSON")
    parser.add_argument("--include_shorts", action="store_true", help="Include short videos (≤2min), excluded by default")
    args = parser.parse_args()

    api_key = get_api_key()

    if args.action == "channel_info":
        if not args.channel:
            print("Error: --channel required for channel_info", file=sys.stderr)
            sys.exit(1)
        info = resolve_channel(api_key, args.channel)
        channel_dir = ensure_channel_dir(info["title"])
        save_json(channel_dir / "channel.json", info)
        print(json.dumps(info, indent=2))

    elif args.action == "list_videos":
        if not args.uploads_playlist or not args.channel_name:
            print("Error: --uploads_playlist and --channel_name required", file=sys.stderr)
            sys.exit(1)
        scope = json.loads(args.scope)
        videos = list_videos(api_key, args.uploads_playlist, args.channel_name, scope, include_shorts=args.include_shorts)
        print(json.dumps(videos, indent=2))


if __name__ == "__main__":
    main()
