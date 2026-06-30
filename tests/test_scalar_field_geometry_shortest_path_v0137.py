import numpy as np
import pytest

from scalar_field_geometry import (
    ShortestPathRecord,
    all_pairs_shortest_path_lengths,
    generate_initial_association_state,
    shortest_path_between_points,
    shortest_path_from_adjacency,
)


def test_shortest_path_from_adjacency_returns_path_and_matches_length_matrix():
    adjacency = np.array(
        [
            [0, 1, 0, 0, 0],
            [0, 0, 1, 1, 0],
            [0, 0, 0, 0, 1],
            [0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0],
        ],
        dtype=np.int64,
    )

    record = shortest_path_from_adjacency(adjacency, source=0, target=4)
    lengths = all_pairs_shortest_path_lengths(adjacency)

    assert isinstance(record, ShortestPathRecord)
    assert record.source == 0
    assert record.target == 4
    assert record.reachable is True
    assert record.path in ((0, 1, 2, 4), (0, 1, 3, 4))
    assert record.length == 3
    assert record.length == int(lengths[0, 4])


def test_shortest_path_from_adjacency_reports_unreachable_without_inventing_path():
    adjacency = np.array(
        [
            [0, 1, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 1],
            [0, 0, 0, 0],
        ],
        dtype=np.int64,
    )

    record = shortest_path_from_adjacency(adjacency, source=0, target=3)

    assert record == ShortestPathRecord(
        source=0,
        target=3,
        path=(),
        length=-1,
        reachable=False,
    )


def test_shortest_path_from_adjacency_handles_source_equals_target():
    adjacency = np.zeros((4, 4), dtype=np.int64)

    record = shortest_path_from_adjacency(adjacency, source=2, target=2)

    assert record.path == (2,)
    assert record.length == 0
    assert record.reachable is True


@pytest.mark.parametrize(
    "adjacency, source, target, message",
    [
        (np.zeros((2, 3), dtype=np.int64), 0, 1, "adjacency must be square"),
        (np.zeros((3, 3), dtype=np.int64), -1, 1, "source out of range"),
        (np.zeros((3, 3), dtype=np.int64), 0, 3, "target out of range"),
    ],
)
def test_shortest_path_from_adjacency_validates_inputs(adjacency, source, target, message):
    with pytest.raises(ValueError, match=message):
        shortest_path_from_adjacency(adjacency, source=source, target=target)


def test_shortest_path_between_points_respects_active_phase_scope():
    state = generate_initial_association_state(
        n_points=6,
        seed=20260626,
        generation_rule="cyclic_offsets",
    )

    record = shortest_path_between_points(
        state=state,
        source=0,
        target=3,
        graph_mode="directed",
        path_scope="active_phase",
        phase=0,
    )

    assert record == ShortestPathRecord(
        source=0,
        target=3,
        path=(0, 1, 2, 3),
        length=3,
        reachable=True,
    )


def test_shortest_path_between_points_respects_completed_scope():
    state = generate_initial_association_state(
        n_points=6,
        seed=20260626,
        generation_rule="cyclic_offsets",
    )

    record = shortest_path_between_points(
        state=state,
        source=0,
        target=3,
        graph_mode="directed",
        path_scope="completed",
        phase=0,
    )

    # Completed scope sees all three slots, including cyclic offset +3.
    assert record == ShortestPathRecord(
        source=0,
        target=3,
        path=(0, 3),
        length=1,
        reachable=True,
    )


def test_shortest_path_between_points_is_readout_only_and_does_not_mutate_state():
    state = generate_initial_association_state(
        n_points=6,
        seed=20260626,
        generation_rule="cyclic_offsets",
    )
    assoc_before = state.assoc.copy()
    fingerprint_before = state.fingerprint

    _ = shortest_path_between_points(
        state=state,
        source=0,
        target=3,
        graph_mode="undirected",
        path_scope="completed",
        phase=2,
    )

    np.testing.assert_array_equal(state.assoc, assoc_before)
    assert state.fingerprint == fingerprint_before
    assert state.verify() is True
