import pytest
from unittest.mock import patch
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
