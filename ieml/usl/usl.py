from itertools import islice

from ieml.commons import LANGUAGES
from ieml.ieml_objects.terms import Term
from ieml.paths.paths import Path
from ieml.paths.tools import enumerate_paths, resolve


class Usl:
    def __init__(self, ieml_object):
        self.ieml_object = ieml_object
        self._rules = None

    def __str__(self):
        return str(self.ieml_object)

    def __eq__(self, other):
        if isinstance(other, Usl):
            return self.ieml_object.__eq__(other.ieml_object)

    def __hash__(self):
        return hash(self.ieml_object)

    @property
    def paths(self):
        if self._rules is None:
            self._rules = {path: term for path, term in enumerate_paths(self.ieml_object, level=Term)}

        return self._rules

    def __getitem__(self, item):
        if isinstance(item, Path):
            if item in self.paths:
                return self.paths[item]

            return resolve(self.ieml_object, item)

        raise NotImplemented

    def auto_translation(self):
        result = {}
        entries = sorted([t for p, t in self.paths.items()])
        for l in LANGUAGES:
            result[l.upper()] = ' '.join((e.translations[l] for e in islice(entries, 10)))

        return result
