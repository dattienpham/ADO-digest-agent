import json
import pytest
from unittest.mock import patch, MagicMock
from agent.teams_sender import send_to_teams


SAMPLE_CARD = {
    "type": "AdaptiveCard",
    "version": "1.5",
    "body": [{"type": "TextBlock", "text": "Test"}],
}

FLOW_URL = "https://fake-flow.example.com/trigger"


def _mock_response(status_code):
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = ""
    return mock


@patch("agent.teams_sender.TEAMS_FLOW_URL", FLOW_URL)
@patch("agent.teams_sender.requests.post")
def test_sends_card_as_json_string(mock_post):
    mock_post.return_value = _mock_response(202)
    send_to_teams(SAMPLE_CARD)
    _, kwargs = mock_post.call_args
    body = kwargs["json"]
    assert "card" in body
    parsed = json.loads(body["card"])
    assert parsed["type"] == "AdaptiveCard"


@patch("agent.teams_sender.TEAMS_FLOW_URL", FLOW_URL)
@patch("agent.teams_sender.requests.post")
def test_accepts_202(mock_post):
    mock_post.return_value = _mock_response(202)
    send_to_teams(SAMPLE_CARD)  # must not raise


@patch("agent.teams_sender.TEAMS_FLOW_URL", FLOW_URL)
@patch("agent.teams_sender.requests.post")
def test_accepts_200(mock_post):
    mock_post.return_value = _mock_response(200)
    send_to_teams(SAMPLE_CARD)  # must not raise


@patch("agent.teams_sender.time.sleep")
@patch("agent.teams_sender.TEAMS_FLOW_URL", FLOW_URL)
@patch("agent.teams_sender.requests.post")
def test_raises_after_all_retries_fail(mock_post, mock_sleep):
    mock_post.return_value = _mock_response(500)
    with pytest.raises(RuntimeError, match="Failed to send card after 3 attempts"):
        send_to_teams(SAMPLE_CARD)


@patch("agent.teams_sender.TEAMS_FLOW_URL", FLOW_URL)
@patch("agent.teams_sender.requests.post")
def test_posts_to_flow_url(mock_post):
    mock_post.return_value = _mock_response(202)
    send_to_teams(SAMPLE_CARD)
    url_called = mock_post.call_args[0][0]
    assert url_called == FLOW_URL
