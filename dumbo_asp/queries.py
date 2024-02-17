import base64
import json
import re
import subprocess
import webbrowser
import zlib
from pathlib import Path
from typing import Final, Iterable, Sequence

import clingo
import igraph
import typeguard
from clingox.reify import reify_program
from dumbo_utils.primitives import PositiveIntegerOrUnbounded
from dumbo_utils.url import compress_object_for_url
from dumbo_utils.validation import validate

from dumbo_asp import utils
from dumbo_asp.primitives.atoms import GroundAtom, SymbolicAtom
from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.predicates import Predicate
from dumbo_asp.primitives.programs import SymbolicProgram
from dumbo_asp.primitives.rules import SymbolicRule
from dumbo_asp.primitives.terms import SymbolicTerm


@typeguard.typechecked
def compute_minimal_unsatisfiable_subsets(
        program: SymbolicProgram,
        up_to: PositiveIntegerOrUnbounded = PositiveIntegerOrUnbounded.of(1),
        *,
        over_the_ground_program: bool = False,
        clingo_path: Path = Path("clingo"),
        wasp: Path = Path("wasp"),
) -> list[SymbolicProgram]:
    predicate: Final = f"__mus__"
    if over_the_ground_program:
        rules = [
            SymbolicRule.parse(f"__constant{predicate}({';'.join(str(term) for term in program.herbrand_universe)}).")
        ]
        for index, rule in enumerate(program, start=1):
            terms = ','.join([str(index), *rule.global_safe_variables])
            rules.append(rule.with_extended_body(SymbolicAtom.parse(f"{predicate}({terms})")))
            variables = '; '.join(f"__constant{predicate}({variable})" for variable in rule.global_safe_variables)
            rules.append(SymbolicRule.parse(f"{{{predicate}({terms})}} :- {variables}."))
        mus_program = SymbolicProgram.of(rules)
    else:
        mus_program = SymbolicProgram.of(
            *(rule.with_extended_body(SymbolicAtom.parse(f"{predicate}({index})"))
              for index, rule in enumerate(program, start=1)),
            SymbolicRule.parse(
                f"{{{predicate}(1..{len(program)})}}."
            ),
        )
    # print(mus_program)
    res = subprocess.run(
        ["bash", "-c",
         f"{clingo_path} --output=smodels | {wasp} --silent --mus={predicate} -n {up_to if up_to.is_int else 0}"],
        input=str(mus_program).encode(),
        capture_output=True,
    )
    validate("exit code", res.returncode, equals=0, help_msg="Computation failed")
    lines = res.stdout.decode().split('\n')
    muses = [Model.of_atoms(line.split()[2:]) for line in lines if line]
    if not over_the_ground_program:
        return [SymbolicProgram.of(program[atom.arguments[0].number - 1] for atom in mus) for mus in muses]
    res = []
    for mus in muses:
        rules = []
        for atom in mus:
            rule = program[atom.arguments[0].number - 1]
            rules.append(rule.apply_variable_substitution(**{
                variable: SymbolicTerm.parse(str(atom.arguments[index]))
                for index, variable in enumerate(rule.global_safe_variables, start=1)
            }))
        res.append(SymbolicProgram.of(rules))
    return res


@typeguard.typechecked
def enumerate_models(
        program: SymbolicProgram, *,
        true_atoms: Iterable[GroundAtom] = (),
        false_atoms: Iterable[GroundAtom] = (),
        unknown_atoms: Iterable[GroundAtom] = (),
        up_to: int = 0,
) -> tuple[Model, ...]:
    """
    Enumerate models of the program that are compatible with the partial assignment.
    Note that the program may be simplified by clingo, so you may want to specify some unknown atoms to prevent
    such simplifications.
    """
    validate("up_to", up_to, min_value=0)

    the_program = Model.of_atoms(
        reify_program(
            Model.of_atoms(true_atoms).as_facts +
            '\n'.join(f":- {atom}." for atom in false_atoms) +
            Model.of_atoms(unknown_atoms).as_choice_rules +
            str(program)
        )
    ).as_facts + META_MODELS

    return __collect_models(the_program, [f"{up_to}"])


