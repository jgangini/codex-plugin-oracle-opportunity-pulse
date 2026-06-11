from __future__ import annotations

import json
import sys
import traceback
from typing import Any, Callable

import opportunity_pulse_core as core


def tool_schema(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": True,
        },
    }


TOOLS = [
    tool_schema(
        "register_opportunity",
        "Create or update a master Oracle opportunity record and compute its wiki folder paths.",
        {
            "client_name": {"type": "string"},
            "country": {"type": "string"},
            "opportunity_key": {"type": "string"},
            "discovery_id": {"type": "string"},
            "opportunity_code": {"type": "string"},
            "sr_number": {"type": "string"},
            "lifecycle_stage": {"type": "string", "enum": sorted(core.LIFECYCLE_STAGES)},
            "workload_description": {"type": "string"},
            "delivery_model": {"type": "string", "enum": sorted(core.DELIVERY_MODELS)},
            "ce_leader_emails": {"type": "array", "items": {"type": "string"}},
            "registered_by_email": {"type": "string"},
            "opportunity_context": {"type": "string"},
            "classification_hints": {"type": "object"},
            "status": {"type": "string"},
        },
        ["client_name"],
    ),
    tool_schema(
        "register_slack_channel",
        "Register a Slack channel URL as a normalized Knowledge Item. V1 stores the link only.",
        {
            "slack_url": {"type": "string"},
            "client_name": {"type": "string"},
            "opportunity_key": {"type": "string"},
            "discovery_id": {"type": "string"},
            "opportunity_code": {"type": "string"},
            "sr_number": {"type": "string"},
            "registered_by_email": {"type": "string"},
            "title": {"type": "string"},
            "notes": {"type": "string"},
        },
        ["slack_url"],
    ),
    tool_schema(
        "scan_agent_data_outlook",
        "Scan supplied received/sent Outlook messages for @agent_data candidates inside an incremental sync window.",
        {
            "today_only": {"type": "boolean", "default": True},
            "scan_from": {"type": "string"},
            "scan_to": {"type": "string"},
            "executed_by_email": {"type": "string"},
            "run_id": {"type": "string"},
            "include_received": {"type": "boolean", "default": True},
            "include_sent": {"type": "boolean", "default": True},
            "received_messages": {"type": "array", "items": {"type": "object"}},
            "sent_messages": {"type": "array", "items": {"type": "object"}},
            "timezone": {"type": "string", "default": core.DEFAULT_TIMEZONE},
        },
    ),
    tool_schema(
        "scan_zoom_ai_companion",
        "Scan supplied Zoom AI Companion Outlook messages from the exact [0] Zoom AI companion folder without requiring @agent_data.",
        {
            "today_only": {"type": "boolean", "default": True},
            "scan_from": {"type": "string"},
            "scan_to": {"type": "string"},
            "executed_by_email": {"type": "string"},
            "run_id": {"type": "string"},
            "require_agent_tag": {"type": "boolean", "default": False},
            "source_scope": {"type": "string", "default": core.DEFAULT_ZOOM_FOLDER},
            "messages": {"type": "array", "items": {"type": "object"}},
            "timezone": {"type": "string", "default": core.DEFAULT_TIMEZONE},
        },
    ),
    tool_schema(
        "propose_candidate",
        "Recompute and return the opportunity classification proposal for a pending candidate.",
        {"candidate_id": {"type": "string"}},
        ["candidate_id"],
    ),
    tool_schema(
        "approve_candidate",
        "Approve a candidate after user confirmation and create the local Knowledge Item/wiki Markdown path.",
        {
            "candidate_id": {"type": "string"},
            "overrides": {"type": "object"},
        },
        ["candidate_id"],
    ),
    tool_schema(
        "reject_candidate",
        "Reject a pending candidate with an optional reason.",
        {
            "candidate_id": {"type": "string"},
            "reason": {"type": "string"},
        },
        ["candidate_id"],
    ),
    tool_schema(
        "add_note",
        "Create a manual Markdown note for an existing opportunity.",
        {
            "opportunity_code": {"type": "string"},
            "opportunity_key": {"type": "string"},
            "discovery_id": {"type": "string"},
            "sr_number": {"type": "string"},
            "client_name": {"type": "string"},
            "markdown_content": {"type": "string"},
            "title": {"type": "string"},
            "registered_by_email": {"type": "string"},
            "notes": {"type": "string"},
        },
        ["markdown_content"],
    ),
    tool_schema(
        "query_opportunity_pulse",
        "Query opportunity state and the Knowledge Wiki by text, client, opportunity, source type, or supplied SharePoint snapshots.",
        {
            "query": {"type": "string"},
            "client_name": {"type": "string"},
            "country": {"type": "string"},
            "opportunity_key": {"type": "string"},
            "discovery_id": {"type": "string"},
            "opportunity_code": {"type": "string"},
            "sr_number": {"type": "string"},
            "status": {"type": "string"},
            "source_type": {"type": "string", "enum": sorted(core.SOURCE_TYPES)},
            "approved_only": {"type": "boolean", "default": True},
            "include_pending": {"type": "boolean", "default": False},
            "documents": {"type": "array", "items": {"type": "object"}},
            "opportunities": {"type": "array", "items": {"type": "object"}},
            "knowledge_items": {"type": "array", "items": {"type": "object"}},
            "index_last_refresh": {"type": "string"},
            "top_k": {"type": "integer", "default": 10},
        },
    ),
    tool_schema(
        "configure_knowledge_wiki",
        "Configure the SharePoint location and list names used by the Oracle Opportunity Pulse Knowledge Wiki.",
        {
            "hostname": {"type": "string"},
            "site_path": {"type": "string"},
            "library_path": {"type": "string"},
            "root_folder": {"type": "string", "default": core.DEFAULT_ROOT_FOLDER},
            "index_folder": {"type": "string"},
            "templates_folder": {"type": "string"},
            "opportunities_list": {"type": "string", "default": "Opportunities"},
            "knowledge_items_list": {"type": "string", "default": "Knowledge Items"},
            "automation_runs_list": {"type": "string", "default": core.DEFAULT_AUTOMATION_RUNS_LIST},
        },
    ),
    tool_schema(
        "configure_pulse_connection",
        "Guided setup for installing a new shared Pulse or connecting this user to an existing SharePoint Pulse.",
        {
            "mode": {"type": "string", "enum": ["install_new", "connect_existing"]},
            "profile_name": {"type": "string"},
            "hostname": {"type": "string"},
            "site_path": {"type": "string"},
            "library_path": {"type": "string"},
            "root_folder": {"type": "string", "default": core.DEFAULT_ROOT_FOLDER},
            "opportunities_list": {"type": "string", "default": "Opportunities"},
            "knowledge_items_list": {"type": "string", "default": "Knowledge Items"},
            "automation_runs_list": {"type": "string", "default": core.DEFAULT_AUTOMATION_RUNS_LIST},
            "timezone": {"type": "string", "default": core.DEFAULT_TIMEZONE},
            "zoom_folder": {"type": "string", "default": core.DEFAULT_ZOOM_FOLDER},
            "shared_profile": {"type": "object"},
        },
        ["mode"],
    ),
    tool_schema(
        "validate_pulse_connection",
        "Validate the active or supplied Pulse connection, connectors, SharePoint locations, source folders, and timezone.",
        {
            "profile": {"type": "object"},
            "connector_status": {"type": "object"},
            "config_path": {"type": "string"},
            "require_slack": {"type": "boolean", "default": False},
        },
    ),
    tool_schema(
        "prepare_daily_sync_automation",
        "Prepare a personal daily Codex automation for Oracle Opportunity Pulse at 18:00 in the user's timezone.",
        {
            "timezone": {"type": "string", "default": core.DEFAULT_TIMEZONE},
            "local_time": {"type": "string", "default": "18:00"},
            "include_received": {"type": "boolean", "default": True},
            "include_sent": {"type": "boolean", "default": True},
            "include_zoom": {"type": "boolean", "default": True},
            "include_slack": {"type": "boolean", "default": False},
            "name": {"type": "string"},
            "connector_status": {"type": "object"},
            "config_path": {"type": "string"},
        },
    ),
    tool_schema(
        "prepare_incremental_sync_window",
        "Prepare the per-user/source/direction scan window from the last successful Automation Runs watermark.",
        {
            "user_email": {"type": "string"},
            "executed_by_email": {"type": "string"},
            "profile_name": {"type": "string"},
            "source_type": {"type": "string", "enum": sorted(core.SOURCE_TYPES)},
            "direction": {"type": "string", "enum": sorted(core.DIRECTIONS)},
            "source_scope": {"type": "string"},
            "timezone": {"type": "string", "default": core.DEFAULT_TIMEZONE},
            "scan_from": {"type": "string"},
            "scan_to": {"type": "string"},
            "now": {"type": "string"},
            "overlap_minutes": {"type": "integer", "default": core.DEFAULT_SYNC_OVERLAP_MINUTES},
        },
    ),
    tool_schema(
        "record_automation_run",
        "Record one per-user/source/direction Automation Runs audit row and compute the next watermark.",
        {
            "run_id": {"type": "string"},
            "user_email": {"type": "string"},
            "executed_by_email": {"type": "string"},
            "profile_name": {"type": "string"},
            "source_type": {"type": "string", "enum": sorted(core.SOURCE_TYPES)},
            "direction": {"type": "string", "enum": sorted(core.DIRECTIONS)},
            "source_scope": {"type": "string"},
            "scan_from": {"type": "string"},
            "scan_to": {"type": "string"},
            "started_at": {"type": "string"},
            "finished_at": {"type": "string"},
            "run_status": {"type": "string", "enum": sorted(core.RUN_STATUSES)},
            "candidate_count": {"type": "integer"},
            "approved_count": {"type": "integer"},
            "rejected_count": {"type": "integer"},
            "last_source_event_at": {"type": "string"},
            "next_scan_from": {"type": "string"},
            "error_summary": {"type": "string"},
            "timezone": {"type": "string", "default": core.DEFAULT_TIMEZONE},
            "overlap_minutes": {"type": "integer", "default": core.DEFAULT_SYNC_OVERLAP_MINUTES},
        },
    ),
    tool_schema(
        "refresh_knowledge_index",
        "Prepare Knowledge Wiki index JSONL files from SharePoint list and Markdown snapshots.",
        {
            "opportunities": {"type": "array", "items": {"type": "object"}},
            "knowledge_items": {"type": "array", "items": {"type": "object"}},
            "documents": {"type": "array", "items": {"type": "object"}},
            "approved_only": {"type": "boolean", "default": True},
            "include_pending": {"type": "boolean", "default": False},
            "write_local_outbox": {"type": "boolean", "default": True},
            "refreshed_at": {"type": "string"},
        },
    ),
    tool_schema(
        "query_knowledge_wiki",
        "Search the Knowledge Wiki using structured filters plus Markdown snapshot content.",
        {
            "query": {"type": "string"},
            "client_name": {"type": "string"},
            "country": {"type": "string"},
            "opportunity_key": {"type": "string"},
            "discovery_id": {"type": "string"},
            "opportunity_code": {"type": "string"},
            "sr_number": {"type": "string"},
            "status": {"type": "string"},
            "source_type": {"type": "string", "enum": sorted(core.SOURCE_TYPES)},
            "from_date": {"type": "string"},
            "to_date": {"type": "string"},
            "approved_only": {"type": "boolean", "default": True},
            "include_pending": {"type": "boolean", "default": False},
            "opportunities": {"type": "array", "items": {"type": "object"}},
            "knowledge_items": {"type": "array", "items": {"type": "object"}},
            "documents": {"type": "array", "items": {"type": "object"}},
            "index_last_refresh": {"type": "string"},
            "index_max_age_hours": {"type": "number", "default": 24},
            "top_k": {"type": "integer", "default": 10},
        },
    ),
    tool_schema(
        "get_opportunity_timeline",
        "Return an approved evidence timeline for one opportunity or filtered Knowledge Wiki snapshot.",
        {
            "client_name": {"type": "string"},
            "opportunity_key": {"type": "string"},
            "discovery_id": {"type": "string"},
            "opportunity_code": {"type": "string"},
            "sr_number": {"type": "string"},
            "source_type": {"type": "string", "enum": sorted(core.SOURCE_TYPES)},
            "opportunities": {"type": "array", "items": {"type": "object"}},
            "knowledge_items": {"type": "array", "items": {"type": "object"}},
            "documents": {"type": "array", "items": {"type": "object"}},
            "descending": {"type": "boolean", "default": False},
            "top_k": {"type": "integer", "default": 200},
        },
    ),
    tool_schema(
        "get_backlinks",
        "Return inbound and outbound Markdown links for a Knowledge Wiki document.",
        {
            "target_path": {"type": "string"},
            "documents": {"type": "array", "items": {"type": "object"}},
            "backlinks": {"type": "array", "items": {"type": "object"}},
        },
        ["target_path"],
    ),
    tool_schema(
        "suggest_wiki_links",
        "Suggest portable relative Markdown links for a draft note or document.",
        {
            "query": {"type": "string"},
            "title": {"type": "string"},
            "markdown_content": {"type": "string"},
            "from_path": {"type": "string"},
            "opportunity_key": {"type": "string"},
            "documents": {"type": "array", "items": {"type": "object"}},
            "top_k": {"type": "integer", "default": 10},
        },
    ),
    tool_schema(
        "provision_sharepoint_registry",
        "Return dry-run Microsoft Graph payloads for the Opportunities, Knowledge Items, and Automation Runs lists.",
        {"dry_run": {"type": "boolean", "default": True}},
    ),
    tool_schema(
        "create_base_sharepoint_lists",
        "Prepare the SharePoint Opportunities, Knowledge Items, and Automation Runs list creation/update plan.",
        {"dry_run": {"type": "boolean", "default": True}},
    ),
    tool_schema(
        "create_base_sharepoint_folders",
        "Prepare the SharePoint Markdown evidence folder structure for the root or one opportunity.",
        {
            "client_name": {"type": "string"},
            "opportunity_key": {"type": "string"},
            "discovery_id": {"type": "string"},
            "opportunity_code": {"type": "string"},
            "sr_number": {"type": "string"},
            "root_folder": {"type": "string"},
            "dry_run": {"type": "boolean", "default": True},
        },
    ),
    tool_schema(
        "check_required_connectors",
        "Check whether required Codex connectors/plugins for SharePoint, Outlook, Slack, and Oracle Opportunity Pulse are enabled.",
        {"config_path": {"type": "string"}},
    ),
    tool_schema(
        "build_daily_sync_prompt",
        "Return the recommended Codex automation prompt and Outlook filters for the daily run.",
        {
            "timezone": {"type": "string", "default": core.DEFAULT_TIMEZONE},
            "local_time": {"type": "string", "default": "18:00"},
            "include_received": {"type": "boolean", "default": True},
            "include_sent": {"type": "boolean", "default": True},
            "include_zoom": {"type": "boolean", "default": True},
            "include_slack": {"type": "boolean", "default": False},
        },
    ),
]


