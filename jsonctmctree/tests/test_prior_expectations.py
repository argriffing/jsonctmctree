"""
Test expectations computed in the absence of data.

"""
from __future__ import division, print_function, absolute_import

from itertools import permutations

import numpy as np
from numpy.testing import assert_allclose

from jsonctmctree.expect import process_json_in
from jsonctmctree.testutil import(
        sample_distn,
        sample_time_reversible_rate_matrix,
        sample_time_nonreversible_rate_matrix,
        )


def _compute_expectations(Q, d, dwell_expect, root_expect):
    nnodes = 5
    nedges = nnodes - 1
    nstates = d.shape[0]
    states = range(nstates)
    edge_rates = sample_distn(nedges)
    state_pairs = list(permutations(range(nstates), 2))
    ntrans = len(state_pairs)
    transition_rates = [Q[i, j] for i, j in state_pairs]

    root_posterior_states = None
    root_posterior_expect = None
    if root_expect is not None:
        root_posterior_states = [[s] for s in states]
        root_posterior_expect = root_expect

    dwell_states = None
    if dwell_expect is not None:
        dwell_states = [[s] for s in states]

    j_in = dict(
            node_count = nnodes,
            process_count = 1,
            state_space_shape = [nstates],
            prior_feasible_states = [[s] for s in states],
            prior_distribution = d.tolist(),
            dwell_states = dwell_states,
            dwell_expect = dwell_expect,
            root_posterior_states = root_posterior_states,
            root_posterior_expect = root_posterior_expect,
            tree = dict(
                row = [0, 0, 2, 2],
                col = [2, 1, 4, 3],
                process = [0]*nedges,
                rate = edge_rates.tolist(),
                ),
            processes = [dict(
                row = [[i] for i, j in state_pairs],
                col = [[j] for i, j in state_pairs],
                rate = transition_rates,
                expect = [1]*ntrans,
                )],
            observable_nodes = [],
            observable_axes = [],
            iid_observations = [
                [],
                [],
                [],
                ])
    return process_json_in(j_in)


def test_prior_expectations():
    nstates = 4
    for fn_sample in (
        sample_time_reversible_rate_matrix,
        sample_time_nonreversible_rate_matrix,
        ):

        Q, d = fn_sample(nstates)
        expected_rate = -np.diag(Q).dot(d)
        dwell_expect = [1] * nstates
        root_expect = None
        j_out = _compute_expectations(Q, d, dwell_expect, root_expect)
        edge_expectations = j_out['edge_expectations']
        for site, expectations in enumerate(edge_expectations):
            assert_allclose(sum(expectations), expected_rate)

        # Check dwell proportion expectations.
        # The sum of state proportions should be 1.0 on each edge.
        edge_dwell = j_out['edge_dwell']
        for site, edge_dwell_sums in enumerate(edge_dwell):
            assert_allclose(edge_dwell_sums, 1)

        # Check that the dwell proportions at each site on each edge
        # correspond to the equilibrium distribution.
        for s in range(nstates):
            dwell_expect = [0] * nstates
            dwell_expect[s] = 1
            root_expect = None
            j_out = _compute_expectations(Q, d, dwell_expect, root_expect)
            edge_dwell = j_out['edge_dwell']
            for site, edge_dwell_sums in enumerate(edge_dwell):
                assert_allclose(edge_dwell_sums, d[s])

        # Check that the prior distribution at the root
        # is the same as the posterior distribution at the root.
        for s in range(nstates):
            root_expect = [0] * nstates
            root_expect[s] = 1
            dwell_expect = None
            j_out = _compute_expectations(Q, d, dwell_expect, root_expect)
            root_value_per_site = j_out['root_values']
            assert_allclose(root_value_per_site, d[s])
