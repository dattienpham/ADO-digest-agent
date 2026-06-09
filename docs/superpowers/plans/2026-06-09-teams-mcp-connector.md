# Teams MCP Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Teams MCP Connector that the AIQ agent can call with `send_digest(title, sections[])` to send a formatted Adaptive Card to a fixed Teams channel.

**Architecture:** `agent/card_builder.py` renders sections into an Adaptive Card JSON dict. `teams_mcp_server.py` is a FastMCP server that exposes one tool (`send_digest`), calls the card builder, then hands the card to the existing `teams_sender.send_to_teams()`. The AIQ agent controls which sections to include; the connector handles all formatting.

**Tech Stack:** Python 3.11, FastMCP 3.4.0, requests, python-dotenv, pytest

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `agent/card_builder.py` | **Create** | Build Adaptive Card dict from `sections[]` |
| `teams_mcp_server.py` | **Create** | FastMCP server — expose `send_digest` tool |
| `tests/test_card_builder.py` | **Replace** | Tests for new `build_card_from_sections` API (old file references non-existent `build_adaptive_card`) |
| `tests/test_teams_mcp_server.py` | **Create** | Smoke test `send_digest` tool (mock `send_to_teams`) |

> `agent/teams_sender.py`, `config.py`, `.env.example` — no changes needed.

---

## Task 1: Card builder — section renderers

**Files:**
- Create: `agent/card_builder.py`
- Replace: `tests/test_card_builder.py`

- [ ] **Step 1: Replace `tests/test_card_builder.py` with failing tests for the new API**

```python
# tests/test_card_builder.py
import pytest
from agent.card_builder import build_card_from_sections


def test_card_schema():
    card = build_card_from_sections("Test Title", [])
    assert card["type"] == "AdaptiveCard"
    assert card["version"] == "1.5"


def test_card_header_contains_title():
    card = build_card_from_sections("ADO Digest · 9AM", [])
    assert card["body"][0]["text"] == "ADO Digest · 9AM"


def test_empty_sections_shows_no_update():
    card = build_card_from_sections("Title", [])
    texts = [b.get("text", "") for b in card["body"]]
    assert any("Không có cập nhật" in t for t in texts)


def test_tickets_section_rendered():
    sections = [{"type": "tickets", "data": [
        {"id": 1, "title": "Fix bug", "state": "Active", "priority": 1, "assignedTo": "Dat"}
    ]}]
    card = build_card_from_sections("Title", sections)
    texts = " ".join(b.get("text", "") for b in card["body"])
    assert "Fix bug" in texts
    assert "#1" in texts


def test_comments_section_rendered():
    sections = [{"type": "comments", "data": [
        {"storyId": 5, "storyTitle": "Auth story", "author": "Nam", "text": "LGTM", "date": "2026-06-09T08:00:00Z"}
    ]}]
    card = build_card_from_sections("Title", sections)
    texts = " ".join(b.get("text", "") for b in card["body"])
    assert "Nam" in texts
    assert "LGTM" in texts


def test_summary_section_rendered():
    sections = [{"type": "summary", "data": {"text": "• 3 tickets mới"}}]
    card = build_card_from_sections("Title", sections)
    texts = " ".join(b.get("text", "") for b in card["body"])
    assert "3 tickets mới" in texts


def test_highlights_section_rendered():
    sections = [{"type": "highlights", "data": [
        {"id": 9, "title": "API down", "reason": "Priority 1 chưa assign"}
    ]}]
    card = build_card_from_sections("Title", sections)
    texts = " ".join(b.get("text", "") for b in card["body"])
    assert "API down" in texts
    assert "Priority 1" in texts


def test_empty_data_section_skipped():
    sections = [
        {"type": "tickets", "data": []},
        {"type": "summary", "data": {"text": ""}},
    ]
    card = build_card_from_sections("Title", sections)
    texts = " ".join(b.get("text", "") for b in card["body"])
    assert "Ticket" not in texts
    assert "Summary" not in texts
    assert "Không có cập nhật" in texts


def test_section_order_preserved():
    sections = [
        {"type": "summary", "data": {"text": "Summary first"}},
        {"type": "tickets", "data": [{"id": 1, "title": "T", "state": "Active", "priority": 2, "assignedTo": "X"}]},
    ]
    card = build_card_from_sections("Title", sections)
    texts = [b.get("text", "") for b in card["body"]]
    summary_idx = next(i for i, t in enumerate(texts) if "Summary first" in t)
    ticket_idx = next(i for i, t in enumerate(texts) if "#1" in t)
    assert summary_idx < ticket_idx
```

