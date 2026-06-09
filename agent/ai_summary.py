import anthropic
from config import ANTHROPIC_API_KEY

SYSTEM_PROMPT = """Bạn là assistant tóm tắt hoạt động ADO cho Manager của team HR.
Nhiệm vụ: đọc danh sách updates và tạo 3-5 bullet points ngắn, bằng tiếng Việt.
Chỉ highlight items thuộc ít nhất 1 tiêu chí: Priority 1/2, overdue, blocked, chưa assign >1 ngày.
Nếu không có item nào urgent, ghi: "Không có điểm cần chú ý đặc biệt trong kỳ này".
Giữ mỗi bullet dưới 15 từ. Không thêm tiêu đề hay giải thích.
Dùng prefix: ⚠️ priority cao · 🔴 overdue · 🚫 blocked · 👤 chưa assign"""


def generate_summary(processed: dict) -> str | None:
    if not ANTHROPIC_API_KEY:
        return None

    lines = []
    story_map = processed.get("story_map", {})

    for s in processed.get("new_stories", []):
        f = s["fields"]
        assignee = f.get("System.AssignedTo")
        assignee_name = assignee.get("displayName", "UNASSIGNED") if assignee else "UNASSIGNED"
        lines.append(
            f"[ADO-{s['id']}] {f.get('System.Title', '')} | "
            f"priority={f.get('Microsoft.VSTS.Common.Priority', 4)} | "
            f"state={f.get('System.State', '')} | "
            f"assignee={assignee_name} | "
            f"created={f.get('System.CreatedDate', '')} | "
            f"dueDate={f.get('Microsoft.VSTS.Scheduling.TargetDate', '')}"
        )

    for wid, cmts in processed.get("comments", {}).items():
        story = story_map.get(wid, {})
        title = story.get("fields", {}).get("System.Title", "")
        for c in cmts:
            text = c.get("text", "")[:200]
            lines.append(f"[ADO-{wid}] {title} | comment: {text}")

    if not lines:
        return None

    user_content = "Danh sách updates trong kỳ:\n" + "\n".join(lines)

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        print(f"[ai_summary] Claude API error: {e}")
        return None
