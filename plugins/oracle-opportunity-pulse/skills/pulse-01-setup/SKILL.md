---
name: pulse-01-setup
description: Guided setup for Oracle Opportunity Pulse SharePoint foundations. Use when installing a new shared Pulse, connecting a user to an existing Pulse, creating, validating, or repairing the Opportunities and Knowledge Items lists, Markdown evidence root folders, _config shared profile, _index folders, _templates, pending queues, per-opportunity folder structures, Graph list payloads, or SharePoint bootstrap prerequisites.
---

# Oracle Opportunity Pulse Setup

## Purpose

Use this skill before ingestion, testing, automation, or wiki query. It is the guided entry point for either installing a new collaborative Pulse in SharePoint or connecting the current user to a Pulse that already exists.

The setup foundation includes the normalized list model, `_config/pulse-profile.json`, base Markdown evidence folders, Knowledge Wiki index folders, and reusable Markdown templates. The `pulse-07-wiki` and `pulse-02-automation` skills depend on this foundation.

## Workflow

1. Ask whether the user is installing a new Pulse or connecting to an existing Pulse.
2. For `install_new`, ask for SharePoint hostname, site path, library path, root folder, list names, timezone, and Zoom folder name.
3. For `connect_existing`, ask where the existing `Opportunities` list, `Knowledge Items` list, and wiki root folder live, or fetch/read `_config/pulse-profile.json` if the user provides it.
4. Run `configure_pulse_connection` with `mode = install_new` or `mode = connect_existing`.
5. Run `validate_pulse_connection` and resolve blocking issues before ingestion or automation.
6. For a new Pulse, run `create_base_sharepoint_lists` to generate the list creation/update plan for:
   - `Opportunities`
   - `Knowledge Items`
7. For a new Pulse, run `create_base_sharepoint_folders` with no client/opportunity to prepare root folders, `_config`, `_index`, `_templates`, and pending queues.
8. Upload or validate the non-secret `_config/pulse-profile.json` using the SharePoint connector or Graph flow.
9. For a specific opportunity, run `create_base_sharepoint_folders` with `client_name` plus `opportunity_key`, `discovery_id`, `opportunity_code`, or `sr_number`.
10. Treat Graph and SharePoint output as dry-run until a confirmed write path exists.

## Guided Questions

Ask only what is missing:

- Are we installing a new Pulse or connecting to an existing Pulse?
- SharePoint hostname, site path, document library path, and wiki root folder.
- List names for `Opportunities` and `Knowledge Items`.
- User timezone as an IANA value such as `America/Lima`, `America/Bogota`, or `America/Mexico_City`.
- Outlook Zoom folder name, defaulting to `[0] Zoom AI companion`.
- Whether Slack is required for this user or only optional link registration in V1.

## Setup To Wiki Handoff

After folders and templates exist in SharePoint, use `pulse-07-wiki` to refresh `_index/*.jsonl`. Setup owns structure; wiki owns indexing, backlinks, timelines, link suggestions, and query behavior.

## Setup To Automation Handoff

After `validate_pulse_connection` returns ready, use `pulse-02-automation` to prepare and create the user's personal 18:00 daily automation. Automation is per user and scans that user's Outlook/Zoom context against the shared Pulse.

## Guardrails

- Do not create a website or frontend.
- Manage SharePoint lists and document-library folders only.
- Do not claim SharePoint changed unless an authorized write action confirms it.
- Do not store tokens, connector credentials, or private Outlook/Slack data in `_config/pulse-profile.json`.
- Keep the two-list model normalized.
- Allow Discovery records before an official opportunity code or SR exists.
- Keep `_index` rebuildable from SharePoint lists and Markdown snapshots.
- Do not answer wiki content questions from setup output alone; hand off to `pulse-07-wiki`.
