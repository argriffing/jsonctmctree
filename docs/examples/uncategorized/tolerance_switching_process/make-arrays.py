from __future__ import print_function, division

import itertools

def get_diffs(a, b):
    return [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]

def main():

    # List all of the self-consistent multivariate states.
    pri_to_tol = [0, 0, 1, 1, 2, 2]
    legit_states = []
    for state in itertools.product([0, 1, 2, 3, 4, 5], [0, 1], [0, 1], [0, 1]):
        pri, tols = state[0], state[1:]
        if not tols[pri_to_tol[pri]]:
            continue
        s = list(state)
        legit_states.append(s)

    # print all legit states
    for s in legit_states:
        print(s)
    print()

    print([1/len(legit_states)] * len(legit_states))
    print()

    # List all of the possible transitions.
    forward_trans = [
            (0, 1), (2, 3), (4, 5),
            (0, 2), (2, 4),
            (1, 3), (3, 5),
            ]
    backward_trans = [(b, a) for a, b in forward_trans]
    trans = forward_trans + backward_trans
    pri_rows = []
    pri_cols = []
    pri_rates = []
    tol_rows = []
    tol_cols = []
    tol_rates = []
    for sa in legit_states:
        for sb in legit_states:
            diffs = get_diffs(sa, sb)
            if len(diffs) != 1:
                continue
            i, x, y = diffs[0]
            if i == 0:
                if (x, y) in trans:
                    pri_rows.append(sa)
                    pri_cols.append(sb)
                    pri_rates.append(3/7)
            else:
                tol_rows.append(sa)
                tol_cols.append(sb)
                tol_rates.append(1)

    #expected_pri_rate = sum(pri_rates) / len(legit_states)

    rows = pri_rows + tol_rows
    cols = pri_cols + tol_cols
    #rates = [r / expected_pri_rate for r in pri_rates] + tol_rates
    rates = pri_rates + tol_rates

    print(',\n'.join(str(s) for s in rows))
    print()

    print(',\n'.join(str(s) for s in cols))
    print()

    print(rates)
    print()

    # Now let's create some transition reductions:
    # synonymous, nonsynonymous, gain-of-tolerance, loss-of-tolerance
    forward_trans_syn = [(0, 1), (2, 3), (4, 5)]
    backward_trans_syn = [(b, a) for a, b in forward_trans_syn]
    forward_trans_non = [(0, 2), (2, 4), (1, 3), (3, 5)]
    backward_trans_non = [(b, a) for a, b in forward_trans_non]
    trans_syn = forward_trans_syn + backward_trans_syn
    trans_non = forward_trans_non + backward_trans_non
    syn_triples = []
    non_triples = []
    gain_triples = []
    loss_triples = []
    for sa in legit_states:
        for sb in legit_states:
            diffs = get_diffs(sa, sb)
            if len(diffs) != 1:
                continue
            i, x, y = diffs[0]
            if i == 0:
                if (x, y) in trans_syn:
                    syn_triples.append((sa, sb, 1))
                elif (x, y) in trans_non:
                    non_triples.append((sa, sb, 1))
            else:
                if y:
                    gain_triples.append((sa, sb, 1))
                else:
                    loss_triples.append((sa, sb, 1))

    print('transition_rates syn:')
    rows, cols, weights = zip(*syn_triples)
    print(',\n'.join(str(s) for s in rows))
    print()
    print(',\n'.join(str(s) for s in cols))
    print()
    print(weights)
    print()

    print('transition_rates non:')
    rows, cols, weights = zip(*non_triples)
    print(',\n'.join(str(s) for s in rows))
    print()
    print(',\n'.join(str(s) for s in cols))
    print()
    print(weights)
    print()

    print('transition_rates gain:')
    rows, cols, weights = zip(*gain_triples)
    print(',\n'.join(str(s) for s in rows))
    print()
    print(',\n'.join(str(s) for s in cols))
    print()
    print(weights)
    print()

    print('transition_rates loss:')
    rows, cols, weights = zip(*loss_triples)
    print(',\n'.join(str(s) for s in rows))
    print()
    print(',\n'.join(str(s) for s in cols))
    print()
    print(weights)
    print()

main()
