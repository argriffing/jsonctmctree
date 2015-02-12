from __future__ import print_function, division, absolute_import

import functools
import json

import numpy as np
from numpy.testing import assert_equal
from scipy.misc import logsumexp
from scipy.optimize import minimize
import pyparsing

import jsonctmctree.interface

s_tree = """((((((cerevisiae,paradoxus),mikatae),kudriavzevii),
bayanus),castellii),kluyveri)"""

def build_tree(parent, root, node, name_to_node, edges):
    if parent is not None:
        edges.append((parent, node))
    neo = node + 1
    if isinstance(root, basestring):
        name_to_node[root] = node
    else:
        for element in root:
            neo = build_tree(node, element, neo, name_to_node, edges)
    return neo

def hky(distn, k):
    R = np.array([
        [0, 1, k, 1],
        [1, 0, 1, k],
        [k, 1, 0, 1],
        [1, k, 1, 0],
        ]) * distn
    return R, R.sum(axis=1).dot(distn)

def gen_transitions(distn, kappa, tau):
    R, expected_rate = hky(distn, kappa)
    R = R / expected_rate
    for i in range(4):
        for j in range(4):
            if i == j:
                for k in range(4):
                    if i != k:
                        yield (i, j), (k, j), R[i, k]
                    if j != k:
                        yield (i, j), (i, k), R[j, k]
            else:
                yield (i, j), (i, i), R[j, i] + tau
                yield (i, j), (j, j), R[i, j] + tau
                for k in range(4):
                    if i != k and j != k:
                        yield (i, j), (k, j), R[i, k]
                        yield (i, j), (i, k), R[j, k]

def pack(distn, kappa, tau, rates):
    return np.log(np.concatenate([distn, [kappa, tau], rates]))

def unpack(X):
    lse = logsumexp(X[0:4])
    unpacking_cost = lse * lse
    distn = np.exp(X[0:4] - lse)
    kappa, tau = np.exp(X[4:6])
    rates = np.exp(X[6:])
    return distn, kappa, tau, rates, unpacking_cost

def get_process_defn_and_prior(distn, kappa, tau):
    triples = list(gen_transitions(distn, kappa, tau))
    rows, cols, transition_rates = zip(*triples)
    process_definition = {
            'row_states' : [list(x) for x in rows],
            'column_states' : [list(x) for x in cols],
            'transition_rates' : list(transition_rates)
            }
    root_prior = {
            "states" : [[0, 0], [1, 1], [2, 2], [3, 3]],
            "probabilities" : list(distn)
            }
    return process_definition, root_prior

def objective_and_gradient(scene, X):
    delta = 1e-8
    distn, kappa, tau, rates, unpacking_cost = unpack(X)
    scene['tree']['edge_rate_scaling_factors'] = rates.tolist()
    log_likelihood_request = {'property' : 'snnlogl'}
    derivatives_request = {'property' : 'sdnderi'}

    # Get the log likelihood and per-edge derivatives.
    # Note that the edge derivatives are of the log likelihood
    # with respect to logs of edge rates, and we will eventually
    # multiply them by -1 to get the gradient of the cost function
    # which we want to minimize rather than the log likelihood function
    # which we want to maximize.
    process_defn, root_prior = get_process_defn_and_prior(distn, kappa, tau)
    scene['root_prior'] = root_prior
    scene['process_definitions'] = [process_defn]
    j_in = {
            'scene' : scene,
            'requests' : [log_likelihood_request, derivatives_request]
            }
    j_out = jsonctmctree.interface.process_json_in(j_in, debug=True)
    log_likelihood, edge_gradient = j_out['responses']
    cost = -log_likelihood + unpacking_cost

    # For each non-edge-specific parameter get finite-differences
    # approximation of the gradient.
    nedges = len(scene['tree']['row_nodes'])
    nparams = len(X) - nedges
    gradient = []
    for i in range(nparams):
        W = np.copy(X)
        W[i] += delta
        distn, kappa, tau, rates, unpacking_cost = unpack(W)
        process_defn, root_prior = get_process_defn_and_prior(distn, kappa, tau)
        scene['root_prior'] = root_prior
        scene['process_definitions'] = [process_defn]
        j_in = {
                'scene' : scene,
                'requests' : [log_likelihood_request]
                }
        j_out = jsonctmctree.interface.process_json_in(j_in)
        ll = j_out['responses'][0]
        c = -ll + unpacking_cost
        slope = (c - cost) / delta
        gradient.append(slope)
    gradient.extend([-x for x in edge_gradient])
    gradient = np.array(gradient)

    # Return cost and gradient.
    print(X)
    print(np.exp(X))
    print(cost)
    print(gradient)
    print()
    return cost, gradient

def main():

    np.set_printoptions(threshold=100000)

    # Flatten the tree into a list of node indices and a list of edges.
    tree = s_tree.replace(',', ' ')
    nestedItems = pyparsing.nestedExpr(opener='(', closer=')')
    tree = (nestedItems + pyparsing.stringEnd).parseString(tree).asList()[0]
    name_to_node = {}
    edges = []
    build_tree(None, tree, 0, name_to_node, edges)

    # Spam the name and node and edges.
    for name, node in name_to_node.items():
        print(node, ':', name)
    for edge in edges:
        print(edge)
    print()

    # Define suffixes indicating paralogs.
    paralog_to_variable = {
            'yal056w' : 0,
            'yor371c' : 1}

    # Read the data (in this case, alignment columns).
    nodes = []
    variables = []
    rows = []
    with open('yeast.paralogs.fasta') as fin:
        while True:
            line = fin.readline().strip().lower()
            if not line:
                break
            name = line[1:-7]
            paralog = line[-7:]
            seq = fin.readline().strip()
            row = ['ACGT'.index(x) for x in seq]
            nodes.append(name_to_node[name])
            variables.append(paralog_to_variable[paralog])
            rows.append(row)
    columns = [list(x) for x in zip(*rows)]

    # Interpret the tree.
    observed_node_count = len(nodes)
    edge_count = len(edges)
    row_nodes, column_nodes = zip(*edges)

    distn = [0.25, 0.25, 0.25, 0.25]
    rates = [1] * edge_count
    kappa = 2.0
    tau = 3.0
    process_defn, root_prior = get_process_defn_and_prior(distn, kappa, tau)
    scene = {
            "node_count" : edge_count + 1,
            "process_count" : 1,
            "state_space_shape" : [4, 4],
            "tree" : {
                "row_nodes" : list(row_nodes),
                "column_nodes" : list(column_nodes),
                "edge_rate_scaling_factors" : rates,
                "edge_processes" : [0] * edge_count
                },
            "root_prior" : root_prior,
            "process_definition" : process_defn,
            "observed_data" : {
                "nodes" : nodes,
                "variables" : variables,
                "iid_observations" : columns
                }
            }

    X = pack(distn, kappa, tau, rates)
    f = functools.partial(objective_and_gradient, scene)
    result = minimize(f, X, jac=True, method='L-BFGS-B')
    print('final value of objective function:', result.fun)
    distn, kappa, tau, rates, unpacking_cost = unpack(result.x)
    print('nucleotide distribution:')
    for nt, p in zip('ACGT', distn):
        print('  ', nt, ':', p)
    print('kappa:', kappa)
    print('tau:', tau)
    print('edge rate scaling factors:')
    for r in rates:
        print('  ', r)

main()