- [ ] **Step 2: Run tests to verify they all fail**

```
cd C:\code\ado-digest-agent
.venv\Scripts\python -m pytest tests/test_card_builder.py -v
```

Expected: `ImportError` — `agent.card_builder` not found.

- [ ] **Step 3: Create `agent/card_builder.py`**

```python
# agent/card_builder.py


def build_card_from_sections(title: str, sections: list[dict]) -> dict:
    body = [
        {
            "type": "TextBlock",
            "text": title,
            "weight": "Bolder",
            "size": "Large",
            "color": "Accent",
            "wrap": True,
        }
    ]

    for section in sections:
        blocks = _render_section(section.get("type"), section.get("data"))
        body.extend(blocks)

    if len(body) == 1:
        body.append({
            "type": "TextBlock",
            "text": "Không có cập nhật trong khoảng thời gian này.",
            "isSubtle": True,
            "wrap": True,
        })

    return {"type": "AdaptiveCard", "version": "1.5", "body": body}


def _render_section(stype: str, data) -> list[dict]:
    if not data:
        return []
    if stype == "summary" and not data.get("text"):
        return []
    renderers = {
        "highlights": _render_highlights,
        "tickets": _render_tickets,
        "comments": _render_comments,
        "summary": _render_summary,
    }
    fn = renderers.get(stype)
    return fn(data) if fn else []


def _render_highlights(items: list[dict]) -> list[dict]:
    blocks: list[dict] = [
        {"type": "TextBlock", "text": "⚠️ Cần chú ý", "weight": "Bolder", "color": "Warning"},
    ]
    for item in items:
        blocks.append({
            "type": "TextBlock",
            "text": f"• #{item['id']} {item['title']} — {item['reason']}",
            "wrap": True,
            "color": "Warning",
        })
    return blocks


def _render_tickets(items: list[dict]) -> list[dict]:
    blocks: list[dict] = [
        {"type": "TextBlock", "text": "🎫 Tickets", "weight": "Bolder"},
    ]
    for item in items:
        p = item.get("priority") or "—"
        state = item.get("state") or "—"
        assignee = item.get("assignedTo") or "Chưa assign"
        blocks.append({
            "type": "TextBlock",
            "text": f"• #{item['id']} {item['title']} · P{p} · {state} · {assignee}",
            "wrap": True,
            "size": "Small",
        })
    return blocks


def _render_comments(items: list[dict]) -> list[dict]:
    blocks: list[dict] = [
        {"type": "TextBlock", "text": "💬 Comments mới", "weight": "Bolder"},
    ]
    for item in items:
        blocks.append({
            "type": "TextBlock",
            "text": f"#{item['storyId']} {item['storyTitle']}",
            "weight": "Bolder",
            "size": "Small",
            "spacing": "Small",
        })
        blocks.append({
            "type": "TextBlock",
            "text": f"{item['author']}: {item['text']}",
            "wrap": True,
            "isSubtle": True,
            "size": "Small",
        })
    return blocks


def _render_summary(data: dict) -> list[dict]:
    return [
        {"type": "TextBlock", "text": "🤖 AI Summary", "weight": "Bolder", "color": "Accent"},
        {"type": "TextBlock", "text": data["text"], "wrap": True, "size": "Small"},
    ]
```

- [ ] **Step 4: Run tests — all should pass**

```
.venv\Scripts\python -m pytest tests/test_card_builder.py -v
```

Expected: 8 tests PASSED.

- [ ] **Step 5: Commit**

```
git add agent/card_builder.py tests/test_card_builder.py
git commit -m "feat: add card_builder with section-based Adaptive Card rendering"
```

---

## Task 2: Teams MCP server

**Files:**
- Create: `teams_mcp_server.py`
- Create: `tests/test_teams_mcp_server.py`

