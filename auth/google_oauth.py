"""
Saarthi AI — Google OAuth2 module for the Health Agent.

Handles the OAuth2 authorization code flow for Google Fit API access.
Tokens (access + refresh) are stored per-user in the health_tokens table
in AlloyDB so the agent can silently refresh them when needed —
users only authenticate once.

Scopes requested:
  - fitness.activity.read   → steps, calories, workout sessions
  - fitness.sleep.read      → sleep sessions and stages
  - fitness.body.read       → heart rate, weight
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from db.alloydb import get_connection

# Load .env only in local/development mode.
if os.getenv("APP_ENV", "development").lower() != "production":
    load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Config ────────────────────────────────────────────────────────────────────

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.sleep.read",
    "https://www.googleapis.com/auth/fitness.body.read",
]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/google/login")
async def google_login(user_id: str = Query(..., description="The user's unique ID")):
    """
    Step 1 of OAuth2: Redirect the user to Google's consent screen.
    user_id is passed as state so we can associate the tokens after callback.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_ID is not configured. Set it in your .env file.",
        )
    if not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_SECRET is not configured.",
        )
    if not GOOGLE_REDIRECT_URI:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_REDIRECT_URI is not configured.",
        )

    scope_str = " ".join(SCOPES)
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": scope_str,
        "access_type": "offline",     # ensures we get a refresh_token
        "prompt": "consent",          # forces refresh_token on every consent
        "state": user_id,             # carry user_id through the redirect
    }

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"{GOOGLE_AUTH_URL}?{query_string}"

    logger.info(f"Redirecting user {user_id} to Google OAuth consent screen")
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(..., description="user_id passed through from login"),
    error: str | None = Query(default=None),
):
    """
    Step 2 of OAuth2: Google redirects here with an authorization code.
    We exchange the code for access + refresh tokens and store them in AlloyDB.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")

    user_id = state

    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

    if token_response.status_code != 200:
        logger.error(f"Token exchange failed: {token_response.text}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange OAuth code: {token_response.text}",
        )

    token_data = token_response.json()
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    token_expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()
    scopes = token_data.get("scope", " ".join(SCOPES))

    # Persist tokens to AlloyDB
    await save_tokens(
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expiry=token_expiry,
        scopes=scopes,
    )

    logger.info(f"Successfully stored OAuth tokens for user {user_id}")

    # Trigger an initial background sync so AlloyDB is populated immediately.
    # The agent reads from AlloyDB during chat — this one-time pull makes that work.
    # Import here to avoid a circular import (health_agent imports auth.google_oauth).
    from agents.health_agent import sync_all_health_data
    asyncio.create_task(sync_all_health_data(user_id, days=30))
    logger.info(f"Initial health data sync scheduled for user {user_id}")

    return {
        "message": (
            "Google Fit connected successfully. "
            "Your health data is being synced in the background — "
            "it will be ready within a few seconds."
        ),
        "user_id": user_id,
        "scopes_granted": scopes.split(" "),
    }


# ── Token Management Helpers ──────────────────────────────────────────────────

async def save_tokens(
    user_id: str,
    access_token: str,
    refresh_token: str,
    token_expiry: str,
    scopes: str,
) -> None:
    """Upsert OAuth tokens for a user in the health_tokens table in AlloyDB."""
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO health_tokens
                (user_id, access_token, refresh_token, token_expiry, scopes, updated_at)
            VALUES ($1, $2, $3, $4, $5, now())
            ON CONFLICT (user_id) DO UPDATE SET
                access_token  = EXCLUDED.access_token,
                refresh_token = CASE
                    WHEN EXCLUDED.refresh_token != '' THEN EXCLUDED.refresh_token
                    ELSE health_tokens.refresh_token
                END,
                token_expiry  = EXCLUDED.token_expiry,
                scopes        = EXCLUDED.scopes,
                updated_at    = now()
            """,
            user_id,
            access_token,
            refresh_token,
            token_expiry,
            scopes,
        )
    finally:
        await conn.close()


async def get_valid_access_token(user_id: str) -> str:
    """
    Returns a valid access token for the user.
    Automatically refreshes the token if it has expired or is about to expire.
    Raises HTTPException 401 if the user has not authenticated yet.
    """
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            "SELECT access_token, refresh_token, token_expiry FROM health_tokens WHERE user_id = $1",
            user_id,
        )
    finally:
        await conn.close()

    if not row:
        raise HTTPException(
            status_code=401,
            detail=(
                f"User '{user_id}' has not connected Google Fit. "
                f"Visit /auth/google/login?user_id={user_id} to authenticate."
            ),
        )

    expiry = datetime.fromisoformat(row["token_expiry"])
    # Refresh if token expires within the next 5 minutes
    if expiry <= datetime.now(timezone.utc) + timedelta(minutes=5):
        logger.info(f"Access token expired for user {user_id}, refreshing...")
        return await _refresh_access_token(user_id, row["refresh_token"])

    return row["access_token"]


async def _refresh_access_token(user_id: str, refresh_token: str) -> str:
    """Use the refresh token to get a new access token from Google."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail=f"Failed to refresh Google access token: {response.text}",
        )

    data = response.json()
    new_access_token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    new_expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()

    await save_tokens(
        user_id=user_id,
        access_token=new_access_token,
        refresh_token=refresh_token,   # refresh_token doesn't change on refresh
        token_expiry=new_expiry,
        scopes="",                     # ON CONFLICT keeps existing scopes
    )

    return new_access_token


async def is_user_authenticated(user_id: str) -> bool:
    """Check whether the user has OAuth tokens stored (i.e., has completed login)."""
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            "SELECT 1 FROM health_tokens WHERE user_id = $1",
            user_id,
        )
        return row is not None
    finally:
        await conn.close()
