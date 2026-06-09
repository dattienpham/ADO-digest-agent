# Teams MCP Connector — Design Spec
**Date:** 2026-06-09  
**Status:** Approved  
**Scope:** Teams MCP Connector + AIQ agent system prompt for manual chat-triggered digest

---

## Context

The ADO MCP Connector already exists (`mcp_server.py`) and exposes 4 tools for fetching work items and comments from Azure DevOps. The remaining piece is a Teams MCP Connector that the AIQ agent can call to send a formatted digest card to a Teams channel, triggered manually when a user chats with the agent.

---

## Architecture

```
User chats with AIQ agent
        │
        ▼
AIQ Agent
    ├── Parse time range (natural language + specific time → UTC)
    ├── Call ADO MCP Connector tools (existing)
    │     ├── get_new_work_items(start_time, end_time)
    │     ├── get_active_work_items(since_time)
    │     └── get_work_item_comments(work_item_id, since_time)
    ├── Decide which sections to include
    └── Call Teams MCP Connector
          └── send_digest(title, sections[])
                    │
                    ▼
              Build Adaptive Card from sections
                    │
                    ▼
              POST Teams Webhook → Card appears in channel
```

---

## Component 1: Teams MCP Connector (`teams_mcp_server.py`)

Single tool exposed to AIQ agent:

```python
send_digest(title: str, sections: list[dict]) -> str
```

### Section Schema

Each section is `{"type": <type>, "data": <data>}`.

**`tickets`**
```json
{
  "type": "tickets",
  "data": [
    {"id": 123, "title": "Fix login bug", "state": "Active", "priority": 1, "assignedTo": "Dat Pham"}
  ]
}
```

**`comments`**
```json
{
  "type": "comments",
  "data": [
    {"storyId": 123, "storyTitle": "Fix login bug", "author": "Nam Le", "text": "Done reviewing", "date": "2026-06-09T08:30:00Z"}
  ]
}
```

**`summary`**
```json
{
  "type": "summary",
  "data": {"text": "• 3 tickets mới\n• 1 ticket chưa assign"}
}
```

**`highlights`**
```json
{
  "type": "highlights",
  "data": [
    {"id": 456, "title": "API timeout", "reason": "Priority 1 chưa assign"}
  ]
}
```

### Card Builder Logic

- Each section type maps to a dedicated Adaptive Card block renderer
- Sections are rendered in the order provided by the agent
- Sections with empty `data` are skipped — no empty blocks rendered
- Final card is assembled and sent via existing `teams_sender.send_to_teams()`
- Returns `"OK"` on success, raises on failure (agent reports error to user)

### Card Layout per Section Type

| Type | Rendering |
|---|---|
| `tickets` | List with ID, title, state badge, priority badge, assignee |
| `comments` | Grouped by story — author + text + date |
| `summary` | Multi-line TextBlock, teal accent |
| `highlights` | ⚠️ block per item with reason |

### Teams Channel

Fixed — configured via `TEAMS_WEBHOOK_URL` in `.env`. Not exposed as a parameter.

---

## Component 2: Agent System Prompt

```
Bạn là ADO Digest Agent. Khi user yêu cầu gửi digest:

1. PARSE THỜI GIAN
   - Hiểu cả tiếng Việt tự nhiên và giờ cụ thể (UTC+7)
   - "sáng nay" → 00:00–09:00 UTC+7 hôm nay
   - "chiều nay" → 09:00–13:00 UTC+7 hôm nay
   - "2 tiếng trước" → now-2h đến now
   - "từ 10h đến 14h" → parse trực tiếp
   - Luôn convert sang UTC trước khi gọi tools (9AM UTC+7 = 02:00 UTC)

2. GỌI ADO TOOLS (theo thứ tự)
   - get_new_work_items(start_time, end_time)
   - get_active_work_items(since_time=start_time)
   - get_work_item_comments(id, since_time=start_time) cho mỗi story

3. QUYẾT ĐỊNH SECTIONS
   - Mặc định: gửi tất cả 4 sections
   - User nói "chỉ tickets" → chỉ include tickets
   - User nói "không cần summary" → bỏ summary
   - highlights: tự phát hiện priority 1 hoặc chưa assign > 1 ngày trong data đã lấy
   - Chỉ include section khi có data — không gửi section trống

4. GỌI send_digest
   - title format: "ADO Digest · {window} · {date}"
   - sections: list theo thứ tự [highlights, tickets, comments, summary]
   - Nếu không có data gì → báo user, không gọi send_digest

5. SAU KHI GỬI
   - Báo user kết quả ngắn gọn: số tickets, comments, có highlight không
   - Nếu lỗi → báo lỗi rõ ràng
```

---

## Data Flow Example

```
User: "gửi digest từ 9h sáng đến giờ"

Agent:
  1. Parse → start="2026-06-09 02:00:00" UTC, end="2026-06-09 09:30:00" UTC
  2. get_new_work_items("2026-06-09 02:00:00", "2026-06-09 09:30:00") → 3 items
  3. get_active_work_items("2026-06-09 02:00:00") → 7 items
  4. get_work_item_comments(id, "2026-06-09 02:00:00") × 3 stories → comments
  5. Build sections:
     - highlights: [item #456 priority 1 chưa assign]
     - tickets: [3 new + 7 active, deduped]
     - comments: [comments from 3 stories]
     - summary: "• 10 tickets active..."
  6. send_digest("ADO Digest · 9AM–11:30AM · 09/06/2026", sections)

Agent: "Đã gửi digest lên Teams — 10 tickets, 3 có comment, 1 highlight (priority 1 chưa assign)."
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| ADO tool trả về empty | Báo user "Không có dữ liệu trong khoảng thời gian này" |
| Teams POST thất bại | Connector retry ×3, nếu vẫn lỗi raise → agent báo user |
| User nhắn thời gian không rõ | Agent hỏi lại trước khi gọi tools |
| Section có data = [] | Bỏ qua, không render block trống |

---

## Files Affected

| File | Action |
|---|---|
| `teams_mcp_server.py` | Tạo mới — FastMCP server với `send_digest` tool |
| `agent/card_builder.py` | Tạo mới — build Adaptive Card từ sections |
| `mcp_server.py` | Không thay đổi |
| `agent/teams_sender.py` | Không thay đổi — tái sử dụng |
| `.env.example` | Thêm `TEAMS_WEBHOOK_URL` nếu chưa có |

---

## Out of Scope

- Multiple Teams channels
- Scheduling / auto-trigger (handled separately when AIQ Schedules ships)
- Authentication beyond PAT + Webhook URL
