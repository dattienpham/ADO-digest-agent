"""
ADO client tests — require a real PAT to run.
Skip by default; run manually with: pytest tests/test_ado_client.py -s
"""
import pytest
import os


@pytest.mark.skipif(not os.environ.get("ADO_PAT"), reason="ADO_PAT not set")
def test_get_new_stories_returns_list():
    from agent.ado_client import get_new_stories
    stories = get_new_stories("2026-01-01T00:00:00Z", "2026-12-31T00:00:00Z")
    assert isinstance(stories, list)


@pytest.mark.skipif(not os.environ.get("ADO_PAT"), reason="ADO_PAT not set")
def test_stories_have_required_fields():
    from agent.ado_client import get_new_stories
    stories = get_new_stories("2026-01-01T00:00:00Z", "2026-12-31T00:00:00Z")
    if stories:
        f = stories[0]["fields"]
        assert "System.Title" in f
        assert "System.State" in f
