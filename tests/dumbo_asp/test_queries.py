import pytest
from dumbo_utils.primitives import PositiveIntegerOrUnbounded

from dumbo_asp.primitives.atoms import GroundAtom
from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.programs import SymbolicProgram
from dumbo_asp.primitives.templates import Template
from dumbo_asp.queries import compute_minimal_unsatisfiable_subsets, validate_in_all_models, \
    validate_cannot_be_true_in_any_stable_model, validate_cannot_be_extended_to_stable_model, enumerate_models, \
    enumerate_counter_models, validate_in_all_models_of_the_reduct, explanation_graph, open_graph_in_xasp_navigator, \
    relevant_herbrand_base


def test_compute_minimal_unsatisfiable_subsets():
    program = SymbolicProgram.parse("""
a.
b.
c.
:- a, b.
:- a, c.
:- b, c.
    """)
    res = compute_minimal_unsatisfiable_subsets(program, PositiveIntegerOrUnbounded.of_unbounded())
    assert len(res) == 3


def test_compute_minimal_unsatisfiable_subsets_over_ground_program():
    program = SymbolicProgram.parse("""
a(1..3).
:- a(X), a(Y), X < Y.
    """)
    res = compute_minimal_unsatisfiable_subsets(program, PositiveIntegerOrUnbounded.of_unbounded())
    assert len(res) == 1
    res = compute_minimal_unsatisfiable_subsets(program, PositiveIntegerOrUnbounded.of_unbounded(),
                                                over_the_ground_program=True)
    assert len(res) == 3


def test_enumerate_models():
    program = SymbolicProgram.parse("""
{a; b; c; d}.
:- c, d.
:- not c, not d.
    """)
    models = enumerate_models(program, true_atoms=Model.of_atoms("a"), false_atoms=Model.of_atoms("b"))
    assert len(models) == 2


def test_enumerate_models_2():
    program = SymbolicProgram.parse("""
a :- b.
    """)
    models = enumerate_models(program, unknown_atoms=Model.of_atoms("a b".split()))
    assert len(models) == 3


def test_enumerate_counter_models():
    program = SymbolicProgram.parse("""
a :- b.
    """)
    models = enumerate_counter_models(program, Model.of_atoms("a b".split()))
    assert len(models) == 2


def test_validate_in_all_models_transitive_closure():
    program = Template.expand_program(SymbolicProgram.parse("""
__apply_template__("@dumbo/transitive closure", (relation, link), (closure, link)).

link(a,b).
link(b,c).
    """))

    validate_in_all_models(
        program=program,
        true_atoms=Model.of_atoms("link(a,b) link(b,c) link(a,c)".split()),
    )

    with pytest.raises(ValueError):
        validate_in_all_models(program=program, true_atoms=Model.of_atoms("link(a,a)".split()))

    with pytest.raises(ValueError):
        validate_in_all_models(
            program=program,
            false_atoms=Model.of_atoms("link(a,a)".split()),
        )


def test_validate_in_all_models_of_the_reduct_transitive_closure():
    program = Template.expand_program(SymbolicProgram.parse("""
__apply_template__("@dumbo/transitive closure", (relation, link), (closure, link)).
    """))

    validate_in_all_models_of_the_reduct(
        program=program,
        model=Model.of_atoms("link(a,b) link(b,c)".split()),
        true_atoms=Model.of_atoms("link(a,c)".split()),
    )

    validate_in_all_models_of_the_reduct(
        program=program,
        model=Model.of_atoms("link(a,b) link(b,c)".split()),
        true_atoms=Model.of_atoms("link(a,b) link(b,c) link(a,c)".split()),
    )

    validate_in_all_models_of_the_reduct(
        program=program,
        model=Model.of_atoms("link(a,b) link(b,c) link(c,d)".split()),
        true_atoms=Model.of_atoms("link(a,b) link(b,c) link(a,c) link(a,d)".split()),
    )

    validate_in_all_models_of_the_reduct(
        program=program,
        model=Model.of_atoms("link(a,b) link(b,c) link(c,d) link(d,a)".split()),
        true_atoms=Model.of_atoms("link(b,a) link(c,a) link(a,a)".split()),
    )

    with pytest.raises(ValueError):
        validate_in_all_models_of_the_reduct(
            program=program,
            model=Model.of_atoms("link(a,b) link(b,c)".split()),
            true_atoms=Model.of_atoms("link(a,a)".split()),
        )

    with pytest.raises(ValueError):
        validate_in_all_models_of_the_reduct(
            program=program,
            model=Model.of_atoms("link(a,b) link(b,c) link(c,d)".split()),
            true_atoms=Model.of_atoms("link(b,b)".split()),
        )