@typeguard.typechecked
def enumerate_counter_models(
        program: SymbolicProgram,
        model: Model,
        *,
        up_to: int = 0,
) -> tuple[Model, ...]:
    validate("up_to", up_to, min_value=0)

    the_program = Model.of_atoms(
        reify_program(
            '\n'.join(f"#external {atom}." for atom in model) +
            str(program)
        )
    ).as_facts + META_COUNTER_MODELS + '\n'.join(f"true(L) :- output({atom},B), literal_tuple(B,L)." for atom in model)

    return __collect_models(the_program, [f"{up_to}"])


@typeguard.typechecked
def validate_in_all_models(
        program: SymbolicProgram, *,
        true_atoms: Iterable[GroundAtom] = (),
        false_atoms: Iterable[GroundAtom] = (),
        unknown_atoms: Iterable[GroundAtom] = (),
) -> None:
    the_program = Model.of_atoms(
        reify_program(
            Model.of_atoms(true_atoms, false_atoms, unknown_atoms).as_choice_rules +
            str(program)
        )
    ).as_facts + META_MODELS

    def check(mode: bool, atoms):
        consequences = set(
            at for at in __collect_models(the_program, ["--enum-mode=cautious" if mode else "--enum-mode=brave"])[-1]
        )
        for atom in atoms:
            validate(f"{mode} atom", atom in consequences, equals=mode,
                     help_msg=f"Atom {atom} was expected to be {str(mode).lower()} in all models")

    check(True, true_atoms)
    check(False, false_atoms)


@typeguard.typechecked
def validate_in_all_models_of_the_reduct(
        program: SymbolicProgram, *,
        model: Model,
        true_atoms: Iterable[GroundAtom] = (),
) -> None:
    the_program = Model.of_atoms(
        reify_program(
            '\n'.join(f"#external {atom}." for atom in model) +
            str(program)
        )
    ).as_facts + META_REDUCT_MODELS + '\n'.join(f"true(L) :- output({atom},B), literal_tuple(B,L)." for atom in model)
    consequences = set(
        at for at in __collect_models(the_program, ["--enum-mode=cautious"])[-1]
    )
    for atom in true_atoms:
        validate(f"True atom", atom in consequences, equals=True,
                 help_msg=f"Atom {atom} was expected to be true in all models")


@typeguard.typechecked
def validate_cannot_be_true_in_any_stable_model(
        program: SymbolicProgram,
        atom: GroundAtom,
        *,
        unknown_atoms: Iterable[GroundAtom] = (),
        local_prefix: str = "__",
) -> None:
    false_in_all_models = False
    try:
        validate_in_all_models(program=program, false_atoms=(atom,), unknown_atoms=unknown_atoms)
        false_in_all_models = True
    except ValueError:
        pass
    if false_in_all_models:
        return

    models = enumerate_models(program, true_atoms=(atom,), unknown_atoms=unknown_atoms)
    for model in models:
        the_program = SymbolicProgram.of(
            *program,
            (SymbolicRule.parse(f"{at}.") for at in model if not at.predicate_name.startswith(local_prefix))
        )
        validate("has counter model", enumerate_counter_models(the_program, model, up_to=1), length=1)


@typeguard.typechecked
def validate_cannot_be_extended_to_stable_model(
        program: SymbolicProgram,
        *,
        true_atoms: Iterable[GroundAtom] = (),
        false_atoms: Iterable[GroundAtom] = (),
        unknown_atoms: Iterable[GroundAtom] = (),
        local_prefix: str = "__",
) -> None:
    false_in_all_models = False
    try:
        fail = f"__fail_{utils.uuid()}"
        validate_in_all_models(program=SymbolicProgram.of(
            (
                *program,
                SymbolicRule.parse(f"\n{fail} :- " + '; '.join(
                    [f"{atom}" for atom in true_atoms] + [f"not {atom}" for atom in false_atoms]
                ) + '.')
            )
        ), false_atoms=(GroundAtom.parse(fail),), unknown_atoms=(*true_atoms, *false_atoms, *unknown_atoms))
        false_in_all_models = True
    except ValueError:
        pass
    if false_in_all_models:
        return

    models = enumerate_models(program, true_atoms=true_atoms, false_atoms=false_atoms, unknown_atoms=unknown_atoms)
    for model in models:
        the_program = SymbolicProgram.of(
            *program,
            (SymbolicRule.parse(f"{at}.") for at in model if not at.predicate_name.startswith(local_prefix))
        )
        validate("has counter model", enumerate_counter_models(the_program, model, up_to=1), length=1)


