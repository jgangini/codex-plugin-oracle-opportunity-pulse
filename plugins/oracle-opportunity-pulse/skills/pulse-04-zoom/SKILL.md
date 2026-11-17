---
name: pulse-04-zoom
description: Capture Zoom AI Companion transcript evidence for Oracle Opportunity Pulse. Use when scanning the exact Outlook folder [0] Zoom AI companion inside an incremental sync window, proposing client/opportunity/SR, approving transcript candidates, or storing Zoom transcript Markdown as Knowledge Items.
---

# Oracle Opportunity Pulse Zoom

## Workflow

1. Find or use the exact Outlook folder `[0] Zoom AI companion`.
2. Use `prepare_incremental_sync_window` for `SourceType = Zoom`, `Direction = MeetingTranscript`, and `SourceScope = [0] Zoom AI companion`.
3. Retrieve every message from that folder inside the sync window.
4. Pass those messages to `scan_zoom_ai_companion`; do not require `@agent_data`.
5. Present proposals with candidate id, client, opportunity, SR, evidence, confidence, and transcript title.
6. Wait for approval or corrected metadata.
7. Use `approve_candidate` after approval.
8. Record the source execution with `record_automation_run`.
9. After approved transcript evidence is written to SharePoint, refresh the Knowledge Wiki index before relying on wiki search.

## Guardrails

- Source type is `Zoom`.
- Direction is `MeetingTranscript`.
- The exact folder is the capture signal; `@agent_data` is not required for Zoom.
- Do not summarize or rewrite transcript Markdown before storing it.
- Do not autoapprove.
- Deduplicate overlap by `internet_message_id` when available, then Zoom/Outlook message id.
- If the wiki index is not refreshed after approval, warn that query results may be stale.
