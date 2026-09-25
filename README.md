# BSE Announcements Monitor — Backup Archiver

Personal backup tool that pulls from BSE's public RSS announcements feed
(`bseindia.com/data/xml/announcements.xml`) every 30 minutes via GitHub Actions,
so announcements are captured even when my laptop/local app is off.

Not affiliated with BSE. No login or credentials required — the feed is public.

## What it does
- Fetches the RSS feed, classifies each announcement (same category/catalyst
  logic as my local BSE Intelligence Monitor site), and appends new items to
  `data/announcements-YYYY-MM-DD.jsonl` (deduped by ID, never overwritten).
- Files are grouped by the announcement's own date, not the run time.

## Merging back
These files get periodically merged into my local `bse_history.db` via a
separate script (`merge_to_history.py`, not part of this repo) to fill any
gaps from time offline.

## Known maintenance note
`classify()` in `sync_bse_announcements.py` is a manually-kept-in-sync copy
of the same function in my local `bse_feed.py`. If I change classification
rules locally, this copy needs updating too, or the two will drift apart.