def __collect_models(program: str, options: list[str]) -> tuple[Model, ...]:
    control = clingo.Control(options)
    control.add(program)
    control.ground([("base", [])])
    res = []

    def collect(model):
        res.append(Model.of_atoms(model.symbols(shown=True)))

    control.solve(on_model=collect)
    return tuple(res)


@typeguard.typechecked
def pack_asp_chef_url(recipe: str, the_input: str | Model | Iterable[Model]) -> str:
    if type(the_input) == Model:
        the_input = the_input.as_facts
    elif type(the_input) != str:
        the_input = '§'.join(model.as_facts for model in the_input)
    url = recipe.replace("/#", "/open#", 1)
    url = url.replace(r"#.*;", "#", 1)
    url = url.replace("#", "#" + compress_object_for_url({"input": the_input}, suffix="") + ";", 1)
    return url


@typeguard.typechecked
def open_graph_in_xasp_navigator(graph_model: Model, *, with_chopped_body=False,
                                 with_backward_search=False, backward_search_symbols=(';', ',', ' :-', ':-')):
    reason_map: Final = {
        "true": {
            "assumption": "true assumption",
            "support": "support",
            "constraint": "required true to falsify body",
            "last support": "required true to satisfy body of last supporting rule",
        },
        "false": {
            "assumption": "false assumption",
            "lack of support": "lack of support",
            "choice": "required false to satisfy choice rule upper bound",
            "head upper bound": "required false to satisfy choice rule upper bound",
            "constraint": "required false to falsify body",
            "last support": "required false to satisfy body of last supporting rule",
        },
    }

    graph = igraph.Graph(directed=True)

    atom_to_rule = {}
    for node in graph_model.filter(when=lambda atom: atom.predicate_name == "node"):
        name = node.arguments[0].string
        value = node.arguments[1].name
        reason = node.arguments[2].arguments[0].name.replace('_', ' ')
        atom_to_rule[name] = ""
        if len(node.arguments[2].arguments) >= 2:
            atom_to_rule[name] = node.arguments[2].arguments[1].string
            if with_chopped_body:
                atom_to_rule[name] = str(SymbolicRule.parse(node.arguments[2].arguments[1].string).with_chopped_body(
                    with_backward_search=with_backward_search, backward_search_symbols=backward_search_symbols
                ))
        graph.add_vertex(name, label=f"{name}\n{reason_map[value][reason]}")

    for link in graph_model.filter(when=lambda atom: atom.predicate_name == "link"):
        source = link.arguments[0].string
        target = link.arguments[1].string
        label = str(
            SymbolicRule.parse(link.arguments[2].string).with_chopped_body(
                with_backward_search=with_backward_search, backward_search_symbols=backward_search_symbols
            )
        ) if len(link.arguments) > 2 else atom_to_rule[source]
        graph.add_edge(source, target, label=label)

    # layout = graph.layout_sugiyama()
    layout = graph.layout_reingold_tilford()
    res = {
        "nodes": [
            {
                "id": index,
                "label": node.attributes()["label"],
                "x": layout.coords[index][0],
                "y": layout.coords[index][1],
            }
            for index, node in enumerate(graph.vs)
        ],
        "links": [
            {
                "source": link.tuple[0],
                "target": link.tuple[1],
                "label": link.attributes()["label"],
            }
            for link in graph.es
        ],
    }
    url = "https://xasp-navigator.netlify.app/#"
    # url = "http://localhost:5173/#"
    json_dump = json.dumps(res, separators=(',', ':')).encode()
    url += base64.b64encode(zlib.compress(json_dump)).decode() + '%21'
    webbrowser.open(url, new=0, autoraise=True)