def call_register_opportunity(args: dict[str, Any]) -> dict[str, Any]:
    return core.register_opportunity(args)


def call_register_slack_channel(args: dict[str, Any]) -> dict[str, Any]:
    return core.register_slack_channel(args)


def call_scan_agent_data_outlook(args: dict[str, Any]) -> dict[str, Any]:
    timezone = args.get("timezone", core.DEFAULT_TIMEZONE)
    scan_from = args.get("scan_from")
    scan_to = args.get("scan_to")
    result: dict[str, Any] = {
        "outlook_scan_plan": core.outlook_scan_plan(timezone, scan_from, scan_to),
        "received": {"count": 0, "candidates": []},
        "sent": {"count": 0, "candidates": []},
    }
    if args.get("include_received", True):
        result["received"] = core.scan_messages(
            args.get("received_messages", []),
            source_type="Outlook",
            direction="Received",
            today_only=args.get("today_only", True),
            timezone=timezone,
            scan_from=scan_from,
            scan_to=scan_to,
            require_agent_tag=True,
            source_scope=args.get("received_source_scope", "Inbox"),
            executed_by_email=args.get("executed_by_email", ""),
            run_id=args.get("run_id", ""),
        )
    if args.get("include_sent", True):
        result["sent"] = core.scan_messages(
            args.get("sent_messages", []),
            source_type="Outlook",
            direction="Sent",
            today_only=args.get("today_only", True),
            timezone=timezone,
            scan_from=scan_from,
            scan_to=scan_to,
            require_agent_tag=True,
            source_scope=args.get("sent_source_scope", "Sent Items"),
            executed_by_email=args.get("executed_by_email", ""),
            run_id=args.get("run_id", ""),
        )
    return result


