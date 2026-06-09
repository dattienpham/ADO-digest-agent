import traceback
from datetime import datetime

from agent.data_processor import get_lookback_window, apply_volume_rules
from agent.ado_client import get_new_stories, get_active_stories_changed_since, get_recent_comments
from agent.ai_summary import generate_summary
from agent.card_builder import build_adaptive_card
from agent.teams_sender import send_to_teams, send_error_card


def orchestrate(run_time: datetime):
    try:
        # Step 1: Lookback window
        start, end = get_lookback_window(run_time)
        print(f"[orchestrate] Window: {start.isoformat()} → {end.isoformat()}")

        # Step 2: Query ADO
        # WIQL requires 'YYYY-MM-DD HH:MM:SS' format, not ISO 8601 with T/Z
        start_iso = start.strftime("%Y-%m-%d %H:%M:%S")
        end_iso = end.strftime("%Y-%m-%d %H:%M:%S")

        new_stories = get_new_stories(start_iso, end_iso)
        active_stories = get_active_stories_changed_since(start_iso)
        comments_map = get_recent_comments(
            [s["id"] for s in active_stories],
            start_iso
        )

        print(f"[orchestrate] new_stories={len(new_stories)}, active_stories={len(active_stories)}, stories_with_comments={len(comments_map)}")

        # Step 3: Process + volume rules
        story_map = {s["id"]: s for s in active_stories + new_stories}
        processed = apply_volume_rules(new_stories, comments_map, story_map)

        # Step 4: AI Summary
        ai_summary = generate_summary(processed)

        # Step 5: Build card
        card = build_adaptive_card(run_time, start, end, processed, ai_summary)

        # Step 6: Send
        send_to_teams(card)
        print("[orchestrate] Done.")

    except Exception as e:
        print(f"[orchestrate] FATAL ERROR: {e}")
        traceback.print_exc()
        send_error_card(str(e))
