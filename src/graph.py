import ast
import os
import sys

from graphviz import Digraph


def main():
    # 入力ソースコードのパスを取得
    pathSrc = sys.argv[0]
    if len(sys.argv) > 1:
        pathSrc = sys.argv[1]
    # 入力ソースコードのファイル名を取得
    nameSrc = os.path.basename(pathSrc)[:-3]
    # 保存するディレクトリの設定
    base = '../data/result/graph/'
    with open(pathSrc) as f:
        # ソースコードの読み込み
        src = f.read()
        # グラフの作成
        graph = Digraph(format="png")
        visit(ast.parse(src), [], 0, graph)
        graph.render(base + nameSrc)


def visit(node, nodes, pindex, g):
    name = str(type(node).__name__)
    content = ast.unparse(node)
    index = len(nodes)
    nodes.append(index)
    g.node(str(index), str(index) + "\n" + name + "\n" + content)
    if index != pindex:
        g.edge(str(pindex), str(index))
    for n in ast.iter_child_nodes(node):
        visit(n, nodes, index, g)


if __name__ == '__main__':
    main()