def call_scan_zoom_ai_companion(args: dict[str, Any]) -> dict[str, Any]:
    timezone = args.get("timezone", core.DEFAULT_TIMEZONE)
    scan_from = args.get("scan_from")
    scan_to = args.get("scan_to")
    source_scope = args.get("source_scope", core.DEFAULT_ZOOM_FOLDER)
    result = core.scan_messages(
        args.get("messages", []),
        source_type="Zoom",
        direction="MeetingTranscript",
        today_only=args.get("today_only", True),
        timezone=timezone,
        scan_from=scan_from,
        scan_to=scan_to,
        require_agent_tag=bool(args.get("require_agent_tag", False)),
        source_scope=source_scope,
        expected_source_scope=core.DEFAULT_ZOOM_FOLDER,
        executed_by_email=args.get("executed_by_email", ""),
        run_id=args.get("run_id", ""),
    )
    result["folder_name"] = core.DEFAULT_ZOOM_FOLDER
    result["outlook_scan_plan"] = core.outlook_scan_plan(timezone, scan_from, scan_to)
    return result


def call_propose_candidate(args: dict[str, Any]) -> dict[str, Any]:
    return core.propose_candidate(args["candidate_id"])


def call_approve_candidate(args: dict[str, Any]) -> dict[str, Any]:
    return core.approve_candidate(args["candidate_id"], args.get("overrides") or {})


