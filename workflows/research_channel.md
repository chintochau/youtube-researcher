# YouTube Channel Research Workflow

## Phase 1: Gather Inputs

Ask the user:
1. **Which channel?** — URL, @handle, or channel name
2. **What do you want to know?** — free text. Mention that they can also use `channel mode` (what's worth watching, what to skip) or `research mode` (deep dive into content) if they want to.

Based on the user's response, determine internally which mode fits:
- If the intent is about **navigating the channel** (what to watch, what to skip, is it worth my time, best videos) → use **channel** prompts
- If the intent is about **understanding content** (build a playbook, answer a question, learn a technique) → use **research** prompts
- If ambiguous or blended → use research prompts with channel-style structure in synthesis

The user's response also serves as the `{user_interest}` / `{topic}` variable used in extraction and synthesis prompts.

## Phase 2: Resolve Channel

Run:
```bash
cd /home/jasonchau/projects/youtube-researcher && python tools/youtube_api.py --action channel_info --channel "<input>"
```

Display to user:
- Channel name, subscriber count, total video count
- Channel description (first 2 lines)

## Phase 3: Estimation & Scope Selection

Present the user with:
- **Total videos on channel**: N
- **Supadata credits needed**: 1 per transcript
- **Scope options**:
  - `all` — fetch everything (N credits)
  - `last_n` — most recent N videos (e.g., last 20)
  - `date_range` — videos between two dates (e.g., after 2024-01-01)
  - `keyword` — only videos with keyword in title/description

Ask user to pick a scope. Construct the scope JSON accordingly:
- `{"type": "all"}`
- `{"type": "last_n", "n": 20}`
- `{"type": "date_range", "after": "2024-01-01", "before": "2024-12-31"}`
- `{"type": "keyword", "q": "options"}`

## Phase 4: Fetch Video List

Run:
```bash
cd /home/jasonchau/projects/youtube-researcher && python tools/youtube_api.py --action list_videos --uploads_playlist "<playlist_id>" --channel_name "<name>" --scope '<scope_json>'
```

Show user: how many videos were fetched.

## Phase 5: Update Excel — Videos

Run:
```bash
cd /home/jasonchau/projects/youtube-researcher && python tools/excel_manager.py --action add_videos --channel_name "<name>" --videos_file "data/<slug>/videos.json"
```

## Phase 6: Fetch Transcripts

**Confirm with user before proceeding** — this costs Supadata credits.

Run:
```bash
cd /home/jasonchau/projects/youtube-researcher && python tools/supadata_api.py --action fetch_transcripts --channel_name "<name>" --videos_file "data/<slug>/videos.json"
```

Show user the result: fetched/skipped/failed counts.

Update Excel transcript status:
```bash
cd /home/jasonchau/projects/youtube-researcher && python tools/excel_manager.py --action mark_transcripts --channel_name "<name>"
```

## Phase 7: Extract Phase

For each video with a transcript, read the transcript and produce an extraction.

### Channel Mode System Prompt
```
You are analyzing a YouTube video to evaluate its worth to a viewer interested in: {user_interest}

Extract structured metadata through the lens of this interest:

## Topics
[List main topics covered]

## Key Concepts
[Each concept with a one-line explanation]

## Skill Level
[beginner / intermediate / advanced]

## Actionable Content
[Specific techniques, frameworks, or steps a viewer can actually apply. Rate: high / medium / low / none]

## Unique Insights
[What does this video offer that you wouldn't find in a generic article or competing video on the same topic?]

## Redundancy Signals
[Key phrases, examples, or talking points that likely appear in other videos on this channel — helps detect overlap later]

## Content Type
[tutorial / strategy / review / case-study / Q&A / opinion / other]

## One-Line Summary
[Single sentence: what you walk away knowing after watching this]

## Relevance to User Interest
[How relevant is this video to "{user_interest}"? Rate: directly relevant / tangentially relevant / not relevant. One-line explanation.]

## Worth Watching?
[Yes / Maybe / No — based on relevance to user interest, information density, and uniqueness]
```

### Research Mode System Prompt
```
The user is researching: {topic}

Extract all key findings, insights, data points, techniques, and arguments relevant to this research topic. Ignore sponsorships, intros, and tangents.

Format:
- Use headings and bullet points
- Include timestamps (hh:mm:ss) where relevant
- Be thorough — capture every relevant detail
- If nothing relevant to the topic: say so in one line
```

**Process**: For each transcript file:
1. Read `data/<slug>/transcripts/<video_id>.txt`
2. Apply the appropriate system prompt
3. Save extraction to `data/<slug>/extractions/<video_id>_<mode>_<topic_slug>.md`

**Important**: Process in batches. For large sets (>20 videos), process 10 at a time and show progress.

## Phase 8: Synthesize Phase

Read ALL extraction files for this run and produce the final report.

### Channel Mode Synthesis Prompt
```
You are a learning advisor. The user is interested in **{user_interest}** and found a video on "{channel_name}" that was valuable. They want to know: what else is worth watching, what can I skip, and how do I get the most out of this channel in limited time?

Below are structured extractions from {video_count} videos. Your job is to be the viewer's filter — judge everything through the lens of "{user_interest}". Videos that don't serve this interest should be skipped regardless of their general quality.

Produce a Channel Learning Report:

## Channel Overview
[2-3 sentences: what this channel teaches, who it's for. Then: how much content is truly unique vs recycled across videos. Give a ratio — e.g., "Of 45 videos analyzed, roughly 15 contain unique material."]

## Content Quality Tiers

### Must-Watch (high information density, unique content, actionable)
For each video:
- **[Video Title]** — [what you'll learn that no other video on this channel covers]. Duration: [X min]. Link: [url]

### Worth Watching (good content but some overlap with must-watch list)
- **[Video Title]** — [what's new here vs the must-watch videos]. Duration: [X min]

### Skip (redundant, low-density, or covered better elsewhere)
- **[Video Title]** — redundant with [which must-watch video covers this better]

## Topic Map
Group videos by topic. For each cluster:
### [Topic Name] ([N] videos, [high/moderate/low] overlap)
- **Best video for this topic:** [title] — [why this one wins]
- **What the others add:** [brief note per video — or "nothing new"]
- **Key concepts unique to this cluster:** [list]

## Recommended Watch Order
If someone has limited time, watch in this order for maximum learning with minimum repetition. Include estimated total time.
1. **[Video Title]** ([X min]) — [why this is first: foundational concepts covered]
2. **[Video Title]** ([X min]) — [what this builds on from #1]
...
**Total time: [X hours Y minutes]**

## Repetition Report
[Which talking points, examples, or ideas appear across 3+ videos? This tells the viewer what the creator considers core vs what's filler. List the repeated elements and which videos contain them.]

## Knowledge Gaps
Topics the channel mentions but never explains well — worth searching elsewhere:
- [gap] — mentioned in [video titles] but never unpacked

Be direct. Be opinionated. The user's time is valuable — every "must-watch" you add costs them 10-30 minutes, so only include videos that genuinely earn it.
```

### Research Mode Synthesis Prompt
```
You are a research synthesizer. The user researched "{topic}" across multiple YouTube videos from {channel_name}.

Produce a comprehensive research summary:

## Key Findings
[Group related insights, note agreements/disagreements between sources]

## Top Takeaways
[Ranked list of most important insights]

## Source Attribution
[Which video each major insight came from]

## Open Questions
[What wasn't fully answered by the available content]

Be thorough but concise. Cite video titles for every claim.
```

## Phase 9: Save Report

1. Save markdown report to `data/<slug>/reports/<timestamp>_<mode>_<topic_slug>.md`
2. Update Excel:
```bash
cd /home/jasonchau/projects/youtube-researcher && python tools/excel_manager.py --action full_update --channel_name "<name>" --mode "<mode>" --topic "<topic>" --videos_file "data/<slug>/videos.json" --report_file "<report_filename>" --video_count <N>
```

3. Tell the user where the report and workbook are saved.

## Error Handling

| Error | Action |
|-------|--------|
| Channel not found | Ask user to double-check the URL/handle |
| YouTube API quota exceeded | Stop and inform user. Resume later. |
| Supadata transcript unavailable | Log the video ID, continue with others |
| Supadata rate limited | Wait and retry with increasing delay |
| Transcript too long for extraction | Split into chunks, extract each, merge |
| Excel file locked | Ask user to close the file |
