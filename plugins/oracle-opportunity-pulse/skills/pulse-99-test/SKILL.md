---
name: pulse-99-test
description: Test Oracle Opportunity Pulse readiness and plugin wiring. Use when checking whether required SharePoint, Outlook Email, Slack, and Oracle Opportunity Pulse tools or plugins are configured, when debugging why the plugin is not visible, or when running smoke tests for guided setup, connect-existing setup, personal automation preparation, list setup, wiki setup, Slack parsing, Outlook candidate detection, Zoom candidate detection, notes, index refresh, and query workflows.
---

# Oracle Opportunity Pulse Test

## Purpose

Use this skill to prove the plugin is ready before real data ingestion and to validate that setup, source skills, and wiki query work as one flow.

## Smoke Test Order

1. Run `check_required_connectors`.
2. Run `configure_pulse_connection` in `install_new` mode with synthetic SharePoint values.
3. Run `validate_pulse_connection` and inspect blocking issues or readiness.
4. Run `configure_pulse_connection` in `connect_existing` mode with a synthetic shared profile.
5. Run `prepare_daily_sync_automation` for 18:00 in `America/Lima` and one additional IANA timezone.
6. Run `build_daily_sync_prompt` and confirm it delegates to automation preparation.
7. Run `create_base_sharepoint_lists` in dry-run mode.
8. Run `create_base_sharepoint_folders` in dry-run mode and confirm `_config/pulse-profile.json`, `_index`, `_templates`, and pending queues appear.
9. Run `configure_knowledge_wiki` with the target SharePoint host/site/library.
10. Register a throwaway Discovery opportunity with `register_opportunity`.
11. Test Slack URL parsing with `register_slack_channel`.
12. Test Outlook and Zoom candidate creation using synthetic messages containing `@agent_data`.
13. Test `propose_candidate`, then `reject_candidate` for synthetic candidates.
14. Run `refresh_knowledge_index` with synthetic opportunities, Knowledge Items, and Markdown documents.
15. Run `query_knowledge_wiki`, `get_opportunity_timeline`, `get_backlinks`, and `suggest_wiki_links`.
16. Run `query_opportunity_pulse` and confirm it includes a `knowledge_wiki` section.

## Success Criteria

- Setup prepares lists, folders, `_index`, `_templates`, and pending queues.
- Guided setup can install a new Pulse or connect to an existing Pulse without storing secrets.
- Personal automation preparation validates timezone, SharePoint, Outlook, Zoom, and Slack readiness before scheduling.
- Source skills create or propose source-specific evidence without autoapproval.
- Wiki tools can refresh index payloads, query approved evidence, produce a timeline, inspect backlinks, and suggest relative Markdown links.

## Visibility Notes

If the plugin is enabled in config but not visible in the active thread, start a new Codex thread after plugin refresh. Current threads do not always acquire newly installed skills and MCP tools.
