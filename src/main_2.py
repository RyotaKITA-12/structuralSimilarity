import ast
import builtins
from collections import Counter
from itertools import chain, combinations
import os
import sys

import zss


def main():
    PATH_CODE = sys.argv[1]
    with open(PATH_CODE) as file_code:
        list_code = file_code.readlines()
        tree_code = ast.parse(''.join(list_code))

        relations_node, grammars_node, contents_node, lines_node, cols_node \
                = parse_src(tree_code)

        nodes = Node.build_nodes(
                    relations_node, grammars_node,
                    contents_node, lines_node, cols_node)

        max_depth_original = max([node.depth for node in nodes])
        max_depth_to_extract = 3
        exact_trees, similar_trees = Node.calculate_similarity_of_tree(
                                        nodes, max_depth_original,
                                        max_depth_to_extract)

        n = 6
        for id1, id2 in exact_trees[n]:
            srcAfter = Node.createDef(list_code, nodes[id1], nodes[id2], nodes, n, 1)

        with open("../data/result/src/output_" + os.path.basename(pathSrc), 'w') as f:
            f.write(''.join(srcAfter))


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


class Node:
    def __init__(self):
        self.id = None
        self.grammar = None
        self.content = None
        self.line = None
        self.columns = (0, 0)
        self.type_node = None
        self.parent = 0
        self.children = []
        self.dist_leave = 0
        self.depth = None

    @staticmethod
    def build_nodes(relations, grammars, contents, lines, cols):
        num_node = len(relations)
        nodes = [Node() for _ in range(num_node + 1)]
        dic_count_child = Counter(list(chain.from_iterable(relations)))

        nodes[0].children = Node.fetch_children(nodes, relations, 0)
        nodes[0].parent = -1
        nodes[0].type_node = 'root'

        for i_node in range(num_node):
            id_node = relations[i_node][0]
            nodes[i_node+1].id          = id_node
            nodes[i_node+1].grammar     = grammars[id_node]
            nodes[i_node+1].content     = contents[id_node]
            nodes[i_node+1].line        = lines[i_node+1]
            nodes[i_node+1].cols        = cols[i_node+1]
            nodes[i_node+1].children    = Node.fetch_children(
                                            nodes, relations, id_node)
            nodes[i_node+1].type_node   = Node.lookup_node_type(
                                            dic_count_child[id_node] - 1)

            for child in nodes[i_node+1].children:
                child.parent = id_node

        for leaf_node in [node for node in nodes if node.type_node == 'leaf']:
            Node.calculate_distance_leave(nodes, leaf_node)

        Node.calculate_node_depth(nodes[0])

        return nodes

    @staticmethod
    def fetch_children(nodes, relations, id_node):
        return [nodes[r[0]] for r in relations if r[1] == id_node]

    @staticmethod
    def lookup_node_type(num_child):
        if num_child > 0:
            return 'inner'
        elif num_child == 0:
            return 'leaf'

    @staticmethod
    def calculate_node_depth(node, d=0):
        node.depth = d
        for child in node.children:
            Node.calculate_node_depth(child, d+1)

    @staticmethod
    def calculate_distance_leave(nodes, leaf_node):
        if leaf_node.id == 0:
            return
        if nodes[leaf_node.parent].dist  < leaf_node.dist + 1:
            nodes[leaf_node.parent].dist = leaf_node.dist + 1
            Node.calculate_distance_leave(nodes, leaf_node.parent)

    @staticmethod
    def getChildren(node):
        return node.children

    @staticmethod
    def getElem(node):
        return node.elem

    @staticmethod
    def calculate_similarity_of_tree(
            nodes, max_depth_original, max_depth_to_extract=5):

        extracted_trees = Node.extract_trees_of_depth(
                            nodes, max_depth_original, max_depth_to_extract)

        combinatnions_of_subtree = \
                [list(combinations(extracted_trees[i], 2)) \
                    for i in range(max_depth_original - max_depth_to_extract)]
        exact_trees = {}
        similar_trees = {}
        for i, combinations in enumerate(combinatnions_of_subtree):
            depth = i + max_depth_to_extract
            similar_trees.update({depth : {}})
            exact_trees  .update({depth : []})
            for tree_1, tree_2 in combinations:
                distance_edit = zss.simple_distance(
                                    nodes[tree_1], nodes[tree_2],
                                    Node.getChildren, Node.getElem, strdist)
                if distance_edit == 0:
                    exact_trees[depth]  .append( \
                                            (tree_1, tree_2))
                else:
                    similar_trees[depth].update( \
                                            {(tree_1, tree_2): distance_edit})
        return exact_trees, similar_trees

    @staticmethod
    def extract_trees_of_depth(
            nodes, max_depth_original, max_depth_to_extract=5):

        extracted_trees = \
                [[] for _ in range(max_depth_to_extract, max_depth_original)]

        for n in range(len(nodes)+1):
            if nodes[n + 1].dist >= max_depth_to_extract:
                extracted_trees[nodes[n + 1].dist - max_depth_to_extract] \
                        .append(nodes[n + 1].id)
