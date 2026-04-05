"""
Saarthi AI — Notes MCP using Google Docs.
Each learning resource gets its own Google Doc.
Notes are appended to the doc with timestamps.
Doc IDs are stored in AlloyDB life_logs for retrieval.
"""

import os
import json
import logging
from datetime import datetime
from uuid import uuid4
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "/home/ajayk10440/Saarthi-AI/token.json")
DOCS_INDEX_FILE = "/home/ajayk10440/Saarthi-AI/docs_index.json"


def _get_credentials():
    """Load and refresh OAuth credentials."""
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


def _get_or_create_doc(resource_title: str) -> str:
    """Get existing Google Doc ID for resource, or create a new one."""
    index = _load_docs_index()

    if resource_title in index:
        return index[resource_title]

    # Create new Google Doc
    drive = _get_drive_service()
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

    # Save to index
    index[resource_title] = doc_id
    _save_docs_index(index)

    logger.info("Created Google Doc for '%s': %s", resource_title, doc_id)
    return doc_id


async def save_learning_note(
    user_id: str,
    resource_title: str,
    note_content: str,
    tags: list[str] | None = None,
) -> dict:
    """Save a study note to Google Docs and record in AlloyDB."""
    try:
        # 1. Get or create Google Doc for this resource
        doc_id = _get_or_create_doc(resource_title)
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
    try:
        index = _load_docs_index()

        if resource_title and resource_title in index:
            # Get specific doc
            docs_to_fetch = {resource_title: index[resource_title]}
        elif resource_title:
            # Try partial match
            docs_to_fetch = {
                k: v for k, v in index.items()
                if resource_title.lower() in k.lower()
            }
        else:
            # All docs
            docs_to_fetch = index

        if not docs_to_fetch:
            return []

        docs_service = _get_docs_service()
        results = []

        for title, doc_id in docs_to_fetch.items():
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
                    "resource": title,
                    "content": full_text.strip(),
                    "doc_url": doc_url,
                })
            except Exception as exc:
                logger.warning("Failed to fetch doc %s: %s", doc_id, exc)

        return results

    except Exception as exc:
        logger.error("Failed to fetch notes from Google Docs: %s", exc)
        return []
