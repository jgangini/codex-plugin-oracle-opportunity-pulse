# Automation Workflow

Daily run time: `18:00` in the user's IANA timezone.

1. Prepare a scan window per user/source/direction from `Automation Runs.NextScanFrom`.
2. If there is no successful history, start at the beginning of the user's local day.
3. Scan Outlook received and sent messages in the window; candidate rule is body contains `@agent_data`.
4. Scan all Zoom transcripts in the exact Outlook folder `[0] Zoom AI companion` in the window; no `@agent_data` marker is required.
5. Use the `Opportunities` master data and `OpportunityContext` to propose classification.
6. Present candidates in the Codex thread with client, opportunity code, SR, confidence, and evidence.
7. Wait for approval or corrections.
8. After approval, save Markdown under the final source folder and create a `Knowledge Items` row.
9. Update `OpportunityContext` with the new approved signal.
10. Record one `Automation Runs` row per user/source/direction with counts, status, `LastSourceEventAt`, and `NextScanFrom`.

Do not autoapprove, even with high confidence.