def call_reject_candidate(args: dict[str, Any]) -> dict[str, Any]:
    return core.reject_candidate(args["candidate_id"], args.get("reason", ""))


def call_add_note(args: dict[str, Any]) -> dict[str, Any]:
    return core.add_note(args)


def call_query_opportunity_pulse(args: dict[str, Any]) -> dict[str, Any]:
    return core.query_opportunity_pulse(args)


def call_configure_knowledge_wiki(args: dict[str, Any]) -> dict[str, Any]:
    return core.configure_knowledge_wiki(args)


def call_configure_pulse_connection(args: dict[str, Any]) -> dict[str, Any]:
    return core.configure_pulse_connection(args)


def call_validate_pulse_connection(args: dict[str, Any]) -> dict[str, Any]:
    return core.validate_pulse_connection(args)


def call_prepare_daily_sync_automation(args: dict[str, Any]) -> dict[str, Any]:
    return core.prepare_daily_sync_automation(args)


def call_prepare_incremental_sync_window(args: dict[str, Any]) -> dict[str, Any]:
    return core.prepare_incremental_sync_window(args)


def call_record_automation_run(args: dict[str, Any]) -> dict[str, Any]:
    return core.record_automation_run(args)


def call_refresh_knowledge_index(args: dict[str, Any]) -> dict[str, Any]:
    return core.refresh_knowledge_index(args)


