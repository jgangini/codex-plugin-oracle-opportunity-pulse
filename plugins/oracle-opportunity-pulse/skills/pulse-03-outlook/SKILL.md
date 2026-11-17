---
name: pulse-03-outlook
description: Capture Outlook email evidence for Oracle Opportunity Pulse. Use when scanning received and sent Outlook messages inside an incremental sync window, finding messages whose body contains @agent_data, proposing customer/opportunity/SR classification, approving or rejecting Outlook candidates, or storing Outlook evidence as Markdown under the normalized Knowledge Items model.
---

# Oracle Opportunity Pulse Outlook

## Workflow

1. Use `prepare_incremental_sync_window` for `SourceType = Outlook` and `Direction = Received` or `Sent`.
2. Use Outlook Email connector to retrieve received/sent messages inside that window.
3. Filter candidate messages whose body contains `@agent_data`; this marker applies to Outlook only.
4. Pass received messages to `scan_agent_data_outlook` with `include_received=true`, `scan_from`, and `scan_to`.
5. Pass sent messages to `scan_agent_data_outlook` with `include_sent=true`, `scan_from`, and `scan_to`.
6. Present each proposal with candidate id, client, opportunity, SR, evidence, confidence, direction, and source URL.
7. Wait for explicit approval or correction.
8. Use `approve_candidate` only after approval.
9. Record the source execution with `record_automation_run`.
10. After approved evidence is written to SharePoint, refresh the Knowledge Wiki index before relying on wiki search.

## Guardrails

- Never scan all historical mail by default; use the incremental window from `Automation Runs`.
- Never autoapprove.
- Preserve original body as Markdown content.
- Store source as `SourceType = Outlook` and direction as `Received` or `Sent`.
- Deduplicate overlap by `internet_message_id` when available, then Outlook message id.
- If the wiki index is not refreshed after approval, warn that query results may be stale.
