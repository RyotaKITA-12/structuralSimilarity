import builtins
from collections import Counter
from copy import copy
from itertools import chain, combinations

import zss

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
    def build_nodes_to_replace(relations, grammars, contents, lines, cols):
        num_node = len(relations)
        nodes = [Node() for _ in range(num_node + 1)]
        dic_count_child = Counter(list(chain.from_iterable(relations)))

        nodes[0].children = Node.fetch_children(nodes, relations, 0)
        nodes[0].parent = 0
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

    # @staticmethod
    # def abstract_nodes_for_comparison(node):
    #     if any(issubclass(getattr(ast, node.grammar), ast.mod),
    #            issubclass(getattr(ast, node.grammar), ast.stmt):
    #     for child in node.children:


    @staticmethod
    def calculate_node_depth(node, d=0):
        node.depth = d
        for child in node.children:
            Node.calculate_node_depth(child, d+1)

    @staticmethod
    def calculate_distance_leave(nodes, leaf_node):
        if leaf_node.id == 0 or leaf_node.id == None:
            return
        if nodes[leaf_node.parent].dist_leave  < leaf_node.dist_leave + 1:
            nodes[leaf_node.parent].dist_leave = leaf_node.dist_leave + 1
            Node.calculate_distance_leave(nodes, nodes[leaf_node.parent])

    @staticmethod
    def get_children(node):
        return node.children

    @staticmethod
    def get_grammar(node):
        return node.grammar

    @staticmethod
    def calculate_similarity_of_tree(
            nodes, max_depth_original, max_depth_to_extract=5):

        extracted_trees = Node.extract_trees_of_depth(
                            nodes, max_depth_original, max_depth_to_extract)

        combinatnions_of_subtree = [list(combinations(extracted_trees[i], 2))
                    for i in range(max_depth_original - max_depth_to_extract)]
        exact_trees = {}
        similar_trees = {}
        for i, combination in enumerate(combinatnions_of_subtree):
            depth = i + max_depth_to_extract
            similar_trees.update({depth : {}})
            exact_trees  .update({depth : []})
            for id_1, id_2 in combination:
                distance_edit = zss.simple_distance(
                                    nodes[id_1], nodes[id_2],
                                    Node.get_children, Node.get_grammar,
                                    strdist)
                if distance_edit == 0:
                    exact_trees[depth]  .append((id_1, id_2))
                else:
                    similar_trees[depth].update({(id_1, id_2): distance_edit})
        return exact_trees, similar_trees

    @staticmethod
    def extract_trees_of_depth(
            nodes, max_depth_original, max_depth_to_extract):

        extracted_trees = \
                [[] for _ in range(max_depth_to_extract, max_depth_original+1)]

        for index_node in range(len(nodes)):
            if nodes[index_node].dist_leave >= max_depth_to_extract:
                (extracted_trees[nodes[index_node].dist_leave
                                 - max_depth_to_extract]
                 .append(nodes[index_node].id))
        return extracted_trees

    @staticmethod
    def create_function(src, nodes, tree_1, tree_2, num_of_func):
        exec_lines_1 = Node.select_line_of_node(tree_1, set())
        exec_lines_2 = Node.select_line_of_node(tree_2, set())
        node_args    = Node.select_args   (nodes, tree_1, tree_2)
        replace_returns, node_returns = Node.select_returns(nodes,
                                                            tree_1, tree_2)
        dic_line_diff_1, dic_line_diff_2 = {}, {}
        dic_var_index_1 = {var[0].content: i + 1
                            for i, var in enumerate(node_returns)}
        dic_var_index_2 = {var[1].content: i + 1
                            for i, var in enumerate(node_returns)}

        indent_base = 0
        for line in src[min(exec_lines_1)]:
            if line == '   ':
                indent_base += 1
        for node_1, node_2 in replace_returns:
            src, dic_var_index_1, dic_line_diff_1 = Node.update_to_variable( \
                                                        src, node_1,
                                                        dic_var_index_1,
                                                        dic_line_diff_1)
            src, dic_var_index_2, dic_line_diff_2 = Node.update_to_variable( \
                                                        src, node_2,
                                                        dic_var_index_2,
                                                        dic_line_diff_2)
        list_to_process_func = src[min(exec_lines_1)-1 : max(exec_lines_1)]
        for i, line in enumerate(list_to_process_func):
            list_to_process_func[i] = '    ' + line[indent_base:]
        args_in_func    = [f"var{dic_var_index_1[t1.content]}"
                                for t1, _ in node_args]
        returns_in_func = [f"var{dic_var_index_1[t1.content]}"
                                for t1, _ in node_returns]
        txt_args_in_func    = ', '.join(args_in_func)
        txt_returns_in_func = ', '.join(returns_in_func)
        src_to_define_func     = (f"def function{num_of_func}"
                                  f"({txt_args_in_func}):\n")
        src_to_define_returns  = f"    return {txt_returns_in_func}\n\n"

        args_in_exec1 = [t1.content for t1, _  in node_args]
        args_in_exec2 = [t2.content for _ , t2 in node_args]
        src_args_in_exec1 = ", ".join(args_in_exec1)
        src_args_in_exec2 = ", ".join(args_in_exec2)

        returns_in_exec1 = [t1.content for t1, _  in node_returns]
        returns_in_exec2 = [t2.content for _ , t2 in node_returns]
        src_returns_in_exec1 = ", ".join(returns_in_exec1)
        src_returns_in_exec2 = ", ".join(returns_in_exec2)

        src_to_process_func = "".join(list_to_process_func)
        src_of_func = [src_to_define_func, src_to_process_func,
                       src_to_define_returns]

        src[min(exec_lines_2)-1 : max(exec_lines_2)] = (
                f"{src_returns_in_exec2} = "
                f"function{num_of_func}({src_args_in_exec2})\n")
        src[min(exec_lines_1)-1 : max(exec_lines_1)] = (
                f"{src_returns_in_exec1} = "
                f"function{num_of_func}({src_args_in_exec1})\n")

        src = src_of_func + src
        return src

    @staticmethod
    def select_line_of_node(node, lines=set()):
        if node.line != 0:
            lines.add(node.line)
        for child in node.children:
            Node.select_line_of_node(child, lines)
        return list(sorted(lines))

    @staticmethod
    def select_args(nodes, t1, t2, args=[]):
        dic_builtin_func = dir(__builtins__)
        is_name     = all([t1.grammar == 'Name',
                           t1.content not in dic_builtin_func])
        is_constant = all([t1.grammar == 'Constant',
                           t1.content != t2.content])
        if is_name or is_constant:
            if ((not len(t1.children) == 0) and
                (not (t1.children[0].grammar == 'Store'))):
                args.append([t1, t2])
        for child_1, child_2 in zip(t1.children, t2.children):
            Node.select_args(nodes, child_1, child_2, args)
        return args

    @staticmethod
    def select_returns(nodes, t1, t2, replaces=[], returns=[],
                       check_for_duplicates=[]):
        dic_builtin_func = dir(__builtins__)
        is_name     = all([t1.grammar == 'Name',
                           t1.content not in dic_builtin_func])
        is_constant = all([t1.grammar == 'Constant',
                           t1.content != t2.content])
        if is_name or is_constant:
            replaces.append([t1, t2])
            if (t1.content not in check_for_duplicates and
                t2.content not in check_for_duplicates):
                returns.append([t1, t2])
                check_for_duplicates.append(t1.content)
                check_for_duplicates.append(t2.content)
        for child_1, child_2 in zip(t1.children, t2.children):
            Node.select_returns(nodes, child_1, child_2, replaces, returns,
                                check_for_duplicates)
        return replaces, returns

    @staticmethod
    def update_to_variable(src, node, dic_var_index, dic_line_diff):
        src_before_rewriting = list(src[node.line - 1])
        src_for_rewriting = copy(src_before_rewriting)
        if node.line - 1 not in dic_line_diff:
            src_for_rewriting[node.cols[0] : node.cols[1]] = \
                                            f"var{dic_var_index[node.content]}"
            dic_line_diff[node.line-1] = (len(src_before_rewriting)
                                          - len(src_for_rewriting))
        else:
            diff = dic_line_diff[node.line-1]
            src_for_rewriting[node.cols[0]-diff : node.cols[1]-diff] = \
                                            f"var{dic_var_index[node.content]}"
            dic_line_diff[node.line-1] += (len(src_before_rewriting)
                                          - len(src_for_rewriting))
        src_after_rewriting = ''.join(src_for_rewriting)
        src[node.line - 1] = src_after_rewriting
        return src, dic_var_index, dic_line_diff
