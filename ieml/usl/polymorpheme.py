from itertools import product, combinations, chain, count

from collections import defaultdict
from typing import List

from ieml.commons import LastUpdatedOrderedDict
from ieml.constants import MORPHEME_SERIE_SIZE_LIMIT_CONTENT, AUXILIARY_CLASS
from ieml.dictionary.script import Script
from ieml.usl import USL


def check_polymorpheme(ms):
    assert all(isinstance(s, Script) for s in ms.constant), "A trait constant must be made of morphemes"
    assert all(isinstance(g[0], tuple) and all(isinstance(gg, Script) for gg in g[0])
               and isinstance(g[1], int) for g in ms.groups), \
        "A trait group must be made of a list of (Morpheme list, multiplicity)"

    assert tuple(sorted(ms.groups)) == ms.groups
    assert tuple(sorted(ms.constant)) == ms.constant

    all_group = [ms.constant, *(g for g, _ in ms.groups)]
    all_morphemes = {str(w): w for g in all_group for w in g}

    assert len(all_morphemes) == sum(len(g) for g in all_group), "The groups and constants must be disjoint"


class PolyMorpheme(USL):
    def __init__(self, constant: List[Script]=(), groups=()):
        super().__init__()

        self.constant = tuple(sorted(constant))
        self.groups = tuple((tuple(sorted(g[0])), g[1]) for g in sorted(groups))

        self._str = ' '.join(chain(map(str, self.constant),
                               ["m{}({})".format(mult, ' '.join(map(str, group))) for group, mult
                                    in self.groups]))

        self.grammatical_class = max((s.grammatical_class for s in self.constant),
                                     default=AUXILIARY_CLASS)
    @property
    def empty(self):
        return not self.constant and not self.groups

    def __lt__(self, other):
        return self.constant < other.constant or \
               (self.constant == other.constant and self.groups < other.groups)


    def _compute_singular_sequences(self):
        if not self.groups:
            return [self]

        # G0, G1, G2 Groups
        # Gi = {Gi_a, Gi_b, ... Words}

        # combinaisons 1: C1
        # 001 -> G0_a, G0_b, ...
        # 010 -> G1_a, ...
        # 100
        # combinaisons 2: C2
        # 011 -> G0_a + G1_a, G0_a + G1_b, ..., G0_b + G1_a, ...
        # 110 -> G1_a + G2_a, G1_a + G2_b, ..., G1_b + G2_a, ...
        # 101
        # combinaisons 3: C3
        # 111 -> G0_a + G1_a + G2_a, ...

        # combinaisons 4: C4
        # 112
        # 121
        # 211

        # combinaisons i: Ci
        # // i = q * 3 + r
        # // s = q + 1
        # r == 0:
        # qqq
        # r == 1:
        # qqs
        # qsq
        # sqq
        # r == 2:
        # qss
        # sqs
        # ssq

        # abcde... = iter (a Words parmi G0) x (b words parmi G1) x (c words parmi G2) x ...
        # Ci = iter {abb, bab, bba}
        #   i = q * 3 + r
        #   a = q + (1 si r = 1 sinon 0)
        #   b = q + (1 si r = 2 sinon 0)

        # Min = min len Groups
        # Max = max len Groups

        # C3 + C2
        # etc...

        # number of groups
        N = len(self.groups)
        min_len = min(map(len, list(zip(*self.groups))[0]))

        max_sizes_groups = defaultdict(set)
        for i, (grp, mult) in enumerate(self.groups):
            for j in range(mult + 1, min_len + 1):
                max_sizes_groups[j].add(i)

        def iter_groups_combinations():
            for i in count():
                # minimum number of elements taken from each groups
                q = i // N

                # number of groups which will yield q + 1 elements
                r = i % N

                if q == min_len + 1 or q in max_sizes_groups:
                    break

                for indexes in combinations(range(N), r):
                    if any(j in max_sizes_groups.get(q + 1, set()) for j in indexes):
                        continue

                    if any(len(self.groups[i][0]) <= q for i in indexes):
                        continue

                    yield from product(*(combinations(self.groups[i][0], q + 1) for i in indexes),
                                       *(combinations(self.groups[i][0], q) for i in range(N) if i not in indexes))

        traits = LastUpdatedOrderedDict()

        SIZE_LIMIT = MORPHEME_SERIE_SIZE_LIMIT_CONTENT# if is_content else MORPHEME_SERIE_SIZE_LIMIT_FUNCTION

        for gs in iter_groups_combinations():
            morpheme_semes = list(set(chain(*gs, self.constant)))
            if len(morpheme_semes) == 0 or len(morpheme_semes) > SIZE_LIMIT:
                continue

            m = PolyMorpheme(constant=morpheme_semes)
            traits[str(m)] = m

        return tuple(traits.values())