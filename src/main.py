import ast
import builtins
from collections import Counter
import itertools
import os
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
        rels, attrs, depths, contents, lines, cols = walk(ast.parse(''.join(src)))
        # 抽象構文木の生成
        nodes, dmax = Node.getNode(rels, attrs, depths, contents, lines, cols)

        k = 3
        # 深さk以上のnode間の類似度計量
        exacts, similars = Node.calSimilar(k, nodes, rels, dmax)

        # Node.showChild(nodes[32], "cols")

        n = 6
        for t1, t2 in exacts[n]:
            srcAfter = Node.createDef(src, t1, t2, nodes, n, 1)

        with open("../data/result/src/output_"+os.path.basename(pathSrc), 'w') as f:
            f.write(''.join(srcAfter))


def walk(node, nodes=[], pindex=0, indent=0, attrs=[], lines=[], depths=[],
         rels=[], noAttrs=[], contents=[], cols=[]):
    depths.append(int(indent))
    attrs.append(node.__class__.__name__)
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

    name = str(type(node).__name__)
    index = len(nodes)
    nodes.append(index)
    noAttrs.append([index, name])
    if index != pindex:
        rels.append([index, pindex])
    for n in ast.iter_child_nodes(node):
        walk(n, nodes, index, indent + 1, attrs, lines, depths, rels, noAttrs, contents, cols)

    return rels, attrs, depths, contents, lines, cols


class Node:
    def __init__(self):
        self.id = None
        self.elem = None
        self.type = None
        self.parent = 0
        self.children = []
        self.dmax = None
        self.line = None
        self.cols = (0, 0)
        self.dist = 0
        self.depth = None
        self.content = None

    @staticmethod
    def getNode(rels, attrs, depths, contents, lines, cols):
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
            nodes[n + 1].content = contents[nodeID]
            if k > 0:
                nodes[n + 1].children = [nodes[r[0]] for r in rels if r[1] == nodeID]
                nodes[n + 1].type = 'inner'
            else:
                nodes[n + 1].type = 'leaf'
                leafs.append(nodes[n + 1].id)
            for child in nodes[n + 1].children:
                child.parent = nodeID
            nodes[n + 1].line = lines[n + 1]
            nodes[n + 1].cols = cols[n + 1]
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

    @staticmethod
    def showChild(node, varInstance):
        print('-----')
        print(node.id, node.content)
        print(getattr(node, varInstance))
        for child in node.children:
            Node.showChild(child, varInstance)

    @staticmethod
    def selectDiff(t1, t2, diffs=[]):
        targets = ['Name', 'Constant']
        # checkElem = t1.elem in targets and t2.elem in targets
        builtins = dir(__builtins__)
        checkName = all([t1.elem == t2.elem == 'Name', t1.content not in builtins, t2.content not in builtins])
        checkConstant = all([t1.elem == t2.elem == 'Constant', t1.content != t2.content])
        if checkName or checkConstant:
            diffs.append([t1.id, t2.id])
        for c1, c2 in zip(t1.children, t2.children):
            Node.selectDiff(c1, c2, diffs)
        return diffs

    @staticmethod
    def createDef(src, t1, t2, nodes, n, nFunc):
        lines1 = Node.selectLine(nodes[t1], set())
        lines2 = Node.selectLine(nodes[t2], set())
        diffs = Node.selectDiff(nodes[t1], nodes[t2])
        indent = 0
        dirVar1, dirVar2 = {}, {}
        dirLine1, dirLine2 = {}, {}
        for c in src[min(lines1)]:
            if c == '  ':
                indent += 1
        n = 1
        for id1, id2 in diffs:
            src, dirVar1, dirLine1 = Node.updateSrc(src, nodes[id1], dirVar1, dirLine1, n)
            src, dirVar2, dirLine2 = Node.updateSrc(src, nodes[id2], dirVar2, dirLine2, n)
            n += 1
        srcFunction = src[min(lines1) - 1:max(lines1)]
        for i, line in enumerate(srcFunction):
            srcFunction[i] = '    ' + line[indent:]
        arguments = [f"var{i+1}" for i in range(len(dirVar1))]
        txtArguments = ", ".join(arguments)
        txtFunction = f"def function{nFunc}({txtArguments}):\n"
        txtReturn = f"    return {txtArguments}\n\n"
        template = [txtFunction, txtReturn]
        template[1:1] = srcFunction
        txtArguments2 = ", ".join(dirVar2.keys())
        src[min(lines2)-1:max(lines2)] =  f"{txtArguments2} = function{nFunc}({txtArguments2})\n"
        txtArguments1 = ", ".join(dirVar1.keys())
        src[min(lines1)-1:max(lines1)] =  f"{txtArguments1} = function{nFunc}({txtArguments1})\n"
        src = template + src
        print(''.join(src))
        return src


    @staticmethod
    def updateSrc(src, node, dirVar, dirLine, n):
        if node.content not in dirVar:
            dirVar[node.content] = str(n)
        srcBefore = list(src[node.line - 1])
        if node.line - 1 not in dirLine:
            srcBefore[node.cols[0]:node.cols[1]] = f"var{dirVar[node.content]}"
            dirLine[node.line - 1] = len(list(src[node.line - 1])) - len(srcBefore)
        else:
            diff = dirLine[node.line - 1]
            srcBefore[node.cols[0] - diff: node.cols[1] - diff] = f"var{dirVar[node.content]}"
            dirLine[node.line - 1] += len(list(src[node.line - 1])) - len(srcBefore)
        srcUpdate = ''.join(srcBefore)
        src[node.line - 1] = srcUpdate
        return src, dirVar, dirLine


def strdist(s1, s2):
    if s1 == s2:
        return 0
    else:
        return 1


if __name__ == '__main__':
    main()
