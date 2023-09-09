from builtins import ValueError
from unittest.mock import patch

import clingo
import clingo.ast
import pytest

from dumbo_asp.primitives import Predicate, Parser, GroundAtom, Model, SymbolicRule, SymbolicProgram, SymbolicAtom, \
    SymbolicTerm, Template


@pytest.fixture
def patched_uuid():
    with patch("dumbo_asp.utils.uuid",
               side_effect=[f"ebc40a28_de77_494a_a139_{i:012}" for i in range(1, 100)]
               ):
        yield


def test_parser_error():
    with pytest.raises(Parser.Error) as err:
        Parser.parse_ground_term("\"a\nb")
    assert err.value.line == 1


@pytest.mark.parametrize("name", [
    "foo//1",
    "foo/-1",
    "foo bar",
    "Foo",
    "-foo",
])
def test_invalid_predicate_name(name):
    with pytest.raises(ValueError):
        Predicate.parse(name)


@pytest.mark.parametrize("name", [
    "foo/1",
    "foo/0",
    "foo",
])
def test_valid_predicate_name(name):
    assert Predicate.parse(name).name == name.split('/')[0]


def test_predicate_order():
    assert Predicate.parse("a/0") < Predicate.parse("a/1")
    assert Predicate.parse("a/1") > Predicate.parse("a/0")
    assert Predicate.parse("a/1") < Predicate.parse("b/0")
    assert Predicate.parse("a") > Predicate.parse("a/0")


@pytest.mark.parametrize("atom", [
    "foo(",
    "foo(1,)",
    "foo(_)",
    "foo(X)",
    "foo(1) bar(2)",
])
def test_invalid_ground_atom(atom):
    with pytest.raises(ValueError):
        GroundAtom.parse(atom)


@pytest.mark.parametrize("atom", [
    "foo",
    "foo(1)",
    "foo(x)",
])
def test_valid_ground_atom(atom):
    assert GroundAtom.parse(atom).predicate.name == atom.split('(')[0]


def test_ground_atom_order():
    assert GroundAtom.parse("a(1)") < GroundAtom.parse("a(2)")
    assert GroundAtom.parse("a(b)") > GroundAtom.parse("a(2)")
    assert GroundAtom.parse("a(b)") > GroundAtom.parse("a(a)")
    assert GroundAtom.parse("a(b)") > GroundAtom.parse("a(\"a\")")
    assert GroundAtom.parse("c(\"b\")") < GroundAtom.parse("c(a)")
    assert GroundAtom.parse("a(-1)") < GroundAtom.parse("a(0)")
    assert GroundAtom.parse("a(-a)") < GroundAtom.parse("a(a)")


@pytest.mark.parametrize("rule", [
    "a :- b.",
    "a(X) :- b(X).",
    "a(X) :- b(Y).",
    "a\n\t:- b.",
    "a :- b( 1 ).",
])
def test_parse_valid_symbolic_rule(rule):
    assert str(SymbolicRule.parse(rule)) == rule


@pytest.mark.parametrize("rule", [
    "a :- b.\na(X) :- b(X).",
    "a(X) :- b(.",
])
def test_parse_invalid_symbolic_rule(rule):
    with pytest.raises(ValueError):
        SymbolicRule.parse(rule)


@pytest.mark.parametrize("program", [
    "a",
    "a : -- b.",
    "a\n\n : --\n\n b.",
])
def test_parse_invalid_program(program):
    with pytest.raises(ValueError):
        Parser.parse_program(program)


@pytest.mark.parametrize("atoms", [
    ["a", "b", "c"],
    ["a", "-b", "c"],
    ["a(1)", "a(2)", "a(b)"],
])
def test_valid_model_of_atoms(atoms):
    assert len(Model.of_atoms(atoms)) == len(atoms)
    assert len(Model.of_atoms(*atoms)) == len(atoms)


@pytest.mark.parametrize("atoms", [
    ["\"a\"", "b", "c"],
    ["a", "not b", "c"],
    ["a(X)", "a(2)", "a(b)"],
])
def test_invalid_model_of_atoms(atoms):
    with pytest.raises(ValueError):
        Model.of_atoms(atoms)


