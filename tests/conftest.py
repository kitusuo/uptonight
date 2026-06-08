"""Shared fixtures and test determinism setup.

The astro modules are exercised against a *real* astroplan ``Observer`` because
their results are deterministic functions of (location, time); mocking astropy
would be brittle over-specification. To keep that deterministic, fast and
offline we pin astropy's IERS handling to the bundled tables (no network) and
force matplotlib onto a headless backend.
"""

import collections

import matplotlib

# Headless rendering: no display, no GUI event loop.
matplotlib.use("Agg")

import pytest  # noqa: E402  (must follow matplotlib.use)
from astropy import units as u  # noqa: E402
from astropy.coordinates import EarthLocation, SkyCoord  # noqa: E402
from astropy.utils import iers  # noqa: E402
from astroplan import FixedTarget, Observer  # noqa: E402
from pytz import timezone  # noqa: E402

# Never reach out to the network for Earth-orientation data; use the tables
# bundled with astropy and tolerate extrapolation for future dates. Set at
# import time so it is in effect before any test builds an Observer.
iers.conf.auto_download = False
iers.conf.auto_max_age = None


# A recorded publish, so assertions read as data rather than mock-call tuples.
Published = collections.namedtuple("Published", ["topic", "payload", "qos", "retain"])


class FakeMessageInfo:
    """Stand-in for paho's MQTTMessageInfo returned by ``publish``."""

    def __init__(self):
        self.rc = 0
        self.wait_for_publish_called = False

    def wait_for_publish(self, timeout=None):
        self.wait_for_publish_called = True

    def __getitem__(self, index):
        # paho exposes (rc, mid) via indexing; the publish loop reads [0].
        return (self.rc, 1)[index]


class FakeMQTTClient:
    """Spy MQTT client: records every publish for state verification."""

    def __init__(self):
        self.published = []
        self.infos = []
        self.disconnect_called = False

    def publish(self, topic, payload=None, qos=0, retain=False, **kwargs):
        self.published.append(Published(topic, payload, qos, retain))
        info = FakeMessageInfo()
        self.infos.append(info)
        return info

    def disconnect(self):
        self.disconnect_called = True

    # --- query helpers, so tests assert intent rather than index into lists ---
    def payload_for(self, suffix):
        """Last payload published to a topic ending in ``suffix`` (or None)."""
        matches = [p.payload for p in self.published if p.topic.endswith(suffix)]
        return matches[-1] if matches else None

    def published_to(self, suffix):
        """All recorded publishes whose topic ends in ``suffix``."""
        return [p for p in self.published if p.topic.endswith(suffix)]

    def topics(self):
        return [p.topic for p in self.published]


@pytest.fixture(autouse=True)
def _offline_polaris(monkeypatch):
    """Avoid the SIMBAD name lookup in Targets (``FixedTarget.from_name('Polaris')``).

    Keeps the suite offline and deterministic; the resolved coordinates are
    fixed catalogue values anyway.
    """
    polaris = FixedTarget(coord=SkyCoord("02h31m49s", "+89d15m51s"), name="Polaris")
    monkeypatch.setattr(FixedTarget, "from_name", staticmethod(lambda name: polaris))


@pytest.fixture
def fake_mqtt_client():
    return FakeMQTTClient()


@pytest.fixture
def make_observer():
    """Factory for a real astroplan Observer at a given location.

    Defaults to a mid-latitude site (Munich) so the common case is an ordinary
    night; tests that need polar behaviour pass an explicit latitude.
    """

    def _make(latitude=48.14, longitude=11.58, elevation=519.0, tz="Europe/Berlin", name="Test Observatory"):
        return Observer(
            name=name,
            location=EarthLocation.from_geodetic(longitude * u.deg, latitude * u.deg, elevation * u.m),
            timezone=timezone(tz),
        )

    return _make