def test_validate_in_all_models_for_unseen_atoms():
    program = Template.expand_program(SymbolicProgram.parse("""
__apply_template__("@dumbo/transitive closure", (relation, link), (closure, link)).
link(a,b).
    """))

    with pytest.raises(ValueError):
        validate_in_all_models(program=program, false_atoms=Model.of_atoms("link(c,d)".split()))


def test_validate_cannot_be_true_in_any_stable_model():
    program = Template.expand_program(SymbolicProgram.parse("""
__fail :- a, not __fail.
    """))

    with pytest.raises(ValueError):
        validate_in_all_models(program=program, false_atoms=Model.of_atoms("a".split()))

    validate_cannot_be_true_in_any_stable_model(program, GroundAtom.parse("a"))


def test_validate_cannot_be_true_in_any_stable_model_2():
    program = Template.expand_program(SymbolicProgram.parse("""
__fail :- a, not __fail.
:- not a, b.

{a}.
    """))

    validate_cannot_be_true_in_any_stable_model(program, GroundAtom.parse("b"))


def test_validate_cannot_be_extended_to_stable_model():
    program = Template.expand_program(SymbolicProgram.parse("""
{a; b}.
__fail :- a, b, not __fail.
__fail :- not a, not b, not __fail.
    """))

    with pytest.raises(ValueError):
        validate_in_all_models(program=program, true_atoms=Model.of_atoms("a".split()))
        validate_in_all_models(program=program, true_atoms=Model.of_atoms("b".split()))
        validate_in_all_models(program=program, false_atoms=Model.of_atoms("a".split()))
        validate_in_all_models(program=program, false_atoms=Model.of_atoms("b".split()))

    validate_cannot_be_extended_to_stable_model(program=program, true_atoms=Model.of_atoms("a b".split()))
    validate_cannot_be_extended_to_stable_model(program=program, false_atoms=Model.of_atoms("a b".split()))


def test_explanation_graph_support():
    program = SymbolicProgram.parse("noo :- a. a :- b. b.")
    answer_set = Model.of_program("b. a.")
    herbrand_base = [GroundAtom.parse(atom) for atom in ["a", "b", "noo"]]
    query = Model.of_program("a.")
    graph = explanation_graph(program, answer_set, herbrand_base, query)
    assert len(graph) == 3
    assert '"a",true,(support,"a :- b' in graph.as_facts
    assert '"b",true,(support,"b :- ' in graph.as_facts
    assert 'link("a","b","a :- b' in graph.as_facts


def test_explanation_graph_head_upper_bound():
    program = SymbolicProgram.parse("{a; b} <= 1.")
    answer_set = Model.of_atoms("b")
    herbrand_base = [GroundAtom.parse(atom) for atom in ["a", "b"]]
    query = Model.of_program("a.")
    graph = explanation_graph(program, answer_set, herbrand_base, query)
    assert len(graph) == 4
    assert '"a",false,(head_upper_bound' in graph.as_facts
    assert '"b",true,(assumption' in graph.as_facts
    assert 'link("a","b"' in graph.as_facts


