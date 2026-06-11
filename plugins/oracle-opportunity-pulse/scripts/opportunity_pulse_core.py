from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import os
import posixpath
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


AGENT_TAG = "@agent_data"
DEFAULT_TIMEZONE = "America/Lima"
DEFAULT_ROOT_FOLDER = "OracleOpportunityPulseWiki"
DEFAULT_ZOOM_FOLDER = "[0] Zoom AI companion"
DEFAULT_CONFIG_FOLDER = "_config"
DEFAULT_INDEX_FOLDER = "_index"
DEFAULT_TEMPLATE_FOLDER = "_templates"
DEFAULT_ATTACHMENTS_FOLDER = "attachments"
PULSE_PROFILE_FILE_NAME = "pulse-profile.json"
DELIVERY_MODELS = {"Oracle Services", "P2P", "Partner", "Customer"}
SOURCE_TYPES = {"Zoom", "Outlook", "Slack", "Notes"}
DIRECTIONS = {"Received", "Sent", "MeetingTranscript", "Manual"}
LIFECYCLE_STAGES = {"Discovery", "Qualified", "OpportunityCreated", "Active", "Closed", "OnHold"}
INDEX_FILE_NAMES = {
    "opportunities": "opportunities.jsonl",
    "knowledge_items": "knowledge-items.jsonl",
    "documents": "documents.jsonl",
    "backlinks": "backlinks.jsonl",
    "tags": "tags.jsonl",
    "last_refresh": "last-refresh.json",
}
DEFAULT_WIKI_TEMPLATES = {
    "opportunity-readme.md": "# {ClientName}\n\n- Opportunity key: `{OpportunityKey}`\n- Country: {Country}\n- Stage: {LifecycleStage}\n\n## Context\n\nSee [context](context.md).\n\n## Evidence\n\n- [Zoom](zoom/)\n- [Outlook received](outlook/received/)\n- [Outlook sent](outlook/sent/)\n- [Slack](slack/)\n- [Notes](notes/)\n",
    "context.md": "# Opportunity context\n\nTags: #customer #discovery\n\n## Current understanding\n\n\n## Open questions\n\n\n## Next steps\n\n",
    "meeting-note.md": "# {Title}\n\nTags: #zoom\n\n## Transcript\n\n",
    "email-capture.md": "# {Title}\n\nTags: #outlook\n\n## Email\n\n",
    "slack-channel.md": "# Slack channel\n\nTags: #slack\n\n- Channel: {SourceUrl}\n\n## Notes\n\n",
    "manual-note.md": "# {Title}\n\nTags: #note\n\n",
}


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_state_path() -> Path:
    configured = os.environ.get("OOP_STATE_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    state_root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    return Path(state_root) / "OracleOpportunityPulse" / "oracle-opportunity-pulse-state.json"


def load_state(path: str | Path | None = None) -> dict[str, Any]:
    state_path = Path(path) if path else default_state_path()
    if not state_path.exists():
        return {
            "version": 1,
            "opportunities": [],
            "knowledge_items": [],
            "candidates": [],
            "rejected_candidates": [],
        }
    return json.loads(state_path.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any], path: str | Path | None = None) -> Path:
    state_path = Path(path) if path else default_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return state_path


def now_iso(timezone: str = DEFAULT_TIMEZONE) -> str:
    return dt.datetime.now(ZoneInfo(timezone)).isoformat(timespec="seconds")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def tokenize(value: str | None) -> set[str]:
    return {part for part in re.split(r"[^a-z0-9]+", normalize_text(value)) if len(part) >= 3}