def test_model_drop():
    assert len(Model.of_atoms("a(1)", "a(1,2)", "b(1)", "c(2)").drop(Predicate.parse("b"))) == 3
    assert len(Model.of_atoms("a(1)", "a(1,2)", "b(1)", "c(2)").drop(Predicate.parse("a"))) == 2
    assert len(Model.of_atoms("a(1)", "a(1,2)", "b(1)", "c(2)").drop(Predicate.parse("a/2"))) == 3
    assert len(Model.of_elements("a(1)", "1", '"a(1)"').drop(Predicate.parse("a/1"))) == 2
    assert len(Model.of_elements("a(1)", "1", 2, '"a(1)"').drop(numbers=True)) == 3
    assert len(Model.of_elements("a(1)", "1", 2, '"a(1)"').drop(numbers=True, strings=True)) == 1


def test_model_of_control():
    control = clingo.Control()
    control.add("base", [], "c. a. b.")
    control.ground([("base", [])])
    model = Model.of_control(control)
    assert len(model) == 3
    assert model[0].predicate == Predicate.parse("a/0")
    assert model[1].predicate == Predicate.parse("b/0")
    assert model[2].predicate == Predicate.parse("c/0")


def test_model_of_control_with_show_numbers():
    control = clingo.Control()
    control.add("base", [], "#show 1.")
    control.ground([("base", [])])
    model = Model.of_control(control)
    assert len(model) == 1
    assert model[0] == 1


def test_no_model():
    control = clingo.Control()
    control.add("base", [], "a :- not a.")
    control.ground([("base", [])])
    with pytest.raises(ValueError):
        Model.of_control(control)


def test_model_of_control_cannot_be_used_for_more_than_one_model():
    control = clingo.Control(["0"])
    control.add("base", [], "{a}.")
    control.ground([("base", [])])
    with pytest.raises(ValueError):
        Model.of_control(control)


def test_model_as_facts():
    assert Model.of_atoms("a", "b", "c").as_facts == "a.\nb.\nc."


def test_model_block_up():
    assert Model.of_atoms("a", "b").block_up == ":- a, b."


def test_model_project():
    assert Model.of_atoms("a(1,2,3)").project(Predicate.parse("a/3"), 1).as_facts == "a(2,3)."


def test_model_substitute():
    assert Model.of_atoms("a(1,2,3)").substitute(Predicate.parse("a/3"), 1, Parser.parse_ground_term("5")).as_facts == \
           "a(5,2,3)."


def test_model_of_elements():
    assert Model.of_elements(1, "2", "\"3\"").as_facts == """
__number(1).
__string(\"2\").
__string(\"3\").
    """.strip()


def test_parse_symbolic_program():
    string = """
foo(X) :-
    bar(X,Y);
    not buzz(Y).
b :-  a.
    """.strip()
    program = SymbolicProgram.parse(string)
    assert str(program) == string
    assert len(program) == 2
    assert str(program[-1]) == string.split('\n')[-1]


def test_symbolic_rule_predicates():
    assert set(SymbolicRule.parse("a(X) :- b(X), not c(X).").predicates) == \
           set(Predicate.parse(p) for p in "a/1 b/1 c/1".split())


def test_symbolic_program_predicates():
    assert set(SymbolicProgram.parse("""
a(X) :- b(X), not c(X).
:- #sum{X,d(X) : e(X)} = Y.
    """.strip()).predicates) == set(Predicate.parse(p) for p in "a/1 b/1 c/1 e/1".split())


def test_symbolic_rule_head_variables():
    assert SymbolicRule.parse("a(X) :- b(X,Y).").head_variables == ("X",)
    assert SymbolicRule.parse("{a(X,Z) : c(Z)} = 1 :- b(X,Y).").head_variables == ("X", "Z")


def test_symbolic_rule_body_variables():
    assert SymbolicRule.parse("a(X) :- b(X,Y).").body_variables == ("X", "Y")
    assert SymbolicRule.parse("{a(X,Z) : c(Z)} = 1 :- b(X,Y), not c(W).").body_variables == ("W", "X", "Y")


