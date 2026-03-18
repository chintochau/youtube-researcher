# YouTube Researcher

An AI agent workflow for researching YouTube channels and their content. No UI, no server — just you and an AI coding agent having a conversation.

You give it a channel and a question. It fetches videos, grabs transcripts, analyzes every video through the lens of your question, and produces a structured report with watch recommendations or research findings.

## How It Works

This project is a **workflow for AI coding agents** — the agent reads the workflow instructions, runs Python tools, and drives the entire research process through conversation. You just say **"start"** and answer a few questions.

**Compatible agents:**
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (built and tested with this)
- [OpenAI Codex](https://chatgpt.com/codex)
- [Google Antigravity](https://antigravity.google/)
- Or any AI coding agent that can read files and run shell commands

No AI/LLM API key is needed — the agent itself *is* the LLM. You just need API keys for the data sources (YouTube and Supadata).

## What You Get

For any channel + topic, the agent produces:

- **Channel mode** — what's worth watching, what to skip, recommended watch order, redundancy analysis
- **Research mode** — deep dive into content, key findings, techniques, source attribution

All outputs are saved as Markdown reports and an Excel workbook.

## Prerequisites

You need two API keys:
- **YouTube Data API v3 key** — [get one here](https://console.cloud.google.com/apis/library/youtube.googleapis.com)
- **Supadata API key** — [get one here](https://supadata.ai) (used for fetching video transcripts, 1 credit per transcript)

## Setup

1. Clone the repo and add your API keys to `.env`:
   ```
   YOUTUBE_API_KEY=your_youtube_api_key
   SUPADATA_API_KEY=your_supadata_api_key
   ```

2. Open the project in your AI coding agent and say **"start"**. The agent will handle the rest (dependencies, venv, etc.).

## Usage

Once your agent is running, just tell it what you want:

> "Start. I want to research the channel @hubaborhidi — what are the best videos on options trading strategies?"

> "Start. Channel is ThePrimeTime — I want a deep dive on everything he's said about Rust vs Go."

> "Start. Check out @NetworkChuck and tell me which videos are worth watching for someone learning cybersecurity."

The agent will:
1. Resolve the channel and show you stats
2. Analyze video titles against your topic and **recommend a smart subset** to save credits (you can override and fetch all)
3. Show cost estimation and ask for confirmation before spending Supadata credits
4. Fetch transcripts (skipping any already cached locally)
5. Analyze each video through the lens of your question
6. Synthesize a final report and save it

Short videos (2 minutes or less) are excluded by default to skip Shorts and promos. You can ask the agent to include them if needed.

## Project Structure

```
tools/                  Python scripts (called by the agent)
  youtube_api.py        YouTube Data API v3 — channel info, video listing
  supadata_api.py       Supadata API — transcript fetching
  excel_manager.py      Excel workbook management
  file_utils.py         Shared utilities
workflows/              Step-by-step procedures the agent follows
  research_channel.md   Main research workflow
data/                   Output directory (one folder per channel)
  {channel}/
    channel.json        Channel metadata
    videos.json         Video list with metadata
    transcripts/        Raw transcripts (one .txt per video)
    extractions/        Per-video analysis (one .md per video)
    reports/            Final synthesis reports (.md)
    {channel}.xlsx      Excel workbook
```

## Cost Awareness

- **YouTube Data API** — free tier is 10,000 units/day (listing videos is cheap, ~1-2 units per request)
- **Supadata** — 1 credit per transcript fetched. The agent always shows the estimated cost and asks for confirmation before fetching.
- **Transcripts are cached** — re-running the workflow on the same channel won't re-fetch transcripts you already have.

## License

MIT