def call_query_knowledge_wiki(args: dict[str, Any]) -> dict[str, Any]:
    return core.query_knowledge_wiki(args)


def call_get_opportunity_timeline(args: dict[str, Any]) -> dict[str, Any]:
    return core.get_opportunity_timeline(args)


def call_get_backlinks(args: dict[str, Any]) -> dict[str, Any]:
    return core.get_backlinks(args)


def call_suggest_wiki_links(args: dict[str, Any]) -> dict[str, Any]:
    return core.suggest_wiki_links(args)


def call_provision_sharepoint_registry(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "dry_run": args.get("dry_run", True),
        "status": "prepared",
        "graph": core.graph_provision_requests(),
        "note": "This tool prepares list and wiki payloads. Execute with an authorized Microsoft Graph workflow before claiming SharePoint changed.",
    }


def call_create_base_sharepoint_lists(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "dry_run": args.get("dry_run", True),
        **core.list_creation_plan(),
    }


def call_create_base_sharepoint_folders(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "dry_run": args.get("dry_run", True),
        **core.folder_creation_plan(
            args.get("client_name"),
            args.get("opportunity_code"),
            args.get("opportunity_key"),
            args.get("discovery_id"),
            args.get("sr_number"),
            args.get("root_folder"),
        ),
    }


