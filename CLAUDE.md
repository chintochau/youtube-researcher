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

## Two Modes

- **Channel mode**: Preset analysis — "which videos to watch, what overlaps, what to skip." No topic needed from user.
- **Research mode**: User provides a topic/goal. Extracts only relevant content, synthesizes into a research report.

Both modes use the same pipeline. The only difference is the extraction and synthesis prompts.

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
