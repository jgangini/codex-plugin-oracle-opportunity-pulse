---
name: pulse-06-notes
description: Add manual Markdown notes to Oracle Opportunity Pulse. Use when capturing human-written notes, decisions, follow-ups, context updates, meeting notes not sourced from Outlook/Zoom/Slack, or manual evidence as SourceType Notes for an existing opportunity.
---

# Oracle Opportunity Pulse Notes

## Workflow

1. Confirm the target opportunity using `OpportunityKey`, `DiscoveryId`, opportunity code, SR, or client name.
2. Use `add_note` with Markdown content and title.
3. Store as `SourceType = Notes` and `Direction = Manual`.
4. Use notes to enrich `OpportunityContext` when they help future classification.
5. After approved note evidence is written to SharePoint, refresh the Knowledge Wiki index before relying on wiki search.

## Guardrails

- Keep Markdown as user-provided content.
- Do not mix notes with Outlook/Zoom source types.
- If the opportunity does not exist, register or confirm it before adding the note.
- If the wiki index is not refreshed after adding the note, warn that query results may be stale.
