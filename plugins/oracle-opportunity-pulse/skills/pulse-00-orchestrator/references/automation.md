# Automation Workflow

Daily run time: `18:00 America/Lima`.

1. Scan only current-day received and sent messages.
2. Candidate rule: body contains `@agent_data`.
3. Scan Zoom transcripts in the exact Outlook folder `[0] Zoom AI companion`.
4. Use the `Opportunities` master data and `OpportunityContext` to propose classification.
5. Present candidates in the Codex thread with client, opportunity code, SR, confidence, and evidence.
6. Wait for approval or corrections.
7. After approval, save Markdown under the final source folder and create a `Knowledge Items` row.
8. Update `OpportunityContext` with the new approved signal.

Do not autoapprove, even with high confidence.
