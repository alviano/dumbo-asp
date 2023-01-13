import dataclasses
import functools
import math
from dataclasses import InitVar
from functools import cached_property
from typing import Any, Callable, Optional, Iterable, Union

import clingo
import clingo.ast
import typeguard

from dumbo_asp import utils
from dumbo_asp.utils import validate, ValidationError


@typeguard.typechecked
class Parser:
    @dataclasses.dataclass(frozen=True)
    class Error(ValueError):
        parsed_string: str
        line: int
        begin: int
        end: int
        message: str

        key: InitVar[Any]
        __key = object()

        def __post_init__(self, key: Any):
            validate("key", key, equals=self.__key, help_msg="Use a factory method")

        @staticmethod
        def parse(error: str, parsed_string: str) -> "Parser.Error":
            parts = error.split(':', maxsplit=3)
            validate("prefix", parts[0], equals="<string>", help_msg="Unexpected source")
            validate("error", parts[3].startswith(" error: "), equals=True, help_msg="Unexpected error")
            begin, end = Parser.parse_range(parts[2])
            return Parser.Error(
                parsed_string=parsed_string,
                line=int(parts[1]),
                begin=begin,
                end=end,
                message=parts[3][len(" error: "):],
                key=Parser.Error.__key,
            )

        def drop(self, *, first: int = 0, last: int = 0) -> "Parser.Error":
            validate("one line", self.line, equals=1, help_msg="Can drop only from one line parsing")
            return Parser.Error(
                parsed_string=self.parsed_string[first:len(self.parsed_string) - last],
                line=self.line,
                begin=self.begin - first,
                end=self.end - first,
                message=self.message,
                key=Parser.Error.__key,
            )

        def __str__(self):
            lines = self.parsed_string.split('\n')
            width = math.floor(math.log10(len(lines))) + 1
            res = [f"Parsing error in line {self.line}, columns {self.begin}-{self.end}"]
            for line_index, the_line in enumerate(lines, start=1):
                res.append(f"{str(line_index).zfill(width)}| {the_line}")
                if line_index == self.line:
                    res.append('>' * width + '| ' + ' ' * (self.begin - 1) + '^' * (self.end - self.begin + 1))
            res.append(f"error: {self.message}")
            return '\n'.join(res)

    @staticmethod
    def parse_range(string: str) -> tuple[int, int]:
        parts = string.split('-', maxsplit=1)
        if len(parts) == 1:
            return int(parts[0]), int(parts[0])
        return int(parts[0]), int(parts[1])

    @staticmethod
    def parse_ground_term(string: str) -> clingo.Symbol:
        try:
            return clingo.parse_term(string)
        except RuntimeError as err:
            raise Parser.Error.parse(str(err), string)

    @staticmethod
    def parse_program(string: str) -> list[clingo.ast.AST]:
        def callback(ast):
            callback.res.append(ast)
        callback.res = []

        messages = []
        try:
            clingo.ast.parse_string(string, callback, logger=lambda code, message: messages.append((code, message)))
            validate("nonempty res", callback.res, min_len=1)
            validate("base program", callback.res[0].ast_type == clingo.ast.ASTType.Program and
                     callback.res[0].name == "base" and len(callback.res[0].parameters) == 0, equals=True)
            validate("only rules", [x for x in callback.res[1:] if x.ast_type != clingo.ast.ASTType.Rule], empty=True)
            return callback.res[1:]
        except RuntimeError:
            errors = [message[1] for message in messages if message[0] == clingo.MessageCode.RuntimeError]
            validate("errors", messages, length=1)
            raise Parser.Error.parse(errors[0], string)