def __explanation_graph_trim_selectors(
    control: clingo.Control,
    selectors: list[GroundAtom],
    selector_to_literal: dict[GroundAtom, int],
) -> None:
    def on_core(core):
        on_core.res = core

    on_core.res = []
    control.solve(
        assumptions=[selector_to_literal[selector] for selector in selectors]
        + [-1],
        on_core=on_core,
    )
    if on_core.res is not None and (len(on_core.res) == 0 or on_core.res[-1] != -1):
        while selectors and selector_to_literal[selectors[-1]] not in on_core.res:
            selectors.pop()
    else:
        selectors.clear()


def __explanation_graph_pus_program(
        program: SymbolicProgram,
        answer_set: Model,
        herbrand_base: Iterable[GroundAtom],
        query: Model,
        pus_predicate: str,
):
    query_atoms = set(query)
    answer_set_atoms = set(answer_set)
    query_literals = []
    constraints = []
    for atom in herbrand_base:
        if atom in query_atoms:
            query_literals.append(str(atom) if atom in answer_set_atoms else f"not {atom}")
            query_atoms.remove(atom)
        else:
            constraints.append(SymbolicRule.parse(
                f":- not {atom} %* assumption *%; {pus_predicate}(answer_set,{len(constraints)})." if atom in answer_set_atoms else
                f":-     {atom} %* assumption *%; {pus_predicate}(answer_set,{len(constraints)})."
            ))
    for atom in query_atoms:
        query_literals.append(f"not {atom}")

    false: Final = Predicate.false().name
    return SymbolicProgram.of(
        *(rule.with_extended_body(SymbolicAtom.parse(f"{pus_predicate}(program,{index})"))
          for index, rule in enumerate(program)),
        *constraints,
        SymbolicRule.parse(f"{pus_predicate} :- {', '.join(query_literals)}."),
        SymbolicRule.parse(
            "{"
            + f"{pus_predicate}(program,0..{len(program) - 1})"
            + (
                f"; {pus_predicate}(answer_set,0..{len(constraints) - 1})"
                if len(constraints) > 0
                else ""
            )
            + "}."
        ),
        # something from to_zero_simplification_version() to make the grounder less intelligent
        SymbolicRule.parse('{' + '; '.join(str(atom) for atom in herbrand_base) + f"}} :- {false}."),
        SymbolicRule.parse(f"{{{false}}}."),
        SymbolicRule.parse(f":- {false}."),
    )


def __explanation_graph_expanded_program(
        pus_program: SymbolicProgram,
        herbrand_base: Iterable[GroundAtom],
        all_selectors: Iterable[GroundAtom],
        pus_predicate: str,
):
    control = clingo.Control(["--supp-models", "--no-ufs-check", "--sat-prepro=no", "--eq=0", "--no-backprop"])
    control.add(str(pus_program))
    control.ground([("base", [])])
    selector_to_literal = {}
    literal_to_selector = {}
    for atom in control.symbolic_atoms.by_signature(pus_predicate, 2):
        selector = GroundAtom.parse(str(atom.symbol))
        selector_to_literal[selector] = atom.literal
        literal_to_selector[atom.literal] = selector

    class Stopper(clingo.Propagator):
        def init(self, init):
            program_literal = init.symbolic_atoms[clingo.Function(pus_predicate)].literal
            init.add_watch(init.solver_literal(program_literal))

        def propagate(self, ctl: clingo.PropagateControl, changes: Sequence[int]) -> None:
            ctl.add_clause(clause=[-changes[0]], tag=True)

    control.register_propagator(Stopper())
    selectors = list(all_selectors)
    __explanation_graph_trim_selectors(
        control=control,
        selectors=selectors,
        selector_to_literal=selector_to_literal,
    )

    required_selectors = 0
    while required_selectors < len(selectors):
        required_selectors += 1
        selectors.insert(
            0, selectors.pop()
        )  # last selector is required... move it ahead
        __explanation_graph_trim_selectors(
            control=control,
            selectors=selectors,
            selector_to_literal=selector_to_literal,
        )

    herbrand_base = Model.of_atoms(*herbrand_base, *all_selectors)
    return SymbolicProgram.of(
        *(rule for index, rule in enumerate(pus_program) if index < len(pus_program) - 3),  # last three rules are from to_zero_simplification_version()
        *(SymbolicRule.parse(f"{atom}.") for atom in selectors)
    ).expand_global_and_local_variables(herbrand_base=herbrand_base)


