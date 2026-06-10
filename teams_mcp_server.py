"""
Teams MCP Server — sends digest cards to Microsoft Teams.

Run (streamable HTTP, for AIQ platform):
    fastmcp run teams_mcp_server.py --transport streamable-http --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

from typing import Annotated, Literal

from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from starlette.middleware import Middleware
from fastmcp import FastMCP
from agent.auth import BearerAuth
from agent.card_builder import build_card_from_sections
from agent.teams_sender import send_to_teams

mcp = FastMCP(
    name="Teams Connector",
    instructions=(
        "Sends formatted digest cards to a Microsoft Teams channel. "
        "Call send_digest with a title and an ordered list of sections."
    ),
)


mcp.add_middleware(Middleware(BearerAuth))


class TicketItem(BaseModel):
    id: int
    title: str
    assignedTo: str = "Chưa assign"
    createdDate: str = ""
    url: str = ""
    state: str = "—"
    priority: int | None = None


class CommentItem(BaseModel):
    storyId: int
    storyTitle: str
    author: str
    text: str
    date: str = ""
    storyUrl: str = ""


class HighlightItem(BaseModel):
    id: int
    title: str
    reason: str
    url: str = ""


class SummaryData(BaseModel):
    text: str


class TicketsSection(BaseModel):
    type: Literal["tickets"]
    data: list[TicketItem]


class CommentsSection(BaseModel):
    type: Literal["comments"]
    data: list[CommentItem]


class HighlightsSection(BaseModel):
    type: Literal["highlights"]
    data: list[HighlightItem]


class SummarySection(BaseModel):
    type: Literal["summary"]
    data: SummaryData


Section = Annotated[
    TicketsSection | CommentsSection | HighlightsSection | SummarySection,
    Field(discriminator="type"),
]

_section_ta: TypeAdapter = TypeAdapter(list[Section])


@mcp.tool()
def send_digest(title: str, sections: list[Section]) -> str:
    """Send a formatted Adaptive Card digest to the configured Teams channel.

    Args:
        title: Card header, e.g. "ADO Digest · 9AM–1PM · 09/06/2026"
        sections: Ordered list of sections. Supported types:

          Tickets (list of work items):
            {"type": "tickets", "data": [{"id": 1, "title": "Fix bug", "assignedTo": "Nam", "createdDate": "2026-06-09 09:00:00", "url": "https://dev.azure.com/org/project/_workitems/edit/1", "state": "Active", "priority": 1}]}

          Comments (grouped by story):
            {"type": "comments", "data": [{"storyId": 1, "storyTitle": "Fix bug", "author": "Nam", "text": "LGTM", "date": "2026-06-09 09:00:00", "storyUrl": "https://dev.azure.com/org/project/_workitems/edit/1"}]}

          Highlights (items needing attention):
            {"type": "highlights", "data": [{"id": 1, "title": "API down", "reason": "Priority 1 chưa assign", "url": "https://dev.azure.com/org/project/_workitems/edit/1"}]}

          Summary (AI-generated text):
            {"type": "summary", "data": {"text": "• 3 tickets mới\n• 1 cần chú ý"}}

          Sections with empty data are skipped automatically.
          Dates should be formatted as "YYYY-MM-DD HH:MM:SS" in UTC+7.

    Returns "OK" on success; raises ValueError for invalid sections,
    propagates errors from the Teams sender on delivery failure.
    """
    try:
        parsed = _section_ta.validate_python(sections)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    sections_dict = [s.model_dump() for s in parsed]
    card = build_card_from_sections(title, sections_dict)
    send_to_teams(card)
    return "OK"


if __name__ == "__main__":
    mcp.run()
