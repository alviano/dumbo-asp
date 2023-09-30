import copy
import dataclasses
import functools
from dataclasses import InitVar
from functools import cached_property
from typing import Optional, Final

import clingo
import clingo.ast
import typeguard
from dumbo_utils.primitives import PrivateKey
from dumbo_utils.validation import validate

from dumbo_asp import utils
from dumbo_asp.primitives.parsers import Parser
from dumbo_asp.primitives.predicates import Predicate
from dumbo_asp.primitives.terms import SymbolicTerm


@functools.total_ordering
@typeguard.typechecked
@dataclasses.dataclass(frozen=True)
class GroundAtom:
    value: clingo.Symbol

    def __post_init__(self):
        validate("atom format", self.value.type, equals=clingo.SymbolType.Function,
                 help_msg="An atom must have a predicate name")

    @staticmethod
    def parse(string: str) -> "GroundAtom":
        return GroundAtom(Parser.parse_ground_term(string))

    @cached_property
    def predicate(self) -> Predicate:
        return Predicate.of(self.value)

    @property
    def predicate_name(self) -> str:
        return self.predicate.name

    @property
    def predicate_arity(self) -> int:
        return self.predicate.arity

    @cached_property
    def arguments(self) -> tuple[clingo.Symbol, ...]:
        return tuple(self.value.arguments)

    @property
    def strongly_negated(self) -> bool:
        return self.value.negative

    def __str__(self):
        return str(self.value)

    def __lt__(self, other: "GroundAtom"):
        if self.predicate < other.predicate:
            return True
        if self.predicate == other.predicate:
            for index, argument in enumerate(self.arguments):
                other_argument = other.arguments[index]
                if argument.type < other_argument.type:
                    return True
                if argument.type > other_argument.type:
                    return False
                if argument.type == clingo.SymbolType.Number:
                    if argument < other_argument:
                        return True
                    if argument > other_argument:
                        return False
                else:
                    s1, s2 = str(argument), str(other_argument)
                    if s1 < s2:
                        return True
                    if s1 > s2:
                        return False
        return False


@typeguard.typechecked
@dataclasses.dataclass(frozen=True)
class SymbolicAtom:
    __value: clingo.ast.AST
    __parsed_string: Optional[str]

    key: InitVar[PrivateKey]
    __key = PrivateKey()

    def __post_init__(self, key: PrivateKey):
        self.__key.validate(key)
        validate("type", self.__value.ast_type,
                 is_in=[clingo.ast.ASTType.SymbolicAtom, clingo.ast.ASTType.Function,
                        clingo.ast.ASTType.BooleanConstant])

    @staticmethod
    def of_false() -> "SymbolicAtom":
        return SymbolicAtom.parse("#false")

    @staticmethod
    def of_ground_atom(atom: GroundAtom) -> "SymbolicAtom":
        return SymbolicAtom.parse(str(atom))

    @staticmethod
    def parse(string: str) -> "SymbolicAtom":
        rule: Final = f":- {string}."
        try:
            program = Parser.parse_program(rule)
        except Parser.Error as error:
            raise error.drop(first=3, last=1)

        validate("one rule", program, length=1,
                 help_msg=f"Unexpected sequence of {len(program)} rules in {utils.one_line(string)}")
        validate("one atom", program[0].body, length=1,
                 help_msg=f"Unexpected conjunction of {len(program[0].body)} atoms in {utils.one_line(string)}")
        literal = program[0].body[0]
        validate("positive", literal.sign, equals=clingo.ast.Sign.NoSign,
                 help_msg=f"Unexpected default negation in {utils.one_line(string)}")
        if "value" in literal.atom.keys():
            validate("#false", literal.atom.value, equals=0)
            atom = SymbolicAtom.parse("foo").__value.update(name="#false")
        else:
            atom = literal.atom.symbol
        return SymbolicAtom(atom, utils.extract_parsed_string(rule, literal.location), key=SymbolicAtom.__key)

    @staticmethod
    def of(value: clingo.ast.AST) -> "SymbolicAtom":
        validate("value", value.ast_type, is_in=[
            clingo.ast.ASTType.Function
        ])
        return SymbolicAtom(value, None, key=SymbolicAtom.__key)

    def __str__(self):
        return self.__parsed_string or str(self.__value)

    def make_copy_of_value(self) -> clingo.ast.AST:
        return copy.deepcopy(self.__value)

    @cached_property
    def predicate(self) -> Predicate:
        return Predicate.parse(self.__value.name, len(self.__value.arguments))

    @property
    def predicate_name(self) -> str:
        if self.__value.name == '#false':
            return self.__value.name
        return self.predicate.name

    @property
    def predicate_arity(self) -> int:
        return self.predicate.arity

    @cached_property
    def arguments(self) -> tuple[SymbolicTerm, ...]:
        return tuple(SymbolicTerm.parse(str(argument)) for argument in self.__value.arguments)

    @property
    def strongly_negated(self) -> bool:
        return self.value.negative

    def match(self, *pattern: "SymbolicAtom") -> bool:
        for a_pattern in pattern:
            if self.predicate == a_pattern.predicate and \
                    all(argument.match(a_pattern.arguments[index]) for index, argument in enumerate(self.arguments)):
                return True
        return False
