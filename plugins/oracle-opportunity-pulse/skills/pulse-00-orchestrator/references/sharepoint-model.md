# SharePoint Model

## Lists

`Opportunities` is the master list and classification memory:

- `OpportunityKey` text, required internal stable key
- `DiscoveryId` text, required when no opportunity code exists yet
- `ClientName` text
- `Country` text
- `OpportunityCode` text, optional during discovery
- `SRNumber` text, optional
- `LifecycleStage` choice: `Discovery`, `Qualified`, `OpportunityCreated`, `Active`, `Closed`, `OnHold`
- `NeedsOpportunityCode` boolean
- `NeedsSR` boolean
- `WorkloadDescription` multiline text
- `DeliveryModel` choice: `Oracle Services`, `P2P`, `Partner`, `Customer`
- `CELeaderEmails` multiline text or JSON array string
- `OpportunityContext` multiline text
- `ClassificationHintsJson` multiline text
- `RegisteredByEmail` text
- `Status` choice: `Active`, `Closed`, `OnHold`
- `CreatedAt` dateTime
- `LastUpdatedAt` dateTime
- `RootFolderUrl` hyperlink/text

`Knowledge Items` is the normalized evidence list:

- `OpportunityLookup` lookup to `Opportunities` when provisioned in SharePoint
- `OpportunityKey` text fallback and stable join key
- `OpportunityCode` text fallback for local/dry-run mode
- `DiscoveryId` text fallback for discovery-stage opportunities
- `SourceType` choice: `Zoom`, `Outlook`, `Slack`, `Notes`
- `Direction` choice: `Received`, `Sent`, `MeetingTranscript`, `Manual`
- `Title` text
- `SourceUrl` hyperlink/text
- `SourceExternalId` text
- `FolderUrl` hyperlink/text
- `MarkdownFileUrl` hyperlink/text
- `CapturedAt` dateTime
- `RegisteredByEmail` text
- `ApprovalStatus` choice: `Proposed`, `Approved`, `Rejected`
- `ClassificationEvidence` multiline text
- `Notes` multiline text

## Wiki Folder Tree

```text
OracleOpportunityPulseWiki/
  _index/
    opportunities.jsonl
    knowledge-items.jsonl
    documents.jsonl
    backlinks.jsonl
    tags.jsonl
    last-refresh.json
  _templates/
    opportunity-readme.md
    context.md
    meeting-note.md
    email-capture.md
    slack-channel.md
    manual-note.md
  _pending/
    outlook/{yyyy-mm-dd}/received/
    outlook/{yyyy-mm-dd}/sent/
    zoom/{yyyy-mm-dd}/
  {ClientName}/
    {OpportunityKey}/
      README.md
      context.md
      zoom/
        README.md
        *.md
      outlook/
        README.md
        received/
          *.md
        sent/
          *.md
      slack/
        README.md
        *.md
      notes/
        README.md
        *.md
      attachments/
```

## Knowledge Wiki Index

The `_index` folder is rebuildable and should not be treated as the only source of truth.

- `opportunities.jsonl`: normalized `Opportunities` rows.
- `knowledge-items.jsonl`: approved `Knowledge Items` metadata by default.
- `documents.jsonl`: Markdown document paths, read status, tags, and optional fetched content.
- `backlinks.jsonl`: generated inbound/outbound Markdown link relationships.
- `tags.jsonl`: generated tag-to-document relationships.
- `last-refresh.json`: refresh timestamp, source root, counts, and filtering flags.

Query approved evidence by default and exclude `_pending` unless the user explicitly asks for pending material. If a document row has metadata only, fetch the `.md` file from SharePoint before producing content-level conclusions.

## Discovery Standard

Early discovery often starts before an official opportunity code or SR exists. In that case:

- Create the record with `LifecycleStage = Discovery`.
- Generate `DiscoveryId` and use it as the initial `OpportunityKey`.
- Keep `OpportunityCode` and `SRNumber` empty.
- Set `NeedsOpportunityCode = true` and `NeedsSR = true`.
- Store evidence normally under `OracleOpportunityPulseWiki/{ClientName}/{OpportunityKey}/`.
- When an official opportunity code or SR arrives, update the same `Opportunities` row and keep the existing `OpportunityKey` so all evidence remains linked.

This prevents duplicate shadow opportunities while preserving traceability from first discovery through qualified opportunity.

## Graph Requirements

Creating lists and list items requires Microsoft Graph permissions that can write SharePoint content, typically `Sites.ReadWrite.All`. In dry-run mode, produce the request payloads and do not claim that SharePoint was changed.
