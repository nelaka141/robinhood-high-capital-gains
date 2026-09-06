"""Google Drive sync for the bot's stateful data files and rotated journal history.

Real file-based transfer: bytes stream directly between local disk and Drive's REST API via
`requests`, never relayed through an MCP tool's chat-style content parameters (that path was
tried first and silently corrupted files above a few KB/tens of KB — see git history on this
file's introduction for the investigation). Auth is a standing OAuth refresh-token credential
read from the GOOGLE_DRIVE_TOKEN_JSON environment variable (the standard google-auth "authorized
user" JSON shape: client_id/client_secret/refresh_token/token_uri/scopes), refreshed as needed —
no browser, no per-cycle consent, same pattern bot/notify.py uses for Gmail via token.json.

Why OAuth-as-a-user rather than a GCP service account: a bare service account has zero Drive
storage quota of its own and can only write into a Shared Drive or via Workspace domain-wide
delegation — neither available on a plain personal (non-Workspace) Google account. A refresh
token for the account's own Google login has no such restriction.

Storage layout — fixed Drive folder IDs under a "Robinhood-Bot-State" folder in the account's own
personal Drive (created once by hand; recreate the tree with the same names/nesting and update
the IDs below if it's ever lost — nothing else depends on the exact IDs beyond this module):
  Robinhood-Bot-State/                        12SwkVAnrybOF-D2aHNQzpKsmNu8VQcgV
    trade_journal.md                          mirror of logs/trade_journal.md (which ALSO stays
                                               git-tracked — Drive here is a convenience copy,
                                               not the source of truth for this one file)
    peak-prices/                               1ssOwdDphKOY4OCaNxUu6HLtO1exe4pp-
      prices.json                             -> peak/prices.json (Drive is authoritative)
    tax-realized-gains-by-year/                1kCOywFmcZBGemK72t9KyHDBdxdXmtRxr
      realized_gains_by_year.json             -> tax/realized_gains_by_year.json (Drive is authoritative)
    price-history/                             18EExEcp4b3ZkvdnardPh255CcPPwmv8X
      daily_bars.json                         -> price_history/daily_bars.json (Drive is authoritative)
    journal-history/                           1Yg734fEjD9gVwwUUubbeTJ_SA_eMCUxC
      history_trade_journal-<N>.md            -> logs/history_trade_journal-<N>.md (Drive-only,
                                               never git — one file per rotation, see journal.py)

None of these three state files or the history_trade_journal-*.md files are git-tracked (see
.gitignore) — the container running a cycle is ephemeral, so `pull_state` MUST run at the start
of every cycle (before anything reads these files) and `push_state` at the end (after everything
that writes them), or state silently reverts to whatever the last pull saw.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

DRIVE_API = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"

ROOT_FOLDER_ID = "12SwkVAnrybOF-D2aHNQzpKsmNu8VQcgV"        # Robinhood-Bot-State
PEAK_PRICES_FOLDER_ID = "1ssOwdDphKOY4OCaNxUu6HLtO1exe4pp-"
TAX_FOLDER_ID = "1kCOywFmcZBGemK72t9KyHDBdxdXmtRxr"
PRICE_HISTORY_FOLDER_ID = "18EExEcp4b3ZkvdnardPh255CcPPwmv8X"
JOURNAL_HISTORY_FOLDER_ID = "1Yg734fEjD9gVwwUUubbeTJ_SA_eMCUxC"

TOKEN_ENV_VAR = "GOOGLE_DRIVE_TOKEN_JSON"
SCOPES = ["https://www.googleapis.com/auth/drive"]

# (local path relative to repo_dir, Drive parent folder id, Drive filename)
STATE_FILES = [
    ("peak/prices.json", PEAK_PRICES_FOLDER_ID, "prices.json"),
    ("tax/realized_gains_by_year.json", TAX_FOLDER_ID, "realized_gains_by_year.json"),
    ("price_history/daily_bars.json", PRICE_HISTORY_FOLDER_ID, "daily_bars.json"),
]


def is_configured() -> bool:
    return bool(os.environ.get(TOKEN_ENV_VAR))


def _credentials() -> Credentials:
    raw = os.environ.get(TOKEN_ENV_VAR)
    if not raw:
        raise RuntimeError(
            f"{TOKEN_ENV_VAR} is not set — Google Drive state sync cannot run. "
            "See bot/README.md, 'Google Drive state sync'."
        )
    creds = Credentials.from_authorized_user_info(json.loads(raw), scopes=SCOPES)
    creds.refresh(Request())
    return creds


def _headers() -> dict:
    return {"Authorization": f"Bearer {_credentials().token}"}


def _find_file(folder_id: str, name: str, headers: dict) -> Optional[str]:
    r = requests.get(
        f"{DRIVE_API}/files",
        headers=headers,
        params={
            "q": f"'{folder_id}' in parents and name = '{name}' and trashed = false",
            "fields": "files(id)",
            "pageSize": 1,
        },
        timeout=30,
    )
    r.raise_for_status()
    files = r.json().get("files", [])
    return files[0]["id"] if files else None


def list_files(folder_id: str, headers: Optional[dict] = None) -> List[dict]:
    headers = headers or _headers()
    r = requests.get(
        f"{DRIVE_API}/files",
        headers=headers,
        params={
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "files(id,name)",
            "pageSize": 1000,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("files", [])


def download_file(file_id: str, local_path: str | Path, headers: Optional[dict] = None) -> None:
    """Streams bytes straight from Drive to disk in chunks — the file's content never passes
    through a Python string, so there's no text-encoding step that could corrupt it."""
    headers = headers or _headers()
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(
        f"{DRIVE_API}/files/{file_id}", headers=headers,
        params={"alt": "media"}, stream=True, timeout=60,
    ) as resp:
        resp.raise_for_status()
        with open(local_path, "wb") as out:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                out.write(chunk)


