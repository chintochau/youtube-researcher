#!/usr/bin/env python3
"""Supadata API client for fetching YouTube video transcripts."""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

from file_utils import load_env, ensure_channel_dir, load_json

TRANSCRIPT_URL = "https://api.supadata.ai/v1/transcript"
MAX_POLL_ATTEMPTS = 120  # 120 * 1s = 2 minutes max wait per job


def get_api_key():
    env = load_env()
    key = env["SUPADATA_API_KEY"]
    if not key:
        print("Error: SUPADATA_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)
    return key


def normalize_content(content):
    """Normalize transcript content — may be a string or a list of segment objects."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # List of segment dicts with "text" keys, or plain strings
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content) if content else ""


def poll_job(api_key, job_id):
    """Poll an async transcript job until completion."""
    url = f"{TRANSCRIPT_URL}/{job_id}"
    headers = {"x-api-key": api_key}

    for attempt in range(MAX_POLL_ATTEMPTS):
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")

        if status == "completed":
            return normalize_content(data.get("content", ""))
        elif status == "failed":
            return None
        # queued or active — keep polling
        time.sleep(1)

    print(f"  -> Job {job_id} timed out after {MAX_POLL_ATTEMPTS}s", file=sys.stderr)
    return None


def fetch_transcript(api_key, video_id):
    """Fetch transcript for a single video. Handles both sync and async responses."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    resp = requests.get(
        TRANSCRIPT_URL,
        params={"url": video_url, "text": "true"},
        headers={"x-api-key": api_key},
        timeout=60,
    )

    if resp.status_code == 200:
        data = resp.json()
        return normalize_content(data.get("content", ""))

    if resp.status_code == 202:
        # Async job for longer videos (>20 min)
        data = resp.json()
        job_id = data.get("jobId")
        if job_id:
            print(f"  -> Long video, polling job {job_id}...", file=sys.stderr)
            return poll_job(api_key, job_id)
        return None

    if resp.status_code in (404, 206, 403):
        return None

    resp.raise_for_status()
    return None


def fetch_transcripts(api_key, channel_name, videos_file):
    """Fetch transcripts for all videos, skipping already-fetched ones."""
    videos = load_json(videos_file)
    channel_dir = ensure_channel_dir(channel_name)
    transcripts_dir = channel_dir / "transcripts"

    stats = {"fetched": 0, "skipped": 0, "failed": 0, "failed_ids": []}
    total = len(videos)

    for i, video in enumerate(videos):
        vid_id = video["video_id"]
        title = video.get("title", vid_id)
        output_path = transcripts_dir / f"{vid_id}.txt"

        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"[{i+1}/{total}] Skipping (cached): {title}", file=sys.stderr)
            stats["skipped"] += 1
            continue

        print(f"[{i+1}/{total}] Fetching: {title}", file=sys.stderr)

        try:
            text = fetch_transcript(api_key, vid_id)
            if text:
                output_path.write_text(text, encoding='utf-8')
                stats["fetched"] += 1
            else:
                print(f"  -> No transcript available", file=sys.stderr)
                stats["failed"] += 1
                stats["failed_ids"].append(vid_id)
        except Exception as e:
            print(f"  -> Error: {e}", file=sys.stderr)
            stats["failed"] += 1
            stats["failed_ids"].append(vid_id)

        # Rate limit between requests
        if i < total - 1:
            time.sleep(0.5)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Supadata transcript fetcher")
    parser.add_argument("--action", required=True, choices=["fetch_transcripts", "fetch_single"])
    parser.add_argument("--channel_name", help="Channel name for file storage")
    parser.add_argument("--videos_file", help="Path to videos.json")
    parser.add_argument("--video_id", help="Single video ID")
    parser.add_argument("--output", help="Output path for single fetch")
    args = parser.parse_args()

    api_key = get_api_key()

    if args.action == "fetch_transcripts":
        if not args.channel_name or not args.videos_file:
            print("Error: --channel_name and --videos_file required", file=sys.stderr)
            sys.exit(1)
        stats = fetch_transcripts(api_key, args.channel_name, args.videos_file)
        print(json.dumps(stats, indent=2))

    elif args.action == "fetch_single":
        if not args.video_id:
            print("Error: --video_id required", file=sys.stderr)
            sys.exit(1)
        text = fetch_transcript(api_key, args.video_id)
        if text:
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                Path(args.output).write_text(text, encoding='utf-8')
                print(f"Saved to {args.output}", file=sys.stderr)
            else:
                print(text)
        else:
            print("No transcript available", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
