"""Darkness classification across latitudes and seasons.

Dates are in 2020 so they fall within astropy's bundled IERS-B coverage: the
tests stay offline and deterministic (no extrapolation warnings, which would
otherwise leak into ``_sun``'s warning capture). Darkness depends on solar
declination (month/day) and latitude, so the calendar year is immaterial.
"""

import pytest

from uptonight.sunmoon import SunMoon


@pytest.mark.parametrize(
    "latitude, longitude, tz, utcoffset, date, expected",
    [
        (48.14, 11.58, "Europe/Berlin", 2, "06/21/20", "astronomical"),  # mid-latitude summer
        (48.14, 11.58, "Europe/Berlin", 2, "12/21/20", "astronomical"),  # mid-latitude winter
        (52.00, 11.58, "Europe/Berlin", 2, "06/21/20", "nautical"),  # deepest twilight is nautical
        (61.50, 23.48, "Europe/Helsinki", 3, "06/03/20", "civil"),  # deepest twilight is civil
        (61.50, 23.48, "Europe/Helsinki", 3, "06/21/20", "none"),  # midnight sun: no darkness
        (85.00, 11.58, "Europe/Berlin", 2, "12/21/20", "astronomical"),  # deep polar night: dark all day
    ],
)
def test_darkness_is_classified_by_deepest_twilight(make_observer, latitude, longitude, tz, utcoffset, date, expected):
    observer = make_observer(latitude=latitude, longitude=longitude, tz=tz)

    sun_moon = SunMoon(observer, observation_date=date, utcoffset=utcoffset)

    assert sun_moon.darkness() == expected


@pytest.mark.parametrize(
    "latitude, longitude, tz, utcoffset, date, expected_is_dark",
    [
        (61.50, 23.48, "Europe/Helsinki", 3, "06/21/20", False),  # midnight sun: no darkness
        (48.14, 11.58, "Europe/Berlin", 2, "06/21/20", True),  # astronomical darkness
        (85.00, 11.58, "Europe/Berlin", 2, "12/21/20", True),  # polar night is still dark
    ],
)
def test_is_dark_is_false_only_without_any_darkness(
    make_observer, latitude, longitude, tz, utcoffset, date, expected_is_dark
):
    observer = make_observer(latitude=latitude, longitude=longitude, tz=tz)

    sun_moon = SunMoon(observer, observation_date=date, utcoffset=utcoffset)

    assert sun_moon.is_dark() is expected_is_dark
