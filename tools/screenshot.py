#!/usr/bin/env python3
"""Extract screenshots from YouTube videos at specific timestamps using yt-dlp + ffmpeg."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from file_utils import ensure_channel_dir

DELAY_BETWEEN_VIDEOS = 3  # seconds between different videos
DELAY_BETWEEN_FRAMES = 1  # seconds between frames from same video


def update_ytdlp():
    """Update yt-dlp to latest version."""
    print("Updating yt-dlp to latest version...", file=sys.stderr)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        # Extract version info
        for line in result.stdout.splitlines():
            if "Successfully installed" in line or "already satisfied" in line:
                print(f"  -> {line.strip()}", file=sys.stderr)
                break
    else:
        print(f"  -> Warning: update failed: {result.stderr[:200]}", file=sys.stderr)


def get_stream_url(video_id):
    """Get the best video stream URL without downloading."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    result = subprocess.run(
        ["yt-dlp", "-f", "best[height<=720]", "-g", url],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip().split("\n")[0]


def extract_frame(stream_url, timestamp, output_path):
    """Extract a single frame at a timestamp from a stream URL."""
    result = subprocess.run(
        [
            "ffmpeg", "-ss", timestamp,
            "-i", stream_url,
            "-frames:v", "1",
            "-q:v", "2",
            "-y",  # overwrite
            str(output_path)
        ],
        capture_output=True, text=True, timeout=30
    )
    return result.returncode == 0


def capture_screenshots(channel_name, screenshots_spec):
    """
    Capture screenshots for multiple videos.

    screenshots_spec: list of {
        "video_id": "abc123",
        "title": "Video Title",
        "timestamps": ["00:05:30", "00:12:45", ...]
    }
    """
    channel_dir = ensure_channel_dir(channel_name)
    screenshots_dir = channel_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    stats = {"captured": 0, "skipped": 0, "failed": 0, "failed_items": []}
    total_videos = len(screenshots_spec)

    for vi, video in enumerate(screenshots_spec):
        vid_id = video["video_id"]
        title = video.get("title", vid_id)
        timestamps = video.get("timestamps", [])

        if not timestamps:
            continue

        # Check if all screenshots already exist
        all_exist = all(
            (screenshots_dir / f"{vid_id}_{ts.replace(':', '-')}.jpg").exists()
            for ts in timestamps
        )
        if all_exist:
            print(f"[{vi+1}/{total_videos}] Skipping (cached): {title} ({len(timestamps)} frames)", file=sys.stderr)
            stats["skipped"] += len(timestamps)
            continue

        print(f"[{vi+1}/{total_videos}] Getting stream: {title}", file=sys.stderr)

        stream_url = get_stream_url(vid_id)
        if not stream_url:
            print(f"  -> Failed to get stream URL", file=sys.stderr)
            stats["failed"] += len(timestamps)
            stats["failed_items"].append({"video_id": vid_id, "reason": "no stream URL"})
            continue

        for ti, ts in enumerate(timestamps):
            output_path = screenshots_dir / f"{vid_id}_{ts.replace(':', '-')}.jpg"

            if output_path.exists():
                print(f"  -> [{ti+1}/{len(timestamps)}] Skipping (cached): {ts}", file=sys.stderr)
                stats["skipped"] += 1
                continue

            print(f"  -> [{ti+1}/{len(timestamps)}] Capturing: {ts}", file=sys.stderr)
            success = extract_frame(stream_url, ts, output_path)

            if success and output_path.exists() and output_path.stat().st_size > 0:
                stats["captured"] += 1
            else:
                print(f"     Failed to capture frame", file=sys.stderr)
                stats["failed"] += 1
                stats["failed_items"].append({"video_id": vid_id, "timestamp": ts})

            if ti < len(timestamps) - 1:
                time.sleep(DELAY_BETWEEN_FRAMES)

        # Delay between videos
        if vi < total_videos - 1:
            time.sleep(DELAY_BETWEEN_VIDEOS)

    return stats


def main():
    parser = argparse.ArgumentParser(description="YouTube video screenshot extractor")
    parser.add_argument("--action", required=True, choices=["capture", "update_ytdlp"])
    parser.add_argument("--channel_name", help="Channel name for file storage")
    parser.add_argument("--spec_file", help="Path to JSON spec file with video IDs and timestamps")
    parser.add_argument("--spec", help="Inline JSON spec")
    args = parser.parse_args()

    if args.action == "update_ytdlp":
        update_ytdlp()
        return

    if args.action == "capture":
        # Always update yt-dlp first
        update_ytdlp()

        if not args.channel_name:
            print("Error: --channel_name required", file=sys.stderr)
            sys.exit(1)

        if args.spec_file:
            with open(args.spec_file, 'r') as f:
                spec = json.load(f)
        elif args.spec:
            spec = json.loads(args.spec)
        else:
            print("Error: --spec_file or --spec required", file=sys.stderr)
            sys.exit(1)

        stats = capture_screenshots(args.channel_name, spec)
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