def test_symbolic_rule_global_safe_variables():
    assert SymbolicRule.parse("a(X) :- b(X,Y).").global_safe_variables == ("X", "Y")
    assert SymbolicRule.parse("a(X,Y) :- b(X).").global_safe_variables == ("X",)
    assert SymbolicRule.parse("a(X) :- b(X), not c(Y).").global_safe_variables == ("X",)
    assert SymbolicRule.parse("a(X) :- X = #count{Y : b(Y)} = X.").global_safe_variables == ("X",)


def test_symbolic_rule_with_extended_body():
    assert str(SymbolicRule.parse("a.").with_extended_body(SymbolicAtom.parse("b"))) == "a :- b."
    assert str(SymbolicRule.parse("a :- b.").with_extended_body(SymbolicAtom.parse("c"), clingo.ast.Sign.Negation)) == \
           "a :- b; not c."
    assert str(SymbolicRule.parse(" a( X , Y ) . ").with_extended_body(SymbolicAtom.parse(" b( Z ) "))) == \
           "a( X , Y )  :- b( Z )."


def test_symbolic_rule_body_as_string():
    assert SymbolicRule.parse("a :- b, c.").body_as_string() == "b; c"


def test_symbolic_rule_apply_variable_substitution():
    assert str(SymbolicRule.parse("a(X) :- b(X,Y).").apply_variable_substitution(X=SymbolicTerm.of_int(1))) == \
           "a(1) :- b(1,Y)."


def test_symbolic_term_parse():
    assert str(SymbolicTerm.parse("1")) == "1"


def test_program_herbrand_universe():
    assert SymbolicProgram.parse("a(X) :- X = 1..3.").herbrand_universe == {SymbolicTerm.of_int(x) for x in range(1, 4)}
    assert SymbolicProgram.parse("a(X,Y) :- X = 1..3, Y = 4..5.").herbrand_universe == \
           {SymbolicTerm.of_int(x) for x in range(1, 6)}
    assert SymbolicProgram.parse("a(b(c)).").herbrand_universe == {SymbolicTerm.parse("c")}


def test_program_herbrand_base():
    assert SymbolicProgram.parse("a(X) :- X = 1..3.").herbrand_base == Model.of_program("a(1..3).")


def foo():
    """
    __module__(transitive_closure).
        output(X,Y) :- input(X,Y).
        output(X,Y) :- input(X,Z), output(Z,Y).
    __end_module__.

    __module__(undirected_transitive_closure).
        __undirected(X,Y) :- input(X,Y).
        __undirected(X,Y) :- input(Y,X).
        __instantiate_module__(transitive_closure, (input, __undirected)).
    __end_module__.

    __show__().

    #const x = 4.
    __const__(x, 4).
    __global_variable__(PRIME, (2, 3, 5, 9, 11)).

    foo :- not bar(PRIME).

    __doc__("bla bla") |
    a :- b.


    __undirected_{uuid.uuid4()}

    __instantiate_module__(transitive_closure, (input, parent), (output, ancestor)).




    """


def test_symbolic_rule_is_fact():
    assert SymbolicRule.parse("a.").is_fact
    assert SymbolicRule.parse("a(1).").is_fact
    assert SymbolicRule.parse("a(x).").is_fact
    assert SymbolicRule.parse("a(X).").is_fact
    assert not SymbolicRule.parse("a | b.").is_fact


def test_symbolic_program_process_constants():
    assert str(SymbolicProgram.parse("""
__const__(x, 10).
a(x).
    """.strip()).process_constants()) == """%* __const__(x, 10). *%\na(10)."""


def test_symbolic_program_process_with_statements():
    assert str(SymbolicProgram.parse("""
__with__(foo(X)).
    a(X).
    b(X,Y) :- c(Y).
__end_with__.
    """.strip()).process_with_statements()) == """
%* __with__(foo(X)). *%
a(X) :- foo(X).
b(X,Y) :- c(Y); foo(X).
%* __end_with__. *%
""".strip()


def test_expand_one_global_variable():
    rule = SymbolicRule.parse("""
block((row, Row), (Row, Col)) :- Row = 1..9, Col = 1..9.
    """.strip())
    program = SymbolicProgram.of(rule)
    rules = rule.expand_global_safe_variables(variables=["Row"], herbrand_base=program.herbrand_base)
    assert len(rules) == 9


