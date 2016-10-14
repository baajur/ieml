from itertools import zip_longest

from ieml.ieml_objects.commons import IEMLObjects
from ieml.ieml_objects.constants import MORPHEME_SIZE_LIMIT
from ieml.ieml_objects.exceptions import InvalidIEMLObjectArgument
from ieml.ieml_objects.terms import Term


class Morpheme(IEMLObjects):
    def __init__(self, term_list):
        if isinstance(term_list, Term):
            _children = (term_list,)
        else:
            try:
                _children = tuple(e for e in term_list)
            except TypeError:
                raise InvalidIEMLObjectArgument(Morpheme, "The argument %s is not an iterable"%str(term_list))

        if not 0 < len(_children) <= MORPHEME_SIZE_LIMIT:
            raise InvalidIEMLObjectArgument(Morpheme, "Invalid terms count %d."%len(_children))

        if not all((isinstance(e, Term) for e in _children)):
            raise InvalidIEMLObjectArgument(Morpheme, "%s do not contain only Term instances."%(str(_children)))

        # check singular sequences intersection
        singular_sequences = [s for t in _children for s in t.script.singular_sequences]
        if len(singular_sequences) != len(set(singular_sequences)):
            raise InvalidIEMLObjectArgument(Morpheme, "Singular sequences intersection in %s."%
                                            str([str(t) for t in _children]))

        super().__init__(sorted(_children))

    @property
    def grammatical_class(self):
        return max(t.grammatical_class for t in self.children)

    @property
    def empty(self):
        return len(self.children) == 1 and self.children[0].empty

    def compute_str(self, children_str):
        return '('+'+'.join(children_str)+')'


class Word(IEMLObjects):
    def __init__(self, root, flexing=None, literals=None):

        if not isinstance(root, Morpheme):
            raise InvalidIEMLObjectArgument(Word, "The root %s of a word must be a Morpheme instance."%(str(root)))

        if flexing is not None:
            if not isinstance(flexing, Morpheme):
                raise InvalidIEMLObjectArgument(Word,
                                                "The flexing %s of a word must be a Morpheme instance." % (str(flexing)))
            _children = (root, flexing)
        else:
            _children = (root,)

        # the root of a word can't be empty
        if _children[0].empty:
            raise InvalidIEMLObjectArgument(Word, "The root of a Word cannot be empty (%s)."%str(_children[0]))

        super().__init__(_children, literals=literals)

    @property
    def grammatical_class(self):
        return self.root.grammatical_class

    @property
    def root(self):
        return self.children[0]

    @property
    def flexing(self):
        return self.children[1]

    def compute_str(self, children_str):
        return '['+'*'.join(children_str)+']'