def explanation_graph(
        program: SymbolicProgram,
        answer_set: Model,
        herbrand_base: Iterable[GroundAtom],
        query: Model,
) -> Model:
    pus_predicate: Final = f"__pus__"
    pus_program = __explanation_graph_pus_program(program, answer_set, herbrand_base, query, pus_predicate)
    selectors = [
        GroundAtom.parse(f"{pus_predicate}(program,{index})")
        for index in range(len(program))
    ] + [
        GroundAtom.parse(f"{pus_predicate}(answer_set,{index})")
        for index in range(len(pus_program) - len(program) - 5)
        # the extended program contains modified original rules, 5 extra rules, and constraints for the answer set
    ]
    expanded_program = __explanation_graph_expanded_program(pus_program, herbrand_base, selectors, pus_predicate)

    serialization = Model.of_atoms(
        *expanded_program.serialize(base64_encode=False),
        *(GroundAtom.parse(f'query({clingo.String(str(query_atom))})') for query_atom in query),
    )

    seen = set()
    sequence = []
    terminate = []

    def collect(model):
        for at in model.symbols(shown=True):
            atom = GroundAtom(at)
            if atom.predicate_name in ["assign", "constraint"]:
                key = (atom.predicate_name, atom.arguments[0])
            elif atom.predicate_name == "cannot_support":
                key = (atom.predicate_name, atom.arguments[0], atom.arguments[1])
            elif atom.predicate_name == "done":
                terminate.append(True)
                continue
            else:
                assert False
            if key not in seen:
                seen.add(key)
                sequence.append(atom)

    def search(meta, callback):
        control = clingo.Control(["1", "--solve-limit=1"])
        control.add("base", [], meta)
        control.add("base", [], serialization.as_facts)
        control.add("base", [], '\n'.join(f"{atom}." for atom in sequence))
        control.ground([("base", [])])
        callback(control)

    while not terminate:
        previous_len = len(sequence)
        search(META_DERIVATION_SEQUENCE, lambda control: control.solve(on_model=collect))
        assert len(sequence) > previous_len

    res = []
    pattern = re.compile(r'__pus__\(answer_set,\d+\)\.$')

    def rewrite_links(model):
        for at in model.symbols(shown=True):
            atom = GroundAtom(at)
            if atom.predicate_name == "node":
                reason = atom.arguments[2]
                if len(reason.arguments) > 1 and re.search(pattern, reason.arguments[1].string):
                    atom = GroundAtom.parse(f"node({atom.arguments[0]},{atom.arguments[1]},(assumption,))")
            res.append(atom)

    search(META_EXPLANATION_GRAPH, lambda control: control.solve(on_model=rewrite_links))
    res = Model.of_atoms(res)
    return res


META_MODELS = """
atom( A ) :- atom_tuple(_,A).
atom(|L|) :-          literal_tuple(_,L).
atom(|L|) :- weighted_literal_tuple(_,L).

{ hold(A) : atom(A) }.

conjunction(B) :- literal_tuple(B),
        hold(L) : literal_tuple(B, L), L > 0;
    not hold(L) : literal_tuple(B,-L), L > 0.

body(normal(B)) :- rule(_,normal(B)), conjunction(B).
body(sum(B,G))  :- rule(_,sum(B,G)),
    #sum { W,L :     hold(L), weighted_literal_tuple(B, L,W), L > 0 ;
           W,L : not hold(L), weighted_literal_tuple(B,-L,W), L > 0 } >= G.

  hold(A) : atom_tuple(H,A)   :- rule(disjunction(H),B), body(B).
{ hold(A) : atom_tuple(H,A) } :- rule(choice(H),B), body(B).

#show.
#show T : output(T,B), conjunction(B).

% avoid warnings
atom_tuple(0,0) :- #false.
conjunction(0) :- #false.
literal_tuple(0) :- #false.
literal_tuple(0,0) :- #false.
weighted_literal_tuple(0,0) :- #false.
weighted_literal_tuple(0,0,0) :- #false.
rule(0,0) :- #false.
"""