def test_expand_all_global_variables():
    rule = SymbolicRule.parse("""
block((row, Row), (Row, Col)) :- Row = 1..9, Col = 1..9.
    """.strip())
    program = SymbolicProgram.of(rule)
    rules = rule.expand_global_safe_variables(variables=rule.global_safe_variables, herbrand_base=program.herbrand_base)
    assert len(rules) == 9 * 9


def test_expand_non_global_variable():
    rule = SymbolicRule.parse("""
block((row, Row), (Row, Col)) :- Row = 1..9, Col = 1..9.
        """.strip())
    program = SymbolicProgram.of(rule)
    with pytest.raises(ValueError):
        rule.expand_global_safe_variables(variables=["X"], herbrand_base=program.herbrand_base)


def test_expand_global_variables_may_need_extra_variables():
    rule = SymbolicRule.parse("""
block((sub, Row', Col'), (Row, Col)) :- Row = 1..9; Col = 1..9; Row' = (Row-1) / 3; Col' = (Col-1) / 3.
    """.strip())
    program = SymbolicProgram.of(rule)
    rules = rule.expand_global_safe_variables(variables=["Row'", "Col'"], herbrand_base=program.herbrand_base)
    assert len(rules) == 9


def test_expand_global_variables_in_program():
    program = SymbolicProgram.parse("""
block((row, Row), (Row, Col)) :- Row = 1..9, Col = 1..9.
block((col, Col), (Row, Col)) :- Row = 1..9, Col = 1..9.
    """.strip())
    program = program.expand_global_safe_variables(rule=program[0], variables=["Row"])
    assert len(program) == 9 + 1
    program = program.expand_global_safe_variables(rule=program[-1], variables=["Col"])
    assert len(program) == 9 + 9


def test_expand_global_variables_in_several_rules():
    program = SymbolicProgram.parse("""
block((row, Row), (Row, Col)) :- Row = 1..9, Col = 1..9.
block((col, Col), (Row, Col)) :- Row = 1..9, Col = 1..9.
    """.strip())
    program = program.expand_global_safe_variables_in_rules({
        program[0]: ["Row"],
        program[1]: ["Col"],
    })
    assert len(program) == 9 + 9


def test_symbolic_term_int():
    term = SymbolicTerm.parse("123")
    assert term.is_int()
    assert term.int_value() == 123


def test_symbolic_term_string():
    term = SymbolicTerm.parse('"foo"')
    assert term.is_string()
    assert str(term) == '"foo"'


def test_symbolic_term_function():
    term = SymbolicTerm.parse("foo")
    term = SymbolicTerm.parse("foo(bar)")
    assert term.is_function()
    assert term.function_name == "foo"
    assert term.function_arity == 1


def test_symbolic_atom_match():
    atom1 = SymbolicAtom.parse("foo(bar)")
    atom2 = SymbolicAtom.parse("foo(X)")
    assert atom1.match(atom2)


def test_symbolic_atom_match_nested():
    atom1 = SymbolicAtom.parse("foo(bar(buzz))")
    atom2 = SymbolicAtom.parse("foo(bar(X))")
    assert atom1.match(atom2)


def test_program_move_up():
    program = SymbolicProgram.parse("""
given((1, 1), 6).
given((1, 3), 9).    
given((2, 9), 1).
given((7, 3), 4).
given((7, 4), 7).
given((8, 9), 8).
given((9, 7), 7).
given((9, 8), 1).
    """)
    program = program.move_up(SymbolicAtom.parse("""
given((7, Col), Value)
    """))
    assert program[0] == SymbolicRule.parse("given((7, 3), 4).")


def test_query_herbrand_base():
    program = SymbolicProgram.parse("""
block((sub, Row', Col'), (Row, Col)) :- Row = 1..9; Col = 1..9; Row' = (Row-1) / 3; Col' = (Col-1) / 3.
    """)
    res = program.query_herbrand_base(
        "Row, Col",
        "block((sub, Row', Col'), (Row, Col)), block((sub, Row', Col'), (7, 9))"
    )
    assert len(res) == 9


def test_expand_conditional_literal():
    program = SymbolicProgram.parse("""
{a(1..3)}.
b :- a(X) : X = 1..3.
    """)
    program = program.expand_global_and_local_variables()
    assert str(program) == """
{ a(1); a(2); a(3) }.
b :- a(1); a(2); a(3).
    """.strip()