def upload_file(
    folder_id: str, name: str, local_path: str | Path,
    mime_type: str = "application/octet-stream", headers: Optional[dict] = None,
) -> str:
    """Creates (or updates, if `name` already exists in `folder_id`) a Drive file from the bytes
    at `local_path`, streamed directly from disk via a multipart request. Returns the file id."""
    headers = headers or _headers()
    existing_id = _find_file(folder_id, name, headers)
    metadata = {"name": name} if existing_id else {"name": name, "parents": [folder_id]}
    with open(local_path, "rb") as fh:
        files = {
            "metadata": (None, json.dumps(metadata), "application/json"),
            "file": (name, fh, mime_type),
        }
        if existing_id:
            r = requests.patch(
                f"{DRIVE_UPLOAD_API}/files/{existing_id}?uploadType=multipart&fields=id",
                headers=headers, files=files, timeout=60,
            )
        else:
            r = requests.post(
                f"{DRIVE_UPLOAD_API}/files?uploadType=multipart&fields=id",
                headers=headers, files=files, timeout=60,
            )
    r.raise_for_status()
    return r.json()["id"]


def pull_state(repo_dir: str | Path) -> None:
    """Cycle start: pull peak/prices.json, tax/realized_gains_by_year.json, and
    price_history/daily_bars.json from Drive into repo_dir, plus every
    logs/history_trade_journal-*.md file from the journal-history folder. A state file missing on
    Drive (first-ever run) is left alone if a local copy already exists, else seeded with an
    empty JSON object so the rest of the pipeline has something well-formed to read."""
    headers = _headers()
    repo_dir = Path(repo_dir)

    for local_rel, folder_id, drive_name in STATE_FILES:
        local_path = repo_dir / local_rel
        file_id = _find_file(folder_id, drive_name, headers)
        if file_id:
            download_file(file_id, local_path, headers)
        elif not local_path.exists():
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text("{}\n")

    logs_dir = repo_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    for f in list_files(JOURNAL_HISTORY_FOLDER_ID, headers):
        download_file(f["id"], logs_dir / f["name"], headers)


def push_state(repo_dir: str | Path) -> None:
    """Cycle end: push the same three state files back to Drive, plus a mirror of
    logs/trade_journal.md and every current logs/history_trade_journal-*.md file."""
    headers = _headers()
    repo_dir = Path(repo_dir)

    for local_rel, folder_id, drive_name in STATE_FILES:
        local_path = repo_dir / local_rel
        if local_path.exists():
            upload_file(folder_id, drive_name, local_path, "application/json", headers)

    journal_path = repo_dir / "logs" / "trade_journal.md"
    if journal_path.exists():
        upload_file(ROOT_FOLDER_ID, "trade_journal.md", journal_path, "text/markdown", headers)

    for p in sorted((repo_dir / "logs").glob("history_trade_journal-*.md")):
        upload_file(JOURNAL_HISTORY_FOLDER_ID, p.name, p, "text/markdown", headers)
