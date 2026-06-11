import pytest
from datetime import datetime
import pytz
from agent.data_processor import get_lookback_window

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


def vn(y, mo, d, h, mi=0):
    return VN_TZ.localize(datetime(y, mo, d, h, mi)).astimezone(pytz.utc)


def test_9am_window():
    run = vn(2026, 6, 2, 9)
    start, end = get_lookback_window(run)
    assert start == vn(2026, 6, 1, 13)
    assert end == vn(2026, 6, 2, 9)


def test_1pm_window():
    run = vn(2026, 6, 2, 13)
    start, end = get_lookback_window(run)
    assert start == vn(2026, 6, 2, 9)
    assert end == vn(2026, 6, 2, 13)


def test_window_returns_utc():
    run = vn(2026, 6, 2, 9)
    start, end = get_lookback_window(run)
    assert start.tzinfo is not None
    assert end.tzinfo is not None


def test_monday_9am_window():
    # 2026-06-08 is a Monday — should look back to Friday (2026-06-05) 1PM
    run = vn(2026, 6, 8, 9)
    start, end = get_lookback_window(run)
    assert start == vn(2026, 6, 5, 13)
    assert end == vn(2026, 6, 8, 9)