def test_expand_negative_conditional_literal():
    program = SymbolicProgram.parse("""
{a(1..3)}.
b :- not a(X) : X = 1..3.
    """)
    program = program.expand_global_and_local_variables()
    assert str(program) == """
{ a(1); a(2); a(3) }.
b :- not a(1); not a(2); not a(3).
    """.strip()


def test_expand_conditional_literal_in_aggregate():
    program = SymbolicProgram.parse("""
{a(1..3)}.
b :- #sum{X : a(X)} >= 3.
    """)
    program = program.expand_global_and_local_variables()
    assert str(program) == """
{ a(1); a(2); a(3) }.
b :- 3 <= #sum { X: a(X) }.
    """.strip()


def test_expand_skips_disabled_rules_by_default():
    program = SymbolicProgram.of(SymbolicRule.parse("""
{a(X) : X = 1..3}.
    """).disable())
    program = program.expand_global_and_local_variables()
    assert str(program) == """
%* {a(X) : X = 1..3}. *%
    """.strip()


def test_expand_disabled_rule():
    program = SymbolicProgram.of(SymbolicRule.parse("""
{a(X) : X = 1..3}.
    """).disable())
    program = program.expand_global_and_local_variables(expand_also_disabled_rules=True)
    assert str(program) == """
%* { a(1); a(2); a(3) }. *%
    """.strip()


def test_expand_disabled_rule_into_several_rules():
    program = SymbolicProgram.of(SymbolicRule.parse("""
a(X) :- X = 1..3.
    """).disable())
    program = program.expand_global_and_local_variables(expand_also_disabled_rules=True)
    assert str(program) == """
%* a(1) :- 1 = (1..3). *%
%* a(2) :- 2 = (1..3). *%
%* a(3) :- 3 = (1..3). *%
    """.strip()


def test_expand_global_variables_in_rule_with_negation():
    program = SymbolicProgram.parse("""
{b(1)}.
{c(1)}.
a(X) :- b(X), not c(X).
    """)
    program = program.expand_global_safe_variables(rule=program[-1], variables=["X"])
    assert len(program) == 3


def test_predicate_renaming_in_symbolic_rule():
    rule = SymbolicRule.parse("a(b) :- b(a).")
    rule = rule.apply_predicate_renaming(a=Predicate.parse("c"))
    assert str(rule) == "c(b) :- b(a)."


def test_predicate_renaming_in_symbolic_program():
    program = SymbolicProgram.parse("""
a(b) :- b(a).
:- foo, bar, a(a), not a(0).
    """.strip()).apply_predicate_renaming(a=Predicate.parse("c"))
    assert str(program) == """
c(b) :- b(a).
#false :- foo; bar; c(a); not c(0).
    """.strip()


def test_template_str():
    program = SymbolicProgram.parse("""
a :- not __a.
__a :- not a.
    """.strip())
    template = Template(name=Template.Name.parse("main"), program=program)
    assert str(template) == """
__template__("main").
a :- not __a.
__a :- not a.
__end__.
    """.strip()


def test_template_instantiation_can_rename_global_predicates_as_local_predicates():
    template = Template(name=Template.Name.parse("main"), program=SymbolicProgram.parse("foo."))
    assert str(template.instantiate(foo=Predicate.parse("__foo"))) == "__foo."


def test_template_instantiation_cannot_rename_local_predicates():
    template = Template(name=Template.Name.parse("main"), program=SymbolicProgram.of())
    with pytest.raises(ValueError):
        template.instantiate(__foo=Predicate.parse("bar"))


def test_template_instantiation(patched_uuid):
    program = SymbolicProgram.parse("""
pred :- not __false.
__false :- not pred.
__static_foo.
    """.strip())
    template = Template(name=Template.Name.parse("main"), program=program)
    assert str(template.instantiate(pred=Predicate.parse("a"))) == f"""
a :- not __false_ebc40a28_de77_494a_a139_000000000002.
__false_ebc40a28_de77_494a_a139_000000000002 :- not a.
_static_foo_ebc40a28_de77_494a_a139_000000000001.
    """.strip()
    assert str(template.instantiate(pred=Predicate.parse("b"))) == f"""
b :- not __false_ebc40a28_de77_494a_a139_000000000003.
__false_ebc40a28_de77_494a_a139_000000000003 :- not b.
_static_foo_ebc40a28_de77_494a_a139_000000000001.
    """.strip()


