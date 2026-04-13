"""
Saarthi AI — Notes MCP using Google Docs.
Each learning resource gets its own Google Doc.
Notes are appended to the doc with timestamps.
Doc IDs are stored in AlloyDB life_logs for retrieval.
"""

import os
import json
import logging
import re
from datetime import datetime
from uuid import uuid4
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "").strip()
DOCS_INDEX_FILE = os.getenv("GOOGLE_DOCS_INDEX_PATH", "docs_index.json")


def _get_credentials():
    """Load and refresh OAuth credentials."""
    if not TOKEN_PATH:
        raise RuntimeError("GOOGLE_TOKEN_PATH is required for notes integration.")
    with open(TOKEN_PATH) as f:
        data = json.load(f)

    creds = Credentials(
        token=data["token"],
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data["scopes"],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        data["token"] = creds.token
        with open(TOKEN_PATH, "w") as f:
            json.dump(data, f, indent=2)
    return creds


def _get_docs_service():
    return build("docs", "v1", credentials=_get_credentials())


def _get_drive_service():
    return build("drive", "v3", credentials=_get_credentials())


def _load_docs_index() -> dict:
    """Load the mapping of resource_title -> Google Doc ID."""
    if os.path.exists(DOCS_INDEX_FILE):
        with open(DOCS_INDEX_FILE) as f:
            return json.load(f)
    return {}


def _save_docs_index(index: dict):
    with open(DOCS_INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def _normalize_title(resource_title: str) -> str:
    normalized = re.sub(r"\s+", " ", resource_title.strip().lower())
    return re.sub(r"[^a-z0-9 _-]", "", normalized).replace(" ", "_")[:120] or "untitled"


def _make_doc_key(user_id: str, resource_title: str, resource_id: str | None = None) -> str:
    if resource_id:
        return f"user:{user_id}:resource:{resource_id}"
    return f"user:{user_id}:resource_title:{_normalize_title(resource_title)}"


async def _user_owns_resource_title(user_id: str, resource_title: str) -> bool:
    """
    Validate user/resource association for note operations.
    """
    if resource_title.strip().lower() == "general":
        return True
    try:
        from db.alloydb import get_connection
        conn = await get_connection()
        try:
            row = await conn.fetchrow(
                """
                SELECT 1
                FROM learning_resources
                WHERE user_id = $1
                  AND LOWER(title) = LOWER($2)
                LIMIT 1
                """,
                user_id,
                resource_title.strip(),
            )
            return row is not None
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning("Ownership check failed user_id=%s title=%s error=%s", user_id, resource_title, exc)
        return False


async def _is_legacy_doc_access_allowed(user_id: str, resource_title: str) -> bool:
    """
    Backward compatibility:
      Legacy key format was just <resource_title>. Allow only if title ownership is
      verifiable and unique to one user in the system.
    """
    try:
        from db.alloydb import get_connection
        conn = await get_connection()
        try:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(DISTINCT user_id) AS owner_count,
                    BOOL_OR(user_id::text = $1) AS includes_requesting_user
                FROM learning_resources
                WHERE LOWER(title) = LOWER($2)
                """,
                user_id,
                resource_title.strip(),
            )
            owner_count = int(row["owner_count"] or 0)
            includes_requesting_user = bool(row["includes_requesting_user"])
            return owner_count == 1 and includes_requesting_user
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning(
            "Legacy access verification failed user_id=%s title=%s error=%s",
            user_id, resource_title, exc,
        )
        return False


def _get_or_create_doc(user_id: str, resource_title: str, resource_id: str | None = None) -> tuple[str, str]:
    """Get existing Google Doc for user/resource key, or create a new one."""
    index = _load_docs_index()
    doc_key = _make_doc_key(user_id=user_id, resource_title=resource_title, resource_id=resource_id)

    if doc_key in index:
        doc_id = index[doc_key]
        logger.info("Notes access user_id=%s access=read key=%s doc_id=%s", user_id, doc_key, doc_id)
        return doc_id, doc_key

    # Create new Google Doc
    _ = _get_drive_service()
    docs = _get_docs_service()

    # Create the doc
    doc = docs.documents().create(body={
        "title": f"Saarthi Notes — {resource_title}"
    }).execute()

    doc_id = doc["documentId"]

    # Add header to the doc
    docs.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": f"📚 Study Notes: {resource_title}\nCreated by Saarthi AI\n{'='*50}\n\n"
                    }
                }
            ]
        }
    ).execute()

    # Save to index with tenant-aware key
    index[doc_key] = doc_id
    _save_docs_index(index)

    logger.info(
        "Notes access user_id=%s access=write_create key=%s doc_id=%s title=%s",
        user_id, doc_key, doc_id, resource_title,
    )
    return doc_id, doc_key


async def save_learning_note(
    user_id: str,
    resource_title: str,
    note_content: str,
    tags: list[str] | None = None,
    resource_id: str | None = None,
) -> dict:
    """Save a study note to Google Docs and record in AlloyDB."""
    if not user_id:
        return {"note_id": None, "saved": False, "error": "user_id is required"}
    if not resource_title.strip():
        return {"note_id": None, "saved": False, "error": "resource_title is required"}
    if not note_content.strip():
        return {"note_id": None, "saved": False, "error": "note_content is required"}

    owns_resource = await _user_owns_resource_title(user_id, resource_title)
    if not owns_resource:
        logger.warning(
            "Notes access rejected user_id=%s access=write title=%s reason=ownership_failed",
            user_id, resource_title,
        )
        return {"note_id": None, "saved": False, "error": "Resource ownership validation failed"}

    try:
        # 1. Get or create Google Doc for this resource
        doc_id, doc_key = _get_or_create_doc(user_id=user_id, resource_title=resource_title, resource_id=resource_id)
        docs = _get_docs_service()

        # 2. Get current doc length to append at end
        doc = docs.documents().get(documentId=doc_id).execute()
        end_index = doc["body"]["content"][-1]["endIndex"] - 1

        # 3. Append note with timestamp (IST = UTC+5:30)
        from datetime import timezone, timedelta
        IST = timezone(timedelta(hours=5, minutes=30))
        timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
        note_text = f"\n[{timestamp}]\n{note_content}\n{'-'*40}\n"

        docs.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": end_index},
                            "text": note_text,
                        }
                    }
                ]
            }
        ).execute()

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        logger.info("Note appended to Google Doc: %s", doc_url)

        # 4. Also save reference in AlloyDB life_logs
        try:
            from db.alloydb import get_connection
            conn = await get_connection()
            try:
                entry = f"[{resource_title}] {note_content}"
                await conn.execute(
                    """
                    INSERT INTO life_logs (id, user_id, domain, entry, logged_at)
                    VALUES ($1, $2, 'learning', $3, now())
                    """,
                    str(uuid4()), user_id, entry,
                )
            finally:
                await conn.close()
        except Exception as db_exc:
            logger.warning("AlloyDB backup failed (note still saved to Docs): %s", db_exc)

        return {
            "note_id": doc_id,
            "doc_key": doc_key,
            "saved": True,
            "resource": resource_title,
            "doc_url": doc_url,
            "logged_at": timestamp,
        }

    except Exception as exc:
        logger.error("Failed to save note to Google Docs: %s", exc)
        return {"note_id": None, "saved": False, "error": str(exc)}


async def get_learning_notes(
    user_id: str,
    resource_title: str | None = None,
) -> list[dict]:
    """Retrieve notes from Google Docs."""
    if not user_id:
        logger.warning("Notes access rejected user_id=<missing> access=read reason=missing_user_id")
        return []

    try:
        index = _load_docs_index()
        docs_to_fetch: dict[str, str] = {}
        prefix = f"user:{user_id}:"
        normalized_title_filter = _normalize_title(resource_title) if resource_title else ""

        # New tenant-safe keys
        for key, doc_id in index.items():
            if not isinstance(key, str):
                continue
            if key.startswith(prefix):
                if normalized_title_filter and normalized_title_filter not in key:
                    continue
                docs_to_fetch[key] = doc_id

        # Legacy keys fallback (resource_title-only)
        if resource_title:
            legacy_candidates = {
                k: v for k, v in index.items()
                if isinstance(k, str) and not k.startswith("user:") and resource_title.lower() in k.lower()
            }
        else:
            legacy_candidates = {
                k: v for k, v in index.items()
                if isinstance(k, str) and not k.startswith("user:")
            }
        for legacy_title, doc_id in legacy_candidates.items():
            allowed = await _is_legacy_doc_access_allowed(user_id, legacy_title)
            if not allowed:
                logger.warning(
                    "Notes access rejected user_id=%s access=read key=%s reason=legacy_ownership_unverified",
                    user_id, legacy_title,
                )
                continue
            docs_to_fetch[legacy_title] = doc_id

        if not docs_to_fetch:
            return []

        docs_service = _get_docs_service()
        results = []

        for key, doc_id in docs_to_fetch.items():
            try:
                doc = docs_service.documents().get(documentId=doc_id).execute()
                doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

                # Extract text content
                full_text = ""
                for element in doc.get("body", {}).get("content", []):
                    para = element.get("paragraph")
                    if para:
                        for pe in para.get("elements", []):
                            tr = pe.get("textRun")
                            if tr:
                                full_text += tr.get("content", "")

                results.append({
                    "note_id": doc_id,
                    "resource": resource_title or key,
                    "doc_key": key,
                    "content": full_text.strip(),
                    "doc_url": doc_url,
                })
                logger.info(
                    "Notes access user_id=%s access=read key=%s doc_id=%s",
                    user_id, key, doc_id,
                )
            except Exception as exc:
                logger.warning("Failed to fetch doc %s: %s", doc_id, exc)

        return results

    except Exception as exc:
        logger.error("Failed to fetch notes from Google Docs: %s", exc)
        return []
