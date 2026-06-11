---
name: pulse-03-outlook
description: Capture Outlook email evidence for Oracle Opportunity Pulse. Use when scanning current-day received and sent Outlook messages, finding messages whose body contains @agent_data, proposing customer/opportunity/SR classification, approving or rejecting Outlook candidates, or storing Outlook evidence as Markdown under the normalized Knowledge Items model.
---

# Oracle Opportunity Pulse Outlook

## Workflow

1. Use Outlook Email connector to retrieve only current-day received and sent messages.
2. Filter candidate messages whose body contains `@agent_data`.
3. Pass received messages to `scan_agent_data_outlook` with `include_received=true`.
4. Pass sent messages to `scan_agent_data_outlook` with `include_sent=true`.
5. Present each proposal with candidate id, client, opportunity, SR, evidence, confidence, direction, and source URL.
6. Wait for explicit approval or correction.
7. Use `approve_candidate` only after approval.
8. After approved evidence is written to SharePoint, refresh the Knowledge Wiki index before relying on wiki search.

## Guardrails

- Never scan all historical mail by default.
- Never autoapprove.
- Preserve original body as Markdown content.
- Store source as `SourceType = Outlook` and direction as `Received` or `Sent`.
- If the wiki index is not refreshed after approval, warn that query results may be stale.
