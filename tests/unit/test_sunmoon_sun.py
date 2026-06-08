"""Sun rise/set handling at the extremes that the high-latitude fixes target."""

from uptonight.sunmoon import SunMoon


def test_no_darkness_leaves_civil_twilight_times_unset(make_observer):
    # When the Sun never crosses the civil horizon there is no civil dusk/dawn;
    # the short civil times must be the None sentinel rather than a crash.
    observer = make_observer(latitude=61.5, longitude=23.48, tz="Europe/Helsinki")

    sun_moon = SunMoon(observer, observation_date="06/21/20", utcoffset=3)

    assert sun_moon.sun_next_setting_civil_short() is None
    assert sun_moon.sun_next_rising_civil_short() is None


def test_normal_night_exposes_sun_set_and_rise(make_observer):
    observer = make_observer(latitude=48.14)

    sun_moon = SunMoon(observer, observation_date="06/03/20", utcoffset=2)

    assert sun_moon.sun_next_setting() is not None
    assert sun_moon.sun_next_rising() is not None


def test_midnight_sun_does_not_raise_and_reports_no_darkness(make_observer):
    # Regression guard for the astroplan tonight() crash at the civil horizon.
    observer = make_observer(latitude=61.5, longitude=23.48, tz="Europe/Helsinki")

    sun_moon = SunMoon(observer, observation_date="06/21/20", utcoffset=3)

    assert sun_moon.is_dark() is False
