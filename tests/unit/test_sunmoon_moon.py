"""Moon rise/set handling, including the masked (no-event) sentinel."""

import re

from uptonight.sunmoon import SunMoon

# Short rise/set strings are formatted as "%m/%d %H:%M".
SHORT_FORMAT = re.compile(r"\d{2}/\d{2} \d{2}:\d{2}")


def test_circumpolar_moon_has_no_rise_or_set_time(make_observer):
    # At 85N the Moon stays above (or below) the horizon for the whole day, so
    # astroplan returns a masked time which must surface as the None sentinel.
    observer = make_observer(latitude=85.0)

    sun_moon = SunMoon(observer, observation_date="01/10/20", utcoffset=2)

    assert sun_moon.moon_next_rising_short() is None
    assert sun_moon.moon_next_setting_short() is None


def test_moon_rise_and_set_are_formatted_when_the_moon_crosses_the_horizon(make_observer):
    observer = make_observer(latitude=48.14)

    sun_moon = SunMoon(observer, observation_date="06/03/20", utcoffset=2)

    assert SHORT_FORMAT.fullmatch(sun_moon.moon_next_rising_short())
    assert SHORT_FORMAT.fullmatch(sun_moon.moon_next_setting_short())


def test_moon_illumination_is_a_percentage(make_observer):
    observer = make_observer(latitude=48.14)

    sun_moon = SunMoon(observer, observation_date="06/03/20", utcoffset=2)

    assert 0 <= sun_moon.moon_illumination() <= 100