def get_first(record: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return default


def as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        return [part.strip() for part in re.split(r"[;,]", stripped) if part.strip()]
    return [value]


def clean_path(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"/+", "/", value.replace("\\", "/")).strip("/")


def slugify_path_part(value: str | None, fallback: str = "unknown") -> str:
    text = normalize_text(value) or fallback
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", text)
    text = re.sub(r"[^a-z0-9._ -]+", "-", text)
    text = re.sub(r"\s+", "-", text).strip(" .-_")
    return text[:80] or fallback


def make_id(prefix: str, seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def parse_slack_url(slack_url: str) -> dict[str, str]:
    parsed = urlparse(slack_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Slack URL must be an absolute URL.")
    host = parsed.netloc.lower()
    if "slack.com" not in host:
        raise ValueError("Slack URL host must be a Slack workspace host.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "archives":
        raise ValueError("Slack URL must include /archives/{channel_id}.")
    channel_id = parts[1]
    if not re.fullmatch(r"[A-Z0-9]{6,}", channel_id):
        raise ValueError("Slack channel id was not recognized.")
    thread_or_message = parts[2] if len(parts) > 2 else ""
    return {
        "workspace_host": host,
        "channel_id": channel_id,
        "thread_or_message": thread_or_message,
        "canonical_url": f"https://{host}/archives/{channel_id}",
    }


def discovery_id_for(client_name: str, created_at: str | None = None) -> str:
    stamp = re.sub(r"[^0-9]", "", created_at or now_iso())[:8] or dt.datetime.utcnow().strftime("%Y%m%d")
    seed = f"{client_name}|{created_at or now_iso()}"
    return f"DISC-{stamp}-{slugify_path_part(client_name, 'client')}-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:6]}"


def stable_opportunity_key(
    client_name: str,
    opportunity_code: str | None = None,
    sr_number: str | None = None,
    discovery_id: str | None = None,
) -> str:
    if discovery_id:
        return discovery_id
    if opportunity_code:
        return f"OPP-{slugify_path_part(opportunity_code, 'opportunity').upper()}"
    if sr_number:
        return f"SR-{slugify_path_part(sr_number, 'sr').upper()}"
    return discovery_id_for(client_name)


def folder_root_for_opportunity(client_name: str, opportunity_key: str) -> str:
    return "/".join(
        [
            DEFAULT_ROOT_FOLDER,
            slugify_path_part(client_name, "client"),
            slugify_path_part(opportunity_key, "opportunity"),
        ]
    )


def source_folder(root_folder: str, source_type: str, direction: str | None = None) -> str:
    source = source_type.lower()
    if source == "zoom":
        return f"{root_folder}/zoom"
    if source == "outlook":
        if direction == "Sent":
            return f"{root_folder}/outlook/sent"
        return f"{root_folder}/outlook/received"
    if source == "slack":
        return f"{root_folder}/slack"
    if source == "notes":
        return f"{root_folder}/notes"
    return root_folder


def markdown_file_name(title: str | None, source_type: str, captured_at: str | None = None) -> str:
    stamp = captured_at or now_iso()
    safe_stamp = re.sub(r"[^0-9A-Za-z]+", "", stamp)[:14] or dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_title = slugify_path_part(title or source_type, source_type.lower())
    return f"{safe_stamp}-{source_type.lower()}-{safe_title}.md"


def opportunity_fields(opportunity: dict[str, Any]) -> dict[str, Any]:
    return {
        "OpportunityKey": opportunity.get("opportunity_key", ""),
        "DiscoveryId": opportunity.get("discovery_id", ""),
        "ClientName": opportunity.get("client_name", ""),
        "Country": opportunity.get("country", ""),
        "OpportunityCode": opportunity.get("opportunity_code", ""),
        "SRNumber": opportunity.get("sr_number", ""),
        "LifecycleStage": opportunity.get("lifecycle_stage", "Discovery"),
        "NeedsOpportunityCode": opportunity.get("needs_opportunity_code", True),
        "NeedsSR": opportunity.get("needs_sr", True),
        "WorkloadDescription": opportunity.get("workload_description", ""),
        "DeliveryModel": opportunity.get("delivery_model", ""),
        "CELeaderEmails": json.dumps(opportunity.get("ce_leader_emails", []), ensure_ascii=False),
        "OpportunityContext": opportunity.get("opportunity_context", ""),
        "ClassificationHintsJson": json.dumps(opportunity.get("classification_hints", {}), ensure_ascii=False),
        "RegisteredByEmail": opportunity.get("registered_by_email", ""),
        "Status": opportunity.get("status", "Active"),
        "CreatedAt": opportunity.get("created_at", ""),
        "LastUpdatedAt": opportunity.get("last_updated_at", ""),
        "RootFolderUrl": opportunity.get("root_folder_url", opportunity.get("root_folder", "")),
    }


def knowledge_fields(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "OpportunityKey": item.get("opportunity_key", ""),
        "OpportunityCode": item.get("opportunity_code", ""),
        "DiscoveryId": item.get("discovery_id", ""),
        "SourceType": item.get("source_type", ""),
        "Direction": item.get("direction", ""),
        "Title": item.get("title", ""),
        "SourceUrl": item.get("source_url", ""),
        "SourceExternalId": item.get("source_external_id", ""),
        "FolderUrl": item.get("folder_url", item.get("folder_path", "")),
        "MarkdownFileUrl": item.get("markdown_file_url", item.get("markdown_path", "")),
        "CapturedAt": item.get("captured_at", ""),
        "RegisteredByEmail": item.get("registered_by_email", ""),
        "ApprovalStatus": item.get("approval_status", "Approved"),
        "ClassificationEvidence": item.get("classification_evidence", ""),
        "Notes": item.get("notes", ""),
    }


def register_opportunity(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    delivery_model = payload.get("delivery_model", "")
    if delivery_model and delivery_model not in DELIVERY_MODELS:
        raise ValueError(f"DeliveryModel must be one of: {', '.join(sorted(DELIVERY_MODELS))}.")
    client_name = payload.get("client_name", "").strip()
    opportunity_code = payload.get("opportunity_code", "").strip()
    sr_number = payload.get("sr_number", "").strip()
    if not client_name:
        raise ValueError("client_name is required. opportunity_code and sr_number are optional during Discovery.")

    current_time = now_iso()
    discovery_id = payload.get("discovery_id", "").strip()
    opportunity_key = payload.get("opportunity_key", "").strip()
    existing = find_opportunity(
        state,
        opportunity_key=opportunity_key,
        discovery_id=discovery_id,
        opportunity_code=opportunity_code,
        sr_number=sr_number,
        client_name=client_name if not (opportunity_key or discovery_id or opportunity_code or sr_number) else None,
    )
    if existing:
        discovery_id = discovery_id or existing.get("discovery_id", "")
        opportunity_key = opportunity_key or existing.get("opportunity_key", "")
    if not discovery_id and not opportunity_code and not sr_number:
        discovery_id = discovery_id_for(client_name, current_time)
    opportunity_key = opportunity_key or stable_opportunity_key(
        client_name,
        opportunity_code=opportunity_code,
        sr_number=sr_number,
        discovery_id=discovery_id,
    )
    lifecycle_stage = payload.get("lifecycle_stage") or (
        "OpportunityCreated" if opportunity_code else "Discovery"
    )
    if lifecycle_stage not in LIFECYCLE_STAGES:
        raise ValueError(f"LifecycleStage must be one of: {', '.join(sorted(LIFECYCLE_STAGES))}.")
    record = existing or {
        "id": make_id("opp", opportunity_key),
        "created_at": current_time,
    }
    record.update(
        {
            "opportunity_key": opportunity_key,
            "discovery_id": discovery_id or record.get("discovery_id", ""),
            "client_name": client_name,
            "country": payload.get("country", record.get("country", "")),
            "opportunity_code": opportunity_code,
            "sr_number": sr_number,
            "lifecycle_stage": lifecycle_stage,
            "needs_opportunity_code": not bool(opportunity_code),
            "needs_sr": not bool(sr_number),
            "workload_description": payload.get(
                "workload_description", record.get("workload_description", "")
            ),
            "delivery_model": delivery_model or record.get("delivery_model", ""),
            "ce_leader_emails": payload.get("ce_leader_emails", record.get("ce_leader_emails", [])),
            "opportunity_context": payload.get(
                "opportunity_context", record.get("opportunity_context", "")
            ),
            "classification_hints": payload.get(
                "classification_hints", record.get("classification_hints", {})
            ),
            "registered_by_email": payload.get(
                "registered_by_email", record.get("registered_by_email", "")
            ),
            "status": payload.get("status", record.get("status", "Active")),
            "last_updated_at": current_time,
        }
    )
    record["root_folder"] = folder_root_for_opportunity(client_name, opportunity_key)

    if existing is None:
        state["opportunities"].append(record)
    save_state(state)
    return {
        "opportunity": record,
        "sharepoint_fields": opportunity_fields(record),
        "wiki_paths": build_wiki_paths(record),
    }


def find_opportunity(
    state: dict[str, Any],
    opportunity_key: str | None = None,
    discovery_id: str | None = None,
    opportunity_code: str | None = None,
    sr_number: str | None = None,
    client_name: str | None = None,
) -> dict[str, Any] | None:
    normalized_key = normalize_text(opportunity_key)
    normalized_discovery = normalize_text(discovery_id)
    normalized_code = normalize_text(opportunity_code)
    normalized_sr = normalize_text(sr_number)
    normalized_client = normalize_text(client_name)
    for opportunity in state.get("opportunities", []):
        if normalized_key and normalize_text(opportunity.get("opportunity_key")) == normalized_key:
            return opportunity
        if normalized_discovery and normalize_text(opportunity.get("discovery_id")) == normalized_discovery:
            return opportunity
        if normalized_code and normalize_text(opportunity.get("opportunity_code")) == normalized_code:
            return opportunity
        if normalized_sr and normalize_text(opportunity.get("sr_number")) == normalized_sr:
            return opportunity
        if normalized_client and normalize_text(opportunity.get("client_name")) == normalized_client:
            return opportunity
    return None


def build_wiki_paths(opportunity: dict[str, Any]) -> dict[str, str]:
    root = opportunity["root_folder"]
    return {
        "root": root,
        "readme": f"{root}/README.md",
        "context": f"{root}/context.md",
        "zoom": f"{root}/zoom",
        "outlook_received": f"{root}/outlook/received",
        "outlook_sent": f"{root}/outlook/sent",
        "slack": f"{root}/slack",
        "notes": f"{root}/notes",
        "attachments": f"{root}/{DEFAULT_ATTACHMENTS_FOLDER}",
    }


def register_slack_channel(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    parsed = parse_slack_url(payload["slack_url"])
    opportunity = find_opportunity(
        state,
        opportunity_key=payload.get("opportunity_key"),
        discovery_id=payload.get("discovery_id"),
        opportunity_code=payload.get("opportunity_code"),
        client_name=payload.get("client_name"),
    )
    if opportunity is None:
        proposal = classify_text(
            state,
            " ".join(
                [
                    payload.get("client_name", ""),
                    payload.get("opportunity_code", ""),
                    payload.get("notes", ""),
                    parsed["channel_id"],
                ]
            ),
        )
        return {
            "status": "needs_confirmation",
            "slack": parsed,
            "proposal": proposal,
            "message": "No exact opportunity was found. Confirm or register the opportunity first.",
        }

    root = opportunity["root_folder"]
    item = {
        "id": make_id("ki", parsed["canonical_url"] + opportunity.get("opportunity_key", opportunity["id"])),
        "opportunity_id": opportunity["id"],
        "opportunity_key": opportunity.get("opportunity_key", ""),
        "discovery_id": opportunity.get("discovery_id", ""),
        "opportunity_code": opportunity.get("opportunity_code", ""),
        "source_type": "Slack",
        "direction": "Manual",
        "title": payload.get("title") or f"Slack channel {parsed['channel_id']}",
        "source_url": parsed["canonical_url"],
        "source_external_id": parsed["channel_id"],
        "folder_path": source_folder(root, "Slack"),
        "markdown_path": "",
        "captured_at": now_iso(),
        "registered_by_email": payload.get("registered_by_email", ""),
        "approval_status": "Approved",
        "classification_evidence": "Slack channel URL was supplied by the user.",
        "notes": payload.get("notes", ""),
    }
    upsert_knowledge_item(state, item)
    save_state(state)
    return {
        "status": "registered",
        "slack": parsed,
        "knowledge_item": item,
        "sharepoint_fields": knowledge_fields(item),
    }


def upsert_knowledge_item(state: dict[str, Any], item: dict[str, Any]) -> None:
    items = state.setdefault("knowledge_items", [])
    for index, existing in enumerate(items):
        if existing.get("id") == item.get("id"):
            items[index] = item
            return
    items.append(item)


def extract_email_body(message: dict[str, Any]) -> str:
    for key in ("body", "text_body", "content", "bodyPreview", "preview"):
        value = message.get(key)
        if isinstance(value, dict):
            content = value.get("content")
            if isinstance(content, str):
                return html.unescape(re.sub(r"<[^>]+>", "", content))
        if isinstance(value, str) and value.strip():
            return value
    return ""


def contains_agent_tag(body: str) -> bool:
    return AGENT_TAG.lower() in body.lower()


def extract_sr_number(text: str) -> str:
    patterns = [
        r"\b(?:SR|Service Request)\s*(?:#|:|-)?\s*([A-Z0-9][A-Z0-9._-]{4,})\b",
        r"\b([0-9]-[0-9]{6,})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def parse_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(raw)
    except ValueError:
        return None


def date_sort_value(value: str | None) -> float:
    parsed = parse_datetime(value)
    if parsed is None:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(DEFAULT_TIMEZONE))
    return parsed.timestamp()


def is_index_stale(last_refresh: str | None, max_age_hours: int | float = 24) -> bool:
    parsed = parse_datetime(last_refresh)
    if parsed is None:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(DEFAULT_TIMEZONE))
    age = dt.datetime.now(ZoneInfo(DEFAULT_TIMEZONE)) - parsed.astimezone(ZoneInfo(DEFAULT_TIMEZONE))
    return age.total_seconds() > float(max_age_hours) * 3600


def is_current_day(value: str | None, timezone: str = DEFAULT_TIMEZONE) -> bool:
    parsed = parse_datetime(value)
    if parsed is None:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone))
    return parsed.astimezone(ZoneInfo(timezone)).date() == dt.datetime.now(
        ZoneInfo(timezone)
    ).date()


def build_candidate(
    message: dict[str, Any],
    source_type: str,
    direction: str,
    timezone: str = DEFAULT_TIMEZONE,
) -> dict[str, Any] | None:
    body = extract_email_body(message)
    if not contains_agent_tag(body):
        return None
    title = message.get("subject") or message.get("title") or "Untitled message"
    captured_at = (
        message.get("receivedDateTime")
        or message.get("sentDateTime")
        or message.get("createdDateTime")
        or now_iso(timezone)
    )
    seed = "|".join(
        [
            str(message.get("id") or message.get("internetMessageId") or ""),
            source_type,
            direction,
            title,
            captured_at,
        ]
    )
    text = "\n".join([title, body])
    return {
        "id": make_id("cand", seed),
        "source_type": source_type,
        "direction": direction,
        "title": title,
        "source_url": message.get("webLink") or message.get("link") or "",
        "source_external_id": message.get("id") or message.get("internetMessageId") or "",
        "captured_at": captured_at,
        "sender": message.get("from") or message.get("sender") or "",
        "to": message.get("toRecipients") or message.get("to") or "",
        "sr_number": extract_sr_number(text),
        "body": body,
        "approval_status": "Proposed",
    }


def scan_messages(
    messages: list[dict[str, Any]],
    source_type: str,
    direction: str,
    today_only: bool = True,
    timezone: str = DEFAULT_TIMEZONE,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = state or load_state()
    candidates = []
    for message in messages:
        date_value = (
            message.get("receivedDateTime")
            if direction == "Received"
            else message.get("sentDateTime") or message.get("receivedDateTime")
        )
        if today_only and not is_current_day(date_value, timezone):
            continue
        candidate = build_candidate(message, source_type, direction, timezone)
        if candidate is None:
            continue
        candidate["proposal"] = classify_candidate(state, candidate)
        upsert_candidate(state, candidate)
        candidates.append(candidate)
    save_state(state)
    return {"count": len(candidates), "candidates": candidates}


def upsert_candidate(state: dict[str, Any], candidate: dict[str, Any]) -> None:
    candidates = state.setdefault("candidates", [])
    for index, existing in enumerate(candidates):
        if existing.get("id") == candidate.get("id"):
            candidates[index] = candidate
            return
    candidates.append(candidate)


def find_candidate(state: dict[str, Any], candidate_id: str) -> dict[str, Any] | None:
    for candidate in state.get("candidates", []):
        if candidate.get("id") == candidate_id:
            return candidate
    return None


def classify_candidate(state: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    text = "\n".join(
        [
            candidate.get("title", ""),
            candidate.get("body", ""),
            candidate.get("sr_number", ""),
        ]
    )
    return classify_text(state, text)


def classify_text(state: dict[str, Any], text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    text_tokens = tokenize(text)
    scored = []
    for opportunity in state.get("opportunities", []):
        score = 0
        evidence = []
        code = normalize_text(opportunity.get("opportunity_code"))
        client = normalize_text(opportunity.get("client_name"))
        sr = normalize_text(opportunity.get("sr_number"))
        if code and code in normalized:
            score += 100
            evidence.append("matched opportunity code")
        if client and client in normalized:
            score += 55
            evidence.append("matched client name")
        if sr and sr in normalized:
            score += 70
            evidence.append("matched SR number")
        context_tokens = tokenize(opportunity.get("opportunity_context", ""))
        hint_tokens = tokenize(json.dumps(opportunity.get("classification_hints", {}), ensure_ascii=False))
        overlap = len(text_tokens & (context_tokens | hint_tokens))
        if overlap:
            score += min(40, overlap * 5)
            evidence.append(f"matched {overlap} context/hint tokens")
        if score:
            scored.append(
                {
                    "opportunity_id": opportunity.get("id"),
                    "opportunity_key": opportunity.get("opportunity_key", ""),
                    "discovery_id": opportunity.get("discovery_id", ""),
                    "client_name": opportunity.get("client_name"),
                    "opportunity_code": opportunity.get("opportunity_code"),
                    "sr_number": opportunity.get("sr_number", ""),
                    "lifecycle_stage": opportunity.get("lifecycle_stage", "Discovery"),
                    "score": score,
                    "confidence": round(min(0.95, score / 140), 2),
                    "evidence": evidence,
                }
            )
    scored.sort(key=lambda item: item["score"], reverse=True)
    return {
        "suggestions": scored[:5],
        "new_opportunity_suggested": not scored or scored[0]["score"] < 35,
    }


def propose_candidate(candidate_id: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    candidate = find_candidate(state, candidate_id)
    if candidate is None:
        raise ValueError(f"Candidate not found: {candidate_id}")
    proposal = classify_candidate(state, candidate)
    candidate["proposal"] = proposal
    upsert_candidate(state, candidate)
    save_state(state)
    return {"candidate": public_candidate(candidate), "proposal": proposal}


def public_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    body = candidate.get("body", "")
    preview = body[:500] + ("..." if len(body) > 500 else "")
    public = dict(candidate)
    public["body_preview"] = preview
    public.pop("body", None)
    return public


def approve_candidate(
    candidate_id: str,
    overrides: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = state or load_state()
    overrides = overrides or {}
    candidate = find_candidate(state, candidate_id)
    if candidate is None:
        raise ValueError(f"Candidate not found: {candidate_id}")
    opportunity_key = overrides.get("opportunity_key")
    discovery_id = overrides.get("discovery_id")
    opportunity_code = overrides.get("opportunity_code")
    sr_number = overrides.get("sr_number", candidate.get("sr_number", ""))
    client_name = overrides.get("client_name")
    selected = None
    if opportunity_key or discovery_id or opportunity_code or sr_number or client_name:
        selected = find_opportunity(
            state,
            opportunity_key=opportunity_key,
            discovery_id=discovery_id,
            opportunity_code=opportunity_code,
            sr_number=sr_number,
            client_name=client_name,
        )
    if selected is None:
        suggestions = candidate.get("proposal", {}).get("suggestions", [])
        if suggestions:
            selected = find_opportunity(
                state,
                opportunity_key=suggestions[0].get("opportunity_key"),
                discovery_id=suggestions[0].get("discovery_id"),
                opportunity_code=suggestions[0].get("opportunity_code"),
                sr_number=suggestions[0].get("sr_number"),
            )
    if selected is None:
        if not client_name:
            return {
                "status": "needs_confirmation",
                "message": "Provide at least client_name to create a Discovery opportunity. opportunity_code and sr_number can be added later.",
                "candidate": public_candidate(candidate),
            }
        selected = register_opportunity(
            {
                "client_name": client_name,
                "country": overrides.get("country", ""),
                "opportunity_code": opportunity_code,
                "sr_number": sr_number,
                "discovery_id": discovery_id,
                "opportunity_key": opportunity_key,
                "lifecycle_stage": overrides.get("lifecycle_stage", "Discovery" if not opportunity_code else "OpportunityCreated"),
                "workload_description": overrides.get("workload_description", ""),
                "delivery_model": overrides.get("delivery_model", ""),
                "ce_leader_emails": overrides.get("ce_leader_emails", []),
                "registered_by_email": overrides.get("registered_by_email", ""),
                "opportunity_context": overrides.get("opportunity_context", ""),
            },
            state=state,
        )["opportunity"]

    source_type = candidate["source_type"]
    direction = candidate["direction"]
    folder_path = source_folder(selected["root_folder"], source_type, direction)
    file_name = markdown_file_name(candidate.get("title"), source_type, candidate.get("captured_at"))
    markdown_path = f"{folder_path}/{file_name}"
    item = {
        "id": make_id("ki", candidate_id + selected["id"]),
        "opportunity_id": selected["id"],
        "opportunity_key": selected.get("opportunity_key", ""),
        "discovery_id": selected.get("discovery_id", ""),
        "opportunity_code": selected.get("opportunity_code", ""),
        "source_type": source_type,
        "direction": direction,
        "title": candidate.get("title", ""),
        "source_url": candidate.get("source_url", ""),
        "source_external_id": candidate.get("source_external_id", ""),
        "folder_path": folder_path,
        "markdown_path": markdown_path,
        "captured_at": candidate.get("captured_at", now_iso()),
        "registered_by_email": overrides.get("registered_by_email", ""),
        "approval_status": "Approved",
        "classification_evidence": json.dumps(candidate.get("proposal", {}), ensure_ascii=False),
        "notes": overrides.get("notes", ""),
    }
    upsert_knowledge_item(state, item)
    candidate["approval_status"] = "Approved"
    candidate["approved_knowledge_item_id"] = item["id"]
    update_context_from_item(selected, candidate, overrides)
    upsert_candidate(state, candidate)
    save_state(state)
    local_file = write_local_outbox(markdown_path, candidate.get("body", ""))
    return {
        "status": "approved",
        "opportunity": selected,
        "knowledge_item": item,
        "sharepoint_fields": knowledge_fields(item),
        "markdown_path": markdown_path,
        "local_outbox_file": str(local_file),
    }


def update_context_from_item(
    opportunity: dict[str, Any],
    candidate: dict[str, Any],
    overrides: dict[str, Any],
) -> None:
    snippets = [
        opportunity.get("opportunity_context", "").strip(),
        overrides.get("context_update", "").strip(),
    ]
    title = candidate.get("title", "")
    sr = candidate.get("sr_number", "")
    if title:
        snippets.append(f"Approved {candidate.get('source_type')} signal: {title}")
    if sr and sr not in opportunity.get("sr_number", ""):
        opportunity["sr_number"] = opportunity.get("sr_number") or sr
    opportunity["opportunity_context"] = "\n".join(part for part in snippets if part).strip()
    opportunity["last_updated_at"] = now_iso()


def write_local_outbox(markdown_path: str, content: str) -> Path:
    outbox_root = default_state_path().parent / "outbox"
    target = outbox_root / Path(markdown_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def reject_candidate(
    candidate_id: str,
    reason: str = "",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = state or load_state()
    candidate = find_candidate(state, candidate_id)
    if candidate is None:
        raise ValueError(f"Candidate not found: {candidate_id}")
    candidate["approval_status"] = "Rejected"
    candidate["rejection_reason"] = reason
    upsert_candidate(state, candidate)
    state.setdefault("rejected_candidates", []).append({"candidate_id": candidate_id, "reason": reason})
    save_state(state)
    return {"status": "rejected", "candidate": public_candidate(candidate)}


def add_note(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    opportunity = find_opportunity(
        state,
        opportunity_key=payload.get("opportunity_key"),
        discovery_id=payload.get("discovery_id"),
        opportunity_code=payload.get("opportunity_code"),
        sr_number=payload.get("sr_number"),
        client_name=payload.get("client_name"),
    )
    if opportunity is None:
        raise ValueError("Target opportunity was not found. Use opportunity_key, discovery_id, opportunity_code, sr_number, or client_name.")
    title = payload.get("title") or "Manual note"
    folder_path = source_folder(opportunity["root_folder"], "Notes")
    markdown_path = f"{folder_path}/{markdown_file_name(title, 'Notes')}"
    item = {
        "id": make_id("ki", opportunity["id"] + title + now_iso()),
        "opportunity_id": opportunity["id"],
        "opportunity_key": opportunity.get("opportunity_key", ""),
        "discovery_id": opportunity.get("discovery_id", ""),
        "opportunity_code": opportunity.get("opportunity_code", ""),
        "source_type": "Notes",
        "direction": "Manual",
        "title": title,
        "source_url": "",
        "source_external_id": "",
        "folder_path": folder_path,
        "markdown_path": markdown_path,
        "captured_at": now_iso(),
        "registered_by_email": payload.get("registered_by_email", ""),
        "approval_status": "Approved",
        "classification_evidence": "Manual note.",
        "notes": payload.get("notes", ""),
    }
    upsert_knowledge_item(state, item)
    save_state(state)
    local_file = write_local_outbox(markdown_path, payload.get("markdown_content", ""))
    return {
        "status": "created",
        "knowledge_item": item,
        "sharepoint_fields": knowledge_fields(item),
        "local_outbox_file": str(local_file),
    }


def record_fields(record: dict[str, Any]) -> dict[str, Any]:
    fields = record.get("fields")
    if isinstance(fields, dict):
        merged = dict(record)
        merged.update(fields)
        return merged
    return record


def normalize_opportunity_record(record: dict[str, Any]) -> dict[str, Any]:
    source = record_fields(record)
    client_name = str(get_first(source, "client_name", "ClientName")).strip()
    opportunity_key = str(get_first(source, "opportunity_key", "OpportunityKey")).strip()
    discovery_id = str(get_first(source, "discovery_id", "DiscoveryId")).strip()
    opportunity_code = str(get_first(source, "opportunity_code", "OpportunityCode")).strip()
    sr_number = str(get_first(source, "sr_number", "SRNumber")).strip()
    if not opportunity_key and client_name:
        opportunity_key = stable_opportunity_key(
            client_name,
            opportunity_code=opportunity_code,
            sr_number=sr_number,
            discovery_id=discovery_id,
        )
    root_folder = str(
        get_first(
            source,
            "root_folder",
            "RootFolder",
            "RootFolderUrl",
            default=folder_root_for_opportunity(client_name, opportunity_key) if client_name and opportunity_key else "",
        )
    )
    return {
        "id": str(get_first(source, "id", "Id", default=make_id("opp", opportunity_key or client_name))),
        "opportunity_key": opportunity_key,
        "discovery_id": discovery_id,
        "client_name": client_name,
        "country": str(get_first(source, "country", "Country")).strip(),
        "opportunity_code": opportunity_code,
        "sr_number": sr_number,
        "lifecycle_stage": str(get_first(source, "lifecycle_stage", "LifecycleStage", default="Discovery")).strip(),
        "needs_opportunity_code": bool(get_first(source, "needs_opportunity_code", "NeedsOpportunityCode", default=not bool(opportunity_code))),
        "needs_sr": bool(get_first(source, "needs_sr", "NeedsSR", default=not bool(sr_number))),
        "workload_description": str(get_first(source, "workload_description", "WorkloadDescription")).strip(),
        "delivery_model": str(get_first(source, "delivery_model", "DeliveryModel")).strip(),
        "ce_leader_emails": as_list(get_first(source, "ce_leader_emails", "CELeaderEmails", default=[])),
        "opportunity_context": str(get_first(source, "opportunity_context", "OpportunityContext")).strip(),
        "classification_hints": get_first(source, "classification_hints", "ClassificationHintsJson", default={}),
        "registered_by_email": str(get_first(source, "registered_by_email", "RegisteredByEmail")).strip(),
        "status": str(get_first(source, "status", "Status", default="Active")).strip(),
        "created_at": str(get_first(source, "created_at", "CreatedAt")).strip(),
        "last_updated_at": str(get_first(source, "last_updated_at", "LastUpdatedAt")).strip(),
        "root_folder": clean_path(root_folder),
    }


def normalize_knowledge_item(record: dict[str, Any]) -> dict[str, Any]:
    source = record_fields(record)
    markdown_path = str(get_first(source, "markdown_path", "MarkdownPath", "MarkdownFileUrl")).strip()
    folder_path = str(get_first(source, "folder_path", "FolderPath", "FolderUrl")).strip()
    source_type = str(get_first(source, "source_type", "SourceType")).strip()
    direction = str(get_first(source, "direction", "Direction")).strip()
    title = str(get_first(source, "title", "Title", default=source_type or "Knowledge item")).strip()
    opportunity_key = str(get_first(source, "opportunity_key", "OpportunityKey")).strip()
    return {
        "id": str(get_first(source, "id", "Id", default=make_id("ki", markdown_path or title))),
        "opportunity_id": str(get_first(source, "opportunity_id", "OpportunityId")).strip(),
        "opportunity_key": opportunity_key,
        "discovery_id": str(get_first(source, "discovery_id", "DiscoveryId")).strip(),
        "opportunity_code": str(get_first(source, "opportunity_code", "OpportunityCode")).strip(),
        "source_type": source_type,
        "direction": direction,
        "title": title,
        "source_url": str(get_first(source, "source_url", "SourceUrl")).strip(),
        "source_external_id": str(get_first(source, "source_external_id", "SourceExternalId")).strip(),
        "folder_path": clean_path(folder_path),
        "markdown_path": clean_path(markdown_path),
        "markdown_file_url": str(get_first(source, "markdown_file_url", "MarkdownFileUrl", default=markdown_path)).strip(),
        "captured_at": str(get_first(source, "captured_at", "CapturedAt")).strip(),
        "registered_by_email": str(get_first(source, "registered_by_email", "RegisteredByEmail")).strip(),
        "approval_status": str(get_first(source, "approval_status", "ApprovalStatus", default="Approved")).strip(),
        "classification_evidence": str(get_first(source, "classification_evidence", "ClassificationEvidence")).strip(),
        "notes": str(get_first(source, "notes", "Notes")).strip(),
    }


def extract_tags(markdown_content: str | None) -> list[str]:
    if not markdown_content:
        return []
    tags = {
        f"#{match.group(1)}"
        for match in re.finditer(r"(?<![\w/])#([A-Za-z][A-Za-z0-9_-]{1,60})\b", markdown_content)
    }
    return sorted(tags, key=str.lower)


def extract_markdown_links(markdown_content: str | None, source_path: str = "") -> list[dict[str, str]]:
    if not markdown_content:
        return []
    links: list[dict[str, str]] = []
    for match in re.finditer(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", markdown_content):
        anchor = match.group(1).strip()
        raw_target = match.group(2).strip()
        target = raw_target
        if not re.match(r"^[a-z][a-z0-9+.-]*:", raw_target, flags=re.IGNORECASE) and not raw_target.startswith("#"):
            base = posixpath.dirname(clean_path(source_path))
            target = clean_path(posixpath.normpath(posixpath.join(base, raw_target)) if base else raw_target)
        links.append({"anchor": anchor, "target_path": target, "raw_target": raw_target})
    return links


def normalize_document_record(record: dict[str, Any]) -> dict[str, Any]:
    source = record_fields(record)
    content = str(get_first(source, "content", "markdown", "text", "body", default=""))
    path = clean_path(str(get_first(source, "path", "markdown_path", "MarkdownPath", "MarkdownFileUrl", "url", "webUrl")))
    title = str(get_first(source, "title", "Title", "name", default=posixpath.basename(path) or "Markdown document")).strip()
    source_type = str(get_first(source, "source_type", "SourceType")).strip()
    return {
        "id": str(get_first(source, "id", "Id", default=make_id("doc", path or title))),
        "path": path,
        "url": str(get_first(source, "url", "webUrl", "MarkdownFileUrl", default=path)).strip(),
        "title": title,
        "opportunity_key": str(get_first(source, "opportunity_key", "OpportunityKey")).strip(),
        "discovery_id": str(get_first(source, "discovery_id", "DiscoveryId")).strip(),
        "opportunity_code": str(get_first(source, "opportunity_code", "OpportunityCode")).strip(),
        "source_type": source_type,
        "captured_at": str(get_first(source, "captured_at", "CapturedAt", "lastModifiedDateTime")).strip(),
        "approval_status": str(get_first(source, "approval_status", "ApprovalStatus", default="Approved")).strip(),
        "content": content,
        "tags": as_list(get_first(source, "tags", "Tags", default=[])) or extract_tags(content),
        "links": extract_markdown_links(content, path),
        "read_status": "read" if content else "metadata_only",
    }


def jsonl(records: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)


def approved_item(item: dict[str, Any]) -> bool:
    return normalize_text(item.get("approval_status", "Approved")) == "approved"


def is_pending_path(path: str | None) -> bool:
    normalized = f"/{clean_path(path)}/"
    return "/_pending/" in normalized


def normalize_site_path(value: str | None) -> str:
    site_path = str(value or "").strip()
    if site_path and not site_path.startswith("/"):
        site_path = f"/{site_path}"
    return site_path


def valid_timezone(value: str | None) -> bool:
    if not value:
        return False
    try:
        ZoneInfo(str(value))
    except Exception:
        return False
    return True


def wiki_config_from_state(state: dict[str, Any]) -> dict[str, Any]:
    configured = state.get("knowledge_wiki_config") or {}
    root_folder = configured.get("root_folder") or DEFAULT_ROOT_FOLDER
    return {
        "hostname": configured.get("hostname", ""),
        "site_path": configured.get("site_path", ""),
        "library_path": clean_path(configured.get("library_path", "Shared Documents")),
        "root_folder": clean_path(root_folder),
        "index_folder": clean_path(configured.get("index_folder", f"{root_folder}/{DEFAULT_INDEX_FOLDER}")),
        "templates_folder": clean_path(configured.get("templates_folder", f"{root_folder}/{DEFAULT_TEMPLATE_FOLDER}")),
        "opportunities_list": configured.get("opportunities_list", "Opportunities"),
        "knowledge_items_list": configured.get("knowledge_items_list", "Knowledge Items"),
    }


def pulse_connection_from_state(state: dict[str, Any]) -> dict[str, Any]:
    connection = state.get("pulse_connection") or {}
    if not connection:
        wiki = wiki_config_from_state(state)
        connection = {
            "hostname": wiki["hostname"],
            "site_path": wiki["site_path"],
            "library_path": wiki["library_path"],
            "root_folder": wiki["root_folder"],
            "opportunities_list": wiki["opportunities_list"],
            "knowledge_items_list": wiki["knowledge_items_list"],
        }
    return normalize_pulse_profile(connection)


def normalize_pulse_profile(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    source = dict(payload or {})
    root_folder = clean_path(str(source.get("root_folder") or DEFAULT_ROOT_FOLDER))
    return {
        "schema_version": 1,
        "profile_name": str(source.get("profile_name") or "Oracle Opportunity Pulse").strip(),
        "mode": str(source.get("mode") or "connect_existing").strip() or "connect_existing",
        "hostname": str(source.get("hostname") or "").strip(),
        "site_path": normalize_site_path(source.get("site_path")),
        "library_path": clean_path(str(source.get("library_path") or "Shared Documents")),
        "root_folder": root_folder,
        "config_folder": clean_path(str(source.get("config_folder") or f"{root_folder}/{DEFAULT_CONFIG_FOLDER}")),
        "index_folder": clean_path(str(source.get("index_folder") or f"{root_folder}/{DEFAULT_INDEX_FOLDER}")),
        "templates_folder": clean_path(str(source.get("templates_folder") or f"{root_folder}/{DEFAULT_TEMPLATE_FOLDER}")),
        "opportunities_list": str(source.get("opportunities_list") or "Opportunities").strip(),
        "knowledge_items_list": str(source.get("knowledge_items_list") or "Knowledge Items").strip(),
        "timezone": str(source.get("timezone") if "timezone" in source else DEFAULT_TIMEZONE).strip(),
        "zoom_folder": str(source.get("zoom_folder") if "zoom_folder" in source else DEFAULT_ZOOM_FOLDER).strip(),
        "source_defaults": {
            "outlook_received": bool((source.get("source_defaults") or {}).get("outlook_received", True)),
            "outlook_sent": bool((source.get("source_defaults") or {}).get("outlook_sent", True)),
            "zoom": bool((source.get("source_defaults") or {}).get("zoom", True)),
            "slack_links": bool((source.get("source_defaults") or {}).get("slack_links", True)),
            "notes": bool((source.get("source_defaults") or {}).get("notes", True)),
        },
    }


def public_pulse_profile(profile: dict[str, Any]) -> dict[str, Any]:
    safe_keys = [
        "schema_version",
        "profile_name",
        "hostname",
        "site_path",
        "library_path",
        "root_folder",
        "config_folder",
        "index_folder",
        "templates_folder",
        "opportunities_list",
        "knowledge_items_list",
        "timezone",
        "zoom_folder",
        "source_defaults",
    ]
    return {key: profile[key] for key in safe_keys if key in profile}


def pulse_profile_path(profile: dict[str, Any]) -> str:
    return clean_path(f"{profile['root_folder']}/{DEFAULT_CONFIG_FOLDER}/{PULSE_PROFILE_FILE_NAME}")


def required_profile_fields(profile: dict[str, Any]) -> list[str]:
    required = [
        "hostname",
        "site_path",
        "library_path",
        "root_folder",
        "opportunities_list",
        "knowledge_items_list",
        "timezone",
        "zoom_folder",
    ]
    return [field for field in required if not str(profile.get(field, "")).strip()]


def configure_pulse_connection(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    shared_profile = payload.get("shared_profile") if isinstance(payload.get("shared_profile"), dict) else {}
    existing = pulse_connection_from_state(state)
    merged = {**existing, **shared_profile, **{key: value for key, value in payload.items() if key != "shared_profile"}}
    mode = str(merged.get("mode") or "install_new").strip()
    if mode not in {"install_new", "connect_existing"}:
        raise ValueError("mode must be install_new or connect_existing.")
    merged["mode"] = mode
    profile = normalize_pulse_profile(merged)
    state["pulse_connection"] = profile
    configure_knowledge_wiki(profile, state=state)
    save_state(state)
    missing = required_profile_fields(profile)
    shared_content = json.dumps(public_pulse_profile(profile), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    folder_plan = folder_creation_plan(root_folder=profile["root_folder"])
    list_plan = list_creation_plan()
    next_steps = (
        ["create_or_validate_lists", "create_base_folders", "upload_shared_pulse_profile", "refresh_knowledge_index"]
        if mode == "install_new"
        else ["validate_existing_lists_and_wiki", "fetch_shared_pulse_profile", "refresh_knowledge_index"]
    )
    return {
        "status": "configured" if not missing else "needs_input",
        "mode": mode,
        "profile": profile,
        "public_shared_profile": public_pulse_profile(profile),
        "shared_profile_file": {
            "path": pulse_profile_path(profile),
            "content_type": "application/json",
            "content": shared_content,
        },
        "missing_required_fields": missing,
        "sharepoint_plan": {
            "site": {"hostname": profile["hostname"], "site_path": profile["site_path"]},
            "lists": list_plan,
            "folders": folder_plan,
        },
        "handoff": {
            "next_steps": next_steps,
            "setup_skill": "pulse-01-setup",
            "wiki_skill": "pulse-07-wiki",
        },
        "note": "The shared Pulse profile contains locations and names only; it never stores tokens or connector credentials.",
    }


def connector_enabled(connector_status: dict[str, Any], name: str) -> bool:
    return bool((connector_status.get("required_connectors") or {}).get(name, {}).get("enabled"))


def plugin_enabled(connector_status: dict[str, Any]) -> bool:
    entries = connector_status.get("plugin_entries") or {}
    return any(bool(info.get("enabled")) for info in entries.values())


def validate_pulse_connection(payload: dict[str, Any] | None = None, state: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    state = state or load_state()
    profile = normalize_pulse_profile(payload.get("profile") or payload or pulse_connection_from_state(state))
    connector_status = payload.get("connector_status") or check_required_connectors(payload.get("config_path"))
    blocking: list[str] = []
    warnings: list[str] = []
    remediation: list[str] = []
    for field in required_profile_fields(profile):
        blocking.append(f"{field} is missing")
        remediation.append(f"Provide {field} through configure_pulse_connection.")
    if profile.get("timezone") and not valid_timezone(profile["timezone"]):
        blocking.append("timezone is not a valid IANA timezone")
        remediation.append("Use an IANA timezone such as America/Lima, America/Bogota, or America/Mexico_City.")
    if not connector_enabled(connector_status, "sharepoint"):
        blocking.append("sharepoint connector is missing or disabled")
        remediation.append("Enable the SharePoint connector before setup or wiki writes.")
    if not connector_enabled(connector_status, "outlook-email"):
        blocking.append("outlook-email connector is missing or disabled")
        remediation.append("Enable the Outlook Email connector before daily Outlook/Zoom scans.")
    if not plugin_enabled(connector_status):
        blocking.append("oracle-opportunity-pulse plugin entry is missing or disabled")
        remediation.append("Refresh/install Oracle Opportunity Pulse and start a new Codex thread.")
    if not connector_enabled(connector_status, "slack"):
        message = "Slack V1 can only register channel links, and the Slack connector is missing or disabled."
        if payload.get("require_slack"):
            blocking.append("slack connector is missing or disabled")
        warnings.append(message)
        remediation.append("Enable Slack when channel registration should be validated for this user.")
    required_paths = [
        profile["root_folder"],
        profile["config_folder"],
        profile["index_folder"],
        profile["templates_folder"],
        f"{profile['root_folder']}/_pending",
        f"{profile['root_folder']}/_pending/outlook",
        f"{profile['root_folder']}/_pending/zoom",
    ]
    source_status = {
        "sharepoint": {
            "enabled": connector_enabled(connector_status, "sharepoint"),
            "lists": [profile["opportunities_list"], profile["knowledge_items_list"]],
            "wiki_root": profile["root_folder"],
            "required_paths": required_paths,
            "profile_file": pulse_profile_path(profile),
        },
        "outlook": {
            "enabled": connector_enabled(connector_status, "outlook-email"),
            "received": True,
            "sent": True,
            "body_marker": AGENT_TAG,
        },
        "zoom": {
            "enabled": connector_enabled(connector_status, "outlook-email"),
            "folder": profile["zoom_folder"],
        },
        "slack": {
            "enabled": connector_enabled(connector_status, "slack"),
            "mode": "link_registration_v1",
        },
    }
    return {
        "ready": not blocking,
        "profile": profile,
        "blocking_issues": blocking,
        "warnings": sorted(set(warnings)),
        "remediation_prompts": sorted(set(remediation)),
        "source_status": source_status,
        "connector_status": connector_status,
    }


def configure_knowledge_wiki(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    existing = wiki_config_from_state(state)
    site_path = normalize_site_path(payload.get("site_path", existing["site_path"]))
    root_folder = clean_path(str(payload.get("root_folder", existing["root_folder"]) or DEFAULT_ROOT_FOLDER))
    config = {
        "hostname": str(payload.get("hostname", existing["hostname"])).strip(),
        "site_path": site_path,
        "library_path": clean_path(str(payload.get("library_path", existing["library_path"]) or "Shared Documents")),
        "root_folder": root_folder,
        "index_folder": clean_path(str(payload.get("index_folder", f"{root_folder}/{DEFAULT_INDEX_FOLDER}"))),
        "templates_folder": clean_path(str(payload.get("templates_folder", f"{root_folder}/{DEFAULT_TEMPLATE_FOLDER}"))),
        "opportunities_list": str(payload.get("opportunities_list", existing["opportunities_list"]) or "Opportunities"),
        "knowledge_items_list": str(payload.get("knowledge_items_list", existing["knowledge_items_list"]) or "Knowledge Items"),
    }
    state["knowledge_wiki_config"] = config
    save_state(state)
    return {
        "status": "configured",
        "config": config,
        "browse_plan": {
            "validate_site": {"hostname": config["hostname"], "site_path": config["site_path"]},
            "browse_root": {
                "hostname": config["hostname"],
                "site_path": config["site_path"],
                "folder_path": "/".join(part for part in [config["library_path"], config["root_folder"]] if part),
            },
            "index_folder": "/".join(part for part in [config["library_path"], config["index_folder"]] if part),
        },
        "note": "Use SharePoint search/fetch/upload tools with this configuration; this local MCP server prepares paths and index payloads.",
    }


def documents_from_knowledge_items(knowledge_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    documents = []
    for item in knowledge_items:
        markdown_path = item.get("markdown_path") or item.get("markdown_file_url")
        if not markdown_path:
            continue
        documents.append(
            normalize_document_record(
                {
                    "id": make_id("doc", markdown_path),
                    "path": markdown_path,
                    "url": item.get("markdown_file_url", markdown_path),
                    "title": item.get("title", posixpath.basename(markdown_path)),
                    "opportunity_key": item.get("opportunity_key", ""),
                    "discovery_id": item.get("discovery_id", ""),
                    "opportunity_code": item.get("opportunity_code", ""),
                    "source_type": item.get("source_type", ""),
                    "captured_at": item.get("captured_at", ""),
                    "approval_status": item.get("approval_status", "Approved"),
                }
            )
        )
    return documents


def build_wiki_backlinks(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    backlinks = []
    for document in documents:
        source_path = document.get("path", "")
        for link in document.get("links", []) or []:
            backlinks.append(
                {
                    "source_path": source_path,
                    "source_title": document.get("title", ""),
                    "target_path": link.get("target_path", ""),
                    "anchor": link.get("anchor", ""),
                    "opportunity_key": document.get("opportunity_key", ""),
                }
            )
    return backlinks


def build_wiki_tag_rows(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for document in documents:
        for tag in document.get("tags", []) or []:
            rows.append(
                {
                    "tag": tag,
                    "path": document.get("path", ""),
                    "title": document.get("title", ""),
                    "opportunity_key": document.get("opportunity_key", ""),
                    "source_type": document.get("source_type", ""),
                }
            )
    return rows


def wiki_index_path(config: dict[str, Any], key: str) -> str:
    return clean_path(f"{config['index_folder']}/{INDEX_FILE_NAMES[key]}")


def refresh_knowledge_index(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    config = wiki_config_from_state(state)
    include_pending = bool(payload.get("include_pending", False))
    approved_only = bool(payload.get("approved_only", True))
    opportunities = [
        normalize_opportunity_record(record)
        for record in payload.get("opportunities", state.get("opportunities", []))
    ]
    knowledge_items = [
        normalize_knowledge_item(record)
        for record in payload.get("knowledge_items", state.get("knowledge_items", []))
    ]
    filtered_items = []
    for item in knowledge_items:
        if approved_only and not approved_item(item):
            continue
        if not include_pending and is_pending_path(item.get("markdown_path") or item.get("folder_path")):
            continue
        filtered_items.append(item)
    document_input = payload.get("documents")
    if document_input is None:
        documents = documents_from_knowledge_items(filtered_items)
    else:
        documents = [normalize_document_record(record) for record in document_input]
        documents = [
            document
            for document in documents
            if (include_pending or not is_pending_path(document.get("path")))
            and (not approved_only or approved_item(document))
        ]
    backlinks = build_wiki_backlinks(documents)
    tags = build_wiki_tag_rows(documents)
    refreshed_at = payload.get("refreshed_at") or now_iso()
    index_payloads = {
        "opportunities": jsonl(opportunities),
        "knowledge_items": jsonl(filtered_items),
        "documents": jsonl(documents),
        "backlinks": jsonl(backlinks),
        "tags": jsonl(tags),
        "last_refresh": json.dumps(
            {
                "refreshed_at": refreshed_at,
                "root_folder": config["root_folder"],
                "counts": {
                    "opportunities": len(opportunities),
                    "knowledge_items": len(filtered_items),
                    "documents": len(documents),
                    "backlinks": len(backlinks),
                    "tags": len(tags),
                },
                "approved_only": approved_only,
                "include_pending": include_pending,
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
    }
    index_files = [
        {
            "key": key,
            "path": wiki_index_path(config, key),
            "content": content,
            "content_type": "application/json" if key == "last_refresh" else "application/x-ndjson",
        }
        for key, content in index_payloads.items()
    ]
    local_files = []
    if payload.get("write_local_outbox", True):
        for file_info in index_files:
            local_files.append(str(write_local_outbox(file_info["path"], file_info["content"])))
    state["knowledge_wiki_index"] = {
        "last_refresh": refreshed_at,
        "counts": {
            "opportunities": len(opportunities),
            "knowledge_items": len(filtered_items),
            "documents": len(documents),
            "backlinks": len(backlinks),
            "tags": len(tags),
        },
    }
    save_state(state)
    return {
        "status": "prepared",
        "config": config,
        "counts": state["knowledge_wiki_index"]["counts"],
        "index_files": index_files,
        "local_outbox_files": local_files,
        "sharepoint_upload_plan": [
            {
                "file_name": posixpath.basename(file_info["path"]),
                "parent_folder_path": "/".join(
                    part for part in [config["library_path"], posixpath.dirname(file_info["path"])] if part
                ),
                "mime_type": file_info["content_type"],
            }
            for file_info in index_files
        ],
    }


def filter_opportunities(opportunities: list[dict[str, Any]], payload: dict[str, Any], query: str) -> list[dict[str, Any]]:
    filters = {
        "client_name": normalize_text(payload.get("client_name")),
        "country": normalize_text(payload.get("country")),
        "opportunity_key": normalize_text(payload.get("opportunity_key")),
        "discovery_id": normalize_text(payload.get("discovery_id")),
        "opportunity_code": normalize_text(payload.get("opportunity_code")),
        "sr_number": normalize_text(payload.get("sr_number")),
        "status": normalize_text(payload.get("status")),
    }
    matches = []
    for opportunity in opportunities:
        if filters["client_name"] and filters["client_name"] not in normalize_text(opportunity.get("client_name")):
            continue
        if filters["country"] and filters["country"] != normalize_text(opportunity.get("country")):
            continue
        if filters["opportunity_key"] and filters["opportunity_key"] != normalize_text(opportunity.get("opportunity_key")):
            continue
        if filters["discovery_id"] and filters["discovery_id"] != normalize_text(opportunity.get("discovery_id")):
            continue
        if filters["opportunity_code"] and filters["opportunity_code"] != normalize_text(opportunity.get("opportunity_code")):
            continue
        if filters["sr_number"] and filters["sr_number"] != normalize_text(opportunity.get("sr_number")):
            continue
        if filters["status"] and filters["status"] != normalize_text(opportunity.get("status")):
            continue
        if query and query not in normalize_text(json.dumps(opportunity, ensure_ascii=False)):
            continue
        matches.append(opportunity)
    return matches


def find_opportunity_for_item(opportunities: list[dict[str, Any]], item: dict[str, Any]) -> dict[str, Any] | None:
    for opportunity in opportunities:
        if item.get("opportunity_key") and item.get("opportunity_key") == opportunity.get("opportunity_key"):
            return opportunity
        if item.get("discovery_id") and item.get("discovery_id") == opportunity.get("discovery_id"):
            return opportunity
        if item.get("opportunity_code") and item.get("opportunity_code") == opportunity.get("opportunity_code"):
            return opportunity
    return None


def query_score(query_text: str, haystack: str) -> tuple[int, list[str]]:
    if not query_text:
        return 0, []
    score = 0
    evidence = []
    normalized_haystack = normalize_text(haystack)
    if query_text and query_text in normalized_haystack:
        score += 30
        evidence.append("matched exact text")
    query_tokens = tokenize(query_text)
    overlap = query_tokens & tokenize(haystack)
    if overlap:
        score += min(60, len(overlap) * 8)
        evidence.append(f"matched {len(overlap)} query tokens")
    return score, evidence


def query_knowledge_wiki(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    config = wiki_config_from_state(state)
    query = normalize_text(payload.get("query", ""))
    include_pending = bool(payload.get("include_pending", False))
    approved_only = bool(payload.get("approved_only", True))
    top_k = int(payload.get("top_k", 10) or 10)
    opportunities = [
        normalize_opportunity_record(record)
        for record in payload.get("opportunities", state.get("opportunities", []))
    ]
    knowledge_items = [
        normalize_knowledge_item(record)
        for record in payload.get("knowledge_items", state.get("knowledge_items", []))
    ]
    documents = [
        normalize_document_record(record)
        for record in payload.get("documents", documents_from_knowledge_items(knowledge_items))
    ]
    matched_opportunities = filter_opportunities(opportunities, payload, "" if knowledge_items else query)
    matched_keys = {opportunity.get("opportunity_key") for opportunity in matched_opportunities if opportunity.get("opportunity_key")}
    evidence_rows = []
    unread_count = 0
    source_filter = payload.get("source_type")
    from_date = parse_datetime(payload.get("from_date"))
    to_date = parse_datetime(payload.get("to_date"))
    documents_by_path = {document.get("path"): document for document in documents if document.get("path")}
    for item in knowledge_items:
        if approved_only and not approved_item(item):
            continue
        path = item.get("markdown_path") or item.get("markdown_file_url")
        if not include_pending and (is_pending_path(path) or is_pending_path(item.get("folder_path"))):
            continue
        if source_filter and item.get("source_type") != source_filter:
            continue
        captured = parse_datetime(item.get("captured_at"))
        if from_date and captured and captured < from_date:
            continue
        if to_date and captured and captured > to_date:
            continue
        item_opportunity = find_opportunity_for_item(opportunities, item)
        if matched_keys and item.get("opportunity_key") not in matched_keys:
            continue
        document = documents_by_path.get(clean_path(path), {})
        if approved_only and document and not approved_item(document):
            continue
        if not include_pending and document and is_pending_path(document.get("path")):
            continue
        haystack = "\n".join(
            [
                json.dumps(item, ensure_ascii=False),
                json.dumps(item_opportunity or {}, ensure_ascii=False),
                document.get("content", ""),
                " ".join(document.get("tags", []) or []),
            ]
        )
        score, score_evidence = query_score(query, haystack)
        if matched_keys:
            score += 40
            score_evidence.append("matched opportunity filter")
        if not query and not matched_keys:
            score += 1
        if document.get("content"):
            score += 10
        else:
            unread_count += 1
        score += min(15, int(date_sort_value(item.get("captured_at")) / 86400) % 16)
        if query and score == 0:
            continue
        evidence_rows.append(
            {
                "score": score,
                "rank_evidence": score_evidence,
                "title": item.get("title", ""),
                "opportunity": item_opportunity,
                "opportunity_key": item.get("opportunity_key", ""),
                "source_type": item.get("source_type", ""),
                "direction": item.get("direction", ""),
                "captured_at": item.get("captured_at", ""),
                "markdown_path": clean_path(path),
                "markdown_file_url": item.get("markdown_file_url") or path,
                "source_url": item.get("source_url", ""),
                "tags": document.get("tags", []),
                "read_status": document.get("read_status", "metadata_only"),
                "excerpt": document.get("content", "")[:500],
                "knowledge_item": item,
            }
        )
    evidence_rows.sort(key=lambda row: (row["score"], date_sort_value(row.get("captured_at"))), reverse=True)
    last_refresh = payload.get("index_last_refresh") or state.get("knowledge_wiki_index", {}).get("last_refresh")
    warnings = []
    mode = "snapshot" if any(key in payload for key in ("opportunities", "knowledge_items", "documents")) else "local_state_fallback"
    if mode == "local_state_fallback":
        warnings.append("No SharePoint index snapshot was supplied; results use the local staging state.")
    if not last_refresh:
        warnings.append("Index refresh metadata was not supplied; SharePoint freshness could not be verified.")
    elif is_index_stale(last_refresh, payload.get("index_max_age_hours", 24)):
        warnings.append("Knowledge wiki index is stale; refresh before relying on this answer.")
    if unread_count:
        warnings.append(f"{unread_count} evidence item(s) have Markdown metadata only; fetch the .md files for full-content answers.")
    return {
        "summary": f"Found {len(matched_opportunities)} opportunity record(s) and {len(evidence_rows[:top_k])} evidence item(s).",
        "mode": mode,
        "config": config,
        "index_status": {
            "last_refresh": last_refresh or "",
            "stale": is_index_stale(last_refresh, payload.get("index_max_age_hours", 24)) if last_refresh else True,
        },
        "opportunities": matched_opportunities,
        "evidence": evidence_rows[:top_k],
        "counts": {
            "opportunities": len(matched_opportunities),
            "evidence": len(evidence_rows[:top_k]),
            "total_ranked_evidence": len(evidence_rows),
        },
        "warnings": warnings,
    }


def get_opportunity_timeline(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    query_result = query_knowledge_wiki({**payload, "query": payload.get("query", ""), "top_k": payload.get("top_k", 200)}, state)
    events = [
        {
            "captured_at": row.get("captured_at", ""),
            "title": row.get("title", ""),
            "source_type": row.get("source_type", ""),
            "direction": row.get("direction", ""),
            "markdown_path": row.get("markdown_path", ""),
            "markdown_file_url": row.get("markdown_file_url", ""),
            "opportunity_key": row.get("opportunity_key", ""),
        }
        for row in query_result["evidence"]
    ]
    events.sort(key=lambda event: date_sort_value(event.get("captured_at")), reverse=bool(payload.get("descending", False)))
    return {
        "summary": f"Timeline contains {len(events)} approved evidence event(s).",
        "events": events,
        "warnings": query_result.get("warnings", []),
    }


def get_backlinks(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    target_path = clean_path(payload.get("target_path"))
    documents = [normalize_document_record(record) for record in payload.get("documents", [])]
    backlinks = payload.get("backlinks")
    backlink_rows = backlinks if backlinks is not None else build_wiki_backlinks(documents)
    inbound = [
        row
        for row in backlink_rows
        if clean_path(row.get("target_path")) == target_path or row.get("target_path") == payload.get("target_path")
    ]
    outbound = []
    for document in documents:
        if clean_path(document.get("path")) == target_path:
            outbound = [
                {
                    "source_path": target_path,
                    "target_path": link.get("target_path", ""),
                    "anchor": link.get("anchor", ""),
                }
                for link in document.get("links", [])
            ]
            break
    return {
        "target_path": target_path,
        "inbound": inbound,
        "outbound": outbound,
        "counts": {"inbound": len(inbound), "outbound": len(outbound)},
        "warnings": [] if documents or backlinks is not None else ["No documents or backlink index was supplied."],
    }


def relative_markdown_link(from_path: str, to_path: str) -> str:
    from_dir = posixpath.dirname(clean_path(from_path))
    target = clean_path(to_path)
    if not from_dir:
        return target
    return posixpath.relpath(target, from_dir)


def suggest_wiki_links(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    query_text = "\n".join([payload.get("query", ""), payload.get("title", ""), payload.get("markdown_content", "")])
    from_path = clean_path(payload.get("from_path"))
    documents = [
        normalize_document_record(record)
        for record in payload.get("documents", documents_from_knowledge_items([normalize_knowledge_item(item) for item in state.get("knowledge_items", [])]))
    ]
    suggestions = []
    for document in documents:
        path = clean_path(document.get("path"))
        if not path or path == from_path or is_pending_path(path):
            continue
        score, evidence = query_score(normalize_text(query_text), "\n".join([document.get("title", ""), document.get("content", ""), " ".join(document.get("tags", []))]))
        if payload.get("opportunity_key") and payload.get("opportunity_key") == document.get("opportunity_key"):
            score += 35
            evidence.append("same opportunity")
        if score <= 0:
            continue
        suggestions.append(
            {
                "score": score,
                "title": document.get("title", ""),
                "path": path,
                "markdown_link": f"[{document.get('title') or posixpath.basename(path)}]({relative_markdown_link(from_path, path)})",
                "opportunity_key": document.get("opportunity_key", ""),
                "tags": document.get("tags", []),
                "evidence": evidence,
            }
        )
    suggestions.sort(key=lambda item: item["score"], reverse=True)
    top_k = int(payload.get("top_k", 10) or 10)
    return {
        "suggestions": suggestions[:top_k],
        "counts": {"suggestions": len(suggestions[:top_k]), "total_ranked": len(suggestions)},
    }


def query_opportunity_pulse(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    query = normalize_text(payload.get("query", ""))
    source_type = payload.get("source_type")
    opportunity_key = normalize_text(payload.get("opportunity_key"))
    discovery_id = normalize_text(payload.get("discovery_id"))
    opportunity_code = normalize_text(payload.get("opportunity_code"))
    sr_number = normalize_text(payload.get("sr_number"))
    client_name = normalize_text(payload.get("client_name"))
    opportunities = []
    for opportunity in state.get("opportunities", []):
        haystack = normalize_text(json.dumps(opportunity, ensure_ascii=False))
        if opportunity_key and normalize_text(opportunity.get("opportunity_key")) != opportunity_key:
            continue
        if discovery_id and normalize_text(opportunity.get("discovery_id")) != discovery_id:
            continue
        if opportunity_code and normalize_text(opportunity.get("opportunity_code")) != opportunity_code:
            continue
        if sr_number and normalize_text(opportunity.get("sr_number")) != sr_number:
            continue
        if client_name and normalize_text(opportunity.get("client_name")) != client_name:
            continue
        if query and query not in haystack:
            continue
        opportunities.append(opportunity)
    knowledge_items = []
    for item in state.get("knowledge_items", []):
        haystack = normalize_text(json.dumps(item, ensure_ascii=False))
        if source_type and item.get("source_type") != source_type:
            continue
        if opportunity_key and normalize_text(item.get("opportunity_key")) != opportunity_key:
            continue
        if discovery_id and normalize_text(item.get("discovery_id")) != discovery_id:
            continue
        if opportunity_code and normalize_text(item.get("opportunity_code")) != opportunity_code:
            continue
        if query and query not in haystack:
            continue
        knowledge_items.append(item)
    return {
        "opportunities": opportunities,
        "knowledge_items": knowledge_items,
        "counts": {
            "opportunities": len(opportunities),
            "knowledge_items": len(knowledge_items),
        },
        "knowledge_wiki": query_knowledge_wiki(payload, state),
    }


def graph_provision_requests() -> dict[str, Any]:
    return {
        "lists": [
            {
                "displayName": "Opportunities",
                "description": "Oracle Opportunity Pulse master opportunity context.",
                "columns": [
                    {"name": "OpportunityKey", "text": {}},
                    {"name": "DiscoveryId", "text": {}},
                    {"name": "ClientName", "text": {}},
                    {"name": "Country", "text": {}},
                    {"name": "OpportunityCode", "text": {}},
                    {"name": "SRNumber", "text": {}},
                    {"name": "LifecycleStage", "choice": {"choices": sorted(LIFECYCLE_STAGES)}},
                    {"name": "NeedsOpportunityCode", "boolean": {}},
                    {"name": "NeedsSR", "boolean": {}},
                    {"name": "WorkloadDescription", "text": {"allowMultipleLines": True}},
                    {"name": "DeliveryModel", "choice": {"choices": sorted(DELIVERY_MODELS)}},
                    {"name": "CELeaderEmails", "text": {"allowMultipleLines": True}},
                    {"name": "OpportunityContext", "text": {"allowMultipleLines": True}},
                    {"name": "ClassificationHintsJson", "text": {"allowMultipleLines": True}},
                    {"name": "RegisteredByEmail", "text": {}},
                    {"name": "Status", "choice": {"choices": ["Active", "Closed", "OnHold"]}},
                    {"name": "CreatedAt", "dateTime": {}},
                    {"name": "LastUpdatedAt", "dateTime": {}},
                    {"name": "RootFolderUrl", "hyperlinkOrPicture": {}},
                ],
            },
            {
                "displayName": "Knowledge Items",
                "description": "Normalized evidence records for opportunity wiki content.",
                "columns": [
                    {"name": "OpportunityKey", "text": {}},
                    {"name": "OpportunityCode", "text": {}},
                    {"name": "DiscoveryId", "text": {}},
                    {"name": "SourceType", "choice": {"choices": sorted(SOURCE_TYPES)}},
                    {"name": "Direction", "choice": {"choices": sorted(DIRECTIONS)}},
                    {"name": "SourceUrl", "hyperlinkOrPicture": {}},
                    {"name": "SourceExternalId", "text": {}},
                    {"name": "FolderUrl", "hyperlinkOrPicture": {}},
                    {"name": "MarkdownFileUrl", "hyperlinkOrPicture": {}},
                    {"name": "CapturedAt", "dateTime": {}},
                    {"name": "RegisteredByEmail", "text": {}},
                    {"name": "ApprovalStatus", "choice": {"choices": ["Proposed", "Approved", "Rejected"]}},
                    {"name": "ClassificationEvidence", "text": {"allowMultipleLines": True}},
                    {"name": "Notes", "text": {"allowMultipleLines": True}},
                ],
            },
        ],
        "root_folder": DEFAULT_ROOT_FOLDER,
        "required_permission": "Sites.ReadWrite.All",
    }


def list_creation_plan() -> dict[str, Any]:
    return {
        "status": "prepared",
        "operation": "create_or_update_lists",
        "lists": graph_provision_requests()["lists"],
        "required_permission": "Sites.ReadWrite.All",
        "execution_note": (
            "SharePoint lists require an existing SharePoint site context or Graph site-id, "
            "but this plugin manages the lists themselves and does not create a website."
        ),
    }


def base_folder_structure(
    client_name: str | None = None,
    opportunity_code: str | None = None,
    opportunity_key: str | None = None,
    discovery_id: str | None = None,
    sr_number: str | None = None,
    root_folder: str | None = None,
) -> dict[str, Any]:
    today = dt.datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).date().isoformat()
    root_base = clean_path(root_folder or DEFAULT_ROOT_FOLDER)
    key = opportunity_key or discovery_id or (stable_opportunity_key(client_name, opportunity_code, sr_number) if client_name else "")
    if client_name and key:
        root = "/".join([root_base, slugify_path_part(client_name, "client"), slugify_path_part(key, "opportunity")])
        folders = [
            root,
            f"{root}/zoom",
            f"{root}/outlook",
            f"{root}/outlook/received",
            f"{root}/outlook/sent",
            f"{root}/slack",
            f"{root}/notes",
            f"{root}/{DEFAULT_ATTACHMENTS_FOLDER}",
        ]
        readmes = [
            f"{root}/README.md",
            f"{root}/context.md",
            f"{root}/zoom/README.md",
            f"{root}/outlook/README.md",
            f"{root}/outlook/received/README.md",
            f"{root}/outlook/sent/README.md",
            f"{root}/slack/README.md",
            f"{root}/notes/README.md",
            f"{root}/{DEFAULT_ATTACHMENTS_FOLDER}/README.md",
        ]
        index_files: list[str] = []
        template_files: list[str] = []
        config_files: list[str] = []
    else:
        root = root_base
        folders = [
            root,
            f"{root}/{DEFAULT_CONFIG_FOLDER}",
            f"{root}/{DEFAULT_INDEX_FOLDER}",
            f"{root}/{DEFAULT_TEMPLATE_FOLDER}",
            f"{root}/_pending",
            f"{root}/_pending/outlook",
            f"{root}/_pending/outlook/{today}",
            f"{root}/_pending/outlook/{today}/received",
            f"{root}/_pending/outlook/{today}/sent",
            f"{root}/_pending/zoom",
            f"{root}/_pending/zoom/{today}",
        ]
        readmes = [f"{root}/README.md"]
        config_files = [f"{root}/{DEFAULT_CONFIG_FOLDER}/{PULSE_PROFILE_FILE_NAME}"]
        index_files = [f"{root}/{DEFAULT_INDEX_FOLDER}/{name}" for name in INDEX_FILE_NAMES.values()]
        template_files = [f"{root}/{DEFAULT_TEMPLATE_FOLDER}/{name}" for name in DEFAULT_WIKI_TEMPLATES]
    return {
        "root": root,
        "folders": folders,
        "readme_files": readmes,
        "config_files": config_files,
        "index_files": index_files,
        "template_files": template_files,
        "required_permission": "Sites.ReadWrite.All",
    }


def folder_creation_plan(
    client_name: str | None = None,
    opportunity_code: str | None = None,
    opportunity_key: str | None = None,
    discovery_id: str | None = None,
    sr_number: str | None = None,
    root_folder: str | None = None,
) -> dict[str, Any]:
    structure = base_folder_structure(client_name, opportunity_code, opportunity_key, discovery_id, sr_number, root_folder)
    return {
        "status": "prepared",
        "operation": "create_folder_structure",
        "structure": structure,
        "graph_intent": {
            "folders": [
                {
                    "path": folder,
                    "method": "PUT",
                    "endpoint_shape": "/drives/{drive-id}/root:/{path}:/content or /children folder creation",
                }
                for folder in structure["folders"]
            ],
            "readme_files": [
                {
                    "path": readme,
                    "method": "PUT",
                    "content_type": "text/markdown",
                }
                for readme in structure["readme_files"]
            ],
            "config_files": [
                {
                    "path": file_path,
                    "method": "PUT",
                    "content_type": "application/json",
                }
                for file_path in structure.get("config_files", [])
            ],
            "index_files": [
                {
                    "path": file_path,
                    "method": "PUT",
                    "content_type": "application/json" if file_path.endswith(".json") else "application/x-ndjson",
                }
                for file_path in structure.get("index_files", [])
            ],
            "template_files": [
                {
                    "path": file_path,
                    "method": "PUT",
                    "content_type": "text/markdown",
                    "template_name": posixpath.basename(file_path),
                    "content": DEFAULT_WIKI_TEMPLATES.get(posixpath.basename(file_path), ""),
                }
                for file_path in structure.get("template_files", [])
            ],
        },
    }


def check_required_connectors(config_path: str | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else Path.home() / ".codex" / "config.toml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    required = {
        "sharepoint": 'plugins."sharepoint@openai-curated"',
        "outlook-email": 'plugins."outlook-email@openai-curated"',
        "slack": 'plugins."slack@openai-curated"',
    }
    plugin_markers = {
        "oracle-opportunity-pulse@codex-pulse": 'plugins."oracle-opportunity-pulse@codex-pulse"',
        "oracle-opportunity-pulse@local": 'plugins."oracle-opportunity-pulse@local"',
    }
    checks = {}
    for name, marker in required.items():
        enabled = marker in text and re.search(
            re.escape(f"[{marker}]") + r"\s+enabled\s*=\s*true",
            text,
            flags=re.MULTILINE,
        ) is not None
        checks[name] = {
            "configured": marker in text,
            "enabled": enabled,
            "required_for": {
                "sharepoint": "creating/managing lists and Markdown evidence files",
                "outlook-email": "scanning received/sent @agent_data messages and Zoom AI Companion folder",
                "slack": "registering and later reading Slack channel links",
            }[name],
        }
    plugin_checks = {}
    for name, marker in plugin_markers.items():
        plugin_checks[name] = {
            "configured": marker in text,
            "enabled": marker in text
            and re.search(
                re.escape(f"[{marker}]") + r"\s+enabled\s*=\s*true",
                text,
                flags=re.MULTILINE,
            )
            is not None,
        }
    missing = [name for name, info in checks.items() if not info["enabled"]]
    return {
        "config_path": str(path),
        "required_connectors": checks,
        "plugin_entries": plugin_checks,
        "ready": not missing and any(info["enabled"] for info in plugin_checks.values()),
        "missing_or_disabled": missing,
        "note": (
            "This checks Codex configuration only. The active thread may still need to be restarted "
            "to load newly enabled plugin skills and MCP tools."
        ),
    }


def outlook_scan_plan(timezone: str = DEFAULT_TIMEZONE) -> dict[str, Any]:
    local_now = dt.datetime.now(ZoneInfo(timezone))
    start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + dt.timedelta(days=1)
    return {
        "timezone": timezone,
        "received_filter": (
            f"receivedDateTime ge {start.astimezone(dt.timezone.utc).isoformat()} "
            f"and receivedDateTime lt {end.astimezone(dt.timezone.utc).isoformat()}"
        ),
        "sent_filter": (
            f"sentDateTime ge {start.astimezone(dt.timezone.utc).isoformat()} "
            f"and sentDateTime lt {end.astimezone(dt.timezone.utc).isoformat()}"
        ),
        "body_marker": AGENT_TAG,
        "zoom_folder": DEFAULT_ZOOM_FOLDER,
    }


def parse_local_time(value: str | None) -> tuple[int, int]:
    text = str(value or "18:00").strip()
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", text)
    if not match:
        raise ValueError("local_time must use HH:MM in 24-hour format.")
    return int(match.group(1)), int(match.group(2))


def build_daily_sync_prompt(payload: dict[str, Any] | None = None, state: dict[str, Any] | None = None) -> dict[str, Any]:
    return prepare_daily_sync_automation(payload or {}, state=state)


def prepare_daily_sync_automation(payload: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or load_state()
    active = pulse_connection_from_state(state)
    overrides = {key: value for key, value in payload.items() if key in active and value not in (None, "")}
    profile = normalize_pulse_profile({**active, **overrides})
    timezone = str(payload.get("timezone") or profile["timezone"] or DEFAULT_TIMEZONE).strip()
    if not valid_timezone(timezone):
        raise ValueError("timezone must be a valid IANA timezone.")
    hour, minute = parse_local_time(payload.get("local_time", "18:00"))
    local_time = f"{hour:02d}:{minute:02d}"
    profile["timezone"] = timezone
    include_received = bool(payload.get("include_received", True))
    include_sent = bool(payload.get("include_sent", True))
    include_zoom = bool(payload.get("include_zoom", True))
    include_slack = bool(payload.get("include_slack", False))
    validation = validate_pulse_connection(
        {
            "profile": profile,
            "connector_status": payload.get("connector_status") or check_required_connectors(payload.get("config_path")),
            "require_slack": include_slack,
        },
        state=state,
    )
    sources = []
    if include_received:
        sources.append("received Outlook messages")
    if include_sent:
        sources.append("sent Outlook messages")
    if include_zoom:
        sources.append(f"Zoom AI Companion messages from {profile['zoom_folder']}")
    if include_slack:
        sources.append("registered Slack channel links")
    source_text = ", ".join(sources) if sources else "configured sources"
    prompt = (
        "Use $pulse-02-automation for the personal daily Oracle Opportunity Pulse sync. "
        f"Validate the active Pulse profile for {profile['hostname']}{profile['site_path']} "
        f"with wiki root {profile['root_folder']} and lists {profile['opportunities_list']} / "
        f"{profile['knowledge_items_list']}. Scan today's {source_text} in timezone {timezone}; "
        f"only capture Outlook or Zoom messages whose body contains {AGENT_TAG}. Propose client, "
        "OpportunityKey, DiscoveryId, opportunity code, SR, source type, direction, evidence, and confidence. "
        "Never autoapprove. Wait for explicit user approval or correction before writing Markdown, Knowledge Items, "
        "or Opportunity updates to SharePoint, then refresh the Knowledge Wiki index."
    )
    rrule = f"RRULE:FREQ=DAILY;BYHOUR={hour};BYMINUTE={minute};BYSECOND=0"
    automation_name = payload.get("name") or f"Oracle Opportunity Pulse daily sync ({profile['profile_name']})"
    return {
        "name": automation_name,
        "schedule": {
            "local_time": local_time,
            "timezone": timezone,
            "description": f"Every day at {local_time} {timezone}.",
        },
        "profile": profile,
        "sources": {
            "include_received": include_received,
            "include_sent": include_sent,
            "include_zoom": include_zoom,
            "include_slack": include_slack,
        },
        "validation": validation,
        "prompt": prompt,
        "outlook_scan_plan": outlook_scan_plan(timezone),
        "codex_automation": {
            "tool": "automation_update",
            "fields": {
                "mode": "create",
                "kind": "heartbeat",
                "destination": "thread",
                "name": automation_name,
                "rrule": rrule,
                "status": "ACTIVE",
                "prompt": prompt,
            },
            "note": "Use Codex automation_update with these fields after the user confirms scheduling.",
        },
    }
