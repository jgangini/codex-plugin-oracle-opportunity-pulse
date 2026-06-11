from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import opportunity_pulse_core as core  # noqa: E402


class KnowledgeWikiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.previous_state = os.environ.get("OOP_STATE_PATH")
        os.environ["OOP_STATE_PATH"] = str(Path(self.tmpdir.name) / "state.json")
        self.opportunity = core.normalize_opportunity_record(
            {
                "OpportunityKey": "DISC-20260611-acme-123456",
                "DiscoveryId": "DISC-20260611-acme-123456",
                "ClientName": "ACME Bank",
                "Country": "PE",
                "LifecycleStage": "Discovery",
                "OpportunityContext": "Database modernization and Exadata latency discovery",
                "Status": "Active",
            }
        )
        self.approved_item = core.normalize_knowledge_item(
            {
                "OpportunityKey": self.opportunity["opportunity_key"],
                "SourceType": "Zoom",
                "Direction": "MeetingTranscript",
                "Title": "Latency discovery call",
                "MarkdownFileUrl": "OracleOpportunityPulseWiki/acme-bank/DISC-20260611-acme-123456/zoom/20260611-zoom-latency.md",
                "CapturedAt": "2026-06-11T15:00:00-05:00",
                "ApprovalStatus": "Approved",
            }
        )
        self.pending_item = core.normalize_knowledge_item(
            {
                "OpportunityKey": self.opportunity["opportunity_key"],
                "SourceType": "Outlook",
                "Direction": "Received",
                "Title": "Pending email",
                "MarkdownFileUrl": "OracleOpportunityPulseWiki/_pending/outlook/2026-06-11/received/pending.md",
                "CapturedAt": "2026-06-11T16:00:00-05:00",
                "ApprovalStatus": "Approved",
            }
        )
        self.proposed_item = core.normalize_knowledge_item(
            {
                "OpportunityKey": self.opportunity["opportunity_key"],
                "SourceType": "Notes",
                "Direction": "Manual",
                "Title": "Unapproved note",
                "MarkdownFileUrl": "OracleOpportunityPulseWiki/acme-bank/DISC-20260611-acme-123456/notes/proposed.md",
                "ApprovalStatus": "Proposed",
            }
        )
        self.document = core.normalize_document_record(
            {
                "path": self.approved_item["markdown_path"],
                "title": "Latency discovery call",
                "opportunity_key": self.opportunity["opportunity_key"],
                "source_type": "Zoom",
                "captured_at": "2026-06-11T15:00:00-05:00",
                "content": "Tags: #zoom #discovery\n\nACME discussed Exadata latency and links to [context](../context.md).",
            }
        )

    def tearDown(self) -> None:
        if self.previous_state is None:
            os.environ.pop("OOP_STATE_PATH", None)
        else:
            os.environ["OOP_STATE_PATH"] = self.previous_state
        self.tmpdir.cleanup()

    def test_base_folder_structure_includes_index_templates_and_attachments(self) -> None:
        root_structure = core.base_folder_structure()
        self.assertIn("OracleOpportunityPulseWiki/_config", root_structure["folders"])
        self.assertIn("OracleOpportunityPulseWiki/_index", root_structure["folders"])
        self.assertIn("OracleOpportunityPulseWiki/_templates", root_structure["folders"])
        self.assertIn("OracleOpportunityPulseWiki/_config/pulse-profile.json", root_structure["config_files"])
        self.assertIn("OracleOpportunityPulseWiki/_index/backlinks.jsonl", root_structure["index_files"])
        self.assertIn("OracleOpportunityPulseWiki/_templates/manual-note.md", root_structure["template_files"])

        opportunity_structure = core.base_folder_structure(
            client_name="ACME Bank",
            opportunity_key=self.opportunity["opportunity_key"],
        )
        self.assertIn(
            "OracleOpportunityPulseWiki/acme-bank/disc-20260611-acme-123456/attachments",
            opportunity_structure["folders"],
        )

    def test_refresh_index_builds_tags_backlinks_and_excludes_pending_by_default(self) -> None:
        result = core.refresh_knowledge_index(
            {
                "opportunities": [self.opportunity],
                "knowledge_items": [self.approved_item, self.pending_item, self.proposed_item],
                "documents": [self.document],
                "write_local_outbox": False,
            }
        )
        self.assertEqual(result["counts"]["knowledge_items"], 1)
        self.assertEqual(result["counts"]["documents"], 1)
        self.assertEqual(result["counts"]["backlinks"], 1)
        self.assertEqual(result["counts"]["tags"], 2)
        tags_file = next(file for file in result["index_files"] if file["key"] == "tags")
        self.assertIn("#zoom", tags_file["content"])
        self.assertNotIn("pending.md", next(file for file in result["index_files"] if file["key"] == "knowledge_items")["content"])

    def test_query_knowledge_wiki_ranks_fetched_markdown_and_warns_on_stale_index(self) -> None:
        result = core.query_knowledge_wiki(
            {
                "query": "Exadata latency",
                "client_name": "ACME",
                "opportunities": [self.opportunity],
                "knowledge_items": [self.approved_item, self.pending_item, self.proposed_item],
                "documents": [self.document],
                "index_last_refresh": "2026-06-10T08:00:00-05:00",
                "index_max_age_hours": 1,
            }
        )
        self.assertEqual(result["counts"]["evidence"], 1)
        self.assertEqual(result["evidence"][0]["source_type"], "Zoom")
        self.assertEqual(result["evidence"][0]["read_status"], "read")
        self.assertTrue(any("stale" in warning.lower() for warning in result["warnings"]))

    def test_backlinks_and_relative_link_suggestions(self) -> None:
        context_path = "OracleOpportunityPulseWiki/acme-bank/DISC-20260611-acme-123456/context.md"
        backlinks = core.get_backlinks(
            {
                "target_path": context_path,
                "documents": [self.document],
            }
        )
        self.assertEqual(backlinks["counts"]["inbound"], 1)

        suggestion = core.suggest_wiki_links(
            {
                "markdown_content": "Need follow up on Exadata latency",
                "from_path": context_path,
                "opportunity_key": self.opportunity["opportunity_key"],
                "documents": [self.document],
            }
        )
        self.assertEqual(suggestion["counts"]["suggestions"], 1)
        self.assertIn("zoom/20260611-zoom-latency.md", suggestion["suggestions"][0]["markdown_link"])

    def test_query_opportunity_pulse_includes_knowledge_wiki_section(self) -> None:
        state = {
            "version": 1,
            "opportunities": [self.opportunity],
            "knowledge_items": [self.approved_item],
            "candidates": [],
            "rejected_candidates": [],
        }
        result = core.query_opportunity_pulse({"query": "ACME"}, state=state)
        self.assertEqual(result["counts"]["opportunities"], 1)
        self.assertIn("knowledge_wiki", result)
        self.assertIn("warnings", result["knowledge_wiki"])

    def test_configure_pulse_connection_install_new_builds_shared_profile(self) -> None:
        result = core.configure_pulse_connection(
            {
                "mode": "install_new",
                "hostname": "contoso.sharepoint.com",
                "site_path": "sites/oracle",
                "library_path": "Shared Documents",
                "root_folder": "OracleOpportunityPulseWiki",
                "timezone": "America/Lima",
            }
        )
        profile = result["profile"]
        self.assertEqual(result["status"], "configured")
        self.assertEqual(profile["mode"], "install_new")
        self.assertEqual(profile["site_path"], "/sites/oracle")
        self.assertEqual(profile["timezone"], "America/Lima")
        self.assertEqual(profile["zoom_folder"], core.DEFAULT_ZOOM_FOLDER)
        self.assertEqual(
            result["shared_profile_file"]["path"],
            "OracleOpportunityPulseWiki/_config/pulse-profile.json",
        )
        self.assertIn("create_or_validate_lists", result["handoff"]["next_steps"])
        self.assertEqual(result["missing_required_fields"], [])

    def test_configure_pulse_connection_connect_existing_accepts_shared_profile(self) -> None:
        shared_profile = {
            "hostname": "contoso.sharepoint.com",
            "site_path": "/sites/shared-pulse",
            "library_path": "Documents",
            "root_folder": "PulseWiki",
            "opportunities_list": "Oracle Opportunities",
            "knowledge_items_list": "Oracle Knowledge Items",
            "timezone": "America/Bogota",
        }
        result = core.configure_pulse_connection(
            {
                "mode": "connect_existing",
                "shared_profile": shared_profile,
            }
        )
        profile = result["profile"]
        self.assertEqual(profile["mode"], "connect_existing")
        self.assertEqual(profile["root_folder"], "PulseWiki")
        self.assertEqual(profile["opportunities_list"], "Oracle Opportunities")
        self.assertEqual(profile["timezone"], "America/Bogota")
        self.assertIn("validate_existing_lists_and_wiki", result["handoff"]["next_steps"])

    def test_validate_pulse_connection_reports_missing_sources_and_timezone(self) -> None:
        result = core.validate_pulse_connection(
            {
                "profile": {
                    "hostname": "contoso.sharepoint.com",
                    "site_path": "/sites/oracle",
                    "library_path": "Shared Documents",
                    "root_folder": "OracleOpportunityPulseWiki",
                    "timezone": "Invalid/Zone",
                    "zoom_folder": "",
                },
                "connector_status": {
                    "required_connectors": {
                        "sharepoint": {"enabled": True},
                        "outlook-email": {"enabled": False},
                        "slack": {"enabled": False},
                    },
                    "plugin_entries": {"oracle-opportunity-pulse@local": {"enabled": True}},
                },
            }
        )
        self.assertFalse(result["ready"])
        self.assertIn("outlook-email connector is missing or disabled", result["blocking_issues"])
        self.assertIn("timezone is not a valid IANA timezone", result["blocking_issues"])
        self.assertIn("zoom_folder is missing", result["blocking_issues"])
        self.assertTrue(any("Slack V1" in warning for warning in result["warnings"]))

    def test_prepare_daily_sync_automation_uses_personal_local_time_without_raw_rrule(self) -> None:
        core.configure_pulse_connection(
            {
                "mode": "install_new",
                "hostname": "contoso.sharepoint.com",
                "site_path": "/sites/oracle",
                "library_path": "Shared Documents",
                "root_folder": "OracleOpportunityPulseWiki",
                "timezone": "America/Lima",
            }
        )
        result = core.prepare_daily_sync_automation(
            {
                "timezone": "America/Bogota",
                "local_time": "18:00",
                "include_slack": True,
                "connector_status": {
                    "required_connectors": {
                        "sharepoint": {"enabled": True},
                        "outlook-email": {"enabled": True},
                        "slack": {"enabled": True},
                    },
                    "plugin_entries": {"oracle-opportunity-pulse@local": {"enabled": True}},
                },
            }
        )
        self.assertEqual(result["schedule"]["local_time"], "18:00")
        self.assertEqual(result["schedule"]["timezone"], "America/Bogota")
        self.assertTrue(result["validation"]["ready"])
        self.assertIn("automation_update", result["codex_automation"]["tool"])
        self.assertNotIn("rrule", result)
        self.assertIn("RRULE", result["codex_automation"]["fields"]["rrule"])
        self.assertIn("never autoapprove", result["prompt"].lower())
        self.assertIn("since last successful run", result["prompt"])

    def test_outlook_agent_tag_required_inside_incremental_window(self) -> None:
        messages = [
            {
                "id": "outlook-1",
                "internetMessageId": "<outlook-1@example.com>",
                "subject": "ACME discovery",
                "receivedDateTime": "2026-06-11T15:00:00-05:00",
                "body": "Please capture this @agent_data for ACME.",
            },
            {
                "id": "outlook-2",
                "internetMessageId": "<outlook-2@example.com>",
                "subject": "ACME FYI",
                "receivedDateTime": "2026-06-11T15:05:00-05:00",
                "body": "No marker here.",
            },
        ]
        result = core.scan_messages(
            messages,
            source_type="Outlook",
            direction="Received",
            today_only=False,
            scan_from="2026-06-11T14:00:00-05:00",
            scan_to="2026-06-11T16:00:00-05:00",
            require_agent_tag=True,
        )
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["skipped"]["missing_agent_tag"], 1)
        self.assertEqual(result["candidates"][0]["source_external_id"], "<outlook-1@example.com>")

    def test_zoom_does_not_require_agent_tag_but_requires_folder_scope(self) -> None:
        message = {
            "id": "zoom-1",
            "internetMessageId": "<zoom-1@example.com>",
            "subject": "Zoom transcript: ACME",
            "receivedDateTime": "2026-06-11T17:00:00-05:00",
            "body": "Zoom transcript without ingestion marker.",
        }
        result = core.scan_messages(
            [message],
            source_type="Zoom",
            direction="MeetingTranscript",
            today_only=False,
            scan_from="2026-06-11T16:00:00-05:00",
            scan_to="2026-06-11T18:00:00-05:00",
            require_agent_tag=False,
            source_scope=core.DEFAULT_ZOOM_FOLDER,
            expected_source_scope=core.DEFAULT_ZOOM_FOLDER,
        )
        self.assertEqual(result["count"], 1)
        self.assertFalse(result["filters"]["require_agent_tag"])

        outside = core.scan_messages(
            [{**message, "id": "zoom-2", "internetMessageId": "<zoom-2@example.com>"}],
            source_type="Zoom",
            direction="MeetingTranscript",
            today_only=False,
            scan_from="2026-06-11T16:00:00-05:00",
            scan_to="2026-06-11T18:00:00-05:00",
            require_agent_tag=False,
            source_scope="Inbox",
            expected_source_scope=core.DEFAULT_ZOOM_FOLDER,
        )
        self.assertEqual(outside["count"], 0)
        self.assertEqual(outside["skipped"]["wrong_source_scope"], 1)

    def test_prepare_incremental_sync_window_uses_local_day_without_history(self) -> None:
        result = core.prepare_incremental_sync_window(
            {
                "user_email": "user@example.com",
                "source_type": "Outlook",
                "direction": "Received",
                "timezone": "America/Lima",
                "now": "2026-06-11T18:00:00-05:00",
            }
        )
        self.assertEqual(result["window_source"], "local_day_start")
        self.assertEqual(result["scan_from"], "2026-06-11T00:00:00-05:00")
        self.assertEqual(result["scan_to"], "2026-06-11T18:00:00-05:00")

    def test_prepare_incremental_sync_window_uses_last_success_and_ignores_failed_runs(self) -> None:
        core.record_automation_run(
            {
                "run_id": "run-success",
                "user_email": "user@example.com",
                "profile_name": "Oracle Opportunity Pulse",
                "source_type": "Outlook",
                "direction": "Received",
                "scan_from": "2026-06-10T00:00:00-05:00",
                "scan_to": "2026-06-10T18:00:00-05:00",
                "started_at": "2026-06-10T18:00:00-05:00",
                "finished_at": "2026-06-10T18:02:00-05:00",
                "run_status": "Succeeded",
                "last_source_event_at": "2026-06-10T17:30:00-05:00",
                "next_scan_from": "2026-06-10T17:20:00-05:00",
            }
        )
        core.record_automation_run(
            {
                "run_id": "run-failed",
                "user_email": "user@example.com",
                "profile_name": "Oracle Opportunity Pulse",
                "source_type": "Outlook",
                "direction": "Received",
                "scan_from": "2026-06-11T08:00:00-05:00",
                "scan_to": "2026-06-11T09:00:00-05:00",
                "run_status": "Failed",
                "error_summary": "PC offline during previous schedule.",
            }
        )
        result = core.prepare_incremental_sync_window(
            {
                "user_email": "user@example.com",
                "profile_name": "Oracle Opportunity Pulse",
                "source_type": "Outlook",
                "direction": "Received",
                "timezone": "America/Lima",
                "now": "2026-06-11T18:00:00-05:00",
            }
        )
        self.assertTrue(result["used_last_successful_run"])
        self.assertEqual(result["scan_from"], "2026-06-10T17:20:00-05:00")

    def test_record_automation_run_sets_watermark_and_list_plan_includes_automation_runs(self) -> None:
        result = core.record_automation_run(
            {
                "run_id": "run-zoom",
                "user_email": "user@example.com",
                "profile_name": "Oracle Opportunity Pulse",
                "source_type": "Zoom",
                "direction": "MeetingTranscript",
                "source_scope": core.DEFAULT_ZOOM_FOLDER,
                "scan_from": "2026-06-11T00:00:00-05:00",
                "scan_to": "2026-06-11T18:00:00-05:00",
                "run_status": "Succeeded",
                "last_source_event_at": "2026-06-11T17:00:00-05:00",
                "timezone": "America/Lima",
            }
        )
        self.assertEqual(result["list_name"], core.DEFAULT_AUTOMATION_RUNS_LIST)
        self.assertEqual(result["automation_run"]["next_scan_from"], "2026-06-11T16:50:00-05:00")
        list_names = [item["displayName"] for item in core.list_creation_plan()["lists"]]
        self.assertIn(core.DEFAULT_AUTOMATION_RUNS_LIST, list_names)

    def test_overlap_deduplicates_by_source_external_id(self) -> None:
        message = {
            "id": "outlook-overlap",
            "internetMessageId": "<overlap@example.com>",
            "subject": "Overlap capture",
            "receivedDateTime": "2026-06-11T17:55:00-05:00",
            "body": "Overlap scan @agent_data.",
        }
        first = core.scan_messages(
            [message],
            source_type="Outlook",
            direction="Received",
            today_only=False,
            scan_from="2026-06-11T17:00:00-05:00",
            scan_to="2026-06-11T18:00:00-05:00",
            require_agent_tag=True,
        )
        second = core.scan_messages(
            [message],
            source_type="Outlook",
            direction="Received",
            today_only=False,
            scan_from="2026-06-11T17:50:00-05:00",
            scan_to="2026-06-11T18:10:00-05:00",
            require_agent_tag=True,
        )
        self.assertEqual(first["count"], 1)
        self.assertEqual(second["count"], 0)
        self.assertEqual(second["skipped"]["duplicates"], 1)


if __name__ == "__main__":
    unittest.main()