META_COUNTER_MODELS = """
atom( A ) :- atom_tuple(_,A).
atom(|L|) :-          literal_tuple(_,L).
atom(|L|) :- weighted_literal_tuple(_,L).

{hold(A)} :- atom(A), true(A).
:- hold(A) : true(A).

conjunction(B) :- literal_tuple(B),
        hold(L) : literal_tuple(B, L), L > 0;
    not true(L) : literal_tuple(B,-L), L > 0.

body(normal(B)) :- rule(_,normal(B)), conjunction(B).
body(sum(B,G))  :- rule(_,sum(B,G)),
    #sum { W,L :     hold(L), weighted_literal_tuple(B, L,W), L > 0 ;
           W,L : not true(L), weighted_literal_tuple(B,-L,W), L > 0 } >= G.

  hold(A) : atom_tuple(H,A)   :- rule(disjunction(H),B), body(B).
{ hold(A) : atom_tuple(H,A) } :- rule(     choice(H),B), body(B).

#show.
#show T : output(T,B), conjunction(B).

% avoid warnings
atom_tuple(0,0) :- #false.
conjunction(0) :- #false.
literal_tuple(0) :- #false.
literal_tuple(0,0) :- #false.
weighted_literal_tuple(0,0) :- #false.
weighted_literal_tuple(0,0,0) :- #false.
rule(0,0) :- #false.
"""

META_REDUCT_MODELS = """
atom( A ) :- atom_tuple(_,A).
atom(|L|) :-          literal_tuple(_,L).
atom(|L|) :- weighted_literal_tuple(_,L).

{hold(A)} :- atom(A), true(A).
:- not hold(A), true(A).

conjunction(B) :- literal_tuple(B),
        hold(L) : literal_tuple(B, L), L > 0;
    not true(L) : literal_tuple(B,-L), L > 0.

body(normal(B)) :- rule(_,normal(B)), conjunction(B).
body(sum(B,G))  :- rule(_,sum(B,G)),
    #sum { W,L :     hold(L), weighted_literal_tuple(B, L,W), L > 0 ;
           W,L : not true(L), weighted_literal_tuple(B,-L,W), L > 0 } >= G.

  hold(A) : atom_tuple(H,A)   :- rule(disjunction(H),B), body(B).
{ hold(A) : atom_tuple(H,A) } :- rule(     choice(H),B), body(B).

#show.
#show T : output(T,B), conjunction(B).

% avoid warnings
atom_tuple(0,0) :- #false.
conjunction(0) :- #false.
literal_tuple(0) :- #false.
literal_tuple(0,0) :- #false.
weighted_literal_tuple(0,0) :- #false.
weighted_literal_tuple(0,0,0) :- #false.
rule(0,0) :- #false.
"""

META_HT_MODELS = """
#const option=1.

atom( A ) :- atom_tuple(_,A).
atom(|L|) :-          literal_tuple(_,L).
atom(|L|) :- weighted_literal_tuple(_,L).

model(h). model(t).

{ hold(A,h) } :- atom(A),    option = 1.
{ hold(A,t) } :- atom(A).
:- hold(L,h), not hold(L,t).

conjunction(B,M) :- model(M), literal_tuple(B),
        hold(L,M) : literal_tuple(B, L), L > 0;
    not hold(L,t) : literal_tuple(B,-L), L > 0.

body(normal(B),M) :- rule(_,normal(B)), conjunction(B,M).
body(sum(B,G),M)  :- model(M), rule(_,sum(B,G)),
    #sum { W,L :     hold(L,M), weighted_literal_tuple(B, L,W), L > 0 ;
           W,L : not hold(L,t), weighted_literal_tuple(B,-L,W), L > 0 } >= G.

               hold(A,M) :  atom_tuple(H,A)   :- rule(disjunction(H),B), body(B,M).
hold(A,M); not hold(A,t) :- atom_tuple(H,A),     rule(     choice(H),B), body(B,M).

#show.
#show (T,M) : output(T,B), conjunction(B,M).

% avoid warnings
atom_tuple(0,0) :- #false.
conjunction(0) :- #false.
literal_tuple(0) :- #false.
literal_tuple(0,0) :- #false.
weighted_literal_tuple(0,0) :- #false.
weighted_literal_tuple(0,0,0) :- #false.
rule(0,0) :- #false.
"""

