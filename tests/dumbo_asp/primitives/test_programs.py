import pytest

from dumbo_asp.primitives.atoms import GroundAtom, SymbolicAtom
from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.predicates import Predicate
from dumbo_asp.primitives.programs import SymbolicProgram
from dumbo_asp.primitives.rules import SymbolicRule
from dumbo_asp.primitives.terms import SymbolicTerm


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


def test_symbolic_program_predicates():
    assert set(SymbolicProgram.parse("""
a(X) :- b(X), not c(X).
:- #sum{X,d(X) : e(X)} = Y.
    """.strip()).predicates) == set(Predicate.parse(p) for p in "a/1 b/1 c/1 e/1".split())


def test_program_herbrand_universe():
    assert SymbolicProgram.parse("a(X) :- X = 1..3.").herbrand_universe == {SymbolicTerm.of_int(x) for x in range(1, 4)}
    assert SymbolicProgram.parse("a(X,Y) :- X = 1..3, Y = 4..5.").herbrand_universe == \
           {SymbolicTerm.of_int(x) for x in range(1, 6)}
    assert SymbolicProgram.parse("a(b(c)).").herbrand_universe == {SymbolicTerm.parse("c")}


def test_program_herbrand_base():
    assert SymbolicProgram.parse("a(X) :- X = 1..3.").herbrand_base == Model.of_program("a(1..3).")


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


def test_expand_zero_global_variables():
    rule = SymbolicRule.parse("""
:- __false__.
    """.strip())
    program = SymbolicProgram.of(rule)
    rules = rule.expand_global_safe_variables(variables=[], herbrand_base=program.herbrand_base)
    assert len(rules) == 1


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


def test_expand_global_variables_wrt_herbrand_base():
    program = SymbolicProgram.parse("""
a(X) :- b(X).
b(X) :- a(X).
    """.strip())
    program = program.expand_global_and_local_variables(
        herbrand_base=program.to_zero_simplification_version(
            extra_atoms=Model.of_program("a(1)."),
            compact=True
        ).herbrand_base_without_false_predicate
    )
    assert len(program) == 2


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
    program = program.move_before(SymbolicAtom.parse("""
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
{a(1); a(2); a(3)}.
b :- a(1); a(2); a(3).
    """.strip()


def test_expand_negative_conditional_literal():
    program = SymbolicProgram.parse("""
{a(1..3)}.
b :- not a(X) : X = 1..3.
    """)
    program = program.expand_global_and_local_variables()
    assert str(program) == """
{a(1); a(2); a(3)}.
b :- not a(1); not a(2); not a(3).
    """.strip()


def test_expand_conditional_literal_in_aggregate():
    program = SymbolicProgram.parse("""
{ a(1..3) }.
b :- #sum{X : a(X)} >= 3.
    """)
    program = program.expand_global_and_local_variables()
    assert str(program) == """
{ a(1); a(2); a(3) }.
b :- #sum{X : a(X)} >= 3.
    """.strip()


def test_expand_skips_disabled_rules_by_default():
    program = SymbolicProgram.of(SymbolicRule.parse("""
{a(X) : X = 1..3}.
    """.strip()).disable())
    program = program.expand_global_and_local_variables()
    assert str(program) == """
%* {a(X) : X = 1..3}. *%
    """.strip()


def test_expand_disabled_rule():
    program = SymbolicProgram.of(SymbolicRule.parse("""
{a(X) : X = 1..3}.
    """.strip()).disable())
    program = program.expand_global_and_local_variables(expand_also_disabled_rules=True)
    assert str(program) == """
%* {a(1); a(2); a(3)}. *%
    """.strip()


def test_expand_disabled_rule_into_several_rules():
    program = SymbolicProgram.of(SymbolicRule.parse("""
a(X) :- X = 1..3.
    """.strip()).disable())
    program = program.expand_global_and_local_variables(expand_also_disabled_rules=True)
    assert str(program) == """
%* a(1) :- 1 = 1..3. *%
%* a(2) :- 2 = 1..3. *%
%* a(3) :- 3 = 1..3. *%
    """.strip()


def test_expand_global_variables_in_rule_with_negation():
    program = SymbolicProgram.parse("""
{b(1)}.
{c(1)}.
a(X) :- b(X), not c(X).
    """)
    program = program.expand_global_safe_variables(rule=program[-1], variables=["X"])
    assert len(program) == 3


def test_predicate_renaming_in_symbolic_program():
    program = SymbolicProgram.parse("""
a(b) :- b(a).
:- foo, bar, a(a), not a(0).
    """.strip()).apply_predicate_renaming(a=Predicate.parse("c"))
    assert str(program) == """
c(b) :- b(a).
#false :- foo; bar; c(a); not c(0).
    """.strip()


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
{a; b; c; d} :- __false__.
{__false__}.
:- #count{0 : __false__; RuleID, Substitution : __false__(RuleID, Substitution)} > 0.
    """.strip()


def test_to_zero_simplification_keeps_all_atoms():
    program = SymbolicProgram.parse("""
a :- b.
b :- a.
    """.strip())
    assert len(program.to_zero_simplification_version(extra_atoms=Model.of_program("a. b."), compact=True)
               .herbrand_base_without_false_predicate) == 2


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