def test_template_expand_program(patched_uuid):
    program = SymbolicProgram.parse("""
__template__("choice").
    predicate(X) :- condition(X), not __false(X).
    __false(X) :- condition(X), not predicate(X).
__end__.

edb(1..3).
__apply_template__("choice", (predicate, a), (condition, edb)).
    """)
    program = Template.expand_program(program, trace=True)
    assert str(program) == f"""
edb(1..3).
%* __apply_template__("choice", (predicate, a), (condition, edb)). *%
a(X) :- edb(X); not __false_ebc40a28_de77_494a_a139_{2:012}(X).
__false_ebc40a28_de77_494a_a139_{2:012}(X) :- edb(X); not a(X).
%* __end__. *%
    """.strip()


def test_template_expand_program_requires_templates_to_be_declared_before_they_are_expanded():
    program = SymbolicProgram.parse("""
edb(1..3).
__apply_template__("choice", (predicate, a), (condition, edb)).

__template__("choice").
    predicate(X) :- condition(X), not __false(X).
    __false(X) :- condition(X), not predicate(X).
__end__.
    """)
    with pytest.raises(KeyError):
        Template.expand_program(program)


def test_template_expand_program_cannot_expand_a_template_inside_itself():
    program = SymbolicProgram.parse("""
__template__("foo").
    __apply_template__("foo").
__end__.
    """)
    with pytest.raises(KeyError):
        Template.expand_program(program)


def test_template_expand_apply_templates_inside_templates(patched_uuid):
    program = SymbolicProgram.parse("""
__template__("transitive closure").
    tc(X,Y) :- r(X,Y).
    tc(X,Z) :- tc(X,Y), r(Y,Z).
__end__.

__template__("transitive closure check").
    __apply_template__("transitive closure", (tc, __tc)).
    :- __tc(X,X).
__end__.


link(a,b).
link(b,a).
__apply_template__("transitive closure check", (r, link)).
    """.strip())
    program = Template.expand_program(program, trace=True)
    assert str(program) == """
link(a,b).
link(b,a).
%* __apply_template__("transitive closure check", (r, link)). *%
%* __apply_template__("transitive closure",(tc,__tc)). *%
__tc_ebc40a28_de77_494a_a139_000000000004(X,Y) :- link(X,Y).
__tc_ebc40a28_de77_494a_a139_000000000004(X,Z) :- __tc_ebc40a28_de77_494a_a139_000000000004(X,Y); link(Y,Z).
%* __end__. *%
#false :- __tc_ebc40a28_de77_494a_a139_000000000004(X,X).
%* __end__. *%
    """.strip()
    with pytest.raises(Model.NoModelError):
        Model.of_program(program)


def test_template_for_tc_from_core_lib():
    program = Template.expand_program(SymbolicProgram.parse("""
link(a,b).
link(b,a).
__apply_template__("@dumbo/transitive closure", (relation, link), (closure, link)).
    """.strip()))
    assert Model.of_program(program) == Model.of_atoms("link(a,b) link(b,a) link(a,a) link(b,b)".split())


def test_template_for_transitive_closure_guaranteed():
    program = Template.expand_program(SymbolicProgram.parse("""
link(a,b).
link(b,a).
__apply_template__("@dumbo/transitive closure guaranteed", (relation, link), (closure, link)).
    """.strip()))
    assert Model.of_program(program).filter(when=lambda atom: atom.predicate_name == "link") == \
           Model.of_atoms("link(a,b) link(b,a) link(a,a) link(b,b)".split())


def test_billion_laughs_attack():
    n = 4
    program = SymbolicProgram.parse(
        """__template__("lol0"). lol. __end__.\n""" +
        '\n'.join(f"""__template__("lol{i+1}"). __apply_template__("lol{i}"). __apply_template__("lol{i}"). __end__."""
                  for i in range(n)) +
        f"""\n__apply_template__("lol{n}").""")
    with pytest.raises(ValueError):
        Template.expand_program(program, limit=10)


