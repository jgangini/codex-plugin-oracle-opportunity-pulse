---
name: pulse-07-wiki
description: Query and maintain the Oracle Opportunity Pulse Knowledge Wiki in SharePoint. Use when searching opportunity knowledge across Opportunities, Knowledge Items, Markdown evidence files, generated indexes, backlinks, tags, timelines, or when refreshing the wiki index and suggesting portable Markdown links.
---

# Oracle Opportunity Pulse Knowledge Wiki

## Purpose

Use this skill to query and maintain the SharePoint-backed Markdown wiki for Oracle opportunities. It assumes `pulse-01-setup` has already installed or connected to a Pulse and created or validated the SharePoint lists, folders, `_config`, `_index`, `_templates`, and pending queues. The wiki combines:

- `Opportunities` as master opportunity context.
- `Knowledge Items` as normalized evidence metadata.
- Markdown files as the complete evidence content.
- `_index/*.jsonl` files as rebuildable search and navigation indexes.

## Workflow

1. Use `configure_knowledge_wiki` when SharePoint host, site path, library path, root folder, or list names need to be stored or confirmed.
2. If setup has not run, hand off to `pulse-01-setup` and use `configure_pulse_connection` first.
3. Use SharePoint tools to browse/fetch the `_index` files and relevant `.md` files.
4. Use `query_knowledge_wiki` with the fetched opportunities, Knowledge Items, documents, and `index_last_refresh` for conversational answers.
5. Use `get_opportunity_timeline` for chronological evidence by opportunity.
6. Use `get_backlinks` to inspect inbound/outbound Markdown links for one document.
7. Use `suggest_wiki_links` before saving a new note when related Markdown links would improve navigation.
8. Use `refresh_knowledge_index` after SharePoint list or Markdown snapshots change, then upload the prepared `_index` files through SharePoint.

## Guardrails

- SharePoint remains the source of truth; local state is only staging or fallback.
- Query approved evidence by default. Include `_pending` only when the user explicitly asks for pending items.
- Do not autoapprove Outlook or Zoom candidates. Keep proposal and approval flow intact.
- Preserve original Markdown content; do not summarize or rewrite captured transcripts or emails during indexing.
- Use `OpportunityKey` as the stable join key, especially for Discovery records without opportunity code or SR.
- If Markdown content was not fetched, say the result is metadata-only before answering from it.
- If `last-refresh.json` is stale or missing, warn before relying on the answer.

## Wiki Conventions

- Use portable relative Markdown links like `[context](context.md)` and `[note](notes/file.md)`.
- Store generated navigation data in `_index/backlinks.jsonl` and `_index/tags.jsonl`.
- Use simple tags in Markdown such as `#customer`, `#discovery`, `#sr`, `#zoom`, `#outlook`, `#slack`, and `#note`.
- Keep aliases and structured metadata in SharePoint lists or `_index`, not as mandatory Markdown frontmatter.

## Refresh Rule

After any approved source capture changes SharePoint content, refresh `_index` before treating wiki search as current. If refresh cannot run, report the stale or metadata-only limitation in the answer.
