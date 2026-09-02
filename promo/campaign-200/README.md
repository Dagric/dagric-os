# Dagric 200-video campaign

This folder is the deduplicated production and publishing ledger for 200 **unique scripted videos**. The rows are production briefs, not finished MP4 files. Every item remains `SCRIPTED_NOT_RENDERED` until a human-reviewed final export exists.

## Guardrails

- One unique master concept per ID; no repeated caption or slug.
- One scheduler owns each post. Do not copy a row into a second scheduler.
- The master calendar leaves at least 12 hours between every two planned posts.
- Times are in America/Chicago.
- Use only Dagric-owned captures/branding and original narration. Do not import trending audio unless the platform explicitly clears it for commercial use.
- Do not schedule review-batch MP4s; they contain a review-only label and are only 720-based proofs.
- Scheduler free-tier limits require rolling uploads. Buffer and Publer each allow only 10 queued posts per connected account; Later currently allows 12 posts per profile per month on this workspace.
- Publer does not support Snapchat, so all Snapchat rows stay in Later.

## Research-based baseline slots

- TikTok: Sunday 9:00 AM.
- Instagram Reels: Wednesday 6:00 PM.
- YouTube Shorts: Friday 4:00 PM.
- Snapchat Spotlight: Tuesday 8:00 PM as an initial test slot; replace it with account analytics after enough posts.

## Files

- `campaign.json`: all scripts, shot directions, captions, rights notes, and ownership.
- `master-schedule.csv`: chronological deduplicated plan.
- `buffer-queue.csv`, `later-queue.csv`, `publer-queue.csv`: scheduler-specific imports/working lists.

## Allocation

```json
{
  "Buffer": {
    "TikTok": 17,
    "YouTube Shorts": 17,
    "Instagram Reels": 16
  },
  "Later": {
    "Instagram Reels": 17,
    "Snapchat Spotlight": 50,
    "TikTok": 17,
    "YouTube Shorts": 16
  },
  "Publer": {
    "YouTube Shorts": 17,
    "Instagram Reels": 17,
    "TikTok": 16
  }
}
```
