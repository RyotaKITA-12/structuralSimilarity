import ast
import builtins
import os
import sys

from graphviz import Digraph


def main():
    PATH_SRC = sys.argv[1]
    with open(PATH_SRC) as file_src:
        list_src = file_src.readlines()
        tree_src = ast.parse(''.join(list_src))

        (relations_node, grammars_node,
         contents_node, lines_node, cols_node) = parse_src(tree_src)

        nodes_to_replace     = Node.build_nodes_to_replace(
                                relations_node, grammars_node,
                                contents_node, lines_node, cols_node)

        max_depth_original = max([node.depth for node in nodes_to_replace])
        max_depth_to_extract = 6
        exact_trees, similar_trees = Node.calculate_similarity_of_tree(
                                        nodes_to_replace,
                                        max_depth_original,
                                        max_depth_to_extract)

        n = 6
        for id1, id2 in exact_trees[n]:
            id1 = exact_trees[max_depth_to_extract][0][0]
            id2 = exact_trees[max_depth_to_extract][0][1]
            src_functionalized = Node.create_function(list_src, nodes_to_replace,
                                                      nodes_to_replace[id1],
                                                      nodes_to_replace[id2],
                                                      num_of_func=1)
        print(''.join(src_functionalized))
        print(exact_trees)
        # print(similar_trees)
        path_base_for_saving = "../data/result/src/output_"
        with open(path_base_for_saving + os.path.basename(PATH_SRC), 'w') as f:
            f.write(''.join(src_functionalized))


def visit(node, nodes, pindex, g):
    name = node.grammar
    content = node.content
    index = len(nodes)
    nodes.append(index)
    g.node(str(index), name + "\n" + content)
    if index != pindex:
        g.edge(str(pindex), str(index))
    for n in node.children:
        visit(n, nodes, index, g)

def parse_src(
        node, nodes=[], index_previous=0, indent=0,
        relations=[], grammars=[], contents=[], lines=[], cols=[]):

    index = len(nodes)
    nodes.append(index)
    if index != index_previous:
        relations.append([index, index_previous])
    grammars.append(node.__class__.__name__)
    contents.append(ast.unparse(node))
    if hasattr(node, 'lineno'):
        lines.append(node.lineno)
    else:
        lines.append(0)
    col = [0, 0]
    if hasattr(node, 'col_offset'):
        col[0] = node.col_offset
    if hasattr(node, 'end_col_offset'):
        col[1] = node.end_col_offset
    cols.append(col)

    for child in ast.iter_child_nodes(node):
        parse_src(child, nodes, index, indent+1,
                  relations, grammars, contents, lines, cols)

    return relations, grammars, contents, lines, cols




def strdist(s1, s2):
    if s1 == s2:
        return 0
    else:
        return 1


if __name__ == '__main__':
    main()
