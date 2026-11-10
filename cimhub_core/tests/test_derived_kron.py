"""cimhub_core.derived.kron: folding grounded conductors out of a series impedance matrix."""

import pytest

from cimhub_core.derived.kron import kron_reduce

# a 4-conductor lower triangle with distinct entries, so a wrong index shows
MATRIX = {(1, 1): 4 + 2j, (2, 1): 1 + 1j, (2, 2): 5 + 3j, (3, 1): 0.5 + 0.2j, (3, 2): 0.7 + 0.4j,
          (3, 3): 6 + 2j, (4, 1): 0.3 + 0.6j, (4, 2): 0.2 + 0.1j, (4, 3): 0.9 + 0.3j, (4, 4): 7 + 4j}


def test_one_conductor_by_hand():
    # Z' = Z11 - Z12 Z21 / Z22 = 2 - 1 * 1 / 4
    assert kron_reduce({(1, 1): 2, (2, 1): 1, (2, 2): 4}, [2]) == {(1, 1): 1.75}


def test_kept_conductors_are_renumbered_in_order():
    reduced = kron_reduce(MATRIX, [2])
    assert set(reduced) == {(1, 1), (2, 1), (2, 2), (3, 1), (3, 2), (3, 3)}
    assert reduced[2, 1] == pytest.approx(MATRIX[3, 1] - MATRIX[2, 1] * MATRIX[3, 2] / MATRIX[2, 2])


def test_elimination_order_does_not_matter():
    assert kron_reduce(MATRIX, [3, 4]) == pytest.approx(kron_reduce(MATRIX, [4, 3]))


def test_nothing_to_eliminate_returns_the_matrix():
    assert kron_reduce(MATRIX, []) == MATRIX


def test_zero_pivot_raises():
    with pytest.raises(ValueError, match="conductor 2: its self impedance is zero"):
        kron_reduce({(1, 1): 1, (2, 1): 1, (2, 2): 0}, [2])