def test_spanning_tree():
    program = SymbolicProgram.parse("""
link(2,1).  
link(2,3).
__apply_template__("@dumbo/collect arguments (arity 2)", (input, link), (output, node)).
__apply_template__("@dumbo/symmetric closure", (relation, link), (closure, link)).
__apply_template__("@dumbo/spanning tree of undirected graph").
    """)
    program = Template.expand_program(program)
    assert Model.of_program(program).filter(when=lambda atom: atom.predicate_name == "tree") == \
           Model.of_atoms("tree(1,2) tree(2,3)".split())


def test_rule_to_zero_simplification_version():
    rule = SymbolicRule.parse("a(X) :- b(X,Y).").to_zero_simplification_version()
    assert rule == SymbolicRule.parse('__false__(("YShYKSA6LSBiKFgsWSku", ("X","Y")), (X,Y)) |\na(X) :- b(X,Y).')


def test_rule_to_zero_simplification_version_compact():
    rule = SymbolicRule.parse("a(X) :- b(X,Y).").to_zero_simplification_version(compact=True)
    assert rule == SymbolicRule.parse('__false__() |\na(X) :- b(X,Y).')
    assert rule == SymbolicRule.parse('__false__() |\na(X) :- b(X,Y).')


def test_rule_is_choice_rule():
    assert SymbolicRule.parse("{a}.").is_choice_rule
    assert not SymbolicRule.parse("a.").is_choice_rule
    assert SymbolicRule.parse("{a(X) : b(X,Y)} = 1 :- c(Y).").is_choice_rule


def test_rule_to_zero_simplification_version_choice_with_elements():
    rule = SymbolicRule.parse("1 <= %* comment *% {a(X)} :- b(X,Y).").to_zero_simplification_version()
    assert rule == SymbolicRule.parse(
        '1 <= %* comment *% {__false__(("MSA8PSAlKiBjb21tZW50IColIHthKFgpfSA6LSBiKFgsWSku", ("X","Y")), (X,Y)); a(X)} '
        ':- b(X,Y).')


def test_rule_to_zero_simplification_version_choice_with_no_elements():
    rule = SymbolicRule.parse("1 <= %* comment {} *% {} :- b(X,Y).").to_zero_simplification_version()
    assert rule == SymbolicRule.parse(
        '1 <= %* comment {} *% {__false__(("MSA8PSAlKiBjb21tZW50IHt9IColIHt9IDotIGIoWCxZKS4=", ("X","Y")), (X,Y))} :- b(X,Y).')


def test_rule_to_zero_simplification_version_constraint():
    rule = SymbolicRule.parse(":- b(X,Y).").to_zero_simplification_version()
    assert rule == SymbolicRule.parse(
        '__false__(("Oi0gYihYLFkpLg==", ("X","Y")), (X,Y))\n:- b(X,Y).')


def test_program_to_zero_simplification_version():
    program = SymbolicProgram.parse("""
a.
b :- not a.
c :- d.
d :- c.
p(X) :- e(X,Y).
e(X,Y) :- X = 11..13, Y = 10 - X/2.
    """.strip()).to_zero_simplification_version(extra_atoms=(GroundAtom.parse(atom) for atom in "a b c d".split()))
    assert str(program) == """
__false__(("YS4=", ()), ()) |
a.
__false__(("YiA6LSBub3QgYS4=", ()), ()) |
b :- not a.
__false__(("YyA6LSBkLg==", ()), ()) |
c :- d.
__false__(("ZCA6LSBjLg==", ()), ()) |
d :- c.
__false__(("cChYKSA6LSBlKFgsWSku", ("X","Y")), (X,Y)) |
p(X) :- e(X,Y).
__false__(("ZShYLFkpIDotIFggPSAxMS4uMTMsIFkgPSAxMCAtIFgvMi4=", ("X","Y")), (X,Y)) |
e(X,Y) :- X = 11..13, Y = 10 - X/2.
a | b | c | d :- __false__().
{__false__()}.
:- #count{0 : __false__(); RuleID, Substitution : __false__(RuleID, Substitution)} > 0.
    """.strip()


