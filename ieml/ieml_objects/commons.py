from collections import defaultdict
from functools import total_ordering

import itertools
import numpy
from gi.overrides.Gtk import TreePath

from ieml.commons import TreeStructure, TreePath, coord, tree_op
from ieml.exceptions import InvalidPathException
from ieml.ieml_objects.exceptions import InvalidIEMLObjectArgument, InvalidTreeStructure


class IEMLType(type):
    """This metaclass enables the comparison of class times, such as (Sentence > Word) == True"""

    def __init__(cls, name, bases, dct):
        child_list = ['Term', 'Morpheme', 'Word', 'Clause', 'Sentence',
                     'SuperClause', 'SuperSentence', 'Text', 'Hyperlink', 'Hypertext']
        if name in child_list:
            cls.__rank = child_list.index(name) + 1
        else:
            cls.__rank = 0

        super(IEMLType, cls).__init__(name, bases, dct)

    def __hash__(self):
        return self.__rank

    def __eq__(self, other):
        if isinstance(other, IEMLType):
            return self.__rank == other.__rank
        else:
            return False

    def __ne__(self, other):
        return not IEMLType.__eq__(self, other)

    def __gt__(self, other):
        return IEMLType.__ge__(self, other) and self != other

    def __le__(self, other):
        return IEMLType.__lt__(self, other) and self == other

    def __ge__(self, other):
        return not IEMLType.__lt__(self, other)

    def __lt__(self, other):
        return self.__rank < other.__rank

    def rank(self):
        return self.__rank


class IEMLObjects(TreeStructure, metaclass=IEMLType):
    closable = False

    def __init__(self, children, literals=None):
        super().__init__()
        self.children = tuple(children)

        _literals = []
        if literals is not None:
            if isinstance(literals, str):
                _literals = [literals]
            else:
                try:
                    _literals = tuple(literals)
                except TypeError:
                    raise InvalidIEMLObjectArgument(self.__class__, "The literals argument %s must be an iterable of "
                                                                    "str or a str."%str(literals))

        self.literals = tuple(_literals)
        self._do_precompute_str()

    def __gt__(self, other):
        if not isinstance(other, IEMLObjects):
            raise NotImplemented

        if self.__class__ != other.__class__:
            return self.__class__ > other.__class__

        return self._do_gt(other)

    def _do_gt(self, other):
        return self.children > other.children

    def compute_str(self, children_str):
        return '#'.join(children_str)

    def _compute_str(self):
        if self._str is not None:
            return self._str
        _literals = ''
        if self.literals:
            _literals = '<' + '><'.join(self.literals) + '>'
        return self.compute_str([e._compute_str() for e in self.children]) + _literals

    def _do_precompute_str(self):
        self._str = self._compute_str()


class TreeGraph:
    def __init__(self, list_transitions):
        """
        Transitions list must be the (start, end, data) the data will be stored as the transition tag
        :param list_transitions:
        """
        # transitions : dict
        #
        self.transitions = defaultdict(list)
        for t in list_transitions:
            self.transitions[t[0]].append((t[1], t))

        self.nodes = sorted(set(self.transitions) | {e[0] for l in self.transitions.values() for e in l})

        # sort the transitions
        for s in self.transitions:
            self.transitions[s].sort(key=lambda t: self.nodes.index(t[0]))

        self.nodes_index = {n: i for i, n in enumerate(self.nodes)}
        _count = len(self.nodes)
        self.array = numpy.zeros((len(self.nodes), len(self.nodes)), dtype=bool)

        for t in self.transitions:
            for end in self.transitions[t]:
                self.array[self.nodes_index[t]][self.nodes_index[end[0]]] = True

        # checking
        # root checking, no_parent hold True for each index where the node has no parent
        parents_count = numpy.dot(self.array.transpose().astype(dtype=int), numpy.ones((_count,), dtype=int))
        no_parents = parents_count == 0
        roots_count = numpy.count_nonzero(no_parents)

        if roots_count == 0:
            raise InvalidTreeStructure('No root node found, the graph has at least a cycle.')
        elif roots_count > 1:
            raise InvalidTreeStructure('Several root nodes found.')

        self.root = self.nodes[no_parents.nonzero()[0][0]]

        if (parents_count > 1).any():
            raise InvalidTreeStructure('A node has several parents.')

        def __stage():
            current = [self.root]
            while current:
                yield current
                current = [child[0] for parent in current for child in self.transitions[parent]]

        self.stages = list(__stage())

    def __getitem__(self, item):
        if not isinstance(item, TreePath):
            raise ValueError('Invalid argument %s, must specify a TreePath object to access node '
                             'in a TreeGraph.'%str(item))
        result = []

        for product in item.develop().args:
            current = self.root
            if len(product.args) == 1:
                break

            end = False
            for c in product.args[1:]:
                if end:
                    raise InvalidPathException(self, item)

                try:
                    current = self.transitions[current][c.branch][1]
                except KeyError:
                    raise InvalidPathException(self, item)

                if c.role == 'm':
                    end = True
                    current = current[2]
                elif c.role == 'a':
                    current = current[1]
                else:
                    raise InvalidPathException(self, item)

            result.append(current)

        return result

    def path_of_node(self, node):
        if node not in self.nodes:
            # can be a mode
            nodes = [(c[0], True) for c_list in self.transitions.values() for c in c_list if c[1][2] == node]
            if not nodes:
                raise ValueError("Node not in tree graph : %s" % str(node))
        else:
            nodes = [(node, False)]

        def _build_coord(node, mode=False):
            if node == self.root:
                return [coord(branch=0, role='s')]

            parent = numpy.where(self.array[:, self.nodes_index[node]])[0][0]
            return _build_coord(parent) + [coord(branch=[c[0] for c in self.transitions[parent]].index(node),
                                                 role='m' if mode else 'a')]

        return TreePath(tree_op(type='+', args=[
            tree_op(type='*', args=_build_coord(node, mode)) for node, mode in nodes
        ]))