@functools.total_ordering
@typeguard.typechecked
@dataclasses.dataclass(frozen=True)
class Predicate:
    name: str
    arity: Optional[int]
    key: InitVar[Any]

    __key = object()
    MAX_ARITY = 999

    def __post_init__(self, key: Any):
        validate("key", key, equals=self.__key, help_msg="Use a factory method")

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
    value: clingo.ast.AST

    def __post_init__(self):
        validate("type", self.value.ast_type, equals=clingo.ast.ASTType.SymbolicAtom)

    @staticmethod
    def parse(string: str) -> "SymbolicAtom":
        try:
            program = Parser.parse_program(f":- {string}.")
        except Parser.Error as error:
            raise error.drop(first=3, last=1)

        validate("one rule", program, length=1,
                 help_msg=f"Unexpected sequence of {len(program)} rules in {utils.one_line(string)}")
        validate("one atom", program[0].body, length=1,
                 help_msg=f"Unexpected conjunction of {len(program[0].body)} atoms in {utils.one_line(string)}")
        literal = program[0].body[0]
        validate("positive", literal.sign, equals=clingo.ast.Sign.NoSign,
                 help_msg=f"Unexpected default negation in {utils.one_line(string)}")
        atom = literal.atom
        return SymbolicAtom(atom)

    def __str__(self):
        return str(self.value)


@typeguard.typechecked
@dataclasses.dataclass(frozen=True)
class SymbolicRule:
    value: clingo.ast.AST
    __parsed_string: Optional[str]

    key: InitVar[Any]
    __key = object()

    def __post_init__(self, key: Any):
        validate("key", key, equals=self.__key, help_msg="Use a factory method")
        validate("type", self.value.ast_type, equals=clingo.ast.ASTType.Rule)

    @staticmethod
    def parse(string: str) -> "SymbolicRule":
        program = Parser.parse_program(string)
        validate("one rule", program, length=1,
                 help_msg=f"Unexpected sequence of {len(program)} rules in {utils.one_line(string)}")
        return SymbolicRule(program[0], utils.extract_parsed_string(string, program[0].location),
                            key=SymbolicRule.__key)

    def __str__(self):
        return str(self.value) if self.__parsed_string is None else self.__parsed_string


