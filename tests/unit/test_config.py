"""Configuration assembly (``main.build_config`` / ``main.fill_horizon``).

These are pure functions: defaults < config.yaml < environment variables. The
environment is injected as a plain dict so no patching of ``os.environ`` is
needed.
"""

from main import build_config, fill_horizon
from uptonight.const import LAYOUT_LANDSCAPE


def test_defaults_apply_without_config_or_environment():
    settings = build_config(None, {}, "/app")

    assert settings["location"]["observatory_name"] == "Backyard"
    assert settings["target_list"] == "/app/targets/GaryImm"
    assert settings["layout"] == LAYOUT_LANDSCAPE
    assert settings["mqtt"] is None


def test_config_section_overrides_the_defaults():
    cfg = {"location": {"latitude": "48d", "longitude": "11d"}}

    settings = build_config(cfg, {}, "/app")

    assert settings["location"]["latitude"] == "48d"
    assert settings["location"]["longitude"] == "11d"


def test_config_merge_skips_none_values():
    cfg = {"location": {"latitude": "48d", "timezone": None}}

    settings = build_config(cfg, {}, "/app")

    assert settings["location"]["timezone"] == "UTC"


def test_environment_overrides_the_config():
    cfg = {"location": {"latitude": "48d", "longitude": "11d"}}

    settings = build_config(cfg, {"LATITUDE": "60d"}, "/app")

    assert settings["location"]["latitude"] == "60d"


def test_elevation_environment_variable_is_parsed_as_int():
    settings = build_config(None, {"ELEVATION": "519"}, "/app")

    assert settings["location"]["elevation"] == 519


def test_observation_max_hours_is_exposed_in_constraints():
    cfg = {"constraints": {"observation_max_hours": 8}}

    settings = build_config(cfg, {}, "/app")

    assert settings["constraints"]["observation_max_hours"] == 8


def test_live_mode_environment_variable_enables_live():
    settings = build_config(None, {"LIVE_MODE": "true"}, "/app")

    assert settings["live"]["enabled"] is True


def test_output_dir_is_resolved_against_the_app_directory():
    cfg = {"output_dir": "out"}

    settings = build_config(cfg, {}, "/base")

    assert settings["output_dir"] == "/base/out"


def test_mqtt_section_is_passed_through():
    cfg = {"mqtt": {"host": "broker", "port": 1883}}

    settings = build_config(cfg, {}, "/app")

    assert settings["mqtt"] == {"host": "broker", "port": 1883}


def test_fill_horizon_returns_none_without_config():
    assert fill_horizon(None) is None


def test_fill_horizon_interpolates_between_anchor_points():
    horizon = {"step_size": 5, "anchor_points": [{"az": 0, "alt": 20}, {"az": 90, "alt": 20}]}

    filled = fill_horizon(horizon)

    assert len(filled) > 1
    assert filled[0] == {"alt": 20.0, "az": 0.0}
