"""Drafts the post-rebalance summary email — CLAUDE.md Step 7's final bullet. Uses the Gmail
API; you must already have valid OAuth credentials available (e.g. a token.json next to your
run script, from the standard Gmail API quickstart flow). This module does not manage that
flow. The Gmail API's draft-attachment path requires MIME multipart construction; the simpler
and equally faithful substitute used here is embedding the journal entry as text in the body.
"""
from __future__ import annotations

import base64
from email.mime.text import MIMEText

SEND_WITH_CLAUDE_LABEL = "Send-With-Claude"


def draft_summary_email(to_address: str, subject: str, body: str, journal_entry_md: str) -> str:
    """Creates a Gmail draft, applies the Send-With-Claude label, returns the draft id.
    Requires: pip install google-api-python-client google-auth-oauthlib
    """
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file("token.json")
    service = build("gmail", "v1", credentials=creds)

    full_body = body + "\n\n" + ("-" * 72) + "\n\n" + journal_entry_md
    message = MIMEText(full_body)
    message["to"] = to_address
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    _apply_label(service, draft["message"]["threadId"], SEND_WITH_CLAUDE_LABEL)
    return draft["id"]


def _apply_label(service, thread_id: str, label_name: str) -> None:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    match = next((l for l in labels if l["name"] == label_name), None)
    label_id = match["id"] if match else service.users().labels().create(
        userId="me", body={"name": label_name}
    ).execute()["id"]
    service.users().threads().modify(userId="me", id=thread_id, body={"addLabelIds": [label_id]}).execute()
