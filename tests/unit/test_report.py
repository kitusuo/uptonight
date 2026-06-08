"""Report output: text/JSON files and the MQTT camera-availability gating.

``Report`` takes its collaborators (observer, sun_moon, plot) by injection, so
tests use lightweight stubs and a real (but cheap) astroplan observer for the
location formatting. ``save_mqtt`` news-up an ``MQTTHandler`` internally, so we
patch that one seam to hand it the spy client and assert on recorded publishes.
"""

from datetime import datetime

import pytest
from astropy.table import Table

from uptonight import report as report_module
from uptonight.report import Report

CONSTRAINTS = {
    "altitude_constraint_min": 30,
    "altitude_constraint_max": 80,
    "airmass_constraint": 2,
    "size_constraint_min": 10,
    "size_constraint_max": 300,
    "moon_separation_min": 45,
    "moon_separation_use_illumination": True,
}


class StubSunMoon:
    def __init__(self, dark=True, illumination=42.0, darkness="astronomical"):
        self._dark = dark
        self._illumination = illumination
        self._darkness = darkness

    def is_dark(self):
        return self._dark

    def moon_illumination(self):
        return self._illumination

    def darkness(self):
        return self._darkness


class StubPlot:
    """Stands in for the matplotlib figure; writes deterministic image bytes."""

    def savefig(self, buffer, format=None):
        buffer.write(b"PNGDATA")


@pytest.fixture(autouse=True)
def _drain_module_message_queue():
    # report.message_queue is a module-level global shared across calls; keep
    # tests independent by draining it before and after each test.
    def _drain():
        while not report_module.message_queue.empty():
            report_module.message_queue.get()

    _drain()
    yield
    _drain()


@pytest.fixture
def make_report(make_observer):
    def _make(sun_moon, output_dir, plot=None, target_list="targets/GaryImm"):
        return Report(
            make_observer(),
            datetime(2020, 6, 3, 22, 0),
            datetime(2020, 6, 4, 4, 0),
            sun_moon,
            str(output_dir),
            "20200603",
            "",
            CONSTRAINTS,
            "",
            target_list,
            plot,
        )

    return _make


def _objects_table(rows=0):
    columns = ["target name", "hmsdms", "right ascension", "declination", "altitude", "azimuth"]
    table = Table(names=columns, dtype=["U20"] * len(columns))
    for index in range(rows):
        table.add_row([f"M{index}", "hms", "ra", "dec", "10", "20"])
    return table


def _install_fake_broker(monkeypatch, spy_client):
    """Patch report.MQTTHandler so save_mqtt connects to the spy client."""

    class FakeHandler:
        def __init__(self, service):
            self._connected = False

        def connected(self):
            return self._connected

        def connect(self):
            self._connected = True
            return spy_client

        def disconnect(self):
            self._connected = False

    monkeypatch.setattr(report_module, "MQTTHandler", FakeHandler)


# --- text / JSON reports -----------------------------------------------------


def test_save_txt_writes_a_report_with_observatory_header(make_report, tmp_path):
    report = make_report(StubSunMoon(), tmp_path)

    report.save_txt(Table({"target name": ["M31"], "size": [180]}), "", False)

    content = (tmp_path / "uptonight-report.txt").read_text(encoding="utf-8")
    assert "UpTonight" in content
    assert "Test Observatory" in content


def test_save_json_writes_a_parseable_report(make_report, tmp_path):
    report = make_report(StubSunMoon(), tmp_path)

    report.save_json(Table({"target name": ["M31"], "size": [180]}), "", False)

    assert (tmp_path / "uptonight-report.json").exists()


# --- MQTT camera-availability gating ----------------------------------------


def test_save_mqtt_takes_image_offline_when_there_is_no_darkness(make_report, fake_mqtt_client, monkeypatch, tmp_path):
    _install_fake_broker(monkeypatch, fake_mqtt_client)
    report = make_report(StubSunMoon(dark=False, darkness="none"), tmp_path)

    report.save_mqtt({"host": "broker"}, _objects_table(rows=0), "objects", False)

    assert fake_mqtt_client.payload_for("/screen_availability") == "OFF"
    assert fake_mqtt_client.published_to("/screen") == []


def test_save_mqtt_publishes_image_and_availability_when_dark(make_report, fake_mqtt_client, monkeypatch, tmp_path):
    _install_fake_broker(monkeypatch, fake_mqtt_client)
    report = make_report(StubSunMoon(dark=True), tmp_path, plot=StubPlot())

    report.save_mqtt({"host": "broker"}, _objects_table(rows=2), "objects", False)

    assert fake_mqtt_client.payload_for("/screen_availability") == "ON"
    assert fake_mqtt_client.payload_for("/screen") == bytearray(b"PNGDATA")


def test_save_mqtt_publishes_darkness_and_count_for_sensors(make_report, fake_mqtt_client, monkeypatch, tmp_path):
    _install_fake_broker(monkeypatch, fake_mqtt_client)
    report = make_report(StubSunMoon(dark=False, darkness="none"), tmp_path)

    report.save_mqtt({"host": "broker"}, _objects_table(rows=0), "objects", False)

    import json

    attributes = json.loads(fake_mqtt_client.payload_for("/attributes"))
    assert attributes["darkness"] == "None"


def test_save_mqtt_returns_without_publishing_when_the_connection_is_rejected(make_report, monkeypatch, tmp_path):
    class RejectingHandler:
        def __init__(self, service):
            pass

        def connected(self):
            return False

        def connect(self):
            raise ConnectionError("not authorized")

    monkeypatch.setattr(report_module, "MQTTHandler", RejectingHandler)
    report = make_report(StubSunMoon(), tmp_path)

    assert report.save_mqtt({"host": "broker"}, _objects_table(rows=0), "objects", False) is None


def test_save_mqtt_publishes_state_for_a_bodies_result(make_report, fake_mqtt_client, monkeypatch, tmp_path):
    _install_fake_broker(monkeypatch, fake_mqtt_client)
    report = make_report(StubSunMoon(dark=False, darkness="none"), tmp_path)
    bodies = Table(names=["target name", "hmsdms", "right ascension", "declination"], dtype=["U20"] * 4)

    report.save_mqtt({"host": "broker"}, bodies, "bodies", False)

    assert fake_mqtt_client.published_to("/state")
