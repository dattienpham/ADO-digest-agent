import logging
from datetime import datetime
from html.parser import HTMLParser
import pytz

_log = logging.getLogger(__name__)


class _StripHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)


def _strip_html(html: str) -> str:
    p = _StripHTML()
    p.feed(html)
    return " ".join("".join(p._parts).split())

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


def _item_url(wid: int) -> str:
    from config import ADO_BASE_URL  # lazy import — avoids mandatory env var at module load
    return f"{ADO_BASE_URL}/_workitems/edit/{wid}"


def _tb(text: str, weight: str = None, size: str = None, spacing: str = None, subtle: bool = False, color: str = None) -> dict:
    block = {"type": "TextBlock", "text": text, "wrap": True}
    if weight:
        block["weight"] = weight
    if size:
        block["size"] = size
    if spacing:
        block["spacing"] = spacing
    if subtle:
        block["isSubtle"] = True
    if color:
        block["color"] = color
    return block


def _fmt_time(iso_str: str) -> str:
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso_str[:19]


def build_adaptive_card(
    run_time: datetime,
    window_start: datetime,
    window_end: datetime,
    processed: dict,
    ai_summary: str | None,
) -> dict:
    local = run_time.astimezone(VN_TZ)
    period = "Sáng" if local.hour < 13 else "Chiều"
    date_str = local.strftime("%d/%m/%Y")
    time_str = local.strftime("%H:%M")
    ws_str = window_start.astimezone(VN_TZ).strftime("%d/%m %H:%M")
    we_str = window_end.astimezone(VN_TZ).strftime("%d/%m %H:%M")

    n_stories = len(processed["new_stories"])
    n_comments = sum(len(v) for v in processed["comments"].values())

    body = [
        _tb(f"📋 ADO Daily Digest — {period} · {date_str}", weight="Bolder", size="Medium"),
        _tb(f"{time_str} · Kỳ: {ws_str} → {we_str}", subtle=True, spacing="None"),
        _tb(f"🆕 {n_stories} ticket mới  ·  💬 {n_comments} comments mới", spacing="Small"),
    ]

    # Section: Comments mới
    if processed["comments"]:
        body.append(_tb("💬 Comment mới", weight="Bolder", spacing="Medium"))
        story_map = processed.get("story_map", {})
        for wid, cmts in processed["comments"].items():
            story = story_map.get(wid, {})
            title = story.get("fields", {}).get("System.Title", f"ADO-{wid}")
            assignee_obj = story.get("fields", {}).get("System.AssignedTo")
            assignee = assignee_obj.get("displayName", "Chưa assign") if assignee_obj else "Chưa assign"
            for c in cmts:
                author_obj = c.get("createdBy", {})
                author = author_obj.get("displayName", "?") if author_obj else "?"
                ts = _fmt_time(c.get("createdDate", ""))
                text = _strip_html(c.get("text", ""))
                body.append(_tb(
                    f"[ADO-{wid}]({_item_url(wid)}) - {title} - **{assignee}**",
                    spacing="Small",
                ))
                body.append(_tb(ts, subtle=True, spacing="None"))
                body.append(_tb(text, spacing="None"))
        if processed["comments_overflow"] > 0:
            body.append(_tb(
                f"_và {processed['comments_overflow']} comments khác..._",
                subtle=True, spacing="None",
            ))

    # Section: Ticket mới
    if processed["new_stories"]:
        body.append(_tb("🆕 Ticket mới", weight="Bolder", spacing="Medium"))
        for s in processed["new_stories"]:
            f = s["fields"]
            wid = s["id"]
            assignee_obj = f.get("System.AssignedTo")
            assignee = assignee_obj.get("displayName", "Chưa assign") if assignee_obj else "Chưa assign"
            title = f.get("System.Title", "")
            ts = _fmt_time(f.get("System.CreatedDate", ""))
            body.append(_tb(
                f"[ADO-{wid}]({_item_url(wid)}) - {title} - **{assignee}**",
                spacing="Small",
            ))
            body.append(_tb(ts, subtle=True, spacing="None"))
        if processed["new_stories_overflow"] > 0:
            body.append(_tb(
                f"_và {processed['new_stories_overflow']} tickets khác..._",
                subtle=True, spacing="None",
            ))

    # Section: AI Summary
    body.append(_tb("🤖 Tóm tắt", weight="Bolder", spacing="Medium"))
    if ai_summary:
        body.append(_tb(ai_summary, spacing="Small", color="Good"))
    else:
        body.append(_tb("Tóm tắt AI không khả dụng", spacing="Small", color="Warning"))

    # Empty state
    if n_stories == 0 and n_comments == 0:
        body = [
            _tb(f"📋 ADO Daily Digest — {period} · {date_str}", weight="Bolder", size="Medium"),
            _tb(f"{time_str} · Kỳ: {ws_str} → {we_str}", subtle=True, spacing="None"),
            _tb("Không có cập nhật mới trong kỳ này.", spacing="Medium", subtle=True),
        ]

    return {"type": "AdaptiveCard", "version": "1.5", "body": body}


