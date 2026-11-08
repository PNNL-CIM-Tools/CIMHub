"""cimhub_core.derived.sequence: a 1- or 2-phase phase matrix from sequence values."""

import pytest

from cimhub_core.derived.sequence import phase_matrix


def test_one_phase_is_the_positive_sequence():
    assert phase_matrix(0.5, None, 1) == {(1, 1): 0.5}


def test_two_phase_is_the_truncated_transform():
    assert phase_matrix(0.3, 0.9, 2) == pytest.approx({(1, 1): 0.5, (2, 1): 0.2, (2, 2): 0.5})


@pytest.mark.parametrize("zero, phases, message", [(None, 2, "needs the zero-sequence"), (0.9, 3, "not 3")])
def test_rejects(zero, phases, message):
    with pytest.raises(ValueError, match=message):
        phase_matrix(0.3, zero, phases)
