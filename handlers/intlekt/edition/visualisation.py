from functools import partial

from ieml.ieml_objects.hypertexts import Hyperlink, Hypertext
from ieml.ieml_objects.sentences import Clause, SuperClause
from ieml.ieml_objects.words import Word, Morpheme
from ieml.usl.tools import usl as _usl, usl
from handlers.commons import exception_handler
from ieml.ieml_objects import Term, Sentence, SuperSentence
from ieml.ieml_objects.texts import Text
from models.terms.terms import TermsConnector

word = "[([a.i.-]+[i.i.-])*([E:A:T:.]+[E:S:.wa.-]+[E:S:.o.-])]"
sentence = "[([([a.i.-]+[i.i.-])*([E:A:T:.]+[E:S:.wa.-]+[E:S:.o.-])]*[([S:.-'B:.-'n.-S:.U:.-',])]*[([E:T:.f.-])])+([([a.i.-]+[i.i.-])*([E:A:T:.]+[E:S:.wa.-]+[E:S:.o.-])]*[([t.i.-s.i.-'u.T:.-U:.-'wo.-',B:.-',_M:.-',_;])]*[([E:E:T:.])])]"


def sample_usls(n, language='EN'):
    return [
        {"ieml" : word, "title" : { 'fr' : "Nous avons l'intention de fabriquer et de vendre beaucoup",
                                    'en' : "We intend to make and sell a lot" }},
        {"ieml" : sentence, "title" : { 'fr': "Nous avons l'intention de fabriquer et de vendre beaucoup de nos véhicules à roues sans conducteurs en Europe",
                                        'en': "We intend to make and sell a lot of driverless vehicles in Europe"}}
    ]


def recent_usls(n, language='EN'):
    return []

def _ieml_object_to_json(u, start=True):
    if isinstance(u, Term):
        return {
            'type': u.__class__.__name__.lower(),
            'script': str(u.script),
            'singular_sequences': [str(s) for s in u.script.singular_sequences],
            'title': {'en': TermsConnector().get_term(u.script)['TAGS']['EN'],
                      'fr': TermsConnector().get_term(u.script)['TAGS']['FR']}
        }
    if not u.closable and start and len(u.children) == 1:
        return _ieml_object_to_json(u.children[0])

    def _build_tree(transition, children_tree, supersentence=False):
        result = {
            'type': 'supersentence-node' if supersentence else 'sentence-node',
            'mode': _ieml_object_to_json(transition[1].mode, start=False),
            'node': _ieml_object_to_json(transition[0], start=False),
            'children': []
        }
        if transition[0] in children_tree:
            result['children'] = [_build_tree(c, children_tree, supersentence=supersentence) for c in
                                  children_tree[transition[0]]]
        return result

    if isinstance(u, Sentence):
        result = {
            'type': 'sentence-root-node',
            'node': _ieml_object_to_json(u.tree_graph.root, start=False),
            'children': [
                _build_tree(c, u.tree_graph.transitions) for c in u.tree_graph.transitions[u.tree_graph.root]
                ]
        }
    elif isinstance(u, SuperSentence):
        result = {
            'type': 'supersentence-root-node',
            'node': _ieml_object_to_json(u.tree_graph.root, start=False),
            'children': [
                _build_tree(c, u.tree_graph.transitions, supersentence=True) for c in
                u.tree_graph.transitions[u.tree_graph.root]
                ]
        }
    else:
        result = {
            'type': u.__class__.__name__.lower(),
            'children': [_ieml_object_to_json(c, start=False) for c in u]
        }

    return result


@exception_handler
def usl_to_json(usl):
    u = _usl(usl["usl"])
    return _ieml_object_to_json(u.ieml_object)


def _tree_node(json, constructor):
    result = []
    for child in json['children']:
        result.append(
            constructor(substance=_json_to_ieml(json['node']),
                        attribute=_json_to_ieml(child['node']),
                        mode=_json_to_ieml(child['mode'])))
        result.extend(_tree_node(child, constructor))
    return result


def _children_list(constructor, json):
    return constructor(children=list(_json_to_ieml(c) for c in json['children']))

type_to_action = {
    Term.__name__.lower(): lambda json: Term(json['script']),
    'sentence-root-node': lambda json: Sentence(_tree_node(json, Clause)),
    'supersentence-root-node': lambda json: SuperSentence(_tree_node(json, SuperClause)),
    'sentence-node': lambda json: Sentence(_tree_node(json, Clause)),
    'supersentence-node': lambda json: SuperSentence(_tree_node(json, SuperClause)),
}
for cls in (Morpheme, Word, Text, Hyperlink, Hypertext):
    type_to_action[cls.__name__.lower()] = partial(_children_list, cls)


def _json_to_ieml(json):
    try:
        return type_to_action[json['type']](json)
    except KeyError as k:
        raise ValueError("The node of type %s was unexpected. Invalid json structure."%str(k))


@exception_handler
def json_to_usl(json):
    """Convert a json representation of an usl to the usl object and return the ieml string."""
    return str(usl(_json_to_ieml(json['json'])))


@exception_handler
def rules_to_usl(rules):
    return str(usl([(r[0], Term(r[1])) for r in rules]))


@exception_handler
def rules_to_json(rules):
    u = usl([(r[0], Term(r[1])) for r in rules])
    return _ieml_object_to_json(u.ieml_object)