META_DERIVATION_SEQUENCE = """
head_bounds(Rule, LowerBound, UpperBound) :-
  rule(Rule), choice(Rule, LowerBound, UpperBound).
head_bounds(Rule, 1, Size) :-
  rule(Rule), not choice(Rule,_,_);
  Size = #count{HeadAtom : head(Rule, HeadAtom)}.

atom(Atom) :- head(Rule, Atom).
atom(Atom) :- pos_body(Rule, Atom).
atom(Atom) :- neg_body(Rule, Atom).

assign'(HeadAtom, true, (support, Rule)) :-
  rule(Rule), head_bounds(Rule, LowerBound, UpperBound);
  head(Rule, HeadAtom), #sum{1, Atom : head(Rule, Atom); -1, Atom : head(Rule, Atom), assign(Atom, false, _)} = LowerBound;
  assign(BodyAtom, true, _) : pos_body(Rule, BodyAtom);
  assign(BodyAtom, false, _) : neg_body(Rule, BodyAtom).

assign'(HeadAtom, false, (head_upper_bound, Rule)) :-
  rule(Rule), head_bounds(Rule, LowerBound, UpperBound);
  head(Rule, HeadAtom), #count{Atom : head(Rule, Atom), assign(Atom, true, _), Atom != HeadAtom} = UpperBound;
  assign(BodyAtom, true, _) : pos_body(Rule, BodyAtom);
  assign(BodyAtom, false, _) : neg_body(Rule, BodyAtom).

cannot_support(Rule, HeadAtom, OtherHeadAtom) :-
  rule(Rule), head(Rule, HeadAtom), not choice(Rule,_,_);
  head(Rule, OtherHeadAtom), OtherHeadAtom != HeadAtom, assign(OtherHeadAtom, true, _).
cannot_support(Rule, HeadAtom, BodyAtom) :-
  rule(Rule), head(Rule, HeadAtom);
  pos_body(Rule, BodyAtom), assign(BodyAtom, false, _).
cannot_support(Rule, HeadAtom, BodyAtom) :-
  rule(Rule), head(Rule, HeadAtom);
  neg_body(Rule, BodyAtom), assign(BodyAtom, true, _).

assign'(Atom, false, (lack_of_support,)) :-
  atom(Atom);
  cannot_support(Rule, Atom, _) : head(Rule, Atom).

last_support(Rule, Atom) :-
  assign(Atom, true, _), head(Rule, Atom);
  cannot_support(Rule', Atom, _) : head(Rule', Atom), Rule' != Rule.
  
assign'(BodyAtom, true, (last_support, Rule, Atom)) :-
  last_support(Rule, Atom);
  pos_body(Rule, BodyAtom).
assign'(BodyAtom, false, (last_support, Rule, Atom)) :-
  last_support(Rule, Atom);
  neg_body(Rule, BodyAtom).
assign'(HeadAtom, false, (last_support, Rule, Atom)) :-
  last_support(Rule, Atom), not choice(Rule, _, _);
  head(Rule, HeadAtom), HeadAtom != Atom.

constraint(Rule, upper_bound) :-
  rule(Rule), head_bounds(Rule, LowerBound, UpperBound);
  #count{Atom : head(Rule, Atom), assign(Atom, true, _)} > UpperBound.
constraint(Rule, lower_bound) :-
  rule(Rule), head_bounds(Rule, LowerBound, UpperBound);
  #sum{1, Atom : head(Rule, Atom); -1, Atom : head(Rule, Atom), assign(Atom, false, _)} < LowerBound.

assign'(Atom, false, (constraint, Rule, Bound)) :-
  constraint(Rule, Bound), pos_body(Rule, Atom);
  assign(Atom', true, _) : pos_body(Rule, Atom'), Atom' != Atom;
  assign(Atom', false, _) : neg_body(Rule,Atom').
assign'(Atom, true, (constraint, Rule, Bound)) :-
  constraint(Rule, Bound), neg_body(Rule, Atom);
  assign(Atom', true, _) : pos_body(Rule, Atom');
  assign(Atom', false, _) : neg_body(Rule,Atom'), Atom' != Atom.
  
#show.
#show assign(Atom, Value, Reason) : assign'(Atom, Value, Reason), not assign(Atom, _, _).
#show cannot_support/3.
#show constraint/2.
#show done : #count{Atom : query(Atom), not assign'(Atom, _, _)} == 0.

% avoid warnings
head(0,0) :- #false.
pos_body(0,0) :- #false.
neg_body(0,0) :- #false.
assign(0,false,0) :- #false.
assign(0,true,0) :- #false.
"""

