import json
import time
import requests
from config import TEAMS_FLOW_URL


def send_to_teams(card: dict, retries: int = 3):
    if not TEAMS_FLOW_URL:
        raise ValueError("TEAMS_FLOW_URL is not configured")
    # Power Automate expects the card as a serialized JSON string, not an object.
    payload = {"card": json.dumps(card)}
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(TEAMS_FLOW_URL, json=payload, timeout=15)
            if resp.status_code in (200, 202):
                print(f"[teams_sender] Card sent (attempt {attempt})")
                return
            print(f"[teams_sender] Attempt {attempt} failed: HTTP {resp.status_code} — {resp.text[:200]}")
        except requests.exceptions.RequestException as e:
            print(f"[teams_sender] Attempt {attempt} exception: {e}")

        if attempt < retries:
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Failed to send card after {retries} attempts")


def send_error_card(error_msg: str):
    card = {
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": "⚠️ ADO Digest Agent — Lỗi", "weight": "Bolder", "color": "Attention"},
            {"type": "TextBlock", "text": error_msg[:500], "wrap": True},
        ],
    }
    try:
        send_to_teams(card, retries=1)
    except Exception as exc:
        print(f"[teams_sender] send_error_card failed: {exc}")
