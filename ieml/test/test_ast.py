import itertools
import unittest

import numpy as np

from ieml.synthax import Text, SuperSentence
from ieml.exceptions import InvalidIEMLObjectArgument, TermNotFoundInDictionary
from ieml.synthax.parser import IEMLParser
from ieml.synthax.sentences import SuperClause
from ieml.tools import RandomPoolIEMLObjectGenerator
from ieml.dictionary.script import script as sc
from ieml.test.helper import *


class TestIEMLType(unittest.TestCase):
    def test_rank(self):
        r = RandomPoolIEMLObjectGenerator(level=Text)
        self.assertEqual(r.term().__class__.ieml_rank(), 1)
        self.assertEqual(r.word().__class__.ieml_rank(), 3)
        self.assertEqual(r.sentence().__class__.ieml_rank(), 5)
        self.assertEqual(r.super_sentence().__class__.ieml_rank(), 7)
        self.assertEqual(r.text().__class__.ieml_rank(), 8)


class TestPropositionsInclusion(unittest.TestCase):

    def setUp(self):
        self.parser = IEMLParser()
        self.sentence = self.parser.parse("""[([([h.O:T:.-])]*[([E:O:.T:M:.-])]*[([E:F:.O:O:.-])])+
                                     ([([h.O:T:.-])]*[([wu.T:.-])]*[([h.O:B:.-])])]""")

    def test_word_in_sentence(self):
        word = self.parser.parse("[([h.O:T:.-])]")
        self.assertIn(word, set(itertools.chain.from_iterable(self.sentence)))

    def test_term_in_sentence(self):
        term = self.parser.parse("[h.O:T:.-]")
        self.assertIn(term, set(itertools.chain.from_iterable(itertools.chain.from_iterable(itertools.chain.from_iterable(self.sentence)))))

    def test_word_not_in_sentence(self):
        word = self.parser.parse("[([wo.S:.-])]")
        self.assertNotIn(word, self.sentence)

class TesttermsFeatures(unittest.TestCase):
    """Checks basic AST features like hashing, ordering for words, morphemes and terms"""

    def setUp(self):
        self.term_a, self.term_b, self.term_c = term("E:A:T:."), term("E:S:.wa.-"), term("E:S:.o.-")

    def test_term_check_fail(self):
        with self.assertRaises(TermNotFoundInDictionary):
            term("E:A:T:.wa.wa.-")

    def test_terms_equality(self):
        """tests that two different instance of a term are still considered equal once linked against the DB"""
        other_instance = term("E:A:T:.")
        self.assertTrue(self.term_a == other_instance)
        self.assertTrue(self.term_a is other_instance) # checking they really are two different instances

    def test_terms_comparison(self):
        s_a = sc("S:M:.e.-M:M:.u.-'+B:M:.e.-M:M:.a.-'+T:M:.e.-M:M:.i.-'")
        s_b = sc("S:M:.e.-M:M:.u.-'")
        self.assertLess(s_b, s_a)

    def test_term_ordering(self):
        """Checks that terms are properly ordered, through the """
        terms_list = [self.term_b, self.term_a, self.term_c]
        terms_list.sort()
        self.assertEqual(terms_list, [self.term_a, self.term_b, self.term_c])

    def test_term_hashing(self):
        """Checks that terms can be used as keys in a hashmap"""
        hashmap = {self.term_a : 1}
        other_instance = term("E:A:T:.")
        self.assertTrue(other_instance in hashmap)

    def test_term_sets(self):
        other_a_instance = term("E:A:T:.")
        terms_set = {self.term_b, self.term_a, self.term_c, other_a_instance}
        self.assertEqual(len(terms_set), 3)


class TestMorphemesFeatures(unittest.TestCase):

    def test_morpheme_checks(self):
        """Creates a morpheme with conflicting terms"""
        with self.assertRaises(InvalidIEMLObjectArgument):
            Morpheme([term("E:A:T:."), term("E:S:.o.-"), term("E:S:.wa.-"), term("E:A:T:.")])

    def _make_and_check_morphemes(self):
        morpheme_a = Morpheme([term("E:A:T:."), term("E:S:.wa.-"),term("E:S:.o.-")])
        morpheme_b = Morpheme([term("a.i.-"), term("i.i.-")])
        return morpheme_a, morpheme_b

    def _make_and_check_suffixed_morphemes(self):
        morpheme_a = Morpheme([term("E:A:T:."), term("E:S:.wa.-")])
        morpheme_b = Morpheme([term("E:A:T:."), term("E:S:.wa.-"),term("E:S:.o.-")])
        return morpheme_a, morpheme_b

    def test_morpheme_reordering(self):
        """Create a new morpheme with terms in the wrong order, and check that it reorders
        after itself after the reorder() method is ran"""
        new_morpheme = Morpheme([term("E:A:T:."), term("E:S:.o.-"), term("E:S:.wa.-")])
        self.assertEqual(str(new_morpheme.children[2]), '[E:S:.o.-]') # last term is right?

    def test_morpheme_equality(self):
        """Tests if two morphemes That are declared the same way are said to be equal
         using the regular equality comparison. It also tests terms reordering"""
        morpheme_a = Morpheme([term("E:A:T:."), term("E:S:.o.-"), term("E:S:.wa.-")])
        morpheme_b = Morpheme([term("E:A:T:."), term("E:S:.wa.-"), term("E:S:.o.-")])
        self.assertTrue(morpheme_a == morpheme_b)

    def test_morpheme_inequality(self):
        morpheme_a , morpheme_b = self._make_and_check_morphemes()
        self.assertTrue(morpheme_a != morpheme_b)

    def test_different_morpheme_comparison(self):
        morpheme_a, morpheme_b = self._make_and_check_morphemes()
        # true because term("E:A:T:.") < term("a.i.-")
        self.assertTrue(morpheme_b > morpheme_a)

    def test_suffixed_morpheme_comparison(self):
        morpheme_a, morpheme_b = self._make_and_check_suffixed_morphemes()
        # true since morph_a suffix of morph_b
        self.assertTrue(morpheme_b > morpheme_a)


