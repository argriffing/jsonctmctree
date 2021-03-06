"""
Given a newick gene tree, return a species tree with averaged branch lengths.

The leaves of the tree should be named according to the taxa.

OK so this module/script was based on the flawed premise that
if a set of branches in a gene tree have the same set of subtree leaf species,
then these branches can be identified with each other in the species tree,
for example for the purpose of averaging their branch lengths to get
branch length guesses.

"""
from __future__ import print_function, division


# Example newick gene tree input.
"""
(((((((cerevisiaeYDR450W:0.0208250416694,paradoxusYDR450W:0.0187907761474):0.00187312520584,mikataeYDR450W:0.0447343695086):0.0101057212007,kudriavzeviiYDR450W:0.0302301795725):0.0135677728727,bayanusYDR450W:0.0372329696241):0.0537401647561,castelliiYDR450W:0.0586859466806):0.0200584641939,(((((cerevisiaeYML026C:0.0208250416694,paradoxusYML026C:0.0187907761474):0.00187312520584,mikataeYML026C:0.0447343695086):0.0101057212007,kudriavzeviiYML026C:0.0302301795725):0.0135677728727,bayanusYML026C:0.0372329696241):0.0537401647561,castelliiYML026C:0.0586859466806):0.0200584641939):0.1,kluyveriYML026C:0.032938469918);
"""


from collections import defaultdict
import argparse
import sys

import networkx as nx

import dendropy


def read_newick(fin):
    # use dendropy to read this newick file
    t = dendropy.Tree(stream=fin, schema='newick')
    nodes = list(t.preorder_node_iter())
    id_to_idx = {id(n) : i for i, n in enumerate(nodes)}
    edges = []
    edge_rates = []
    for dendro_edge in t.preorder_edge_iter():
        if dendro_edge.tail_node and dendro_edge.head_node:
            na = id_to_idx[id(dendro_edge.tail_node)]
            nb = id_to_idx[id(dendro_edge.head_node)]
            edges.append((na, nb))
            edge_rates.append(dendro_edge.length)
    name_to_node = {str(n.taxon) : id_to_idx[id(n)] for n in t.leaf_nodes()}
    return edges, edge_rates, name_to_node


def _nx_to_newick(T, na, nb, node_to_name, edge_to_rate):
    successors = list(T.successors(nb))
    if successors:
        arr = []
        for nc in successors:
            s = _nx_to_newick(T, nb, nc, node_to_name, edge_to_rate)
            arr.append(s)
        base_name = '(' + ', '.join(arr) + ')'
    else:
        base_name = node_to_name.get(nb, None)
        if base_name is None:
            raise Exception('Found a node that has no successors but also '
                    'has no leaf name.')
    if na is not None:
        edge = (na, nb)
        rate = edge_to_rate[edge]
        return base_name + ':' + str(rate)
    else:
        return base_name + ';'


def nx_to_newick(T, node_to_name, edge_to_rate):
    root = list(nx.dfs_preorder_nodes(T))[0]
    return _nx_to_newick(T, None, root, node_to_name, edge_to_rate)