def test_rules_grouped_by_false_predicate():
    program = SymbolicProgram.parse("""
a(X) :- b(X,Y), not c(Y).
b(1,1).
b(1,2).
c(1).
    """).to_zero_simplification_version()
    substitutions, variables = program.rules_grouped_by_false_predicate
    assert variables["a(X) :- b(X,Y), not c(Y)."] == {'X': 0, 'Y': 1}
    assert [[str(x) for x in sub.arguments] for sub in substitutions["a(X) :- b(X,Y), not c(Y)."]] == \
           [['1', '1'], ['1', '2']]


def test_rule_positive_body_literals():
    assert len(SymbolicRule.parse(":- b(X), c(X), not d(X).").positive_body_literals) == 2
    assert len(SymbolicRule.parse("a(X) :- X == 1..2.").positive_body_literals) == 0


def test_rule_negative_body_literals():
    assert len(SymbolicRule.parse(":- b(X), c(X), not d(X).").negative_body_literals) == 1
    assert len(SymbolicRule.parse("a(X) :- X == 1..2, not X == 2..3.").negative_body_literals) == 0


def test_rule_serialization():
    assert Model.of_atoms(SymbolicRule.parse("a(1) :- b(1,2), not c(2).").serialize()).as_facts == """
head("YSgxKSA6LSBiKDEsMiksIG5vdCBjKDIpLg==","YSgxKQ==").
neg_body("YSgxKSA6LSBiKDEsMiksIG5vdCBjKDIpLg==","YygyKQ==").
pos_body("YSgxKSA6LSBiKDEsMiksIG5vdCBjKDIpLg==","YigxLDIp").
rule("YSgxKSA6LSBiKDEsMiksIG5vdCBjKDIpLg==").    
    """.strip()


def test_program_serialization():
    assert Model.of_atoms(SymbolicProgram.parse("""
a(1) :- b(1,2), not c(2).
b(1,2).
    """.strip()).serialize()) == Model.of_program("""
head("YSgxKSA6LSBiKDEsMiksIG5vdCBjKDIpLg==","YSgxKQ==").
head("YigxLDIpLg==","YigxLDIp").
neg_body("YSgxKSA6LSBiKDEsMiksIG5vdCBjKDIpLg==","YygyKQ==").
pos_body("YSgxKSA6LSBiKDEsMiksIG5vdCBjKDIpLg==","YigxLDIp").
rule("YSgxKSA6LSBiKDEsMiksIG5vdCBjKDIpLg==").
rule("YigxLDIpLg==").
    """.strip())


def test_constraint_serialization():
    assert Model.of_atoms(SymbolicRule.parse(":- b(1,2), not c(2).".strip()).serialize(base64_encode=False)) == \
           Model.of_program("""
neg_body(":- b(1,2), not c(2).","c(2)").
pos_body(":- b(1,2), not c(2).","b(1,2)").
rule(":- b(1,2), not c(2).").
           """.strip())


def test_choice_rule_serialization():
    assert Model.of_atoms(SymbolicRule.parse("{a; b} = 1 :- c.".strip()).serialize(base64_encode=False)) == \
           Model.of_program("""
choice("{a; b} = 1 :- c.",1,1).
head("{a; b} = 1 :- c.","a").
head("{a; b} = 1 :- c.","b").
pos_body("{a; b} = 1 :- c.","c").
rule("{a; b} = 1 :- c.").
           """.strip())


def test_disjunctive_rule_serialization():
    assert Model.of_atoms(SymbolicRule.parse("a | b :- c.".strip()).serialize(base64_encode=False)) == \
           Model.of_program("""
head("a | b :- c.","a").
head("a | b :- c.","b").
pos_body("a | b :- c.","c").
rule("a | b :- c.").
           """.strip())


def test_interval_serialization():
    assert Model.of_atoms(SymbolicRule.parse("a :- 1 = 2..3.").serialize(base64_encode=False)) == \
           Model.of_program("""
head("a :- 1 = 2..3.","a").
pos_body("a :- 1 = 2..3.","1 = (2..3)").
rule("a :- 1 = 2..3.").
           """.strip())
    assert Model.of_atoms(SymbolicRule.parse("a :- 2 = 1..3.").serialize(base64_encode=False)) == \
           Model.of_program("""
head("a :- 2 = 1..3.","a").
rule("a :- 2 = 1..3.").
           """.strip())
