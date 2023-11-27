import dataclasses
from dataclasses import InitVar
from functools import cached_property
from typing import Callable, Optional, Iterable, Union, Final, Any

import clingo
import clingo.ast
import typeguard
from dumbo_utils.primitives import PrivateKey
from dumbo_utils.validation import validate, ValidationError

from dumbo_asp.primitives.atoms import GroundAtom
from dumbo_asp.primitives.parsers import Parser
from dumbo_asp.primitives.predicates import Predicate
from dumbo_asp.utils import uuid


@typeguard.typechecked
@dataclasses.dataclass(frozen=True, order=True)
class Model:
    value: tuple[GroundAtom | int | str, ...]

    key: InitVar[PrivateKey]
    __key = PrivateKey()

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
    def of_program(*args: Any | Iterable[Any]) -> "Model":
        program = []

        for arg in args:
            if type(arg) is str:
                program.append(str(arg))
            else:
                try:
                    program.extend(str(elem) for elem in arg)
                except TypeError:
                    program.append(str(arg))
        control = clingo.Control()
        control.add('\n'.join(program))
        control.ground([("base", [])])
        return Model.of_control(control)

    @staticmethod
    def of_atoms(*args: Union[str, clingo.Symbol, GroundAtom, Iterable[str | clingo.Symbol | GroundAtom]]) -> "Model":
        res = Model.of_elements(*args)
        validate("only atoms", res.contains_only_ground_atoms, equals=True,
                 help_msg="Use Model.of_elements() to create a model with numbers and strings")
        return res

    @staticmethod
    def of_elements(
            *args: int | str | clingo.Symbol | GroundAtom | Iterable[int | str | clingo.Symbol | GroundAtom]
    ) -> "Model":
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
                for atom in element:
                    built_element = build(atom)
                    validate("is atom", built_element, help_msg=f"Failed to build atom from {element}")
                    flattened.append(built_element)
        return Model(
            key=Model.__key,
            value=
            tuple(sorted(x for x in flattened if type(x) is int)) +
            tuple(sorted(x for x in flattened if type(x) is str)) +
            tuple(sorted(x for x in flattened if type(x) is GroundAtom))
        )

    def __post_init__(self, key: PrivateKey):
        self.__key.validate(key)

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

    @property
    def as_choice_rules(self) -> str:
        def build(element):
            if type(element) is int:
                return f"{{__number({element})}}."
            if type(element) is str:
                return f"{{__string(\"{element}\")}}."
            return f"{{{element}}}."

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

    @cached_property
    def __compute_substitutions_control(self):
        program = self.as_choice_rules
        control = clingo.Control()
        control.add(program)
        control.ground([("base", [])])
        return control

    def compute_substitutions(self, *, arguments: str, number_of_arguments: int,
                              conjunctive_query: str) -> tuple[list[clingo.Symbol], ...]:
        predicate: Final = f"__query_{uuid()}__"
        self.__compute_substitutions_control.add(predicate, [], f"{predicate}({arguments}) :- {conjunctive_query}.")
        self.__compute_substitutions_control.ground([(predicate, [])])
        return tuple(
            atom.symbol.arguments
            for atom in self.__compute_substitutions_control.symbolic_atoms.by_signature(predicate, number_of_arguments)
        )