#        return extracted_trees

    @staticmethod
    def create_function(nodes, list_code, tree_1, tree_2, num_of_func):
        lines_1 = Node.select_line_of_node(tree_1, set())
        lines_2 = Node.select_line_of_node(tree_2, set())
        replace_args    = Node.select_args   ((nodes, tree_1, tree_2)
        replace_returns = Node.select_returns((nodes, tree_1, tree_2)
        dic_line_diff_1, dic_line_diff_2 = {}, {}
        dic_var_index_1 = {var[0].content: i + 1 \
                            for i, var in enumerate(replace_returns)}
        dic_var_index_2 = {var[1].content: i + 1 \
                            for i, var in enumerate(replace_returns)}

        indent_base = 0
        for line in src[min(lines1)]:
            if line == '   ':
                indent_base += 1
        for node_1, node_2 in replace_returns:
            src, dic_var_index_1, dic_line_diff_1 = Node.update_to_variable( \
                                                        src, node_1,
                                                        dic_var_index_1,
                                                        dic_line_diff_1)
            src, dic_var_index_2, dic_line_diff_2 = Node.update_to_variable( \
                                                        src, node_1,
                                                        dic_var_index_2,
                                                        dic_line_diff_2)
        src_of_func = src[min(lines_1)-1 : max(lines_1)]
        for i, line in enumerate(src_of_func):
            src_of_func[i] = '    ' + line[indent_base:]
        args_in_func = [f"var{dic_var_index_1[t1]}" \
                                for t1, _ in replace_args]
        returns_in_func   = [f"var{dic_var_index_1[t1]}" \
                                for t1, _ in replace_returns]
        txt_args_in_func    = ', '.join(args_in_func)
        txt_returns_in_func = ', '.join(returns_in_func)
        txt_define_func = f"def function{num_of_func}({txt_args_in_func}):\n"
        txt_define_returns = f"    return {txt_returns_in_func}\n\n"
        template = [txt_define_func, src_of_func, txtReturn]
        dic_var_index_1.keys()
        args_in_exec1 = ", ".join(dirVar1.keys())
        args_in_exec2 = ", ".join(dirVar2.keys())
        src[min(lines2) - 1:max(lines2)] = f"{txtArguments2} = function{nFunc}({txtArguments2})\n"
        txtArguments1 = ", ".join(dirVar1.keys())
        src[min(lines1) - 1:max(lines1)] = f"{txtArguments1} = function{nFunc}({txtArguments1})\n"
        src = template + src
        print(''.join(src))
        return src

    @staticmethod
    def select_line_of_node(node, lines=set()):
        if node.line != 0:
            lines.add(node.line)
        for child in node.children:
            Node.select_line_of_node(child, lines)
        return list(sorted(lines))

    @staticmethod
    def select_args(nodes, t1, t2, args=[])
        targets = ['Name', 'Constant']
        builtins = dir(__builtins__)
        is_name = all([t1.grammar == 'Name', t1.content not in builtins])
        is_constant = all([t1.elem == 'Constant', t1.content != t2.content])
        if is_name or is_constant:
            if not (len(t1.children) == 1 and t1.children[0] == 'store'):
                args.append([t1, t2])
        for c1, c2 in zip(t1.children, t2.children):
            Node.selectArgs(nodes, c1, c2, args, returns)
        return args

    def select_returns(nodes, t1, t2, returns=[]):
        targets = ['Name', 'Constant']
        builtins = dir(__builtins__)
        is_name = all([t1.grammar == 'Name', t1.content not in builtins])
        is_constant = all([t1.elem == 'Constant', t1.content != t2.content])
        if is_name or is_constant:
            returns.append([t1, t2])
        for c1, c2 in zip(t1.children, t2.children):
            Node.selectArgs(nodes, c1, c2, args, returns)
        return returns

    @staticmethod
    def update_to_variable(src, node, dirVars, dirLine):
        srcBefore = list(src[node.line - 1])
        if node.line - 1 not in dirLine: srcBefore[node.cols[0]:node.cols[1]] = f"var{dirVars[node.content]}" dirLine[node.line - 1] = len(list(src[node.line - 1])) - len(srcBefore)
        else:
            diff = dirLine[node.line - 1]
            srcBefore[node.cols[0] - diff: node.cols[1] - diff] = f"var{dirVars[node.content]}"
            dirLine[node.line - 1] += len(list(src[node.line - 1])) - len(srcBefore)
        srcUpdate = ''.join(srcBefore)
        src[node.line - 1] = srcUpdate
        return src, dirVars, dirLine

    @staticmethod
    def showChild(node, varInstance):
        print('-----')
        print(node.id, node.content)
        print(getattr(node, varInstance))
        for child in node.children:
            Node.showChild(child, varInstance)


def strdist(s1, s2):
    if s1 == s2:
        return 0
    else:
        return 1


if __name__ == '__main__':
    main()