- [ ] **Step 1: Write failing test for `send_digest` tool (mocks `send_to_teams`)**

```python
# tests/test_teams_mcp_server.py
import pytest
from unittest.mock import patch, call
from teams_mcp_server import send_digest


def test_send_digest_returns_ok():
    sections = [{"type": "tickets", "data": [
        {"id": 1, "title": "Bug fix", "state": "Active", "priority": 2, "assignedTo": "Dat"}
    ]}]
    with patch("teams_mcp_server.send_to_teams") as mock_send:
        result = send_digest("ADO Digest · Test", sections)
    assert result == "OK"
    mock_send.assert_called_once()


def test_send_digest_passes_card_to_sender():
    sections = [{"type": "summary", "data": {"text": "• All good"}}]
    with patch("teams_mcp_server.send_to_teams") as mock_send:
        send_digest("Title", sections)
    card = mock_send.call_args[0][0]
    assert card["type"] == "AdaptiveCard"
    texts = " ".join(b.get("text", "") for b in card["body"])
    assert "All good" in texts


def test_send_digest_propagates_sender_error():
    with patch("teams_mcp_server.send_to_teams", side_effect=RuntimeError("webhook failed")):
        with pytest.raises(RuntimeError, match="webhook failed"):
            send_digest("Title", [])
```

- [ ] **Step 2: Run tests to verify they fail**

```
.venv\Scripts\python -m pytest tests/test_teams_mcp_server.py -v
```

Expected: `ImportError` — `teams_mcp_server` not found.

- [ ] **Step 3: Create `teams_mcp_server.py`**

```python
# teams_mcp_server.py
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
```

- [ ] **Step 4: Run tests — all should pass**

```
.venv\Scripts\python -m pytest tests/test_teams_mcp_server.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Run full test suite to check no regressions**

```
.venv\Scripts\python -m pytest -v
```

Expected: all tests PASSED.

- [ ] **Step 6: Commit**

```
git add teams_mcp_server.py tests/test_teams_mcp_server.py
git commit -m "feat: add Teams MCP Connector with send_digest tool"
```

---

## Task 3: Smoke-test the running server

- [ ] **Step 1: Start the Teams MCP server**

In a terminal (requires `TEAMS_WEBHOOK_URL` set in `.env`):

```
.venv\Scripts\fastmcp run teams_mcp_server.py --transport sse --host 0.0.0.0 --port 8001
```

Expected output:
```
Starting MCP server 'Teams Connector' with transport 'sse' on http://127.0.0.1:8001/sse
```

- [ ] **Step 2: Open FastMCP inspector and connect**

In a second terminal:

```
.venv\Scripts\fastmcp dev inspector teams_mcp_server.py
```

In the browser, switch transport to **SSE**, URL `http://localhost:8001/sse`, click Connect.

- [ ] **Step 3: Call `send_digest` from inspector with a test payload**

```json
{
  "title": "ADO Digest · Smoke Test",
  "sections": [
    {
      "type": "highlights",
      "data": [{"id": 999, "title": "Test ticket", "reason": "Smoke test"}]
    },
    {
      "type": "summary",
      "data": {"text": "• Smoke test thành công"}
    }
  ]
}
```

Expected: response `"OK"` and card appears in Teams channel.

- [ ] **Step 4: Add SSE port note to `.env.example`**

Add this comment after the Teams section:

```
# Teams MCP Connector port (run separately from ADO connector on 8000)
# TEAMS_MCP_PORT=8001
```

Edit `.env.example`:

```
# ADO
ADO_PAT=your_personal_access_token_here
ADO_ORG=agentiqai
ADO_PROJECT=AgentIQ

# Teams
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/xxx/IncomingWebhook/yyy/zzz

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Optional overrides
MAX_STORIES=10
MAX_COMMENT_STORIES=10
MAX_COMMENTS_PER_STORY=2

# MCP Connector ports
# ADO connector:   fastmcp run mcp_server.py --transport sse --host 0.0.0.0 --port 8000
# Teams connector: fastmcp run teams_mcp_server.py --transport sse --host 0.0.0.0 --port 8001
```

- [ ] **Step 5: Final commit**

```
git add .env.example
git commit -m "docs: add MCP connector port notes to .env.example"
```
