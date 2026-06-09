"""
Teams MCP Server — sends digest cards to Microsoft Teams.

Run (HTTP/SSE, for AIQ platform):
    fastmcp run teams_mcp_server.py --transport sse --host 0.0.0.0 --port 8001
"""
from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from agent.card_builder import build_card_from_sections
from agent.teams_sender import send_to_teams

mcp = FastMCP(
    name="Teams Connector",
    instructions=(
        "Sends formatted digest cards to a Microsoft Teams channel. "
        "Call send_digest with a title and an ordered list of sections."
    ),
)


@mcp.tool()
def send_digest(title: str, sections: list[dict]) -> str:
    """Send a formatted Adaptive Card digest to the configured Teams channel.

    Args:
        title: Card header, e.g. "ADO Digest · 9AM–1PM · 09/06/2026"
        sections: Ordered list of sections. Each section is
                  {"type": "tickets"|"comments"|"summary"|"highlights", "data": [...]}
                  Sections with empty data are skipped automatically.

    Returns "OK" on success, raises RuntimeError on failure.
    """
    card = build_card_from_sections(title, sections)
    send_to_teams(card)
    return "OK"


if __name__ == "__main__":
    mcp.run()