def test_explanation_graph_lack_of_support():
    program = SymbolicProgram.parse("a :- b.")
    answer_set = Model.empty()
    herbrand_base = [GroundAtom.parse(atom) for atom in ["a", "b"]]
    query = Model.of_program("a.")
    graph = explanation_graph(program, answer_set, herbrand_base, query)
    assert len(graph) == 4
    assert '"a",false,(lack_of_support,' in graph.as_facts
    assert '"b",false,(lack_of_support,' in graph.as_facts
    assert 'link("a","b","a :- b' in graph.as_facts


def test_explanation_graph_lack_of_support_multiple_rules():
    program = SymbolicProgram.parse("a :- b.  a :- c.")
    answer_set = Model.empty()
    herbrand_base = [GroundAtom.parse(atom) for atom in ["a", "b", "c"]]
    query = Model.of_program("a.")
    graph = explanation_graph(program, answer_set, herbrand_base, query)
    assert '"a",false,(lack_of_support,' in graph.as_facts
    assert '"b",false,(lack_of_support,' in graph.as_facts
    assert 'link("a","b","a :- b' in graph.as_facts
    assert 'link("a","c","a :- c' in graph.as_facts


def test_explanation_graph_last_support():
    program = SymbolicProgram.parse("a :- b. :- not a. {b}.")
    answer_set = Model.of_program("b.")
    herbrand_base = [GroundAtom.parse(atom) for atom in ["a", "b"]]
    query = Model.of_program("b.")
    graph = explanation_graph(program, answer_set, herbrand_base, query)
    assert len(graph) == 4
    assert '"a",true,(constraint,' in graph.as_facts
    assert '"b",true,(last_support,' in graph.as_facts
    assert 'link("b","a"' in graph.as_facts


def test_explanation_graph_constraint():
    program = SymbolicProgram.parse("a :- not b. :- a. {a; b}.")
    answer_set = Model.of_program("b.")
    herbrand_base = [GroundAtom.parse(atom) for atom in ["a", "b"]]
    query = Model.of_program("b.")
    graph = explanation_graph(program, answer_set, herbrand_base, query)
    # print(graph.as_facts)
    # open_graph_in_xasp_navigator(graph, with_chopped_body=True, with_backward_search=True,
    #                              backward_search_symbols=(';', ' :-'))
    assert len(graph) == 4
    assert '"a",false,(constraint,' in graph.as_facts
    assert '"b",true,(constraint,' in graph.as_facts
    assert 'link("b","a"' in graph.as_facts


def test_explanation_graph_last_support_multiple_rules():
    program = SymbolicProgram.parse("a :- b.  a :- c.  :- not a.  :- c.  {b}.")
    answer_set = Model.of_program("a. b.")
    herbrand_base = [GroundAtom.parse(atom) for atom in ["a", "b", "c"]]
    query = Model.of_program("b.")
    graph = explanation_graph(program, answer_set, herbrand_base, query)
    assert '"b",true,(last_support,' in graph.as_facts
    assert 'link("b","a"' in graph.as_facts
    assert 'link("b","c"' in graph.as_facts


def test_with_named_anonymous_variables():
    program = SymbolicProgram.parse("a :- b(_). {b(0)}.")
    answer_set = Model.of_program("a. b(0).")
    herbrand_base = [GroundAtom.parse(atom) for atom in ["a", "b(0)"]]
    query = Model.of_program("a.")
    graph = explanation_graph(program, answer_set, herbrand_base, query)
    assert '"a",true,(support,' in graph.as_facts
    assert 'link("a","b(0)"' in graph.as_facts


def test_relevant_herbrand_base():
    program = SymbolicProgram.parse("a(X) :- b(X), not c(X).")
    atoms = Model.of_atoms("b(1)", "c(1)", "b(2)", "c(3)")
    hb = relevant_herbrand_base(program, atoms)
    assert len(hb) == 6
    assert "a(1)" in str(hb)
    assert "a(2)" in str(hb)
    assert "a(3)" not in str(hb)
