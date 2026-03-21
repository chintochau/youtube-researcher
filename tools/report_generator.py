#!/usr/bin/env python3
"""Generate HTML reports from markdown with embedded images and video links."""

import argparse
import json
import re
import sys
from pathlib import Path

from file_utils import load_json, ensure_channel_dir, slugify

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --bg: #1a1a2e;
    --surface: #16213e;
    --surface2: #0f3460;
    --text: #e0e0e0;
    --text-muted: #a0a0b0;
    --accent: #e94560;
    --accent2: #533483;
    --link: #6cb4ee;
    --border: #2a2a4a;
    --code-bg: #0d1117;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
  }}
  h1 {{
    font-size: 2rem;
    color: #fff;
    border-bottom: 3px solid var(--accent);
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
  }}
  h2 {{
    font-size: 1.5rem;
    color: #fff;
    margin-top: 2.5rem;
    margin-bottom: 1rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--border);
  }}
  h3 {{
    font-size: 1.2rem;
    color: var(--link);
    margin-top: 1.8rem;
    margin-bottom: 0.6rem;
  }}
  h4 {{
    font-size: 1.05rem;
    color: var(--text);
    margin-top: 1.2rem;
    margin-bottom: 0.4rem;
  }}
  p {{ margin-bottom: 0.8rem; }}
  a {{ color: var(--link); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  ul, ol {{
    margin-left: 1.5rem;
    margin-bottom: 1rem;
  }}
  li {{ margin-bottom: 0.3rem; }}
  strong {{ color: #fff; }}
  code {{
    background: var(--code-bg);
    padding: 0.15rem 0.4rem;
    border-radius: 3px;
    font-size: 0.9em;
  }}
  blockquote {{
    border-left: 4px solid var(--accent);
    padding: 0.5rem 1rem;
    margin: 1rem 0;
    background: var(--surface);
    border-radius: 0 6px 6px 0;
  }}
  hr {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 2rem 0;
  }}
  /* Table of contents */
  .toc {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 2rem;
  }}
  .toc h2 {{
    margin-top: 0;
    border-bottom: none;
    font-size: 1.2rem;
  }}
  .toc ul {{ list-style: none; margin-left: 0; }}
  .toc li {{ margin-bottom: 0.2rem; }}
  .toc a {{ color: var(--link); }}
  /* Video cards */
  .video-card {{
    display: flex;
    gap: 1rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
    align-items: flex-start;
  }}
  .video-card img {{
    width: 200px;
    min-width: 200px;
    border-radius: 6px;
    object-fit: cover;
  }}
  .video-card .info {{ flex: 1; }}
  .video-card .info h4 {{ margin-top: 0; }}
  .video-card .info .meta {{
    color: var(--text-muted);
    font-size: 0.85em;
    margin-bottom: 0.4rem;
  }}
  /* Screenshot */
  .screenshot {{
    margin: 1rem 0;
    text-align: center;
  }}
  .screenshot img {{
    max-width: 100%;
    border-radius: 8px;
    border: 1px solid var(--border);
  }}
  .screenshot .caption {{
    color: var(--text-muted);
    font-size: 0.85em;
    margin-top: 0.3rem;
  }}
  /* Source tag */
  .source {{
    display: inline-block;
    background: var(--surface2);
    color: var(--link);
    font-size: 0.8em;
    padding: 0.1rem 0.5rem;
    border-radius: 12px;
    margin-left: 0.3rem;
    text-decoration: none;
  }}
  .source:hover {{ background: var(--accent2); color: #fff; text-decoration: none; }}
  /* Responsive */
  @media (max-width: 600px) {{
    .video-card {{ flex-direction: column; }}
    .video-card img {{ width: 100%; min-width: unset; }}
  }}
</style>
</head>
<body>
{content}
</body>
</html>"""


def load_videos_lookup(videos_file):
    """Build a lookup from video title/ID to metadata."""
    if not videos_file or not Path(videos_file).exists():
        return {}
    videos = load_json(videos_file)
    lookup = {}
    for v in videos:
        lookup[v["video_id"]] = v
        lookup[v["title"].lower()] = v
    return lookup


def find_screenshots(channel_name):
    """Find all screenshot files for a channel."""
    channel_dir = ensure_channel_dir(channel_name)
    screenshots_dir = channel_dir / "screenshots"
    if not screenshots_dir.exists():
        return {}
    screenshots = {}
    for f in screenshots_dir.glob("*.jpg"):
        # filename: {video_id}_{timestamp}.jpg
        parts = f.stem.rsplit("_", 1)
        if len(parts) == 2:
            vid_id = parts[0]
            # Handle nested video IDs with dashes
            if vid_id not in screenshots:
                screenshots[vid_id] = []
            screenshots[vid_id].append({
                "path": str(f),
                "filename": f.name,
                "timestamp": parts[1].replace("-", ":"),
            })
    return screenshots


def md_to_html(md_content, videos_lookup, screenshots, channel_name):
    """Convert markdown to HTML with enhancements."""
    lines = md_content.split("\n")
    html_parts = []
    toc_entries = []
    in_list = False
    in_ordered_list = False
    list_type = None

    channel_dir = ensure_channel_dir(channel_name)

    for line in lines:
        stripped = line.strip()

        # Close open lists if line is not a list item
        if in_list and not stripped.startswith("- ") and not stripped.startswith("* ") and stripped != "":
            html_parts.append("</ul>")
            in_list = False
        if in_ordered_list and not re.match(r'^\d+\.', stripped) and stripped != "":
            html_parts.append("</ol>")
            in_ordered_list = False

        # Headers
        h_match = re.match(r'^(#{1,4})\s+(.*)', stripped)
        if h_match:
            level = len(h_match.group(1))
            text = h_match.group(2)
            anchor = slugify(text)
            if level <= 2:
                toc_entries.append((level, text, anchor))
            html_parts.append(f'<h{level} id="{anchor}">{format_inline(text, videos_lookup)}</h{level}>')
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            html_parts.append("<hr>")
            continue

        # Blockquote
        if stripped.startswith("> "):
            html_parts.append(f'<blockquote>{format_inline(stripped[2:], videos_lookup)}</blockquote>')
            continue

        # Unordered list
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            content = stripped[2:]
            html_parts.append(f'<li>{format_inline(content, videos_lookup)}</li>')
            continue

        # Ordered list
        ol_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if ol_match:
            if not in_ordered_list:
                html_parts.append("<ol>")
                in_ordered_list = True
            content = ol_match.group(2)
            html_parts.append(f'<li>{format_inline(content, videos_lookup)}</li>')
            continue

        # Empty line
        if stripped == "":
            continue

        # Regular paragraph
        html_parts.append(f'<p>{format_inline(stripped, videos_lookup)}</p>')

    # Close any open lists
    if in_list:
        html_parts.append("</ul>")
    if in_ordered_list:
        html_parts.append("</ol>")

    # Build TOC
    toc_html = '<div class="toc"><h2>Table of Contents</h2><ul>'
    for level, text, anchor in toc_entries:
        indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * (level - 1)
        toc_html += f'<li>{indent}<a href="#{anchor}">{text}</a></li>'
    toc_html += "</ul></div>"

    # Insert video cards for any video references
    content = toc_html + "\n".join(html_parts)

    # Inject screenshots where referenced
    for vid_id, ss_list in screenshots.items():
        for ss in ss_list:
            # Use relative path from the HTML file location
            rel_path = f"../screenshots/{ss['filename']}"
            ts = ss["timestamp"]
            video = videos_lookup.get(vid_id, {})
            caption = f'{video.get("title", vid_id)} @ {ts}'
            yt_link = f'https://youtube.com/watch?v={vid_id}&t={timestamp_to_seconds(ts)}s'
            img_html = f'''<div class="screenshot">
                <a href="{yt_link}" target="_blank">
                    <img src="{rel_path}" alt="{caption}" loading="lazy">
                </a>
                <div class="caption">{caption} <a href="{yt_link}" class="source" target="_blank">Watch</a></div>
            </div>'''
            # Try to insert near mentions of this video (by title or video ID)
            inserted = False
            title = video.get("title", "")
            if title and title in content:
                content = content.replace(
                    title,
                    title + img_html,
                    1  # only first occurrence
                )
                inserted = True
            if not inserted and vid_id in content:
                content = content.replace(
                    vid_id,
                    vid_id + img_html,
                    1  # only first occurrence
                )

    return content


def format_inline(text, videos_lookup):
    """Format inline markdown: bold, italic, code, links."""
    # Code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Bold
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)

    # Auto-link video titles to YouTube
    for title_lower, video in videos_lookup.items():
        if isinstance(video, dict) and "video_id" in video:
            title = video.get("title", "")
            if title and title in text:
                yt_url = f'https://youtube.com/watch?v={video["video_id"]}'
                text = text.replace(
                    title,
                    f'{title} <a href="{yt_url}" class="source" target="_blank">Watch</a>',
                    1
                )

    return text


def timestamp_to_seconds(ts):
    """Convert HH:MM:SS or MM:SS to seconds."""
    parts = ts.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0


def generate_html_report(channel_name, report_file, videos_file):
    """Generate an HTML report from a markdown report."""
    report_path = Path(report_file)
    md_content = report_path.read_text(encoding="utf-8")

    videos_lookup = load_videos_lookup(videos_file)
    screenshots = find_screenshots(channel_name)

    # Extract title from first H1
    title_match = re.search(r'^#\s+(.+)', md_content, re.MULTILINE)
    title = title_match.group(1) if title_match else "Research Report"

    html_content = md_to_html(md_content, videos_lookup, screenshots, channel_name)
    full_html = HTML_TEMPLATE.format(title=title, content=html_content)

    output_path = report_path.with_suffix(".html")
    output_path.write_text(full_html, encoding="utf-8")

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate HTML report from markdown")
    parser.add_argument("--channel_name", required=True)
    parser.add_argument("--report_file", required=True, help="Path to markdown report")
    parser.add_argument("--videos_file", help="Path to videos.json for link enrichment")
    args = parser.parse_args()

    output = generate_html_report(args.channel_name, args.report_file, args.videos_file)
    print(json.dumps({"html_report": output}))


if __name__ == "__main__":
    main()
