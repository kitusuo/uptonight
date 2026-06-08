"""Unit tests for the observing-window cap (`_cap_window`)."""

import pytest
from astropy import units as u
from astropy.time import Time

from uptonight.uptonight import _cap_window

NOON = Time("2020-12-21T12:00:00", scale="utc")


def test_no_cap_when_max_hours_is_none():
    start, end = NOON, NOON + 24 * u.hour

    result_start, result_end = _cap_window(start, end, None)

    assert result_start is start
    assert result_end is end


def test_no_cap_when_window_is_within_the_limit():
    start, end = NOON, NOON + 6 * u.hour

    result_start, result_end = _cap_window(start, end, 8)

    assert result_start is start
    assert result_end is end


def test_window_exactly_at_the_limit_is_not_capped():
    start, end = NOON, NOON + 8 * u.hour

    result_start, result_end = _cap_window(start, end, 8)

    assert result_start is start
    assert result_end is end


def test_window_longer_than_the_limit_is_capped_to_max_hours():
    start, end = NOON, NOON + 24 * u.hour

    result_start, result_end = _cap_window(start, end, 8)

    assert (result_end - result_start).to(u.hour).value == pytest.approx(8)


def test_capped_window_is_centred_on_the_window_midpoint():
    start, end = NOON, NOON + 24 * u.hour  # midpoint is NOON + 12h
    midpoint = start + 12 * u.hour

    result_start, result_end = _cap_window(start, end, 8)

    assert (result_start - (midpoint - 4 * u.hour)).to(u.second).value == pytest.approx(0, abs=1e-3)
    assert (result_end - (midpoint + 4 * u.hour)).to(u.second).value == pytest.approx(0, abs=1e-3)
