"""Sun rise/set handling at the extremes that the high-latitude fixes target."""

from uptonight.sunmoon import SunMoon


def test_no_darkness_leaves_civil_twilight_times_unset(make_observer):
    # When the Sun never crosses the civil horizon there is no civil dusk/dawn;
    # the short civil times must be the None sentinel rather than a crash.
    observer = make_observer(latitude=61.5, longitude=23.48, tz="Europe/Helsinki")

    sun_moon = SunMoon(observer, observation_date="06/21/20", utcoffset=3)

    assert sun_moon.sun_next_setting_civil_short() is None
    assert sun_moon.sun_next_rising_civil_short() is None


def test_normal_night_sun_sets_before_it_rises(make_observer):
    observer = make_observer(latitude=48.14)

    sun_moon = SunMoon(observer, observation_date="06/03/20", utcoffset=2)

    assert sun_moon.sun_next_setting() < sun_moon.sun_next_rising()


def test_unrelated_warning_does_not_break_darkness_classification(make_observer, monkeypatch):
    # Only astroplan's TargetAlwaysUp/NeverUp warnings may steer the darkness
    # cascade. Any other warning raised while computing the sunset (e.g. from a
    # dependency) used to skip every branch, leaving darkness "" and the
    # placeholder sunrise, which then crashed building the time range.
    import warnings

    from astropy import units as u

    observer = make_observer(latitude=48.14)
    original = observer.sun_set_time

    def noisy_sun_set_time(*args, **kwargs):
        warnings.warn("unrelated dependency warning", UserWarning)
        return original(*args, **kwargs)

    monkeypatch.setattr(observer, "sun_set_time", noisy_sun_set_time)

    sun_moon = SunMoon(observer, observation_date="12/15/25", utcoffset=1)

    assert sun_moon.darkness() == "astronomical"
    assert sun_moon.sun_next_setting() < sun_moon.sun_next_rising()
    assert sun_moon.sun_next_rising() - sun_moon.sun_next_setting() < 1 * u.day
