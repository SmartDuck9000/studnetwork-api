"""
this module works with graphs, which can be described as followed:
graph is a tree. basic usage - forming graph, where nodes are users, and links are
distances (vector distance) between users, and tree-forming is the task to define edges
so that the nearer users are, the less graph distance is between them.

also, graph supports several detail level (defined by depth, which is calculated from root-user).
nodes on each depth level have predefined number of children. Yet, graph may be constructed with lesser number of nodes
than is required to fill all children-relations.
"""

import numpy as np

from .config import *


def get_next_graph_depth(prev_depth: int = 0):
    if prev_depth in [0, None]:
        return start_depth
    else:
        return prev_depth + depth_step


def get_graph_size(depth: int):
    """returns how many nodes are in fully-equipped with nodes graph of the given depth"""
    size = 1
    cur_size = 1
    ln = len(expand_sizes)

    for i in range(min(ln, depth)):
        cur_size *= expand_sizes[i]
        size += cur_size
    if ln < depth:
        size += cur_size * later_expand_size*(depth - ln)
    return size


def form_tree(root, sorted_nodes, dist_func):
    """ 'root' is a user which becomes the root of the tree
    'sorted_nodes' - nodes which will form all the tree. they are sorted by distance to the root
    (not necessarily by dist_func)"""
    root = form_tree_recurse([root], sorted_nodes, 0, dist_func)[0]
    return tree_pop_fields(root, ['vector'])


def tree_pop_fields(root, fields):
    """deletes given fields (as iterable of keys) from root and all its children (recursively)
    returnes updated root """
    for f in fields:
        root.pop(f)
    if root['is_leaf']: return root
    for i in range(len(root['children'])):
        root['children'][i]['child'] = tree_pop_fields(root['children'][i]['child'], fields)
    return root


def form_tree_recurse(roots, nodes, depth, dist_func):
    print(' ' * depth, len(roots), len(nodes))
    if len(nodes) == 0:
        for r in roots:
            r['is_leaf'] = True
            r['children'] = []
        return roots
    if depth >= len(expand_sizes):
        children_cnt = later_expand_size
    else:
        children_cnt = expand_sizes[depth]
    rn = len(roots)
    children, nodes = nodes[:rn*children_cnt], nodes[rn*children_cnt:]

    children = form_tree_recurse(children, nodes, depth+1, dist_func)
    dist_matr = [[15 - 1 * depth for c in children] for r in roots]
    for r in roots:
        r['children'] = []
    for i in range(len(children)):
        min_cost = np.inf
        best_j = -1
        for j in range(rn):
            cost = dist_matr[j][i] + len(roots[j]['children']) * graph_group_weight
            if cost < min_cost:
                min_cost, best_j = cost, j
        roots[best_j]['children'].append({'edge_length':dist_matr[best_j][i], 'child': children[i]})
        print(depth, dist_matr[best_j][i])
    for r in roots:
        r['is_leaf'] = len(r['children']) == 0

    return roots


if __name__ == '__main__':
    for i in range(20):
        print(get_graph_size(i))
