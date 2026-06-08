"""Invariants on shared constants that other modules rely on."""

from uptonight.const import (
    DARKNESS_ASTRONOMICAL,
    DARKNESS_CIVIL,
    DARKNESS_NAUTICAL,
    DARKNESS_NONE,
    DEVICE_TYPE_CAMERA,
    FUNCTIONS,
    SENSOR_NAME,
)


def test_darkness_levels_are_distinct():
    levels = {DARKNESS_ASTRONOMICAL, DARKNESS_NAUTICAL, DARKNESS_CIVIL, DARKNESS_NONE}

    assert len(levels) == 4


def test_sensor_name_index_addresses_the_function_definition():
    # The SENSOR_* index constants must line up with the function tuples.
    camera_function = FUNCTIONS[DEVICE_TYPE_CAMERA][0]

    assert camera_function[SENSOR_NAME] == "Plot"
