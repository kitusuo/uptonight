import logging
import math
import os
import pathlib
import sys
import time
from time import sleep

import yaml

from uptonight.const import (
    DEFAULT_AIRMASS_CONSTRAINT,
    DEFAULT_ALTITUDE_CONSTRAINT_MAX,
    DEFAULT_ALTITUDE_CONSTRAINT_MIN,
    DEFAULT_FRACTION_OF_TIME_OBSERVABLE_THRESHOLD,
    DEFAULT_LIVE_MODE_INTERVAL,
    DEFAULT_MAX_NUMBER_WITHIN_THRESHOLD,
    DEFAULT_MOON_SEPARATION_MIN,
    DEFAULT_MOON_SEPARATION_USE_ILLUMINATION,
    DEFAULT_NORTH_TO_EAST_CCW,
    DEFAULT_OBSERVATION_MAX_HOURS,
    DEFAULT_SIZE_CONSTRAINT_MAX,
    DEFAULT_SIZE_CONSTRAINT_MIN,
    DEFAULT_TARGETS,
    LAYOUT_LANDSCAPE,
)
from uptonight.uptonight import UpTonight

_LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s (%(threadName)s) [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def build_config(cfg, env, app_directory):
    """Assemble the UpTonight settings from config and environment.

    Pure (no file or network I/O): given the parsed ``config.yaml`` dict (or
    None) and a mapping of environment variables, return a dict of all the
    settings UpTonight needs. Environment variables override the config file,
    which overrides the defaults.

    Args:
        cfg (dict | None): Parsed config.yaml content.
        env (Mapping): Environment variables (``os.environ`` in production).
        app_directory (str): Base directory for resolving relative paths.

    Returns:
        dict: The resolved settings.
    """

    cfg = cfg or {}

    location = {"longitude": "", "latitude": "", "elevation": 0, "timezone": "UTC", "observatory_name": "Backyard"}
    environment = {"pressure": 0, "temperature": 0, "relative_humidity": 0}
    constraints = {
        "altitude_constraint_min": DEFAULT_ALTITUDE_CONSTRAINT_MIN,
        "altitude_constraint_max": DEFAULT_ALTITUDE_CONSTRAINT_MAX,
        "airmass_constraint": DEFAULT_AIRMASS_CONSTRAINT,
        "size_constraint_min": DEFAULT_SIZE_CONSTRAINT_MIN,
        "size_constraint_max": DEFAULT_SIZE_CONSTRAINT_MAX,
        "moon_separation_min": DEFAULT_MOON_SEPARATION_MIN,
        "moon_separation_use_illumination": DEFAULT_MOON_SEPARATION_USE_ILLUMINATION,
        "fraction_of_time_observable_threshold": DEFAULT_FRACTION_OF_TIME_OBSERVABLE_THRESHOLD,
        "max_number_within_threshold": DEFAULT_MAX_NUMBER_WITHIN_THRESHOLD,
        "north_to_east_ccw": DEFAULT_NORTH_TO_EAST_CCW,
        "observation_max_hours": DEFAULT_OBSERVATION_MAX_HOURS,
    }
    colors = {
        "ticks": "#9C9C9C",
        "grid": "#9C9C9C",
        "axes": "#262626",
        "figure": "#1C1C1C",
        "legend": "#262626",
        "alttime": "#CC6666",
        "meridian": "#66CC66",
        "text": "#FFFFFF",
    }
    features = {"horizon": False, "objects": True, "bodies": True, "comets": False, "alttime": False}

    observation_date = None
    target_list = f"{app_directory}/{DEFAULT_TARGETS}"
    type_filter = ""
    output_dir = f"{app_directory}/out"
    live = {}
    bucket_list = []
    done_list = []
    custom_targets = []
    horizon = None
    layout = LAYOUT_LANDSCAPE
    output_datestamp = False
    target = None
    prefix = ""
    mqtt = None

    def _cfg_merge(section, target_dict):
        if cfg.get(section):
            target_dict.update({k: v for k, v in cfg[section].items() if v is not None})

    _cfg_merge("location", location)
    _cfg_merge("environment", environment)
    _cfg_merge("constraints", constraints)
    _cfg_merge("colors", colors)
    _cfg_merge("live", live)

    if cfg.get("mqtt") is not None:
        mqtt = {k: v for k, v in cfg["mqtt"].items() if v is not None}

    if cfg.get("observation_date") is not None:
        observation_date = cfg["observation_date"]
    if cfg.get("target_list") is not None:
        target_list = cfg["target_list"]
    if cfg.get("type_filter") is not None:
        type_filter = cfg["type_filter"]
    if cfg.get("output_dir") is not None:
        output_dir = f"{app_directory}/{cfg['output_dir']}"
    if cfg.get("live_mode") is not None:  # deprecated
        live = {"enabled": bool(cfg["live_mode"]), "interval": DEFAULT_LIVE_MODE_INTERVAL}
    if cfg.get("layout") is not None:
        layout = cfg["layout"]
    if cfg.get("prefix") is not None:
        prefix = cfg["prefix"]
    if cfg.get("bucket_list") is not None:
        bucket_list = cfg["bucket_list"]
    if cfg.get("done_list") is not None:
        done_list = cfg["done_list"]
    if cfg.get("custom_targets") is not None:
        custom_targets = cfg["custom_targets"]
    if cfg.get("horizon") is not None:
        horizon = cfg["horizon"]
    if cfg.get("features") is not None:
        features = cfg["features"]
    if cfg.get("output_datestamp") is not None:
        output_datestamp = cfg["output_datestamp"]

    if env.get("TARGET") is not None:
        target = env.get("TARGET")
    if env.get("LONGITUDE") is not None:
        location["longitude"] = env.get("LONGITUDE")
    if env.get("LATITUDE") is not None:
        location["latitude"] = env.get("LATITUDE")
    if env.get("ELEVATION") is not None:
        location["elevation"] = int(env.get("ELEVATION"))
    if env.get("TIMEZONE") is not None:
        location["timezone"] = env.get("TIMEZONE")
    if env.get("OBSERVATORY_NAME") is not None:
        location["observatory_name"] = env.get("OBSERVATORY_NAME")
    if env.get("PRESSURE") is not None:
        environment["pressure"] = float(env.get("PRESSURE"))
    if env.get("TEMPERATURE") is not None:
        environment["temperature"] = float(env.get("TEMPERATURE"))
    if env.get("RELATIVE_HUMIDITY") is not None:
        environment["relative_humidity"] = float(env.get("RELATIVE_HUMIDITY"))
    if env.get("OBSERVATION_DATE") is not None:
        observation_date = env.get("OBSERVATION_DATE")
    if env.get("TARGET_LIST") is not None:
        target_list = env.get("TARGET_LIST")
    if env.get("TYPE_FILTER") is not None:
        type_filter = env.get("TYPE_FILTER")
    if env.get("OUTPUT_DIR") is not None:
        output_dir = env.get("OUTPUT_DIR")
    if env.get("LIVE_MODE") is not None and env.get("LIVE_MODE").lower() == "true":
        live = {"enabled": True, "interval": DEFAULT_LIVE_MODE_INTERVAL}
    if env.get("PREFIX") is not None:
        prefix = env.get("PREFIX")

    return {
        "location": location,
        "environment": environment,
        "constraints": constraints,
        "colors": colors,
        "features": features,
        "layout": layout,
        "observation_date": observation_date,
        "target_list": target_list,
        "type_filter": type_filter,
        "output_dir": output_dir,
        "live": live,
        "bucket_list": bucket_list,
        "done_list": done_list,
        "custom_targets": custom_targets,
        "horizon": horizon,
        "output_datestamp": output_datestamp,
        "target": target,
        "prefix": prefix,
        "mqtt": mqtt,
    }


def fill_horizon(horizon):
    """Interpolate the horizon anchor points into a dense alt/az list.

    Args:
        horizon (dict | None): Horizon config with ``step_size`` and
            ``anchor_points``, or None.

    Returns:
        list | None: Interpolated alt/az points, or None when no horizon is set.
    """

    if horizon is None:
        return None

    step_size = horizon.get("step_size", 4)
    anchor_points = horizon.get("anchor_points", [])

    horizon_filled = []
    for index, horizon_direction in enumerate(anchor_points):
        az_start = horizon_direction.get("az")
        alt_start = horizon_direction.get("alt")
        az_stop = anchor_points[index + 1].get("az")
        alt_stop = anchor_points[index + 1].get("alt")

        distance = math.sqrt((alt_stop - alt_start) ** 2 + (az_stop - az_start) ** 2)
        steps = round(distance / step_size, 0)
        if steps == 0:
            steps = 1
        inc_alt = (alt_stop - alt_start) / steps
        inc_az = (az_stop - az_start) / steps

        for step in range(0, int(steps)):
            horizon_filled.append({"alt": alt_start + inc_alt * step, "az": az_start + inc_az * step})

        if index == len(anchor_points) - 2:
            break

    return horizon_filled


def main():
    """Main"""
    # Determine if application is a script file or frozen exe
    if getattr(sys, "frozen", False):
        app_directory = "/app"
        _LOGGER.debug(f"UpTonight running frozen, app directory set to {app_directory}")
    elif __file__:
        app_directory = pathlib.Path(__file__).parent.resolve()
        _LOGGER.debug(f"UpTonight running as script file, app directory set to {app_directory}")

    # Read config.yaml
    cfg = None
    if os.path.isfile(f"{app_directory}/config.yaml"):
        with open(f"{app_directory}/config.yaml", "r", encoding="utf-8") as ymlfile:
            cfg = yaml.safe_load(ymlfile)

    settings = build_config(cfg, os.environ, app_directory)
    location = settings["location"]
    environment = settings["environment"]
    constraints = settings["constraints"]
    colors = settings["colors"]
    features = settings["features"]
    layout = settings["layout"]
    observation_date = settings["observation_date"]
    target_list = settings["target_list"]
    type_filter = settings["type_filter"]
    output_dir = settings["output_dir"]
    live = settings["live"]
    bucket_list = settings["bucket_list"]
    done_list = settings["done_list"]
    custom_targets = settings["custom_targets"]
    output_datestamp = settings["output_datestamp"]
    target = settings["target"]
    prefix = settings["prefix"]
    mqtt = settings["mqtt"]

    horizon_filled = fill_horizon(settings["horizon"])

    # We need at least a longitude and latitude, the rest is optional
    if location["longitude"] == "" or location["latitude"] == "":
        _LOGGER.error("Longitude and/or latitude not set")
        sys.exit(1)

    start = time.time()

    # Do the math
    if live.get("enabled"):
        _LOGGER.info("UpTonight live mode")
        while True:
            uptonight = UpTonight(
                location=location,
                features=features,
                colors=colors,
                output_datestamp=output_datestamp,
                environment=environment,
                constraints=constraints,
                target_list=target_list,
                bucket_list=bucket_list,
                done_list=done_list,
                custom_targets=custom_targets,
                observation_date=observation_date,
                type_filter=type_filter,
                output_dir=output_dir,
                live=live.get("enabled"),
                layout=layout,
                target=target,
                prefix=prefix,
            )

            uptonight.calc(
                bucket_list=bucket_list,
                done_list=done_list,
                type_filter=type_filter,
                horizon=horizon_filled,
            )
            sleep(live.get("interval", DEFAULT_LIVE_MODE_INTERVAL))
    else:
        _LOGGER.info("UpTonight one-time calculation mode")

        uptonight = UpTonight(
            location=location,
            features=features,
            colors=colors,
            output_datestamp=output_datestamp,
            environment=environment,
            constraints=constraints,
            target_list=target_list,
            bucket_list=bucket_list,
            done_list=done_list,
            custom_targets=custom_targets,
            observation_date=observation_date,
            type_filter=type_filter,
            output_dir=output_dir,
            live=False,
            layout=layout,
            target=target,
            prefix=prefix,
            mqtt=mqtt,
        )

        uptonight.calc(
            bucket_list=bucket_list,
            done_list=done_list,
            type_filter=type_filter,
            horizon=horizon_filled,
        )

    end = time.time()
    _LOGGER.info("Execution time: %s seconds", end - start)


if __name__ == "__main__":
    main()
