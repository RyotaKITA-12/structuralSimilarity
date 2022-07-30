import ast
import os
import sys

from graphviz import Digraph


class AstGraph:
    path_src = sys.argv[0]
    base = './'

    def __init__(self):
        if len(sys.argv) > 1:
            self.path_src = sys.argv[1]
        if len(sys.argv) > 2:
            self.base = sys.argv[2]
        self.name_src = os.path.basename(self.path_src)[:-3]
        with open(self.path_src) as f:
            src = f.read()
            graph = Digraph(format="png")
            self._visit(ast.parse(src), [], 0, graph)
            graph.render(self.base + self.name_src)

    def _visit(self, node, nodes, pindex, g):
        name = str(type(node).__name__)
        index = len(nodes)
        nodes.append(index)
        if index != 0:
            g.node(str(index), f"{str(index)}\n{name}", penwidth="3")
        if pindex != 0:
            if index != pindex:
                g.edge(str(pindex), str(index))
        for n in ast.iter_child_nodes(node):
            self._visit(n, nodes, index, g)

if __name__ == '__main__':
    a = AstGraph()

