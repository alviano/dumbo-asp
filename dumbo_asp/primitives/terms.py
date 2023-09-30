import copy
import dataclasses
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


@typeguard.typechecked
@dataclasses.dataclass(frozen=True)
class SymbolicTerm:
    __value: clingo.ast.AST
    __parsed_string: Optional[str]

    key: InitVar[PrivateKey]
    __key = PrivateKey()

    def __post_init__(self, key: PrivateKey):
        self.__key.validate(key)
        validate("type", self.__value.ast_type, is_in=[clingo.ast.ASTType.SymbolicTerm, clingo.ast.ASTType.Function,
                                                       clingo.ast.ASTType.Variable])

    @staticmethod
    def parse(string: str) -> "SymbolicTerm":
        rule: Final = f":- a({string})."
        try:
            program = Parser.parse_program(rule)
        except Parser.Error as error:
            raise error.drop(first=5, last=2)

        validate("one rule", program, length=1,
                 help_msg=f"Unexpected sequence of {len(program)} rules in {utils.one_line(string)}")
        validate("one atom", program[0].body, length=1,
                 help_msg=f"Unexpected conjunction of {len(program[0].body)} atoms in {utils.one_line(string)}")
        atom = program[0].body[0].atom.symbol
        validate("arity", atom.arguments, length=1,
                 help_msg=f"Unexpected sequence of {len(atom.arguments)} terms in {utils.one_line(string)}")
        return SymbolicTerm(atom.arguments[0], utils.extract_parsed_string(rule, atom.arguments[0].location),
                            key=SymbolicTerm.__key)

    @staticmethod
    def of_int(value: int) -> "SymbolicTerm":
        return SymbolicTerm.parse(str(value))

    @staticmethod
    def of_string(value: str) -> "SymbolicTerm":
        return SymbolicTerm.parse(f'"{value}"')

    def __str__(self):
        return self.__parsed_string or str(self.__value)

    def is_int(self) -> bool:
        return self.__value.ast_type == clingo.ast.ASTType.SymbolicTerm and \
            self.__value.symbol.type == clingo.SymbolType.Number

    def is_string(self) -> bool:
        return self.__value.ast_type == clingo.ast.ASTType.SymbolicTerm and \
            self.__value.symbol.type == clingo.SymbolType.String

    def is_function(self) -> bool:
        return self.__value.ast_type == clingo.ast.ASTType.Function or \
            self.__value.ast_type == clingo.ast.ASTType.SymbolicTerm and \
            self.__value.symbol.type == clingo.SymbolType.Function

    def is_variable(self) -> bool:
        return self.__value.ast_type == clingo.ast.ASTType.Variable

    def int_value(self) -> int:
        return self.__value.symbol.number

    def string_value(self) -> str:
        return self.__value.symbol.string

    @property
    def function_name(self) -> str:
        return self.__value.name if self.__value.ast_type == clingo.ast.ASTType.Function else self.__value.symbol.name

    @property
    def function_arity(self) -> int:
        return len(self.__value.arguments if self.__value.ast_type == clingo.ast.ASTType.Function else
                   self.__value.symbol.arguments)

    @cached_property
    def arguments(self) -> tuple["SymbolicTerm", ...]:
        return tuple(SymbolicTerm.parse(str(argument)) for argument in self.__value.arguments) \
            if "arguments" in self.__value.keys() else ()

    def make_copy_of_value(self) -> clingo.ast.AST:
        return copy.deepcopy(self.__value)

    def match(self, pattern: "SymbolicTerm") -> bool:
        if pattern.is_variable() or self.is_variable():
            return True
        if pattern.is_function():
            return self.is_function() and pattern.function_name == self.function_name and \
                pattern.function_arity == self.function_arity and \
                all(argument.match(pattern.arguments[index]) for index, argument in enumerate(self.arguments))
        return pattern == self

