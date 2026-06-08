"""Tests for the add-on's options -> UpTonight config.yaml generation (run.sh).

The real ``run.sh`` is executed with a small fake ``bashio`` library so the
add-on options and the MQTT service can be supplied from the test, and the
generated config is parsed back and asserted. Requires bash + jq (present on CI
runners); skipped otherwise.

The fake mirrors real bashio semantics that matter here: ``bashio::config``
returns the string ``"null"`` for a missing key, booleans as ``"true"``/
``"false"``, and ``has_value`` treats ``"null"``/empty as absent.
"""

import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

ADDON_RUN_SH = Path(__file__).resolve().parent.parent / "uptonight-addon" / "run.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None or shutil.which("bash") is None,
    reason="bash and jq are required to exercise run.sh",
)

FAKE_BASHIO = textwrap.dedent(
    """
    bashio::config() { jq -r --arg k "$1" 'if has($k) then .[$k] else "null" end' "${TEST_OPTIONS_JSON}"; }
    bashio::config.has_value() { local v; v="$(bashio::config "$1")"; [ -n "$v" ] && [ "$v" != "null" ]; }
    bashio::services.available() { [ "${TEST_MQTT_AVAILABLE:-false}" = "true" ]; }
    bashio::services() {
        case "$2" in
            host) echo "${TEST_MQTT_HOST:-null}";;
            port) echo "${TEST_MQTT_PORT:-null}";;
            username) echo "${TEST_MQTT_USERNAME:-null}";;
            password) echo "${TEST_MQTT_PASSWORD:-null}";;
        esac
    }
    bashio::log.info() { echo "INFO: $*" >&2; }
    bashio::log.warning() { echo "WARN: $*" >&2; }
    bashio::log.error() { echo "ERROR: $*" >&2; }
    bashio::exit.nok() { echo "FATAL: $*" >&2; exit 1; }
    """
)

BASE_OPTIONS = {
    "latitude": 48.137,
    "longitude": 11.575,
    "elevation": 519,
    "timezone": "Europe/Berlin",
    "observatory_name": "Home",
    "objects": True,
    "bodies": True,
    "comets": False,
    "horizon": False,
    "alttime": False,
}


def _run_addon(tmp_path, options, mqtt=None):
    """Execute run.sh in dry-run mode and return (CompletedProcess, config_path)."""
    (tmp_path / "options.json").write_text(json.dumps(options), encoding="utf-8")
    (tmp_path / "bashio.sh").write_text(FAKE_BASHIO, encoding="utf-8")
    config_path = tmp_path / "config.yaml"

    env = {k: v for k, v in os.environ.items() if k != "TZ"}  # deterministic timezone fallback
    env.update(
        {
            "BASHIO_LIB": str(tmp_path / "bashio.sh"),
            "TEST_OPTIONS_JSON": str(tmp_path / "options.json"),
            "CONFIG_PATH": str(config_path),
            "OUTPUT_DIR": str(tmp_path / "out"),
            "ADDON_DRY_RUN": "1",
        }
    )
    if mqtt is not None:
        env["TEST_MQTT_AVAILABLE"] = "true"
        for field in ("host", "port", "username", "password"):
            if field in mqtt:
                env[f"TEST_MQTT_{field.upper()}"] = str(mqtt[field])

    result = subprocess.run(["bash", str(ADDON_RUN_SH)], env=env, capture_output=True, text=True)
    return result, config_path


def _generate_config(tmp_path, options, mqtt=None):
    result, config_path = _run_addon(tmp_path, options, mqtt=mqtt)
    assert result.returncode == 0, result.stderr
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def test_location_options_map_to_the_location_section(tmp_path):
    config = _generate_config(tmp_path, BASE_OPTIONS)

    assert config["location"] == {
        "latitude": 48.137,
        "longitude": 11.575,
        "elevation": 519,
        "timezone": "Europe/Berlin",
        "observatory_name": "Home",
    }


def test_feature_toggles_map_to_the_features_section(tmp_path):
    config = _generate_config(tmp_path, BASE_OPTIONS)

    assert config["features"] == {
        "objects": True,
        "bodies": True,
        "comets": False,
        "horizon": False,
        "alttime": False,
    }


def test_mqtt_service_maps_to_the_mqtt_section(tmp_path):
    mqtt = {"host": "core-mosquitto", "port": 1883, "username": "addons", "password": "secret"}

    config = _generate_config(tmp_path, BASE_OPTIONS, mqtt=mqtt)

    assert config["mqtt"] == {
        "host": "core-mosquitto",
        "port": 1883,
        "user": "addons",  # HA's "username" maps to UpTonight's "user"
        "password": "secret",
        "clientid": "uptonight",
    }


def test_mqtt_section_is_omitted_when_no_service_is_offered(tmp_path):
    config = _generate_config(tmp_path, BASE_OPTIONS)

    assert "mqtt" not in config


def test_anonymous_broker_omits_username_and_password(tmp_path):
    # An anonymous broker exposes no username/password; the literal "null"
    # bashio returns must not leak into the config.
    config = _generate_config(tmp_path, BASE_OPTIONS, mqtt={"host": "core-mosquitto", "port": 1883})

    assert config["mqtt"] == {"host": "core-mosquitto", "port": 1883, "clientid": "uptonight"}


def test_observation_date_is_included_when_set(tmp_path):
    config = _generate_config(tmp_path, {**BASE_OPTIONS, "observation_date": "06/21/26"})

    assert config["observation_date"] == "06/21/26"


def test_observation_date_is_omitted_when_blank(tmp_path):
    config = _generate_config(tmp_path, {**BASE_OPTIONS, "observation_date": ""})

    assert "observation_date" not in config


def test_optional_fields_fall_back_to_defaults(tmp_path):
    minimal = {
        "latitude": 60.17,
        "longitude": 24.94,
        "objects": True,
        "bodies": False,
        "comets": False,
        "horizon": False,
        "alttime": False,
    }

    config = _generate_config(tmp_path, minimal)

    assert config["location"]["elevation"] == 0
    assert config["location"]["timezone"] == "UTC"
    assert config["location"]["observatory_name"] == "Home"


def test_missing_required_latitude_fails_without_writing_config(tmp_path):
    options = {k: v for k, v in BASE_OPTIONS.items() if k != "latitude"}

    result, config_path = _run_addon(tmp_path, options)

    assert result.returncode != 0
    assert not config_path.exists()