META_EXPLANATION_GRAPH = """
link(Atom, BodyAtom, Rule) :-
  assign(Atom, _, (support, Rule));
  pos_body(Rule, BodyAtom).
link(Atom, BodyAtom, Rule) :-
  assign(Atom, _, (support, Rule));
  neg_body(Rule, BodyAtom).
link(Atom, FalseHeadAtom, Rule) :-
  assign(Atom, _, (support, Rule));
  head(Rule, FalseHeadAtom), assign(FalseHeadAtom, false, _).

link(Atom, BodyAtom, Rule) :-
  assign(Atom, _, (head_upper_bound, Rule));
  pos_body(Rule, BodyAtom).
link(Atom, BodyAtom, Rule) :-
  assign(Atom, _, (head_upper_bound, Rule));
  neg_body(Rule, BodyAtom).
link(Atom, TrueHeadAtom, Rule) :-
  assign(Atom, _, (head_upper_bound, Rule));
  head(Rule, TrueHeadAtom), assign(TrueHeadAtom, true, _).

link(Atom, BecauseOfAtom, Rule) :-
  assign(Atom, _, (lack_of_support,));
  head(Rule, Atom), cannot_support(Rule, Atom, BecauseOfAtom).

link(Atom, AtomToSupport, Rule) :-
  assign(Atom, _, (last_support, Rule, AtomToSupport)).
link(Atom, BecauseOfAtom, Rule) :-
  assign(Atom, _, (last_support, Rule, AtomToSupport));
  cannot_support(Rule, AtomToSupport, BecauseOfAtom).

link(Atom, TrueHeadAtom, Rule) :-
  assign(Atom, _, (constraint, Rule, upper_bound));
  head(Rule, TrueHeadAtom), assign(TrueHeadAtom, true, _).
link(Atom, FalseHeadAtom, Rule) :-
  assign(Atom, _, (constraint, Rule, lower_bound));
  head(Rule, FalseHeadAtom), assign(FalseHeadAtom, false, _).
link(Atom, BodyAtom, Rule) :-
  assign(Atom, _, (constraint, Rule, _));
  pos_body(Rule, BodyAtom), BodyAtom != Atom.
link(Atom, BodyAtom, Rule) :-
  assign(Atom, _, (constraint, Rule, _));
  neg_body(Rule, BodyAtom), BodyAtom != Atom.


reach(Atom) :- query(Atom).
reach(Atom') :- reach(Atom), link(Atom, Atom', _), not hide(Atom').
hide(Atom) :- head(Rule, Atom); not pos_body(Rule,_); not neg_body(Rule,_).

#show.
#show node(X,V,R) : assign(X,V,R), reach(X).
#show link(X,Y,R) : link(X,Y,R), reach(X), reach(Y).
#show link(X,X,R) : assign(X,V,(I,R)), reach(X), I != support, not reach(Y) : link(X,Y,_).
#show link(X,X,R) : assign(X,V,(constraint,R,_)), reach(X), not reach(Y) : link(X,Y,_).
#show link(X,X,"__in_no_head__ :- __pus__.") : assign(X,V,(lack_of_support,)), reach(X), not reach(Y) : link(X,Y,_).

% avoid warnings
head(0,0) :- #false.
pos_body(0,0) :- #false.
neg_body(0,0) :- #false.
assign(0,0,0) :- #false.
constraint(0,0) :- #false.
cannot_support(0,0,0) :- #false.
"""