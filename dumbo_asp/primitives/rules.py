import base64
import dataclasses
import re
from dataclasses import InitVar
from functools import cached_property
from typing import Optional, Iterable, Any, Final

import clingo
import clingo.ast
import typeguard
from clingo.ast import ComparisonOperator, Location
from dumbo_utils.primitives import PrivateKey
from dumbo_utils.validation import validate

from dumbo_asp import utils
from dumbo_asp.primitives.atoms import SymbolicAtom, GroundAtom
from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.parsers import Parser
from dumbo_asp.primitives.predicates import Predicate
from dumbo_asp.primitives.terms import SymbolicTerm
from dumbo_asp.utils import uuid, extract_parsed_string


@typeguard.typechecked
@dataclasses.dataclass(frozen=True)
class SymbolicRule:
    __value: clingo.ast.AST
    __parsed_string: Optional[str]
    disabled: bool

    key: InitVar[PrivateKey]
    __key = PrivateKey()

    def __post_init__(self, key: PrivateKey):
        self.__key.validate(key)
        validate("type", self.__value.ast_type, equals=clingo.ast.ASTType.Rule)

    @staticmethod
    def parse(string: str, disabled: bool = False) -> "SymbolicRule":
        program = Parser.parse_program(string)
        validate("one rule", program, length=1,
                 help_msg=f"Unexpected sequence of {len(program)} rules in {utils.one_line(string)}")
        return SymbolicRule(program[0], string, disabled=disabled, key=SymbolicRule.__key)

    @staticmethod
    def of(value: clingo.ast.AST, disabled: bool = False) -> "SymbolicRule":
        validate("value", value.ast_type == clingo.ast.ASTType.Rule, equals=True)
        return SymbolicRule(value, None, disabled=disabled, key=SymbolicRule.__key)

    def __str__(self):
        res = self.__parsed_string or str(self.__value)
        return f"%* {res} *%" if self.disabled else res

    def transform(self, transformer: clingo.ast.Transformer) -> Any:
        transformer(self.__value)

    @property
    def is_fact(self) -> bool:
        return len(self.__value.body) == 0 and self.is_normal_rule

    @property
    def is_normal_rule(self) -> bool:
        return self.__value.head.ast_type == clingo.ast.ASTType.Literal and \
            self.__value.head.sign == clingo.ast.Sign.NoSign

    @property
    def is_choice_rule(self) -> bool:
        return self.__value.head.ast_type == clingo.ast.ASTType.Aggregate

    @property
    def is_disjunctive_rule(self) -> bool:
        return self.__value.head.ast_type == clingo.ast.ASTType.Disjunction

    @property
    def is_constraint(self) -> bool:
        return self.head_atom == SymbolicAtom.of_false()

    @property
    def head_atom(self) -> SymbolicAtom:
        if ("atom" in self.__value.head.keys()) and ("value" in self.__value.head.atom.keys()):
            validate("#false", self.__value.head.atom.value, equals=0)
            return SymbolicAtom.of_false()
        return SymbolicAtom.of(self.__value.head.atom.symbol)

    @staticmethod
    def __compute_choice_bounds(choice):
        left, right = 0, "unbounded"
        if choice.left_guard is not None:
            validate("left guard", choice.left_guard.comparison != ComparisonOperator.NotEqual, equals=True)
            if choice.left_guard.comparison == ComparisonOperator.LessThan:
                left = f"{choice.left_guard.term} + 1"
            elif choice.left_guard.comparison == ComparisonOperator.LessEqual:
                left = f"{choice.left_guard.term}"
            elif choice.left_guard.comparison == ComparisonOperator.GreaterThan:
                right = f"{choice.left_guard.term} - 1"
            elif choice.left_guard.comparison == ComparisonOperator.GreaterEqual:
                right = f"{choice.left_guard.term}"
            elif choice.left_guard.comparison == ComparisonOperator.Equal:
                left = f"{choice.left_guard.term}"
                right = f"{choice.left_guard.term}"
            else:
                raise ValueError("Choice with != are not supported.")
        if choice.right_guard is not None:
            validate("right guard", choice.right_guard.comparison, is_in=[ComparisonOperator.LessThan,
                                                                          ComparisonOperator.LessEqual])
            if choice.right_guard.comparison == ComparisonOperator.LessThan:
                right = f"{choice.right_guard.term} + 1"
            elif choice.right_guard.comparison == ComparisonOperator.LessEqual:
                right = f"{choice.right_guard.term}"
        return left, right

    @property
    def choice_lower_bound(self) -> str:
        validate("choice rule", self.is_choice_rule, equals=True)
        return self.__compute_choice_bounds(self.__value.head)[0]

    @property
    def choice_upper_bound(self) -> str:
        validate("choice rule", self.is_choice_rule, equals=True)
        return self.__compute_choice_bounds(self.__value.head)[1]

    @property
    def positive_body_literals(self) -> tuple[SymbolicAtom, ...]:
        return tuple(SymbolicAtom.of(literal.atom.symbol)
                     for literal in self.__value.body
                     if literal.sign == clingo.ast.Sign.NoSign and "symbol" in literal.atom.keys())

    @property
    def negative_body_literals(self) -> tuple[SymbolicAtom, ...]:
        return tuple(SymbolicAtom.of(literal.atom.symbol)
                     for literal in self.__value.body
                     if literal.sign == clingo.ast.Sign.Negation and "symbol" in literal.atom.keys())

    def serialize(self, *, base64_encode: bool = True) -> tuple[GroundAtom, ...]:
        def b64(s):
            return f'"{base64.b64encode(str(s).encode()).decode()}"' if base64_encode else \
                str(clingo.String(str(s)))
        rule = b64(self)
        res = [f'rule({rule})']
        if self.is_normal_rule:
            if not self.is_constraint:
                res.append(f"head({rule}, {b64(self.head_atom)})")
        elif self.is_choice_rule:
            lb, ub = self.__compute_choice_bounds(self.__value.head)
            res.append(f"choice({rule}, {lb}, {ub})")
            for atom in self.__value.head.elements:
                assert not atom.condition  # extend to conditional
                res.append(f"head({rule}, {b64(atom)})")
        elif self.is_disjunctive_rule:
            for atom in self.__value.head.elements:
                assert not atom.condition  # extend to conditional
                res.append(f"head({rule}, {b64(atom)})")
        else:
            assert False
        for literal in self.__value.body:
            if "atom" not in literal.keys():
                assert False  # extend?
            if literal.sign == clingo.ast.Sign.NoSign:
                predicate = "pos_body"
            elif literal.sign == clingo.ast.Sign.Negation:
                predicate = "neg_body"
            else:
                assert False  # extend

            if literal.atom.ast_type == clingo.ast.ASTType.Comparison:
                if Model.empty().compute_substitutions(
                    arguments="",
                    number_of_arguments=0,
                    conjunctive_query=str(literal.atom)
                ):
                    if predicate == "pos_body":
                        continue
                else:
                    if predicate == "neg_body":
                        continue
            res.append(f'{predicate}({rule}, {b64(literal.atom)})')
        return tuple(GroundAtom.parse(atom) for atom in res)

    @cached_property
    def head_variables(self) -> tuple[str, ...]:
        res = set()

        class Transformer(clingo.ast.Transformer):
            def visit_Variable(self, node):
                res.add(str(node))
                return node

        Transformer().visit(self.__value.head)
        return tuple(sorted(res))

    @cached_property
    def body_variables(self) -> tuple[str, ...]:
        res = set()

        class Transformer(clingo.ast.Transformer):
            def visit_Variable(self, node):
                res.add(str(node))
                return node

        Transformer().visit_sequence(self.__value.body)
        return tuple(sorted(res))

    @cached_property
    def global_safe_variables(self) -> tuple[str, ...]:
        res = set()

        class Transformer(clingo.ast.Transformer):
            def visit_Literal(self, node):
                if node.sign == clingo.ast.Sign.NoSign:
                    self.visit_children(node)

            def visit_ConditionalLiteral(self, node):
                # a conditional literal cannot bound new variables
                # (this is not the case for "existential" variables, which are not covered at the moment)
                pass

            def visit_BodyAggregate(self, node):
                for guard in [node.left_guard, node.right_guard]:
                    if guard is not None and guard.comparison == clingo.ast.ComparisonOperator.Equal:
                        self.visit(guard.term)

            def visit_Variable(self, node):
                if node.name != '_':
                    res.add(node.name)
                return node

        Transformer().visit_sequence(self.__value.body)
        return tuple(sorted(res))

    @cached_property
    def predicates(self) -> tuple[Predicate, ...]:
        res = set()

        class Transformer(clingo.ast.Transformer):
            def visit_Function(self, node):
                res.add((node.name, len(node.arguments)))
                return node

            def visit_Literal(self, node):
                if "symbol" in node.atom.keys():
                    res.add((node.atom.symbol.name, len(node.atom.symbol.arguments)))
                elif "elements" in node.atom.keys():
                    for element in node.atom.elements:
                        self.visit(element.update(terms=[]))
                return node

        Transformer().visit(self.__value)
        return tuple(Predicate.parse(*pred) for pred in res)

    def disable(self) -> "SymbolicRule":
        return SymbolicRule(self.__value, self.__parsed_string, True, key=self.__key)

    def with_extended_body(self, atom: SymbolicAtom, sign: clingo.ast.Sign = clingo.ast.Sign.NoSign) -> "SymbolicRule":
        literal = f"{atom}" if sign == clingo.ast.Sign.NoSign else \
            f"not {atom}" if sign == clingo.ast.Sign.Negation else \
            f"not not {atom}"
        if self.__parsed_string is None:
            string = str(self)
            line = 1
            column = len(string) - 1
        else:
            string = self.__parsed_string
            line = self.__value.location.end.line
            column = self.__value.location.end.column - 1
        new_rule = utils.insert_in_parsed_string(
            f"; {literal}" if len(self.__value.body) > 0 else f" :- {literal}", string, line, column
        )
        return self.parse(new_rule, self.disabled)

    def with_chopped_body(self, *,
                          with_backward_search=False, backward_search_symbols=(';', ',', ' :-', ':-')) -> "SymbolicRule":
        validate("body", self.__value.body, min_len=1, help_msg="Cannot chop on empty body")
        the_rule = SymbolicRule.parse(str(self.__value)) if self.__parsed_string is None else self
        string = the_rule.__parsed_string
        body = the_rule.__value.body
        if len(body) == 1:
            begin = the_rule.__value.head.location.end
        else:
            begin = body[-2].location.end
        location = clingo.ast.Location(begin, body[-1].location.end)

        def backward_search():
            res = extract_parsed_string(string, clingo.ast.Location(begin, body[-1].location.begin))
            while True:
                for symbol in backward_search_symbols:
                    if res.endswith(symbol):
                        return res[:-len(symbol)]
                validate("backward search", res, min_len=1,
                         help_msg="Backward search failure! Specify a different symbol")
                res = res[:-1]

        new_rule = utils.replace_in_parsed_string(string, location, backward_search() if with_backward_search else "")
        return self.parse(new_rule, self.disabled)

    def body_as_string(self, separator: str = "; ") -> str:
        return separator.join(str(x) for x in self.__value.body)

    def apply_variable_substitution(self, **kwargs: SymbolicTerm) -> "SymbolicRule":
        class Transformer(clingo.ast.Transformer):
            def visit_Variable(self, node):
                if str(node) not in kwargs.keys():
                    return node
                return kwargs[str(node)].make_copy_of_value()

        return self.of(Transformer().visit(self.__value), self.disabled)

    def apply_term_substitution(self, **kwargs: SymbolicTerm) -> "SymbolicRule":
        class Transformer(clingo.ast.Transformer):
            def visit_SymbolicTerm(self, node):
                if str(node) not in kwargs.keys():
                    return node
                return kwargs[str(node)].make_copy_of_value()

        return self.of(Transformer().visit(self.__value), self.disabled)

    def apply_predicate_renaming(self, **kwargs: Predicate) -> "SymbolicRule":
        class Transformer(clingo.ast.Transformer):
            def visit_Function(self, node):
                return node.update(name=kwargs[node.name].name) if node.name in kwargs.keys() else node

        return self.of(Transformer().visit(self.__value), self.disabled)

    def __expand_global_safe_variables(
            self,
            *,
            variables: Iterable[str],
            herbrand_base: Model,
            expand_also_local_variables=False,
    ) -> tuple["SymbolicRule", ...]:
        the_variables: Final = set(var for var in variables if var in self.global_safe_variables)
        validate("variables", set(variables), equals=the_variables)
        substitutions = herbrand_base.compute_substitutions(
            arguments=','.join(the_variables),
            number_of_arguments=len(the_variables),
            conjunctive_query=self.body_as_string(),
        ) if the_variables else ([],)

        prefix = uuid()
        suffix = uuid()

        class Transformer(clingo.ast.Transformer):
            def __init__(self):
                super().__init__()
                self.possibly_has_local_variables = False
                self.locations = []

            def visit_Variable(self, node):
                if node.name in the_variables:
                    self.locations.append((node.location, prefix + node.name + suffix))
                return node

            # def visit_BodyAggregateElement(self, node):  NOT SUPPORTED AT THE MOMENT
            def visit_ConditionalLiteral(self, node):
                self.possibly_has_local_variables = True
                self.visit_children(node)
                return node

        transformer = Transformer()
        transformer.visit(self.__value)
        fmt = self.__parsed_string or str(self.__value)
        for location, replacement in reversed(transformer.locations):
            fmt = utils.replace_in_parsed_string(fmt, location, replacement)

        pattern = f"{prefix}({'|'.join(var for var in the_variables)}){suffix}"
        var_to_index = {var: index for index, var in enumerate(the_variables)}

        def apply(substitution):
            return re.sub(pattern, lambda m: substitution[var_to_index[m.group(1)]], fmt)

        if expand_also_local_variables and transformer.possibly_has_local_variables:
            return tuple(
                SymbolicRule.parse(apply([str(s) for s in substitution]), self.disabled)
                .__expand_local_variables(herbrand_base=herbrand_base)
                for substitution in substitutions
            )
        else:
            return tuple(
                SymbolicRule.parse(apply([str(s) for s in substitution]), self.disabled)
                for substitution in substitutions
            )

    def __expand_local_variables(self, *, herbrand_base: Model) -> "SymbolicRule":
        class Transformer(clingo.ast.Transformer):
            def __init__(self):
                super().__init__()
                self.substitutions = []

            # def visit_BodyAggregateElement(self, node):  NOT SUPPORTED AT THE MOMENT
            def visit_ConditionalLiteral(self, node):
                substitutions = herbrand_base.compute_substitutions(
                    arguments=','.join(str(arg) for arg in node.literal.atom.symbol.arguments),
                    number_of_arguments=len(node.literal.atom.symbol.arguments),
                    conjunctive_query=f"{', '.join(str(condition) for condition in node.condition)}",
                )
                self.substitutions.append(
                    (
                        Location(
                            begin=node.location.begin,
                            end=node.condition[-1].location.end if node.condition else node.location.end
                        ),
                        [
                            (
                                "not " if node.literal.sign == clingo.ast.Sign.Negation else
                                "not not " if node.literal.sign == clingo.ast.Sign.DoubleNegation
                                else ""
                            ) +
                            f"{node.literal.atom.symbol.name}({','.join(str(arg) for arg in arguments)})" if arguments
                            else f"{node.literal.atom.symbol.name}"
                            for arguments in substitutions
                        ]
                    )
                )
                return node

        transformer = Transformer()
        transformer.visit(self.__value)
        rule = self.__parsed_string or str(self.__value)
        for location, atoms in reversed(transformer.substitutions):
            rule = utils.replace_in_parsed_string(rule, location, '; '.join(atoms))
        return SymbolicRule.parse(rule, disabled=self.disabled)

    def expand_global_safe_variables(
            self,
            *,
            variables: Iterable[str],
            herbrand_base: Model,
    ) -> tuple["SymbolicRule", ...]:
        return self.__expand_global_safe_variables(variables=variables, herbrand_base=herbrand_base,
                                                   expand_also_local_variables=False)

    def expand_global_and_local_variables(self, *, herbrand_base: Model) -> tuple["SymbolicRule", ...]:
        return self.__expand_global_safe_variables(variables=self.global_safe_variables, herbrand_base=herbrand_base,
                                                   expand_also_local_variables=True)

    def match(self, *pattern: SymbolicAtom) -> bool:
        class Transformer(clingo.ast.Transformer):
            def visit_SymbolicAtom(self, node):
                atom = SymbolicAtom.of(node.symbol)
                if atom.match(*pattern):
                    Transformer.matched = True
                return node
        Transformer.matched = False

        Transformer().visit(self.__value)
        return Transformer.matched

    def to_zero_simplification_version(self, *, compact=False) -> "SymbolicRule":
        if compact:
            atom = Predicate.false().name
        else:
            rule_vars_as_strings = ','.join(f'"{var}"' for var in self.global_safe_variables)
            rule_id = f'("{base64.b64encode(str(self).encode()).decode()}", ' \
                      f'({rule_vars_as_strings}{"," if len(rule_vars_as_strings) == 1 else ""}))'
            rule_vars = ','.join(self.global_safe_variables)

            atom = f'{Predicate.false().name}({rule_id}, ' \
                   f'({rule_vars}{"," if len(rule_vars) == 1 else ""}))'

        if self.is_choice_rule:
            if self.__value.head.elements:
                _, line, column = self.__value.head.elements[0].location.begin
                return SymbolicRule.parse(
                    utils.insert_in_parsed_string(f"{atom};\n{' ' * (column-1)}", str(self), line, column)
                )
            s = str(self)
            index = 0
            while True:
                if s[index] == '%':
                    index += 1
                    if s[index] == '*':
                        index += 1
                        while s[index] != '*' or s[index + 1] != '%':
                            index += 1
                        index += 1
                    else:
                        index += 1
                        while s[index] != '\n':
                            index += 1
                if s[index] == '{':
                    break
                index += 1
            return SymbolicRule.parse(s[:index + 1] + f"{atom}" + s[index + 1:])
        if self.is_constraint:
            return SymbolicRule.parse(f'{atom}\n{self}')
        return SymbolicRule.parse(f'{atom} |\n{self}')
