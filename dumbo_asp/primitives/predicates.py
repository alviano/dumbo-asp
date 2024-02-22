import dataclasses
import functools
from dataclasses import InitVar
from functools import lru_cache
from typing import Optional

import clingo
import clingo.ast
import typeguard
from dumbo_utils.primitives import PrivateKey
from dumbo_utils.validation import validate

from dumbo_asp.primitives.parsers import Parser


@functools.total_ordering
@typeguard.typechecked
@dataclasses.dataclass(frozen=True)
class Predicate:
    name: str
    arity: Optional[int]

    key: InitVar[PrivateKey]
    __key = PrivateKey()

    MAX_ARITY = 999

    def __post_init__(self, key: PrivateKey):
        self.__key.validate(key)

    @staticmethod
    def parse(name: str, arity: Optional[int] = None) -> "Predicate":
        split = name.split('/', maxsplit=1)
        if len(split) == 2:
            validate("arity not given", arity is None, equals=True, help_msg="The arity is given already in the name")
            name, arity = split[0], int(split[1])

        term = Parser.parse_ground_term(name)
        validate("name", term.type, equals=clingo.SymbolType.Function)
        validate("name", term.arguments, length=0)
        validate("name", term.negative, equals=False)
        if arity is not None:
            validate("arity", arity, min_value=0, max_value=Predicate.MAX_ARITY)
        return Predicate(
            name=term.name,
            arity=arity,
            key=Predicate.__key,
        )

    @staticmethod
    def of(term: clingo.Symbol) -> "Predicate":
        return Predicate(
            name=term.name,
            arity=len(term.arguments),
            key=Predicate.__key,
        )

    def drop_arity(self) -> "Predicate":
        return Predicate(
            name=self.name,
            arity=None,
            key=Predicate.__key,
        )

    def with_arity(self, arity: int) -> "Predicate":
        validate("arity", arity, min_value=0, max_value=Predicate.MAX_ARITY)
        return Predicate(
            name=self.name,
            arity=arity,
            key=Predicate.__key,
        )

    def match(self, other: "Predicate") -> bool:
        if self.name != other.name:
            return False
        if self.arity is None or other.arity is None:
            return True
        return self.arity == other.arity

    def __lt__(self, other: "Predicate"):
        if self.name < other.name:
            return True
        if self.name > other.name:
            return False

        if self.arity is None:
            return False
        if other.arity is None:
            return True

        return self.arity < other.arity

    @staticmethod
    @lru_cache
    def false() -> "Predicate":
        return Predicate.of(clingo.Function("__false__")).drop_arity()
