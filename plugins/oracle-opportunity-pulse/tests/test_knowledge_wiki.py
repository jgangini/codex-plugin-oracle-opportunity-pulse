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


if __name__ == "__main__":
    unittest.main()
