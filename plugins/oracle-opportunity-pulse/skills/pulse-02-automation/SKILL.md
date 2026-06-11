---
name: pulse-02-automation
description: Create and validate a personal Oracle Opportunity Pulse daily Codex automation. Use when scheduling, preparing, validating, repairing, or explaining the 18:00 per-user sync that scans Outlook received/sent messages, Zoom AI Companion transcripts, optional Slack link readiness, SharePoint Pulse connection, timezone, and source folders before proposing candidates for approval.
---

# Oracle Opportunity Pulse Automation

## Purpose

Use this skill after `pulse-01-setup` has configured or connected the current user to a shared Pulse. It creates a personal Codex automation for that user, usually at 18:00 in their local timezone.

The automation never autoapproves content. It scans current-day sources, proposes classifications, and waits for explicit approval before any SharePoint writes.

## Workflow

1. Run `validate_pulse_connection` to confirm SharePoint, Outlook Email, Slack readiness, wiki root, list names, Zoom folder, and timezone.
2. Ask for the user's timezone only if it is missing or invalid. Use IANA values such as `America/Lima`, `America/Bogota`, or `America/Mexico_City`.
3. Run `prepare_daily_sync_automation` with:
   - `local_time = 18:00`
   - `timezone = <user timezone>`
   - `include_received = true`
   - `include_sent = true`
   - `include_zoom = true`
   - `include_slack = false` unless Slack readiness must be enforced for this user.
4. Review blocking issues and remediation prompts with the user.
5. After confirmation, call Codex `automation_update` with the returned `codex_automation.fields`.

## Personal Automation Rule

Each user creates their own automation. The shared Pulse lives in SharePoint, but each user scans their own Outlook received/sent messages and Zoom AI Companion folder at their own 18:00 local time.

Do not create a central/shared automation unless the user explicitly requests a gateway account and confirms the account, permissions, and ownership model.

## Source Rules

- Outlook: scan received and sent messages from the current day only.
- Ingestion marker: body must contain `@agent_data`.
- Zoom: scan the exact configured Zoom folder, default `[0] Zoom AI companion`.
- Slack V1: validate connector/link registration only; do not claim Slack message ingestion.
- Notes: manual only, not part of the scheduled scan.

## Guardrails

- Never autoapprove candidates.
- Do not write SharePoint evidence until the user approves or corrects a proposal.
- Do not expose or store connector credentials in Pulse profiles or automation prompts.
- Use the native Codex `automation_update` tool for scheduling; do not invent another scheduler.
- If the index may be stale after approved writes, refresh `_index` before relying on wiki search.