class TestWords(unittest.TestCase):

    def setUp(self):
        self.morpheme_a = Morpheme([term("E:A:T:."), term("E:S:.wa.-"),term("E:S:.o.-")])
        self.morpheme_b = Morpheme([term("a.i.-"), term("i.i.-")])
        self.word_a = Word(self.morpheme_a, self.morpheme_b)
        self.word_b = Word(Morpheme([term("E:A:T:."), term("E:S:.o.-"), term("E:S:.wa.-")]),
                          Morpheme([term("a.i.-"), term("i.i.-")]))

    def test_words_equality(self):
        """Checks that the == operator works well on words build from the same elements"""
        self.assertTrue(self.word_b == self.word_a)

    def test_words_hashing(self):
        """Verifies words can be used as keys in a hashmap"""
        new_word = Word(Morpheme([term("E:A:T:."), term("E:S:.o.-"), term("E:S:.wa.-")]))
        word_hashmap = {new_word : 1,
                        self.word_a : 2}
        self.assertTrue(self.word_b in word_hashmap)

    def test_words_with_different_substance_comparison(self):
        word_a,word_b = Word(self.morpheme_a),  Word(self.morpheme_b)
        # true because term("E:A:T:.") < term("a.i.-")
        self.assertTrue(word_a < word_b)


class TestClauses(unittest.TestCase):

    def test_simple_comparison(self):
        """Tests the comparison on two clauses not sharing the same substance"""
        a, b, c, d, e, f = tuple(get_words_list())
        clause_a, clause_b = Clause(a,b,c), Clause(d,e,f)
        self.assertTrue(clause_a < clause_b)

    def test_attr_comparison(self):
        """tests the comparison between two clauses sharing the same substance"""
        a, b, c, d, e, f = tuple(get_words_list())
        clause_a, clause_b = Clause(a,b,c), Clause(a,e,c)
        self.assertTrue(clause_a < clause_b)


class TestSentences(unittest.TestCase):

    def test_adjacency_graph_building(self):
        sentence = get_test_sentence()
        adjancency_matrix = np.array([[False,True,True,False,False],
                                      [False,False,False,True,True],
                                      [False,False,False,False,False],
                                      [False,False,False,False,False],
                                      [False,False,False,False,False]])
        self.assertTrue((sentence.tree_graph.array == adjancency_matrix).all())

    def test_two_many_roots(self):
        a, b, c, d, e, f = tuple(get_words_list())
        with self.assertRaises(InvalidIEMLObjectArgument):
            Sentence([Clause(a, b, f), Clause(a, c, f), Clause(b, e, f), Clause(d, b, f)])

    def test_too_many_parents(self):
        a, b, c, d, e, f = tuple(get_words_list())
        with self.assertRaises(InvalidIEMLObjectArgument):
            Sentence([Clause(a, b, f), Clause(a, c, f), Clause(b, e, f), Clause(b, d, f), Clause(c, d, f)])

    def test_no_root(self):
        a, b, c, d, e, f = tuple(get_words_list())
        with self.assertRaises(InvalidIEMLObjectArgument):
            Sentence([Clause(a, b, f), Clause(b, c, f), Clause(c, a, f), Clause(b, d, f), Clause(c, d, f)])

    def test_clause_ordering(self):
        a, b, c, d, e, f = tuple(get_words_list())
        clause_a, clause_b, clause_c, clause_d = Clause(a,b,f), Clause(a,c,f), Clause(b,d,f), Clause(b,e,f)
        sentence = Sentence([clause_a, clause_b, clause_c, clause_d])
        self.assertEqual(sentence.children, (clause_a, clause_b,clause_c, clause_d))


class TestSuperSentence(unittest.TestCase):

    def setUp(self):
        self.rnd_gen = RandomPoolIEMLObjectGenerator(Sentence)

    def test_supersentence_creation(self):
        a, b, c, d, e, f = tuple(self.rnd_gen.sentence() for i in range(6))
        try:
            super_sentence = SuperSentence([SuperClause(a,b,f), SuperClause(a,c,f), SuperClause(b,e,f), SuperClause(b,d,f)])
        except InvalidIEMLObjectArgument as e:
            self.fail()