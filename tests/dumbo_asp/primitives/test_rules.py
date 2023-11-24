import clingo
import pytest

from dumbo_asp.primitives.atoms import SymbolicAtom
from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.predicates import Predicate
from dumbo_asp.primitives.rules import SymbolicRule
from dumbo_asp.primitives.terms import SymbolicTerm


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


def test_symbolic_rule_predicates():
    assert set(SymbolicRule.parse("a(X) :- b(X), not c(X).").predicates) == \
           set(Predicate.parse(p) for p in "a/1 b/1 c/1".split())


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
           " a( X , Y )  :- b( Z ). "


def test_symbolic_rule_body_as_string():
    assert SymbolicRule.parse("a :- b, c.").body_as_string() == "b; c"


def test_symbolic_rule_apply_variable_substitution():
    assert str(SymbolicRule.parse("a(X) :- b(X,Y).").apply_variable_substitution(X=SymbolicTerm.of_int(1))) == \
           "a(1) :- b(1,Y)."


def test_symbolic_rule_is_fact():
    assert SymbolicRule.parse("a.").is_fact
    assert SymbolicRule.parse("a(1).").is_fact
    assert SymbolicRule.parse("a(x).").is_fact
    assert SymbolicRule.parse("a(X).").is_fact
    assert not SymbolicRule.parse("a | b.").is_fact


def test_expand_zero_global_variables_with_local_variables():
    rule = SymbolicRule.parse("""
:- bar(X) : foo(X).
    """.strip())
    rules = rule.expand_global_and_local_variables(herbrand_base=Model.of_program("foo(1..3)."))
    assert len(rules) == 1
    assert str(rules[0]) == ":- bar(3); bar(2); bar(1)."


def test_predicate_renaming_in_symbolic_rule():
    rule = SymbolicRule.parse("a(b) :- b(a).")
    rule = rule.apply_predicate_renaming(a=Predicate.parse("c"))
    assert str(rule) == "c(b) :- b(a)."


def test_rule_to_zero_simplification_version():
    rule = SymbolicRule.parse("a(X) :- b(X,Y).").to_zero_simplification_version()
    assert rule == SymbolicRule.parse('__false__(("YShYKSA6LSBiKFgsWSku", ("X","Y")), (X,Y)) |\na(X) :- b(X,Y).')


def test_rule_to_zero_simplification_version_compact():
    rule = SymbolicRule.parse("a(X) :- b(X,Y).").to_zero_simplification_version(compact=True)
    assert rule == SymbolicRule.parse('__false__ |\na(X) :- b(X,Y).')
    assert rule == SymbolicRule.parse('__false__ |\na(X) :- b(X,Y).')


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
        '1 <= %* comment {} *% '
        '{__false__(("MSA8PSAlKiBjb21tZW50IHt9IColIHt9IDotIGIoWCxZKS4=", ("X","Y")), (X,Y))} :- b(X,Y).')


def test_rule_to_zero_simplification_version_constraint():
    rule = SymbolicRule.parse(":- b(X,Y).").to_zero_simplification_version()
    assert rule == SymbolicRule.parse(
        '__false__(("Oi0gYihYLFkpLg==", ("X","Y")), (X,Y))\n:- b(X,Y).')


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
