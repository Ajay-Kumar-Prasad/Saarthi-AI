"""
Saarthi AI — Tasks MCP wrapper (thin layer over workspace_mcp client).
Kept separate so other agents can import task tools without pulling in
the full workspace MCP toolset.
"""

import os
import logging
from tools.workspace_mcp.client import (
    get_tasks,
    mock_create_task,
    mock_list_tasks,
    MOCK_WORKSPACE_MCP,
)

logger = logging.getLogger(__name__)


async def list_tasks(user_id: str, max_results: int = 20) -> list[dict]:
    return await get_tasks(user_id, max_results)


async def create_task(
    user_id: str,
    title: str,
    due: str = "",
    notes: str = "",
) -> dict:
    if MOCK_WORKSPACE_MCP:
        logger.info("[MOCK] Creating task user_id=%s title=%s", user_id, title)
        return await mock_create_task(title, due, notes)
    logger.warning("Direct MCP task creation not supported outside ADK agent context.")
    return {"created": False, "error": "MCP not available outside ADK agent"}