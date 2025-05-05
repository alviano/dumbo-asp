from builtins import ValueError
from unittest.mock import patch

import pytest

from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.predicates import Predicate
from dumbo_asp.primitives.programs import SymbolicProgram
from dumbo_asp.primitives.templates import Template


@pytest.fixture
def patched_uuid():
    with patch("dumbo_asp.utils.uuid",
               side_effect=[f"ebc40a28_de77_494a_a139_{i:012}" for i in range(1, 100)]
               ):
        yield


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
    with pytest.raises(ValueError):
        Template.expand_program(program)


def test_template_expand_program_cannot_expand_a_template_inside_itself():
    program = SymbolicProgram.parse("""
__template__("foo").
    __apply_template__("foo").
__end__.
    """)
    with pytest.raises(ValueError):
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


def test_billion_laughs_attack():
    n = 4
    program = SymbolicProgram.parse(
        """__template__("lol0"). lol. __end__.\n""" +
        '\n'.join(f"""__template__("lol{i+1}"). __apply_template__("lol{i}"). __apply_template__("lol{i}"). __end__."""
                  for i in range(n)) +
        f"""\n__apply_template__("lol{n}").""")
    with pytest.raises(ValueError):
        Template.expand_program(program, limit=10)


def test_core_template_names():
    assert '@dumbo/collect argument 1 of 1' in Template.core_template_names()


def test_is_core_template():
    assert Template.is_core_template('@dumbo/collect argument 1 of 1')


def test_core_template():
    assert str(Template.core_template('@dumbo/collect argument 1 of 1').program) == 'output(X0) :- input(X0).'


def test_template_predicates():
    assert set(Template.core_template('@dumbo/collect argument 1 of 1').predicates()) == {Predicate.parse('output', 1), Predicate.parse('input', 1)}
    assert set(Template.core_template("@dumbo/symmetric closure guaranteed").predicates()) == {Predicate.parse('closure', 2), Predicate.parse('relation', 2)}


def test_cannot_redefine_templates():
    with pytest.raises(ValueError):
        Template.expand_program(SymbolicProgram.parse("""
        __template__("@test/foo").
            ok :- ok(X).
        __end__.
        __template__("@test/foo").
            ok :- ok2(X).
        __end__.
            """), register_templates=True)
    with pytest.raises(ValueError):
        Template.expand_program(SymbolicProgram.parse("""
        __template__("@test/foo").
            ok :- ok(X).
        __end__.
        __template__("@test/foo").
            ok :- ok2(X).
        __end__.
            """), register_templates=False)


def test_template_predicate_with_multiple_arities():
    Template.expand_program(SymbolicProgram.parse("""
__template__("@test/ok").
    ok :- ok(X).
__end__.
    """), register_templates=True)
    assert Template.is_core_template("@test/ok")
    assert set(Template.core_template("@test/ok").predicates()) == {Predicate.parse('ok', 0), Predicate.parse('ok', 1)}
    program = Template.expand_program(SymbolicProgram.parse("""
__apply_template__("@test/ok", (ok(0), bar), (ok, buzz)).
    """))
    assert str(program) == "bar :- buzz(X)."
