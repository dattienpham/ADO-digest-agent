from datetime import datetime, timedelta
import pytz
from config import MAX_STORIES, MAX_COMMENT_STORIES

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


def get_lookback_window(run_time: datetime) -> tuple[datetime, datetime]:
    """
    9AM run  → window: 1PM yesterday → 9AM today
    1PM run  → window: 9AM today    → 1PM today
    """
    local = run_time.astimezone(VN_TZ)
    hour = local.hour

    if hour == 9:
        end = local.replace(hour=9, minute=0, second=0, microsecond=0)
        # Monday 9AM: look back to Friday 1PM (skip weekend)
        days_back = 3 if local.weekday() == 0 else 1
        prev_day = local - timedelta(days=days_back)
        start = prev_day.replace(hour=13, minute=0, second=0, microsecond=0)
    elif hour == 13:
        end = local.replace(hour=13, minute=0, second=0, microsecond=0)
        start = local.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        # Fallback for manual/test runs: use last 4 hours
        end = local
        start = local - timedelta(hours=4)

    return start.astimezone(pytz.utc), end.astimezone(pytz.utc)


def _priority_key(item: dict) -> tuple:
    p = item["fields"].get("Microsoft.VSTS.Common.Priority") or 4
    changed = item["fields"].get("System.ChangedDate", "")
    return (int(p), changed)


def apply_volume_rules(
    new_stories: list[dict],
    comments_map: dict[int, list],
    story_map: dict[int, dict],
) -> dict:
    sorted_stories = sorted(new_stories, key=_priority_key)

    # Sort stories with comments by priority
    comment_items = list(comments_map.items())
    comment_items.sort(key=lambda x: _priority_key(
        story_map.get(x[0], {"fields": {"Microsoft.VSTS.Common.Priority": 4, "System.ChangedDate": ""}})
    ))

    return {
        "new_stories": sorted_stories[:MAX_STORIES],
        "new_stories_overflow": max(0, len(sorted_stories) - MAX_STORIES),
        "comments": dict(comment_items[:MAX_COMMENT_STORIES]),
        "comments_overflow": max(0, len(comment_items) - MAX_COMMENT_STORIES),
        "story_map": story_map,
    }