@typeguard.typechecked
@dataclasses.dataclass(frozen=True, order=True)
class Model:
    key: dataclasses.InitVar[Any]
    value: tuple[GroundAtom | int | str, ...]

    __key = object()

    class NoModelError(ValueError):
        def __init__(self, *args):
            super().__init__("no stable model", *args)

    class MultipleModelsError(ValueError):
        def __init__(self, *args):
            super().__init__("more than one stable model", *args)

    @staticmethod
    def empty():
        return Model(key=Model.__key, value=())

    @staticmethod
    def of_control(control: clingo.Control) -> "Model":
        def on_model(model):
            if on_model.cost is not None and on_model.cost <= model.cost:
                on_model.exception = True
            on_model.cost = model.cost
            on_model.res = Model.of_elements(model.symbols(shown=True))
        on_model.cost = None
        on_model.res = None
        on_model.exception = False

        control.solve(on_model=on_model)
        if on_model.res is None:
            raise Model.NoModelError
        if on_model.exception:
            raise Model.MultipleModelsError
        return on_model.res

    @staticmethod
    def of_program(*args: str | Iterable[str]) -> "Model":
        program = []
        for arg in args:
            if type(arg) is str:
                program.append(arg)
            else:
                program.extend(arg)
        control = clingo.Control()
        control.add("base", [], '\n'.join(program))
        control.ground([("base", [])])
        return Model.of_control(control)

    @staticmethod
    def of_atoms(*args: Union[str, clingo.Symbol, GroundAtom,
                              Iterable[Union[str, clingo.Symbol, GroundAtom]]]) -> "Model":
        res = Model.of_elements(*args)
        validate("only atoms", res.contains_only_ground_atoms, equals=True,
                 help_msg="Use Model.of_elements() to create a model with numbers and strings")
        return res

    @staticmethod
    def of_elements(*args: Union[int, str, clingo.Symbol, GroundAtom,
                    Iterable[Union[int, str, clingo.Symbol, GroundAtom]]]) -> "Model":
        def build(atom):
            if type(atom) in [GroundAtom, int]:
                return atom
            if type(atom) is clingo.Symbol:
                if atom.type == clingo.SymbolType.Number:
                    return atom.number
                if atom.type == clingo.SymbolType.String:
                    return atom.string
                return GroundAtom(atom)
            if type(atom) is str:
                try:
                    return GroundAtom.parse(atom)
                except ValidationError:
                    if atom[0] == '"' == atom[-1]:
                        return Parser.parse_ground_term(atom).string
                    return Parser.parse_ground_term(f'"{atom}"').string
            return None

        flattened = []
        for element in args:
            built_element = build(element)
            if built_element is not None:
                flattened.append(built_element)
            else:
                flattened.extend(build(atom) for atom in element)
        return Model(
            key=Model.__key,
            value=
            tuple(sorted(x for x in flattened if type(x) is int)) +
            tuple(sorted(x for x in flattened if type(x) is str)) +
            tuple(sorted(x for x in flattened if type(x) is GroundAtom))
        )

    def __post_init__(self, key: Any):
        validate("create key", key, equals=self.__key, help_msg="Use a factory method.")

    def __str__(self):
        return ' '.join(str(x) for x in self.value)

    def __len__(self):
        return len(self.value)

    def __getitem__(self, item):
        return self.value[item]

    def __iter__(self):
        return self.value.__iter__()

    @cached_property
    def contains_only_ground_atoms(self) -> bool:
        return all(type(element) == GroundAtom for element in self)

    @property
    def as_facts(self) -> str:
        def build(element):
            if type(element) is int:
                return f"__number({element})."
            if type(element) is str:
                return f"__string(\"{element}\")."
            return f"{element}."
        return '\n'.join(build(element) for element in self)

    def drop(self, predicate: Optional[Predicate] = None, numbers: bool = False, strings: bool = False) -> "Model":
        def when(element):
            if type(element) is GroundAtom:
                return predicate is None or not predicate.match(element.predicate)
            if type(element) is int:
                return not numbers
            assert type(element) is str
            return not strings

        return self.filter(when)

    def filter(self, when: Callable[[GroundAtom], bool]) -> "Model":
        return Model(key=self.__key, value=tuple(atom for atom in self if when(atom)))

    def map(self, fun: Callable[[GroundAtom], GroundAtom]) -> 'Model':
        return Model(key=self.__key, value=tuple(sorted(fun(atom) for atom in self)))

    def rename(self, predicate: Predicate, new_name: Predicate) -> "Model":
        validate("same arity", predicate.arity == new_name.arity, equals=True,
                 help_msg="Predicates must have the same arity")
        return self.map(lambda atom: atom if not predicate.match(atom.predicate) else GroundAtom(
            clingo.Function(new_name.name, atom.arguments)
        ))

    def substitute(self, predicate: Predicate, argument: int, term: clingo.Symbol) -> "Model":
        validate("argument", argument, min_value=1, max_value=predicate.arity, help_msg="Arguments are indexed from 1")

        def mapping(atom: GroundAtom) -> GroundAtom:
            if not predicate.match(atom.predicate):
                return atom
            return GroundAtom(clingo.Function(
                atom.predicate_name,
                [arg if index != argument else term for index, arg in enumerate(atom.arguments, start=1)]
            ))
        return self.map(mapping)

    def project(self, predicate: Predicate, argument: int) -> "Model":
        validate("argument", argument, min_value=1, max_value=predicate.arity, help_msg="Arguments are indexed from 1")

        def mapping(atom: GroundAtom) -> GroundAtom:
            if not predicate.match(atom.predicate):
                return atom
            return GroundAtom(clingo.Function(
                atom.predicate_name,
                [arg for index, arg in enumerate(atom.arguments, start=1) if index != argument]
            ))
        return self.map(mapping)

    @property
    def block_up(self) -> str:
        return ":- " + ", ".join([f"{atom}" for atom in self]) + '.'