# ---------------------------------------------------------------------------
# New section-based API
# ---------------------------------------------------------------------------


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
    if fn is None:
        _log.warning("Unknown section type %r — skipping", stype)
        return []
    return fn(data)


def _id_link(iid, url: str) -> str:
    return f"[#{iid}]({url})" if url else f"#{iid}"


def _render_highlights(items: list[dict]) -> list[dict]:
    blocks: list[dict] = [
        {"type": "TextBlock", "text": "⚠️ Cần chú ý", "weight": "Bolder", "color": "Warning"},
    ]
    for item in items:
        iid = item.get("id", "?")
        url = item.get("url", "")
        title = item.get("title", "—")
        reason = item.get("reason", "—")
        blocks.append({
            "type": "TextBlock",
            "text": f"• {_id_link(iid, url)} {title} — {reason}",
            "wrap": True,
            "color": "Warning",
        })
    return blocks


def _render_tickets(items: list[dict]) -> list[dict]:
    blocks: list[dict] = [
        {"type": "TextBlock", "text": "🎫 Tickets mới", "weight": "Bolder"},
    ]
    for item in items:
        iid = item.get("id", "?")
        url = item.get("url", "")
        title = item.get("title", "—")
        assignee = item.get("assignedTo") or "Chưa assign"
        created = item.get("createdDate", "")
        blocks.append({
            "type": "TextBlock",
            "text": f"{_id_link(iid, url)} — {title} (**{assignee}**)",
            "wrap": True,
            "size": "Small",
            "spacing": "Small",
        })
        if created:
            blocks.append({
                "type": "TextBlock",
                "text": created,
                "isSubtle": True,
                "size": "Small",
                "spacing": "None",
            })
    return blocks


def _render_comments(items: list[dict]) -> list[dict]:
    blocks: list[dict] = [
        {"type": "TextBlock", "text": "💬 Comments mới", "weight": "Bolder"},
    ]
    for item in items:
        story_id = item.get("storyId", "?")
        story_url = item.get("storyUrl", "")
        story_title = item.get("storyTitle", "—")
        author = item.get("author", "?")
        date = item.get("date", "")
        text = item.get("text", "")
        blocks.append({
            "type": "TextBlock",
            "text": f"{_id_link(story_id, story_url)} — {story_title} · **{author}**",
            "wrap": True,
            "size": "Small",
            "spacing": "Small",
        })
        if date:
            blocks.append({
                "type": "TextBlock",
                "text": date,
                "isSubtle": True,
                "size": "Small",
                "spacing": "None",
            })
        blocks.append({
            "type": "TextBlock",
            "text": f"{author}: {text}",
            "wrap": True,
            "isSubtle": True,
            "size": "Small",
            "spacing": "None",
        })
    return blocks


def _render_summary(data: dict) -> list[dict]:
    return [
        {"type": "TextBlock", "text": "🤖 AI Summary", "weight": "Bolder", "color": "Accent"},
        {"type": "TextBlock", "text": data.get("text", ""), "wrap": True, "size": "Small"},
    ]
