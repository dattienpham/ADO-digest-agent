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
        {"id": 1, "title": "Fix bug", "assignedTo": "Dat", "createdDate": "2026-06-09 09:00:00",
         "url": "https://dev.azure.com/org/proj/_workitems/edit/1"}
    ]}]
    card = build_card_from_sections("Title", sections)
    texts = " ".join(b.get("text", "") for b in card["body"])
    assert "Fix bug" in texts
    assert "#1" in texts
    assert "Dat" in texts
    assert "2026-06-09 09:00:00" in texts


def test_tickets_url_rendered_as_link():
    sections = [{"type": "tickets", "data": [
        {"id": 7, "title": "T", "url": "https://example.com/7"}
    ]}]
    card = build_card_from_sections("Title", sections)
    texts = " ".join(b.get("text", "") for b in card["body"])
    assert "[#7](https://example.com/7)" in texts


def test_tickets_no_url_fallback():
    sections = [{"type": "tickets", "data": [{"id": 3, "title": "T"}]}]
    card = build_card_from_sections("Title", sections)
    texts = " ".join(b.get("text", "") for b in card["body"])
    assert "#3" in texts
    assert "http" not in texts


def test_comments_section_rendered():
    sections = [{"type": "comments", "data": [
        {"storyId": 5, "storyTitle": "Auth story", "author": "Nam", "text": "LGTM",
         "date": "2026-06-09 08:00:00", "storyUrl": "https://dev.azure.com/org/proj/_workitems/edit/5"}
    ]}]
    card = build_card_from_sections("Title", sections)
    texts = " ".join(b.get("text", "") for b in card["body"])
    assert "Nam" in texts
    assert "LGTM" in texts
    assert "2026-06-09 08:00:00" in texts
    assert "[#5]" in texts


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
    summary_idx = next((i for i, t in enumerate(texts) if "Summary first" in t), None)
    ticket_idx = next((i for i, t in enumerate(texts) if "#1" in t), None)
    assert summary_idx is not None, "Summary block not found"
    assert ticket_idx is not None, "Ticket block not found"
    assert summary_idx < ticket_idx


def test_unknown_section_type_skipped():
    sections = [{"type": "bogus_type", "data": [1, 2, 3]}]
    card = build_card_from_sections("Title", sections)
    texts = [b.get("text", "") for b in card["body"]]
    assert any("Không có cập nhật" in t for t in texts)
