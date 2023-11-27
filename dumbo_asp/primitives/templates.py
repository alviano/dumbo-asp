import dataclasses
from dataclasses import InitVar
from pathlib import Path

import clingo
import clingo.ast
import typeguard
from dumbo_utils.primitives import PrivateKey
from dumbo_utils.validation import validate

from dumbo_asp import utils
from dumbo_asp.primitives.predicates import Predicate
from dumbo_asp.primitives.programs import SymbolicProgram


@typeguard.typechecked
@dataclasses.dataclass(frozen=True)
class Template:
    @dataclasses.dataclass(frozen=True)
    class Name:
        value: str
        key: InitVar[PrivateKey]
        __key = PrivateKey()

        def __post_init__(self, key: PrivateKey):
            self.__key.validate(key)

        @staticmethod
        def parse(name: str) -> "Template.Name":
            term = clingo.String(name)
            return Template.Name(
                value=term.string,
                key=Template.Name.__key,
            )

        def __str__(self):
            return self.value

    name: "Template.Name"
    program: SymbolicProgram
    __static_uuid: str = dataclasses.field(default_factory=lambda: utils.uuid(), init=False)

    __core_templates = None
    __core_templates_directory = Path(__file__).parent.parent / "templates"
    __core_templates_files = [f"{name}.template.asp" for name in [
        "dumbo",
        "binary_relations",
        "sets",
        "graphs",
    ]]

    @staticmethod
    def __init_core_templates():
        if Template.__core_templates is not None:
            return
        Template.__core_templates = {}

        def register(template: str):
            name, program = template.strip().split('\n', maxsplit=1)
            name = f"@dumbo/{name}"
            assert name not in Template.__core_templates
            Template.__core_templates[name] = Template(
                Template.Name.parse(name),
                Template.expand_program(SymbolicProgram.parse(program.strip())),
            )

        def register_all(templates: str, *, sep="----"):
            for template in templates.strip().split(sep):
                if template:
                    lines = [line[4:] if index > 0 and len(line) >= 4 else line
                             for index, line in enumerate(template.strip().split('\n'))]
                    register('\n'.join(lines))

        for arity in range(10):
            terms = ','.join('X' + str(i) for i in range(arity))
            register(f"""
exact copy (arity {arity})
output({terms}) :- input({terms}).
:- output({terms}), not input({terms}).
            """)
            if arity > 0:
                register(f"collect arguments (arity {arity})\n" +
                         '\n'.join(f"output(X{index}) :- input({terms})." for index in range(arity)))
                for other_arity in range(arity):
                    register(f"collect argument {other_arity + 1} of {arity}\n" +
                             f"output(X{other_arity}) :- input({terms}).")

        for file in Template.__core_templates_files:
            with open(Template.__core_templates_directory / file) as templates_file:
                Template.expand_program(SymbolicProgram.parse(templates_file.read()), register_templates=True)

    @staticmethod
    def core_template(name: str) -> "Template":
        Template.__init_core_templates()
        return Template.__core_templates[name]

    @staticmethod
    def is_core_template(name: str) -> bool:
        Template.__init_core_templates()
        return name in Template.__core_templates

    @staticmethod
    def core_templates() -> int:
        Template.__init_core_templates()
        return len(Template.__core_templates)

    @staticmethod
    def core_templates_as_parsable_string() -> str:
        Template.__init_core_templates()
        res = []
        for key, value in Template.__core_templates.items():
            res.append(str(value))
        return '\n'.join(res)

    @staticmethod
    def expand_program(program: SymbolicProgram, *, limit: int = 100_000, register_templates: bool = False,
                       trace: bool = False) -> SymbolicProgram:
        Template.__init_core_templates()
        templates = {}
        template_under_read = None
        res = []
        for rule in program:
            validate("avoid blow up", len(res) + (len(template_under_read[1]) if template_under_read else 0),
                     max_value=limit,
                     help_msg=f"The expansion takes more than {limit} rules. "
                              f"If you trust the code, try again by increasing the limit.")
            if rule.disabled or not rule.is_normal_rule:
                if template_under_read is not None:
                    template_under_read[1].append(rule)
                else:
                    res.append(rule)
            elif rule.head_atom.predicate_name == "__template__":
                validate("empty body", rule.is_fact, equals=True)
                validate("arity 1", rule.head_atom.predicate_arity, equals=1)
                validate("arg#0", rule.head_atom.arguments[0].is_string(), equals=True)
                validate("no nesting", template_under_read is None, equals=True)
                validate("not a core template", Template.is_core_template(rule.head_atom.predicate.name), equals=False)
                validate("not seen", rule.head_atom.predicate.name not in templates, equals=True)
                template_under_read = (rule.head_atom.arguments[0].string_value(), [])
            elif rule.head_atom.predicate_name == "__end__":
                validate("empty body", rule.is_fact, equals=True)
                validate("arity 0", rule.head_atom.predicate_arity, equals=0)
                validate("not in a template", template_under_read)
                if trace:
                    template_under_read[1].append(rule.disable())
                the_template = Template(name=Template.Name.parse(template_under_read[0]),
                                        program=SymbolicProgram.of(template_under_read[1]))
                if register_templates:
                    Template.__core_templates[template_under_read[0]] = the_template
                else:
                    templates[template_under_read[0]] = the_template
                template_under_read = None
            elif rule.head_atom.predicate_name == "__apply_template__":
                validate("empty body", rule.is_fact, equals=True)
                validate("arity >= 1", rule.head_atom.predicate_arity, min_value=1)
                validate("arg#0", rule.head_atom.arguments[0].is_string(), equals=True)
                template_name = rule.head_atom.arguments[0].string_value()
                if Template.is_core_template(template_name):
                    template = Template.core_template(template_name)
                else:
                    validate("known template", template_name in templates, equals=True,
                             help_msg=f"Unknown template: {template_name}")
                    template = templates[template_name]
                mapping = {}
                for argument in rule.head_atom.arguments[1:]:
                    validate("mapping args", argument.is_function(), equals=True)
                    validate("mapping args", argument.function_name, equals='')
                    validate("mapping args", argument.function_arity, equals=2)
                    validate("mapping args", argument.arguments[0].is_function(), equals=True)
                    validate("mapping args", argument.arguments[0].function_arity, equals=0)
                    validate("mapping args", argument.arguments[1].is_function(), equals=True)
                    validate("mapping args", argument.arguments[1].function_arity, equals=0)
                    mapping[argument.arguments[0].function_name] = Predicate.parse(argument.arguments[1].function_name)
                if template_under_read is None:
                    if trace:
                        res.append(rule.disable())
                    res.extend(r for r in template.instantiate(**mapping))
                else:
                    if trace:
                        template_under_read[1].append(rule.disable())
                    template_under_read[1].extend(r for r in template.instantiate(**mapping))
            elif template_under_read is not None:
                template_under_read[1].append(rule)
            else:
                res.append(rule)

        return SymbolicProgram.of(res)

    def __str__(self):
        return f"""__template__("{self.name}").\n{self.program}\n__end__."""

    def __repr__(self):
        return f"""Template(name="{self.name}", program={self.program})"""

    def instantiate(self, **kwargs: Predicate) -> SymbolicProgram:
        Template.__init_core_templates()
        for arg in kwargs:
            validate("kwargs", arg.startswith('__'), equals=False,
                     help_msg="Local predicates cannot be renamed externally.")
        static_uuid = self.__static_uuid
        local_uuid = utils.uuid()
        mapping = {**kwargs}
        for predicate in self.program.predicates:
            if not predicate.name.endswith('__'):
                if predicate.name.startswith('__static_'):
                    mapping[predicate.name] = Predicate.parse(f"{predicate.name[1:]}_{static_uuid}")
                elif predicate.name.startswith('__'):
                    mapping[predicate.name] = Predicate.parse(f"{predicate.name}_{local_uuid}")
        return self.program.apply_predicate_renaming(**mapping)
