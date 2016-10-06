import random

import itertools

from ieml.ieml_objects.terms import Term
from ieml.script.operator import script

from ieml.ieml_objects.hypertexts import Hypertext
from ieml.ieml_objects.sentences import Sentence, Clause, SuperSentence, SuperClause
from ieml.ieml_objects.texts import Text
from ieml.ieml_objects.words import Word, Morpheme


class RandomPoolIEMLObjectGenerator:
    def __init__(self, level, pool_size=20):
        self.level = level
        self.pool_size = pool_size

        if level > Text:
            raise ValueError('Cannot generate object higher than a Text.')

        self._build_pools()

    def _build_pools(self):
        """
        Slow method, retrieve all the terms from the database.
        :return:
        """
        from models.terms.terms import TermsConnector as tc
        self.terms_pool = set(Term(script(t['_id'])) for t in tc().get_all_terms()[:self.pool_size])

        if self.level >= Word:
            # words
            self.words_pool = set(self.word() for i in range(self.pool_size))

        if self.level >= Sentence:
            # sentences
            self.sentences_pool = set(self.sentence() for i in range(self.pool_size))

        if self.level >= SuperSentence:
            self.super_sentences_pool = set(self.super_sentence() for i in range(self.pool_size))

        if self.level >= Text:
            self.propositions_pool = set(itertools.chain.from_iterable((self.words_pool, self.sentences_pool, self.super_sentences_pool)))

        # self.hypertext_pool = set(self.hypertext() for i in range(self.pool_size))

    def term(self):
        return random.sample(self.terms_pool, 1)[0]

    def word(self):
        return Word(Morpheme(random.sample(self.terms_pool, 3)), Morpheme(random.sample(self.terms_pool, 2)))

    def _build_graph_object(self, primitive, mode, object):
        nodes = {primitive()}
        modes = set()

        result = set()

        for i in range(random.randint(2, 6)):
            while True:
                s, a, m = *random.sample(nodes, 1), primitive(), mode()
                if a in nodes or m in nodes or a in modes:
                    continue

                nodes.add(a)
                modes.add(m)

                result.add(object(s, a, m))
                break
        return result

    def sentence(self):
        def p():
            return random.sample(self.words_pool, 1)[0]

        return Sentence(self._build_graph_object(p, p, Clause))

    def super_sentence(self):
        def p():
            return random.sample(self.sentences_pool, 1)[0]

        return SuperSentence(self._build_graph_object(p, p, SuperClause))

    def text(self):
        return Text(random.sample(self.propositions_pool, random.randint(1, 8)))

    # def hypertext(self):
    #     def text():
    #         return random.sample(self.text_pool, 1)[1]
    #
    #
    #
    #     return Hypertext(self._build_graph_object(text, , SuperSentence))

if __name__ == '__main__':
    r = RandomPoolIEMLObjectGenerator(Text)
    print(str(r.sentence()))