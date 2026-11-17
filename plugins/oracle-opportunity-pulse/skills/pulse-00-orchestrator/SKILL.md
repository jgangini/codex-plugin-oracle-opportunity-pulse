---
name: pulse-00-orchestrator
description: Manage Oracle Opportunity Pulse workflows for normalized SharePoint lists and Markdown evidence capture. Use when registering Oracle opportunities, Slack channel links, Outlook emails tagged with @agent_data, Zoom AI Companion transcripts, manual notes, managing the Opportunities, Knowledge Items, or Automation Runs lists, or querying opportunity evidence by customer, country, opportunity code, SR, source type, or Markdown file links.
---

# Oracle Opportunity Pulse

## Overview

Use this skill as the main orchestrator for Oracle Opportunity Pulse. It coordinates setup, source capture, approval, Markdown evidence, and Knowledge Wiki query workflows. SharePoint writes require an authorized Microsoft Graph or SharePoint connector path; never claim writes succeeded unless a write tool or Graph execution confirms it.

## Model

Use three SharePoint lists:

- `Opportunities`: the master opportunity context used for classification.
- `Knowledge Items`: normalized evidence rows with `SourceType = Zoom | Outlook | Slack | Notes`.
- `Automation Runs`: per-user/source/direction audit rows and incremental sync watermarks.

Store Markdown evidence below `OracleOpportunityPulseWiki/{ClientName}/{OpportunityKey}/`, with source folders for `zoom`, `outlook/received`, `outlook/sent`, `slack`, and `notes`.

Use `OpportunityKey` as the stable join key. If there is no official opportunity code or SR yet, create a Discovery record with generated `DiscoveryId`, `LifecycleStage = Discovery`, `NeedsOpportunityCode = true`, and `NeedsSR = true`.

Use `_index/*.jsonl` files for rebuildable wiki search, tags, backlinks, and freshness metadata. Use `_templates/*.md` for portable Markdown templates and keep evidence content unchanged.

Read `references/sharepoint-model.md` before creating list payloads or explaining the schema.

## Skill Map

- Use `pulse-01-setup` for SharePoint foundations: lists, root folders, `_index`, `_templates`, pending queues, and per-opportunity folders.
- Use `pulse-07-wiki` after setup to configure the wiki, refresh `_index`, query evidence, inspect timelines/backlinks, and suggest Markdown links.
- Use `pulse-02-automation` after setup validation to prepare or create each user's personal 18:00 daily sync automation.
- Use `pulse-03-outlook`, `pulse-04-zoom`, `pulse-05-slack`, and `pulse-06-notes` only for source-specific capture or registration.
- Use `pulse-99-test` to validate connector readiness and smoke-test the full path.

## Workflow

1. Run guided setup with `configure_pulse_connection` in `install_new` or `connect_existing` mode.
2. Validate readiness with `validate_pulse_connection`.
3. Register or update an opportunity with `register_opportunity`.
4. Create or validate the base lists with `create_base_sharepoint_lists`.
5. Create or validate root/opportunity folders with `create_base_sharepoint_folders`.
6. Prepare a personal daily automation with `prepare_daily_sync_automation` and use Codex `automation_update` only after user confirmation.
7. Register Slack by URL with `register_slack_channel`. Slack V1 stores the channel link only; do not read Slack messages unless a Slack API connector/token is explicitly available.
8. Use `prepare_incremental_sync_window` for each user/source/direction; first run starts at local day start, later runs resume from `Automation Runs.NextScanFrom`.
9. Scan Outlook candidates with `scan_agent_data_outlook` for messages inside the sync window whose body contains `@agent_data`.
10. Scan Zoom transcripts with `scan_zoom_ai_companion` for every message inside the sync window in the exact configured Outlook folder, default `[0] Zoom AI companion`; do not require `@agent_data`.
11. Use `propose_candidate` to show client, opportunity, SR, confidence, and evidence.
12. Wait for explicit user approval or correction.
13. Use `approve_candidate` only after approval. It writes local state and prepares Markdown/wiki paths or Graph payloads.
14. Use `record_automation_run` after each source scan to audit counts and compute the next watermark.
15. Use `query_opportunity_pulse` or `query_knowledge_wiki` for conversational lookup over opportunities, Knowledge Items, and fetched Markdown snapshots.
16. Use `refresh_knowledge_index` after list or Markdown snapshots change, then upload the generated `_index` files with the SharePoint connector.
17. Use `get_opportunity_timeline`, `get_backlinks`, and `suggest_wiki_links` for wiki navigation workflows.

## Handoff Rule

After any approved Outlook, Zoom, Slack, or Notes evidence is stored in SharePoint, refresh the Knowledge Wiki index before relying on wiki search. Querying before refresh is allowed only with an explicit stale-index warning.

## Guardrails

- Use incremental scan windows by default; first run starts at local day start, later runs use the last successful `Automation Runs` watermark with a 10 minute overlap.
- Treat `@agent_data` in the email body as the Outlook ingestion signal only.
- Treat the exact Zoom folder `[0] Zoom AI companion` as the Zoom ingestion signal; do not require `@agent_data` for Zoom.
- Always propose; never autoapprove.
- Preserve Markdown content without frontmatter or summaries. Put metadata in SharePoint list fields or sidecar JSON.
- Query only approved Knowledge Items by default, and exclude `_pending` unless the user asks for pending content.
- Warn when a query uses local staging state or metadata-only Markdown because SharePoint content was not fetched.
- Use `CELeaderEmails` as multiple Oracle email addresses in V1, not SharePoint Person fields.
- Do not force `OpportunityCode` or `SRNumber` during early discovery; use `OpportunityKey`/`DiscoveryId` and update the same row later.
- Keep `DeliveryModel` to `Oracle Services`, `P2P`, `Partner`, or `Customer`.

## Automation Prompt

For the personal daily Codex automation, use `pulse-02-automation` and `prepare_daily_sync_automation`. Default to 18:00 in the user's IANA timezone.

```text
Use $pulse-02-automation to validate my Pulse connection and prepare my personal 18:00 daily sync automation for my timezone.
```
