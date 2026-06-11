---
name: pulse-04-zoom
description: Capture Zoom AI Companion transcript evidence for Oracle Opportunity Pulse. Use when scanning the exact Outlook folder [0] Zoom AI companion, detecting Zoom transcript messages tagged with @agent_data, proposing client/opportunity/SR, approving transcript candidates, or storing Zoom transcript Markdown as Knowledge Items.
---

# Oracle Opportunity Pulse Zoom

## Workflow

1. Find or use the exact Outlook folder `[0] Zoom AI companion`.
2. Retrieve only current-day messages from that folder.
3. Keep only messages whose body contains `@agent_data`.
4. Pass those messages to `scan_zoom_ai_companion`.
5. Present proposals with candidate id, client, opportunity, SR, evidence, confidence, and transcript title.
6. Wait for approval or corrected metadata.
7. Use `approve_candidate` after approval.
8. After approved transcript evidence is written to SharePoint, refresh the Knowledge Wiki index before relying on wiki search.

## Guardrails

- Source type is `Zoom`.
- Direction is `MeetingTranscript`.
- Do not summarize or rewrite transcript Markdown before storing it.
- Do not autoapprove.
- If the wiki index is not refreshed after approval, warn that query results may be stale.
