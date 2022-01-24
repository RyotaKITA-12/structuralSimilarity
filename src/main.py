import ast
from collections import Counter
import itertools
import sys

import zss


def main():
    # 入力ソースコードのパスを取得
    pathSrc = sys.argv[0]
    if len(sys.argv) > 1:
        pathSrc = sys.argv[1]
    with open(pathSrc) as f:
        # ソースコードの読み込み
        src = f.readlines()

        """
        attrs = ['Module', 'Import', 'alias' ... ]
        lines = [0, 1, 0, 3, 3, 0, ... ]
        depths = [0, 1, 2, 1, 2, 3, ... ]
        rels = [[1, 0], [2, 1], [3, 0], [4, 3], ... ]]
        noAttrs = [[1, 'Import'], [2, 'alias'], [3, 'Assign'] ... ]]
        """

        # 構文解析(属性, 行番号, 深さ, 関係性, nodeID)
        attrs, lines, depths, rels, noAttrs = walk(ast.parse(''.join(src)), [], 0)

        # 抽象構文木の生成
        nodes, dmax = Node.getNode(rels, attrs, depths, lines)

        k = 3
        # 深さk以上のnode間の類似度計量
        exacts, similars = Node.calSimilar(k, nodes, rels, dmax)

        print(similars)
        print(exacts)
        n = 6
        print("---")
        for t1, t2 in exacts[n]:
            lines1 = Node.selectLine(nodes[t1], set())
            lines2 = Node.selectLine(nodes[t2], set())

            src1 = src[min(lines1)-1:max(lines1)]
            src2 = src[min(lines2)-1:max(lines2)]

            template = ["def function{}():\n", "return"]
            template[1:1] = src1
            # template[1:1]
            print(''.join(template))


def walk(node, nodes, pindex, indent=0, attrs=[], lines=[], depths=[], rels=[], noAttrs=[]):
    for f in ast.iter_fields(node):
        print(f)
    print("---")
    depths.append(int(indent))
    attrs.append(node.__class__.__name__)
    if hasattr(node, 'lineno'):
        lines.append(node.lineno)
    else:
        lines.append(0)
    name = str(type(node).__name__)
    index = len(nodes)
    nodes.append(index)
    noAttrs.append([index, name])
    if index != pindex:
        rels.append([index, pindex])
    for n in ast.iter_child_nodes(node):
        walk(n, nodes, index, indent + 1, attrs, lines, depths, rels, noAttrs)

    return attrs, lines, depths, rels, noAttrs


class Node:
    def __init__(self):
        self.id = None
        self.elem = None
        self.type = None
        self.parent = 0
        self.children = []
        self.dmax = None
        self.line = None
        self.dist = 0
        self.depth = None

    @staticmethod
    def getNode(rels, attrs, depths, lines):
        cntRels = Counter(list(itertools.chain.from_iterable(rels)))
        N = len(rels)
        nodes = [Node() for _ in range(N + 1)]
        nodes[0].children = [nodes[r[0]] for r in rels if r[1] == 0]
        nodes[0].parent = -1
        nodes[0].type = 'root'
        leafs = []
        for n in range(N):
            nodeID = rels[n][0]
            k = cntRels[nodeID] - 1
            nodes[n + 1].id = nodeID
            nodes[n + 1].elem = attrs[nodeID]
            if k > 0:
                nodes[n + 1].children = [nodes[r[0]] for r in rels if r[1] == nodeID]
                nodes[n + 1].type = 'inner'
            else:
                nodes[n + 1].type = 'leaf'
                leafs.append(nodes[n + 1].id)
            for child in nodes[n + 1].children:
                child.parent = nodeID
            nodes[n + 1].line = lines[n+1]
        for leaf in leafs:
            Node.calDist(nodes, leaf)
        Node.calDepth(nodes[0])
        dmax = max([n.depth for n in nodes])

        return nodes, dmax

    @staticmethod
    def getChildren(node):
        return node.children

    @staticmethod
    def getElem(node):
        return node.elem

    @staticmethod
    def calDepth(node, d=0):
        node.depth = d
        for child in node.children:
            Node.calDepth(child, d + 1)

    @staticmethod
    def calDist(nodes, ID):
        if str(ID) == '0':
            return
        if nodes[int(nodes[int(ID)].parent)].dist < nodes[int(ID)].dist + 1:
            nodes[int(nodes[int(ID)].parent)].dist = nodes[int(ID)].dist + 1
            Node.calDist(nodes, nodes[int(ID)].parent)

    @staticmethod
    def selectDepth(nodes, N, dmax, k=5):
        kNodes = [[] for _ in range(k, dmax)]
        for n in range(N):
            if nodes[n + 1].dist >= k:
                kNodes[nodes[n + 1].dist - k].append(nodes[n + 1].id)

        return kNodes

    @staticmethod
    def calSimilar(k, nodes, rels, dmax):
        # 深さk以上のnodeIDを取り出し
        kNodes = Node.selectDepth(nodes, len(rels), dmax, k)

        # 深さk以上の部分木の組み合わせ
        combos = [list(itertools.combinations(kNodes[i], 2)) for i in range(dmax - k)]
        exacts = {}
        similars = {}
        for i, combo in enumerate(combos):
            similars.update({i + k: {}})
            exacts.update({i + k: []})
            for t1, t2 in combo:
                s = zss.simple_distance(nodes[t1], nodes[t2], Node.getChildren, Node.getElem, strdist)
                if s == 0:
                    exacts[i + k].append((t1, t2))
                else:
                    similars[i + k].update({(t1, t2): s})
        return exacts, similars

    @staticmethod
    def selectLine(node, lines=set()):
        if node.line != 0:
            lines.add(node.line)
        for child in node.children:
            Node.selectLine(child, lines)
        return list(sorted(lines))


def strdist(s1, s2):
    if s1 == s2:
        return 0
    else:
        return 1


if __name__ == '__main__':
    main()
