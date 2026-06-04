from datetime import time

import pytest

from alarm_clock.timeparse import TimeParseError, format_time, parse_time


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("00:00", time(0, 0)),
        ("23:59", time(23, 59)),
        ("9:05", time(9, 5)),
        ("14:30", time(14, 30)),
        ("12:00 AM", time(0, 0)),
        ("12:00 PM", time(12, 0)),
        ("1:00 PM", time(13, 0)),
        ("11:59 pm", time(23, 59)),
        ("7:45 am", time(7, 45)),
        ("  08:00  ", time(8, 0)),
    ],
)
def test_parse_valid(raw, expected):
    assert parse_time(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "24:00",
        "12:60",
        "abc",
        "25:00",
        "-1:00",
        "13:00 PM",
        "0:00 AM",
        "noon",
        "7",
        "7:5",
    ],
)
def test_parse_invalid(raw):
    with pytest.raises(TimeParseError):
        parse_time(raw)


def test_format_time_zero_pads():
    assert format_time(time(7, 5)) == "07:05"
    assert format_time(time(0, 0)) == "00:00"
    assert format_time(time(23, 59)) == "23:59"