def process_newick_string(newick_stream_in, newick_stream_out, paralogs):

    # Define the map from paralog name to index.
    paralog_name_to_idx = {s : i for i, s in enumerate(paralogs)}

    # Parse the newick string.
    edges, edge_rates, name_to_node = read_newick(newick_stream_in)
    original_edge_to_idx = {e : i for i, e in enumerate(edges)}

    # Break the full names into species and gene components.
    # At the same time, track the species names,
    # and track each paralog and species index.
    node_to_paralog_idx = dict()
    node_to_species_idx = dict()
    species_name_to_idx = dict()
    species_list = []
    for full_name, node in name_to_node.items():
        paralog_names = []
        species_names = []
        for p in paralogs:
            if full_name.endswith(p):
                paralog_names.append(p)
                species_names.append(full_name[:-len(p)])
        if not species_names or not paralog_names:
            raise Exception('The input name "%s" does not seem to be in '
                    'the form of a species name prefix followed by a gene '
                    'name suffix, for the given list of gene names "%s".' % (
                        full_name, paralogs))
        if len(paralog_names) != 1 or len(species_names) != 1:
            raise Exception('Failed to uniquely parse the name "%s" '
                    'into a species name followed by a gene name.' % full_name)
        paralog_name = paralog_names[0]
        species_name = species_names[0]

        # Map the node of the full tree to the species index.
        species_idx = species_name_to_idx.get(species_name, None)
        if species_idx is None:
            species_idx = len(species_list)
            species_name_to_idx[species_name] = species_idx
            species_list.append(species_name)
        node_to_species_idx[node] = species_idx

        # Map the node of the full tree to the paralog index.
        paralog_idx = paralog_name_to_idx.get(paralog_name, None)
        if paralog_idx is None:
            raise Exception('Failed to interpret the paralog name for '
                    'the full name "%s"' % full_name)
        node_to_paralog_idx[node] = paralog_idx

    # Create the full gene tree.
    T = nx.DiGraph()
    T.add_edges_from(edges)

    # For each node of the full gene tree,
    # map the node to a sorted tuple of subtree species indices.
    node_to_subtree_species_indices = dict()
    for na in nx.dfs_postorder_nodes(T):
        subtree_species_indices = set()
        successors = list(T.successors(na))
        if successors:
            for nb in successors:
                subtree_species_indices.update(
                        node_to_subtree_species_indices[nb])
        else:
            subtree_species_indices.add(node_to_species_idx[na])
        node_to_subtree_species_indices[na] = tuple(
                sorted(subtree_species_indices))

    # Each unique collection of descendent species indices
    # will corrspond to a unique node in the species tree.
    unique_descendent_species_index_tuples = set(
            node_to_subtree_species_indices.values())
    descendent_species_idx_list = list(unique_descendent_species_index_tuples)
    descendent_species_to_sptree_node = {tup : i for i, tup in enumerate(
        descendent_species_idx_list)}

    # Begin creating the species tree.
    sptree_edge_to_edge_idx = dict()
    sptree_edges = []
    sptree_edge_idx_to_original_edge_idx_list = defaultdict(list)
    for original_edge in T.edges():

        # Extract some information about the gene tree edge.
        na, nb = original_edge
        original_edge_idx = original_edge_to_idx[original_edge]

        # Determine the corresponding species tree nodes and edge.
        na_species_node = descendent_species_to_sptree_node[
                node_to_subtree_species_indices[na]]
        nb_species_node = descendent_species_to_sptree_node[
                node_to_subtree_species_indices[nb]]
        sptree_edge = (na_species_node, nb_species_node)

        # Add or look up the species tree edge index.
        sptree_edge_idx = sptree_edge_to_edge_idx.get(sptree_edge, None)
        if sptree_edge_idx is None:
            sptree_edge_idx = len(sptree_edges)
            sptree_edge_to_edge_idx[sptree_edge] = sptree_edge_idx
            sptree_edges.append(sptree_edge)

        # Add the index of the original edge to the list of such
        # edges associated to the species tree edge.
        sptree_edge_idx_to_original_edge_idx_list[sptree_edge_idx].append(
                original_edge_idx)

    # Create the list of branch lengths for the species tree
    # by averaging the corresponding branch lengths of the gene tree.
    sptree_edge_rates = []
    for sptree_edge_idx, sptree_edge in enumerate(sptree_edges):
        original_edge_rate_sum = 0
        original_edge_rate_count = 0
        original_edge_idx_list = sptree_edge_idx_to_original_edge_idx_list[
                sptree_edge_idx]
        for original_edge_idx in original_edge_idx_list:
            original_edge_rate = edge_rates[original_edge_idx]
            original_edge_rate_sum += original_edge_rate
            original_edge_rate_count += 1
        if not original_edge_rate_count:
            raise Exception('Found a branch on the species tree that does not '
                    'correspond to any branch on the gene tree.')
        sptree_edge_rate = original_edge_rate_sum / original_edge_rate_count
        sptree_edge_rates.append(sptree_edge_rate)

    # Define a map from species node to leaf species name.
    # Note that only leaf species nodes will be keys in this dict.
    sptree_node_to_species_name = dict()
    for sptree_node, species_indices in enumerate(
            unique_descendent_species_index_tuples):
        if len(species_indices) == 1:
            species_idx = species_indices[0]
            species_name = species_list[species_idx]
            sptree_node_to_species_name[sptree_node] = species_name

    # Define the map from species edge to species rate.
    sptree_edge_to_rate = dict(zip(sptree_edges, sptree_edge_rates))

    print(len(T))
    print(len(T.edges()))
    print(node_to_subtree_species_indices)
    print('species list:', species_list)
    print('sptree node to species name:', sptree_node_to_species_name)
    print('sptree edge to rate:', sptree_edge_to_rate)
    print('sptree edges:', sptree_edges)

    # Create the networkx graph representing the species tree.
    Tsp = nx.DiGraph()
    Tsp.add_edges_from(sptree_edges)

    # Get the newick string representing the species tree.
    s_out = nx_to_newick(Tsp, sptree_node_to_species_name, sptree_edge_to_rate)

    print('dendropy to newick tree:')
    print(s_out)


def main(args):
    # Read the newick string defining the gene tree on stdin,
    # and write the newick string defining the species tree on stdout,
    # averaging the corresponding branch lengths.
    process_newick_string(sys.stdin, sys.stdout, args.paralogs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--paralogs', nargs='+')
    args = parser.parse_args()
    main(args)
