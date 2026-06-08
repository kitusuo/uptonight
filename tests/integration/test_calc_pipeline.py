"""End-to-end UpTonight.calc runs exercising the full pipeline.

These are slower (they build the orchestrator and run the astro calculations and
matplotlib rendering), so they are marked ``slow``. A tiny on-disk target list
keeps them tractable, the IERS download is patched out, and comets/horizon are
left off (network / extra config) and covered elsewhere.
"""

import glob
import json

import pytest
import yaml

import uptonight.uptonight as uptonight_module
from uptonight.uptonight import UpTonight

pytestmark = pytest.mark.slow

COLORS = {
    "ticks": "#9C9C9C",
    "grid": "#9C9C9C",
    "axes": "#262626",
    "figure": "#1C1C1C",
    "legend": "#262626",
    "alttime": "#CC6666",
    "meridian": "#66CC66",
    "text": "#FFFFFF",
}
ENVIRONMENT = {"pressure": 1.0, "temperature": 10, "relative_humidity": 0.5}
# alttime on so the per-target altitude/time plots in plot.py are exercised too.
FEATURES = {"objects": True, "bodies": True, "comets": False, "horizon": False, "alttime": True}

# A few bright summer deep-sky objects, high in the sky at mid-northern latitude.
TARGETS = [
    {"name": "M 13", "description": "Hercules Cluster", "type": "Globular Cluster",
     "constellation": "Hercules", "ra": "16 41 41", "dec": "+36 27 35", "size": 20.0, "mag": 5.8},
    {"name": "M 57", "description": "Ring Nebula", "type": "Planetary Nebula",
     "constellation": "Lyra", "ra": "18 53 35", "dec": "+33 01 45", "size": 1.4, "mag": 8.8},
    {"name": "M 27", "description": "Dumbbell Nebula", "type": "Planetary Nebula",
     "constellation": "Vulpecula", "ra": "19 59 36", "dec": "+22 43 16", "size": 8.0, "mag": 7.4},
    {"name": "M 51", "description": "Whirlpool Galaxy", "type": "Galaxy",
     "constellation": "Canes Venatici", "ra": "13 29 53", "dec": "+47 11 43", "size": 11.0, "mag": 8.4},
]


def _constraints(max_hours=None, max_number=60):
    return {
        "altitude_constraint_min": 20,
        "altitude_constraint_max": 80,
        "airmass_constraint": 3,
        "size_constraint_min": 1,
        "size_constraint_max": 300,
        "moon_separation_min": 30,
        "moon_separation_use_illumination": False,
        "fraction_of_time_observable_threshold": 0.0,
        "max_number_within_threshold": max_number,
        "north_to_east_ccw": False,
        "observation_max_hours": max_hours,
    }


@pytest.fixture(autouse=True)
def _no_iers_download(monkeypatch):
    monkeypatch.setattr(uptonight_module, "download_IERS_A", lambda: None)


@pytest.fixture
def target_list(tmp_path):
    (tmp_path / "mini.yaml").write_text(yaml.safe_dump(TARGETS), encoding="utf-8")
    return str(tmp_path / "mini")


def _run(location, date, target_list, output_dir, max_hours=None, layout="landscape", live=False,
         max_number=60, type_filter="", bucket_list=None, done_list=None):
    output_dir.mkdir(exist_ok=True)
    uptonight = UpTonight(
        location=location,
        features=FEATURES,
        colors=COLORS,
        environment=ENVIRONMENT,
        constraints=_constraints(max_hours, max_number),
        target_list=target_list,
        observation_date=date,
        type_filter=type_filter,
        output_dir=str(output_dir),
        layout=layout,
        live=live,
        mqtt=None,
    )
    uptonight.calc(bucket_list=bucket_list, done_list=done_list, type_filter=type_filter)
    return output_dir


def _report_row_count(output_dir):
    # pandas.json is column-oriented: {"target name": {"0": ..., "1": ...}, ...}
    report = json.loads((output_dir / "uptonight-report.json").read_text(encoding="utf-8"))
    return len(report["target name"])


MID_LATITUDE = {
    "longitude": "11.58d", "latitude": "48.14d", "elevation": 519,
    "timezone": "Europe/Berlin", "observatory_name": "Test",
}
HIGH_LATITUDE = {
    "longitude": "23.48d", "latitude": "61.5d", "elevation": 150,
    "timezone": "Europe/Helsinki", "observatory_name": "Test",
}
POLAR = {
    "longitude": "11.58d", "latitude": "85d", "elevation": 0,
    "timezone": "Europe/Berlin", "observatory_name": "Test",
}


def test_normal_night_writes_a_plot(target_list, tmp_path):
    out = _run(MID_LATITUDE, "06/03/20", target_list, tmp_path / "out")

    assert glob.glob(str(out / "*plot*.png"))


def test_normal_night_reports_observable_targets(target_list, tmp_path):
    out = _run(MID_LATITUDE, "06/03/20", target_list, tmp_path / "out")

    assert _report_row_count(out) > 0


def test_no_darkness_skips_the_plot(target_list, tmp_path):
    out = _run(HIGH_LATITUDE, "06/21/20", target_list, tmp_path / "out")

    assert glob.glob(str(out / "*plot*.png")) == []


def test_no_darkness_yields_an_empty_report(target_list, tmp_path):
    out = _run(HIGH_LATITUDE, "06/21/20", target_list, tmp_path / "out")

    assert _report_row_count(out) == 0


def test_capped_window_in_deep_polar_night_still_renders(target_list, tmp_path):
    out = _run(POLAR, "12/21/20", target_list, tmp_path / "out", max_hours=6)

    assert glob.glob(str(out / "*plot*.png"))


def test_portrait_layout_renders(target_list, tmp_path):
    out = _run(MID_LATITUDE, "06/03/20", target_list, tmp_path / "out", layout="portrait")

    assert glob.glob(str(out / "*plot*.png"))


def test_live_mode_renders_for_the_current_moment(target_list, tmp_path):
    # Live mode uses a now-based one-minute window instead of the dark window.
    out = _run(MID_LATITUDE, "06/03/20", target_list, tmp_path / "out", live=True)

    assert glob.glob(str(out / "*plot*.png"))


def test_type_filter_and_bucket_list_select_a_subset(target_list, tmp_path):
    # type_filter excludes non-nebulae (even bucket-listed M 13), and the low
    # max-number cap exercises the threshold-clamping branch.
    out = _run(
        MID_LATITUDE, "06/03/20", target_list, tmp_path / "out",
        max_number=1, type_filter="Nebula", bucket_list=["M 13"],
    )

    assert glob.glob(str(out / "*plot*.png"))
