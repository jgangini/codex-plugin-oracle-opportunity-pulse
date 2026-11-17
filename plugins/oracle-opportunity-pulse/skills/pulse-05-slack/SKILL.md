---
name: pulse-05-slack
description: Register Slack channel links for Oracle Opportunity Pulse. Use when a user provides a Slack channel URL, wants to associate a Slack group/channel with a client and opportunity, parse a Slack archives URL, register the channel as SourceType Slack, or prepare Slack evidence folders without reading Slack messages automatically.
---

# Oracle Opportunity Pulse Slack

## Workflow

1. Parse the Slack URL with `register_slack_channel`.
2. Extract workspace host and channel id from URLs such as `https://oracle.enterprise.slack.com/archives/C0B9ZUGPV33`.
3. Match or ask for client and opportunity if the master list cannot identify one.
4. Register a `Knowledge Items` row with `SourceType = Slack` and `Direction = Manual`.
5. After the Slack link is written to SharePoint, refresh the Knowledge Wiki index before relying on wiki search.

## Guardrails

- V1 registers Slack links only.
- Do not claim Slack messages were read unless a Slack API connector/token is explicitly available.
- If future Slack message ingestion is enabled, use `Automation Runs` watermarks per user/channel and deduplicate by Slack timestamp.
- Use Slack metadata to help classify future Outlook/Zoom evidence.
- If the wiki index is not refreshed after registration, warn that query results may be stale.
