"""Targets: target-list assembly and result-table schemas.

A tiny on-disk target list keeps these fast and independent of the bundled
catalogues. The SIMBAD lookup for Polaris is patched out in conftest.
"""

import pytest
import yaml

from uptonight.targets import Targets

MINI_TARGETS = [
    {
        "name": "Abell 21",
        "description": "Medusa Nebula",
        "type": "Planetary Nebula",
        "constellation": "Gemini",
        "ra": "07 29 03",
        "dec": "+13 14 48",
        "size": 10.0,
        "mag": -9999,  # sentinel: should be normalised to 0.0
    },
    {
        "name": "M 31",
        "description": "Andromeda Galaxy",
        "type": "Galaxy",
        "constellation": "Andromeda",
        "ra": "00 42 44",
        "dec": "+41 16 09",
        "size": 190.0,
        "mag": 3.4,
    },
]


@pytest.fixture
def target_list_path(tmp_path):
    (tmp_path / "mini.yaml").write_text(yaml.safe_dump(MINI_TARGETS), encoding="utf-8")
    return str(tmp_path / "mini")


def test_listed_targets_are_loaded(target_list_path):
    targets = Targets(target_list=target_list_path)

    names = list(targets.input_targets()["name"])
    assert "Abell 21" in names
    assert "M 31" in names


def test_polaris_is_always_appended(target_list_path):
    targets = Targets(target_list=target_list_path)

    assert "Polaris" in list(targets.input_targets()["name"])


def test_custom_targets_are_appended(target_list_path):
    custom = [
        {
            "name": "My Target",
            "description": "d",
            "type": "Galaxy",
            "constellation": "X",
            "ra": "01 00 00",
            "dec": "+10 00 00",
            "size": 5,
            "mag": 9,
        }
    ]

    targets = Targets(target_list=target_list_path, custom_targets=custom)

    assert "My Target" in list(targets.input_targets()["name"])


def test_single_target_mode_keeps_only_the_requested_target(target_list_path):
    targets = Targets(target_list=target_list_path, target="M 31")

    names = targets.input_targets()["name"]
    assert list(names[names != "Polaris"]) == ["M 31"]


def test_magnitude_sentinel_is_normalised_to_zero(target_list_path):
    targets = Targets(target_list=target_list_path)

    table = targets.input_targets()
    abell = table[table["name"] == "Abell 21"][0]
    assert abell["mag"] == 0.0


@pytest.mark.parametrize(
    "table_method, expected_column",
    [
        ("targets_table", "foto"),
        ("bodies_table", "max altitude"),
        ("comets_table", "distance earth au"),
    ],
)
def test_result_table_exposes_its_key_column(target_list_path, table_method, expected_column):
    targets = Targets(target_list=target_list_path)

    assert expected_column in getattr(targets, table_method)().colnames
