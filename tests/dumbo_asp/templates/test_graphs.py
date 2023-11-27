from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.programs import SymbolicProgram
from dumbo_asp.primitives.templates import Template


def test_spanning_tree():
    program = SymbolicProgram.parse("""
link(2,1).  
link(2,3).
__apply_template__("@dumbo/collect arguments (arity 2)", (input, link), (output, node)).
__apply_template__("@dumbo/symmetric closure", (relation, link), (closure, link)).
__apply_template__("@dumbo/spanning tree of undirected graph").
    """)
    program = Template.expand_program(program)
    assert Model.of_program(program).filter(when=lambda atom: atom.predicate_name == "tree") == \
           Model.of_atoms("tree(1,2) tree(2,3)".split())


def test_all_simple_directed_paths():
    program = SymbolicProgram.parse("""
link(1,2).
link(2,3).
link(2,4).
__apply_template__("@dumbo/collect arguments (arity 2)", (input, link), (output, node)).
__apply_template__("@dumbo/all simple directed paths").
    """)
    program = Template.expand_program(program)
    model = Model.of_program(program)
    assert len(model.filter(when=lambda atom: atom.predicate_name == "path")) == 9


def test_all_simple_directed_paths_of_given_max_length():
    program = SymbolicProgram.parse("""
link(1,2).
link(2,3).
link(2,4).
max_length(2).
__apply_template__("@dumbo/collect arguments (arity 2)", (input, link), (output, node)).
__apply_template__("@dumbo/all simple directed paths").
    """)
    program = Template.expand_program(program)
    model = Model.of_program(program)
    assert len(model.filter(when=lambda atom: atom.predicate_name == "path")) == 9


def test_all_simple_directed_paths_of_given_length():
    program = SymbolicProgram.parse("""
link(1,2).
link(2,3).
link(2,4).
length(2).
__apply_template__("@dumbo/collect arguments (arity 2)", (input, link), (output, node)).
__apply_template__("@dumbo/all simple directed paths of given length").
    """)
    program = Template.expand_program(program)
    model = Model.of_program(program)
    assert len(model.filter(when=lambda atom: atom.predicate_name == "path")) == 2
