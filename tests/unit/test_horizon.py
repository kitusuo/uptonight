"""UpTonightHorizon: coordinate conversion and plotting."""

import matplotlib.pyplot as plt
import pytest
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time

from uptonight.horizon import UpTonightHorizon

OBS_TIME = Time("2020-06-03T22:00:00")


@pytest.fixture
def horizon_helper(make_observer):
    observer = make_observer(latitude=48.14)
    timeframe = {"observing_start_time": OBS_TIME}
    return UpTonightHorizon(observer, timeframe, {"north_to_east_ccw": False}, {"ticks": "#9C9C9C"})


def test_altaz_to_radec_round_trips_back_to_altaz(horizon_helper, make_observer):
    observer = make_observer(latitude=48.14)
    location = EarthLocation.from_geodetic(observer.longitude, observer.latitude, observer.elevation)
    alt_in, az_in = 30.0, 120.0

    ra_deg, dec_deg = horizon_helper._altaz_to_radec(alt_in, az_in, OBS_TIME, location)

    recovered = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs").transform_to(
        AltAz(obstime=OBS_TIME, location=location)
    )
    assert recovered.alt.degree == pytest.approx(alt_in, abs=0.1)
    assert recovered.az.degree == pytest.approx(az_in, abs=0.1)


def test_horizon_plots_each_direction_onto_the_axes(horizon_helper):
    ax = plt.figure().add_subplot(projection="polar")
    collections_before = len(ax.collections)

    result = horizon_helper.horizon([{"alt": 20, "az": 0}, {"alt": 25, "az": 90}], ax)

    assert result is ax
    assert len(result.collections) > collections_before  # markers were drawn
