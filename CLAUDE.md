# YouTube Researcher

A Claude Code workflow for researching YouTube channels and their content.

## How It Works

This project is a **Claude Code-driven workflow** — no UI, no server. When the user says **"start"**, follow the workflow in `workflows/research_channel.md` step by step.

## Project Layout

```
tools/              Python scripts for API calls and data management
  youtube_api.py    YouTube Data API v3 — channel resolution, video listing
  supadata_api.py   Supadata API — transcript fetching
  excel_manager.py  Excel workbook management (openpyxl)
  file_utils.py     Shared utilities (env loading, file paths, slugify)
workflows/          Step-by-step procedures
  research_channel.md   The main research workflow
data/               Output directory (one folder per channel)
  {channel}/
    channel.json        Channel metadata
    videos.json         Master video list
    transcripts/        Raw transcripts (one .txt per video)
    extractions/        Per-video analysis (one .md per video per run)
    reports/            Final synthesis reports (.md)
    {channel}.xlsx      Cumulative Excel workbook
```

## Two Modes (internal — user doesn't need to pick)

- **Channel mode**: What's worth watching, what overlaps, what to skip. Triggered when user intent is about navigating the channel.
- **Research mode**: Deep dive into content — build a playbook, answer questions, learn techniques. Triggered when user intent is about understanding content.

The user just says what they want to know. Claude determines which mode fits. User can also explicitly say "channel mode" or "research mode" if they want to.

## Key Rules

1. **Always show estimation before spending credits.** Before fetching transcripts, show the user how many videos and how many Supadata credits it will cost. Get explicit confirmation.
2. **Never re-fetch cached data.** Transcripts are saved locally. If a transcript file already exists, skip it.
3. **One channel = one folder = one workbook.** All data for a channel accumulates in its folder. The Excel workbook is the central structured artifact.
4. **Process in batches.** For extraction phase with >20 videos, process 10 at a time and show progress.
5. **Save reports as files.** Always save the final report as a markdown file AND update the Excel workbook. Don't just print to conversation.

## Running Tools

All Python tools are in `tools/` and should be run from the project root with the venv activated:
```bash
cd /home/jasonchau/projects/youtube-researcher && source venv/bin/activate && python tools/<script>.py <args>
```

Tools print results as JSON to stdout and progress/errors to stderr.

## Environment

API keys are in `.env`:
- `YOUTUBE_API_KEY` — YouTube Data API v3
- `SUPADATA_API_KEY` — Supadata transcript API