def call_check_required_connectors(args: dict[str, Any]) -> dict[str, Any]:
    return core.check_required_connectors(args.get("config_path"))


def call_build_daily_sync_prompt(args: dict[str, Any]) -> dict[str, Any]:
    return core.build_daily_sync_prompt(args)


CALLS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "register_opportunity": call_register_opportunity,
    "register_slack_channel": call_register_slack_channel,
    "scan_agent_data_outlook": call_scan_agent_data_outlook,
    "scan_zoom_ai_companion": call_scan_zoom_ai_companion,
    "propose_candidate": call_propose_candidate,
    "approve_candidate": call_approve_candidate,
    "reject_candidate": call_reject_candidate,
    "add_note": call_add_note,
    "query_opportunity_pulse": call_query_opportunity_pulse,
    "configure_knowledge_wiki": call_configure_knowledge_wiki,
    "configure_pulse_connection": call_configure_pulse_connection,
    "validate_pulse_connection": call_validate_pulse_connection,
    "prepare_daily_sync_automation": call_prepare_daily_sync_automation,
    "prepare_incremental_sync_window": call_prepare_incremental_sync_window,
    "record_automation_run": call_record_automation_run,
    "refresh_knowledge_index": call_refresh_knowledge_index,
    "query_knowledge_wiki": call_query_knowledge_wiki,
    "get_opportunity_timeline": call_get_opportunity_timeline,
    "get_backlinks": call_get_backlinks,
    "suggest_wiki_links": call_suggest_wiki_links,
    "provision_sharepoint_registry": call_provision_sharepoint_registry,
    "create_base_sharepoint_lists": call_create_base_sharepoint_lists,
    "create_base_sharepoint_folders": call_create_base_sharepoint_folders,
    "check_required_connectors": call_check_required_connectors,
    "build_daily_sync_prompt": call_build_daily_sync_prompt,
}


def send(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def result(message_id: Any, value: Any) -> None:
    send({"jsonrpc": "2.0", "id": message_id, "result": value})


def error(message_id: Any, code: int, message: str, data: Any | None = None) -> None:
    payload = {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}
    if data is not None:
        payload["error"]["data"] = data
    send(payload)


def handle(request: dict[str, Any]) -> None:
    method = request.get("method")
    message_id = request.get("id")
    if method == "initialize":
        result(
            message_id,
            {
                "protocolVersion": request.get("params", {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "oracle-opportunity-pulse", "version": "1.0.2"},
            },
        )
        return
    if method == "notifications/initialized":
        return
    if method == "ping":
        result(message_id, {})
        return
    if method == "tools/list":
        result(message_id, {"tools": TOOLS})
        return
    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments") or {}
        handler = CALLS.get(name)
        if handler is None:
            error(message_id, -32601, f"Unknown tool: {name}")
            return
        try:
            output = handler(arguments)
            result(
                message_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(output, indent=2, ensure_ascii=False),
                        }
                    ],
                    "isError": False,
                },
            )
        except Exception as exc:  # noqa: BLE001
            result(
                message_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": f"{type(exc).__name__}: {exc}",
                        }
                    ],
                    "isError": True,
                },
            )
        return
    if method in {"resources/list", "prompts/list"}:
        result(message_id, {"resources": []} if method == "resources/list" else {"prompts": []})
        return
    error(message_id, -32601, f"Method not found: {method}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            handle(request)
        except Exception:  # noqa: BLE001
            error(None, -32700, "Parse or server error", traceback.format_exc())


if __name__ == "__main__":
    main()
