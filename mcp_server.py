"""
ADO MCP Server — exposes Azure DevOps as tools for AI agents.

Run (stdio, for Claude Desktop / mcp dev):
    python mcp_server.py

Run (streamable HTTP, for AIQ platform):
    fastmcp run mcp_server.py --transport streamable-http --host 0.0.0.0 --port 8000
"""

import os
import sys
from datetime import datetime

# Load .env so ADO_PAT etc. are available when running directly
from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from agent.auth import BearerAuth
from agent.ado_client import (
    get_new_stories,
    get_active_stories_changed_since,
    get_recent_comments,
    _get_items_by_ids,
)


def _sort_and_cap(items: list[dict], date_field: str, cap: int = 10) -> list[dict]:
    """Sort by Priority asc (1=Critical first), then date_field desc. Dedup and cap."""
    def _key(item):
        f = item.get("fields", {})
        priority = f.get("Microsoft.VSTS.Common.Priority") or 99
        raw = f.get(date_field) or "2000-01-01T00:00:00Z"
        try:
            ts = datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            ts = 0.0
        return (priority, -ts)

    seen: set[int] = set()
    result = []
    for item in sorted(items, key=_key):
        if item["id"] not in seen:
            seen.add(item["id"])
            result.append(item)
        if len(result) == cap:
            break
    return result

mcp = FastMCP(
    name="ADO Connector",
    instructions=(
        "Provides tools to query Azure DevOps work items and comments. "
        "All time parameters use UTC in format 'YYYY-MM-DD HH:MM:SS'."
    ),
)


@mcp.tool()
def get_new_work_items(start_time: str, end_time: str) -> list[dict]:
    """Get new User Stories created in ADO within a time window.

    Args:
        start_time: Window start in UTC — format 'YYYY-MM-DD HH:MM:SS'
        end_time:   Window end in UTC   — format 'YYYY-MM-DD HH:MM:SS'

    Returns list of work items with id and fields (Title, State, Priority, AssignedTo, CreatedDate).
    """
    items = get_new_stories(start_time, end_time)
    sorted_items = _sort_and_cap(items, date_field="System.CreatedDate")
    return [{"id": s["id"], "fields": s.get("fields", {})} for s in sorted_items]


@mcp.tool()
def get_active_work_items(since_time: str) -> list[dict]:
    """Get active User Stories that changed in ADO since a given time.

    Args:
        since_time: Start time in UTC — format 'YYYY-MM-DD HH:MM:SS'

    Returns list of work items with id and fields (Title, State, Priority, AssignedTo, ChangedDate).
    """
    items = get_active_stories_changed_since(since_time)
    sorted_items = _sort_and_cap(items, date_field="System.ChangedDate")
    return [{"id": s["id"], "fields": s.get("fields", {})} for s in sorted_items]


@mcp.tool()
def get_work_item_comments(work_item_id: int, since_time: str) -> list[dict]:
    """Get new comments on a specific ADO work item since a given time.

    Args:
        work_item_id: The ADO work item ID (integer)
        since_time:   Filter comments from this time in UTC — format 'YYYY-MM-DD HH:MM:SS'

    Returns list of comment objects with createdDate, createdBy, and text (HTML stripped).
    """
    from html.parser import HTMLParser

    class _Strip(HTMLParser):
        def __init__(self):
            super().__init__()
            self._parts = []
        def handle_data(self, data):
            self._parts.append(data)

    def strip_html(html: str) -> str:
        p = _Strip()
        p.feed(html)
        return " ".join("".join(p._parts).split())

    results = get_recent_comments([work_item_id], since_time)
    comments = results.get(work_item_id, [])
    return [
        {
            "createdDate": c.get("createdDate", ""),
            "author": c.get("createdBy", {}).get("displayName", "?"),
            "text": strip_html(c.get("text", "")),
        }
        for c in comments
    ]


@mcp.tool()
def get_work_items_by_ids(ids: list[int]) -> list[dict]:
    """Get full details for a list of ADO work item IDs (batch, max 200).

    Args:
        ids: List of ADO work item IDs

    Returns list of work items with id and fields.
    """
    items = _get_items_by_ids(ids)
    return [{"id": s["id"], "fields": s.get("fields", {})} for s in items]


if __name__ == "__main__":
    import uvicorn
    app = mcp.http_app()
    app.add_middleware(BearerAuth)
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
