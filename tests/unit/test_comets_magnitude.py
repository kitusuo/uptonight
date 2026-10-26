"""UpTonightComets._compute_visual_magnitude: standard comet magnitude formula."""

import pytest

from uptonight.comets import UpTonightComets


def _magnitude(g, k, earth, sun):
    # The method does not touch instance state, so skip the networked __init__.
    comets = object.__new__(UpTonightComets)
    return comets._compute_visual_magnitude(
        {"magnitude_g": g, "magnitude_k": k, "distance_au_earth": earth, "distance_au_sun": sun}
    )


def test_at_one_au_from_earth_and_sun_magnitude_is_g():
    assert _magnitude(g=5.0, k=10.0, earth=1.0, sun=1.0) == pytest.approx(5.0)


def test_geocentric_distance_uses_five_log_delta():
    # T = g + 5*log10(Δ) + k*log10(r); Δ=10, r=1 -> g + 5
    assert _magnitude(g=5.0, k=10.0, earth=10.0, sun=1.0) == pytest.approx(10.0)


def test_heliocentric_distance_uses_k_log_r():
    # Δ=1, r=10 -> g + k (no extra 2.5 factor)
    assert _magnitude(g=5.0, k=10.0, earth=1.0, sun=10.0) == pytest.approx(15.0)
