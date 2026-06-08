"""Unit tests for the ``_is_no_event`` masked-time sentinel helper."""

import numpy as np
from astropy.time import Time

from uptonight.sunmoon import _is_no_event


def test_none_is_treated_as_no_event():
    assert _is_no_event(None) is True


def test_valid_time_is_an_event():
    valid = Time("2020-06-21T00:00:00", scale="utc")

    assert _is_no_event(valid) is False


def test_masked_time_is_no_event():
    # astroplan returns a masked Time when a body never crosses the horizon.
    masked = Time(np.ma.MaskedArray([58000.0], mask=[True]), format="mjd", scale="utc")

    assert _is_no_event(masked) is True


def test_time_like_without_mask_attribute_is_an_event():
    # Defensive: anything lacking a ``masked`` attribute is a real event.
    class Bare:
        pass

    assert _is_no_event(Bare()) is False
